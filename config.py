# config.py
"""Configuração central do assistente jurídico (legislação brasileira)."""

import os
import re

from dotenv import load_dotenv

# Em produção as variáveis vêm do painel de deploy. O .env é só conveniência local:
# se não existir, load_dotenv não faz nada e o os.getenv lê direto do ambiente.
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Base legal indexada: textos compilados baixados do Planalto
PASTA_DADOS = os.getenv("PASTA_DADOS", os.path.join(BASE_DIR, "dados"))

# Diplomas indexados; a sigla vira metadado e filtro de busca
DIPLOMAS_INDEXADOS = {
    "CP": "codigo_penal.json",
    "CLT": "clt.json",
}

# Banco vetorial: PostgreSQL + pgvector
URL_POSTGRES_BRUTA = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL", "")


def _normalizar_url(url: str) -> str:
    """Garante o driver psycopg (v3) exigido pelo langchain-postgres."""
    if url.startswith("postgresql+") or not url:
        return url
    return re.sub(r"^postgres(ql)?://", "postgresql+psycopg://", url)


URL_POSTGRES = _normalizar_url(URL_POSTGRES_BRUTA)

# As convenções vivem nas tabelas cct_documentos/cct_chunks, mantidas pelo pipeline do
# Agente 1.0 — o ClauseCraft só lê delas. Hoje ficam no mesmo banco das coleções, então
# esta variável é opcional; existe para o caso de a base de CCTs mudar de servidor.
URL_POSTGRES_CCT_BRUTA = os.getenv("CCT_POSTGRES_URL") or URL_POSTGRES_BRUTA

NOME_COLECAO = os.getenv("COLLECTION_NAME", "legislacao")

# Coleção separada para os modelos de peça do escritório
COLECAO_PECAS = os.getenv("COLLECTION_PECAS", "pecas_modelo")

# Peças-modelo: lidas de fora do repositório, porque contêm dados de cliente.
# Sem padrão de propósito — é caminho de máquina de trabalho, não de container.
# Só `preparar_pecas.py` usa isso, e ele roda localmente.
PASTA_PECAS = os.getenv("PASTA_PECAS", "")

# Provedor de embeddings: "openai" (padrão) ou "huggingface" (local, sem custo de API)
PROVEDOR_EMBEDDING = os.getenv("EMBEDDING_PROVIDER", "openai").lower()

# Modelos de embedding — ambos lidam bem com português jurídico
MODELO_EMBEDDING_OPENAI = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MODELO_EMBEDDING_HF = os.getenv(
    "EMBEDDING_MODEL_HF",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
)

# Modelo de linguagem usado pelos agentes (OpenAI por padrão; configurável no .env)
MODELO_LLM = os.getenv("LLM_MODEL", "openai/gpt-4o")

# MCP do juscraper — jurisprudência de 2º grau dos TJs, julgados de 1º grau do TJSP,
# Datajud e Comunica CNJ. Não cobre TRT/TST.
URL_MCP_JUSCRAPER = os.getenv("MCP_JUSCRAPER_URL", "https://juscraper.nexusdevhub.com/mcp")

# Fontes brasileiras confiáveis de jurisprudência (edite conforme a necessidade do escritório)
FONTES_JURISPRUDENCIA = [
    d.strip()
    for d in os.getenv(
        "FONTES_JURISPRUDENCIA",
        "stf.jus.br,stj.jus.br,jusbrasil.com.br,cnj.jus.br",
    ).split(",")
    if d.strip()
]

# Quantidade de artigos retornados na busca semântica
TOP_K = int(os.getenv("TOP_K", "5"))

# Dimensão do vetor — precisa bater com o modelo de embedding escolhido
DIMENSOES_CONHECIDAS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


# Variáveis sem as quais o app não funciona. Conferidas na subida, não no meio de uma análise.
OBRIGATORIAS = {
    "OPENAI_API_KEY": "chave da OpenAI usada pelos agentes e pelos embeddings",
    "POSTGRES_URL": "PostgreSQL com pgvector: legislação, modelos de peça e convenções",
}


def validar_ambiente() -> list[str]:
    """Devolve a lista de variáveis obrigatórias que estão faltando."""
    return [
        f"{nome} — {descricao}"
        for nome, descricao in OBRIGATORIAS.items()
        if not os.getenv(nome)
    ]


def criar_embeddings():
    """Instancia a função de embeddings usada tanto na indexação quanto na busca.

    Importante: indexação e consulta precisam usar o MESMO provedor/modelo.
    Se trocar de provedor, recrie o vetorstore com `python construir_vectordb.py`.
    """
    if PROVEDOR_EMBEDDING == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=MODELO_EMBEDDING_OPENAI)

    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=MODELO_EMBEDDING_HF)


def dimensao_embedding() -> int | None:
    """Dimensão do vetor, usada para criar a coluna no Postgres."""
    configurada = os.getenv("EMBEDDING_DIM")
    if configurada:
        return int(configurada)
    if PROVEDOR_EMBEDDING == "openai":
        return DIMENSOES_CONHECIDAS.get(MODELO_EMBEDDING_OPENAI, 1536)
    return 768  # padrão dos modelos multilíngues base do sentence-transformers


_VECTORSTORES: dict[str, object] = {}


def criar_vectorstore(recriar: bool = False, colecao: str | None = None):
    """Abre (ou recria) a coleção pgvector com os artigos indexados.

    Há uma instância por coleção, reaproveitada no processo inteiro: o langchain-postgres
    declara as tabelas num MetaData global do SQLAlchemy, e recriar o mesmo PGVector a cada
    chamada quebra com "Table 'langchain_pg_collection' is already defined".

    Args:
        recriar: se True, apaga a coleção existente antes de gravar — use apenas na indexação.
        colecao: nome da coleção; por padrão a da legislação.
    """
    colecao = colecao or NOME_COLECAO
    if colecao in _VECTORSTORES and not recriar:
        return _VECTORSTORES[colecao]

    if not URL_POSTGRES:
        raise EnvironmentError(
            "❌ POSTGRES_URL não configurada no .env "
            "(ex.: postgresql://usuario:senha@host:5432/banco)"
        )

    from langchain_postgres import PGVector

    _VECTORSTORES[colecao] = PGVector(
        embeddings=criar_embeddings(),
        connection=URL_POSTGRES,
        collection_name=colecao,
        embedding_length=dimensao_embedding(),
        use_jsonb=True,
        # exige privilégio no banco; desligue se o usuário do deploy não for superusuário
        # e a extensão já estiver instalada
        create_extension=os.getenv("PGVECTOR_CREATE_EXTENSION", "true").lower() == "true",
        pre_delete_collection=recriar,
    )
    return _VECTORSTORES[colecao]
