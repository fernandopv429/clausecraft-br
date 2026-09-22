# cct_store.py
"""Armazenamento das Convenções Coletivas de Trabalho no PostgreSQL + pgvector.

As CCTs não ficam na mesma coleção da legislação porque a consulta é diferente:
buscar cláusula de CCT é *filtrar* (sindicato, data de vigência, município) e só
depois ordenar por similaridade. Por isso vigência é coluna DATE, não metadado solto.
"""

import re
import unicodedata
from datetime import date

import psycopg

from config import URL_POSTGRES_BRUTA, criar_embeddings, dimensao_embedding

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS cct_documentos (
    id                  BIGSERIAL PRIMARY KEY,
    arquivo             TEXT NOT NULL,
    hash_arquivo        TEXT NOT NULL UNIQUE,
    categoria           TEXT NOT NULL,
    tipo                TEXT,
    titulo              TEXT,
    sindicato_laboral   TEXT,
    sindicato_patronal  TEXT,
    base_territorial    TEXT,
    registro_mte        TEXT,
    vigencia_inicio     DATE,
    vigencia_fim        DATE,
    abrangencia         TEXT DEFAULT 'estadual',
    municipios          TEXT[],
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cct_chunks (
    id              BIGSERIAL PRIMARY KEY,
    documento_id    BIGINT NOT NULL REFERENCES cct_documentos(id) ON DELETE CASCADE,
    ordem           INT NOT NULL,
    clausula_ref    TEXT,
    clausula_titulo TEXT,
    conteudo        TEXT NOT NULL,
    embedding       vector({dim}),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cct_chunks_documento ON cct_chunks (documento_id);
CREATE INDEX IF NOT EXISTS idx_cct_doc_vigencia ON cct_documentos (categoria, vigencia_inicio, vigencia_fim);
"""


def conectar():
    return psycopg.connect(URL_POSTGRES_BRUTA, connect_timeout=30)


def criar_schema():
    """Cria tabelas e índices (idempotente)."""
    with conectar() as conexao, conexao.cursor() as cursor:
        cursor.execute(SCHEMA.format(dim=dimensao_embedding()))
        # bancos criados antes desta coluna existir
        cursor.execute("ALTER TABLE cct_documentos ADD COLUMN IF NOT EXISTS base_territorial TEXT")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cct_chunks_hnsw "
            "ON cct_chunks USING hnsw (embedding vector_cosine_ops)"
        )


def normalizar(texto: str) -> str:
    """Minúsculo e sem acento — para comparar município e sindicato."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return sem_acento.strip().lower()


# O sindicato é definido pela ATIVIDADE PREPONDERANTE DA EMPREGADORA, não pela função do
# trabalhador: porteiro de empresa de asseio segue a CCT de asseio. Sem esse vínculo o app
# escolheria a convenção pelo cargo e citaria cláusula de convenção que não rege o contrato.
RAMOS_COBERTOS = [
    ("vigilancia", r"vigil[âa]nc|seguran[çc]a patrimonial|transporte de valores|escolta armada|segurança privada"),
    ("asseio", r"asseio|conserva[çc][ãa]o|limpeza|higieniza[çc][ãa]o|facilities|zeladoria"),
    ("porteiros", r"presta[çc][ãa]o de servi[çc]os a terceiros|terceiriza|portaria|m[ãa]o de obra tempor[áa]ria"),
]


def mapear_categoria(ramo_empregadora: str) -> str | None:
    """Traduz a atividade da empregadora na categoria da CCT. None = fora da cobertura."""
    if not ramo_empregadora:
        return None
    alvo = normalizar(ramo_empregadora)
    for categoria, padrao in RAMOS_COBERTOS:
        if re.search(normalizar(padrao), alvo):
            return categoria
    return None


def categorias_no_banco() -> list[str]:
    """Categorias que realmente têm convenção indexada — a lista não é fixa no código."""
    with conectar() as conexao, conexao.cursor() as cursor:
        cursor.execute("SELECT DISTINCT categoria FROM cct_documentos ORDER BY categoria")
        return [linha[0] for linha in cursor.fetchall()]


def documento_ja_ingerido(hash_arquivo: str) -> bool:
    with conectar() as conexao, conexao.cursor() as cursor:
        cursor.execute("SELECT 1 FROM cct_documentos WHERE hash_arquivo = %s", (hash_arquivo,))
        return cursor.fetchone() is not None


def registro_ja_ingerido(registro_mte: str | None) -> str | None:
    """O mesmo documento costuma aparecer com nomes diferentes; o registro no MTE é a chave real."""
    if not registro_mte:
        return None
    with conectar() as conexao, conexao.cursor() as cursor:
        cursor.execute("SELECT arquivo FROM cct_documentos WHERE registro_mte = %s", (registro_mte,))
        linha = cursor.fetchone()
        return linha[0] if linha else None


def gravar_documento(meta: dict, chunks: list[dict]) -> int:
    """Grava um documento e suas cláusulas já vetorizadas. Devolve o id do documento."""
    embeddings = criar_embeddings().embed_documents([c["conteudo"] for c in chunks])

    with conectar() as conexao, conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO cct_documentos
                (arquivo, hash_arquivo, categoria, tipo, titulo, sindicato_laboral,
                 sindicato_patronal, base_territorial, registro_mte, vigencia_inicio,
                 vigencia_fim, abrangencia, municipios)
            VALUES (%(arquivo)s, %(hash_arquivo)s, %(categoria)s, %(tipo)s, %(titulo)s,
                    %(sindicato_laboral)s, %(sindicato_patronal)s, %(base_territorial)s,
                    %(registro_mte)s, %(vigencia_inicio)s, %(vigencia_fim)s,
                    %(abrangencia)s, %(municipios)s)
            RETURNING id
            """,
            meta,
        )
        documento_id = cursor.fetchone()[0]

        cursor.executemany(
            """
            INSERT INTO cct_chunks (documento_id, ordem, clausula_ref, clausula_titulo, conteudo, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    documento_id,
                    i,
                    chunk.get("clausula_ref"),
                    chunk.get("clausula_titulo"),
                    chunk["conteudo"],
                    str(vetor),
                )
                for i, (chunk, vetor) in enumerate(zip(chunks, embeddings))
            ],
        )
    return documento_id


def buscar_clausulas(
    consulta: str,
    categoria: str | None = None,
    vigente_em: date | None = None,
    limite: int = 5,
) -> list[dict]:
    """Busca cláusulas por similaridade, filtrando antes por categoria e vigência.

    Args:
        consulta: pergunta em linguagem natural (ex.: "percentual de hora extra").
        categoria: 'vigilancia', 'asseio' ou 'porteiros'.
        vigente_em: devolve apenas CCTs em vigor nessa data (normalmente a data da rescisão).
        limite: quantidade de cláusulas retornadas.
    """
    vetor = str(criar_embeddings().embed_query(consulta))

    filtros, parametros = [], {"vetor": vetor, "limite": limite}
    if categoria:
        filtros.append("d.categoria = %(categoria)s")
        parametros["categoria"] = categoria
    if vigente_em:
        filtros.append(
            "(d.vigencia_inicio IS NULL OR d.vigencia_inicio <= %(data)s) "
            "AND (d.vigencia_fim IS NULL OR d.vigencia_fim >= %(data)s)"
        )
        parametros["data"] = vigente_em

    onde = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    with conectar() as conexao, conexao.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT d.categoria, d.titulo, d.registro_mte, d.vigencia_inicio, d.vigencia_fim,
                   c.clausula_ref, c.clausula_titulo, c.conteudo,
                   1 - (c.embedding <=> %(vetor)s::vector) AS similaridade
            FROM cct_chunks c
            JOIN cct_documentos d ON d.id = c.documento_id
            {onde}
            ORDER BY c.embedding <=> %(vetor)s::vector
            LIMIT %(limite)s
            """,
            parametros,
        )
        colunas = [descricao[0] for descricao in cursor.description]
        return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
