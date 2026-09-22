# construir_vectordb.py
"""Indexa a legislação brasileira (Código Penal e CLT) no PostgreSQL (pgvector)."""

import json
import os

from langchain_core.documents import Document

from config import (
    DIPLOMAS_INDEXADOS,
    NOME_COLECAO,
    PASTA_DADOS,
    URL_POSTGRES_BRUTA,
    criar_vectorstore,
)


def carregar_artigos(arquivo: str) -> list[dict]:
    """Lê um JSON gerado por `baixar_legislacao.py`."""
    with open(os.path.join(PASTA_DADOS, arquivo), "r", encoding="utf-8") as f:
        return json.load(f)


def preparar_documentos(artigos: list[dict], sigla: str, incluir_revogados: bool = False) -> list[Document]:
    """Converte cada artigo em Document, com a sigla do diploma como filtro de busca."""
    documentos = []

    for artigo in artigos:
        if artigo.get("revogado") and not incluir_revogados:
            continue

        cabecalho = artigo["artigo"]
        if artigo.get("rubrica"):
            cabecalho = f"{cabecalho} — {artigo['rubrica']}"

        localizacao = " | ".join(
            parte
            for parte in (
                artigo.get("parte"),
                f"{artigo.get('titulo')} - {artigo.get('titulo_nome')}" if artigo.get("titulo") else None,
                f"{artigo.get('capitulo')} - {artigo.get('capitulo_nome')}" if artigo.get("capitulo") else None,
                f"{artigo.get('secao')} - {artigo.get('secao_nome')}" if artigo.get("secao") else None,
            )
            if parte
        )

        documentos.append(
            Document(
                page_content=f"{artigo['diploma_nome']}\n{cabecalho}\n{localizacao}\n\n{artigo['texto']}",
                metadata={
                    "diploma": sigla,
                    "artigo": artigo["artigo"],
                    "rubrica": artigo.get("rubrica") or "",
                    "parte": artigo.get("parte") or "",
                    "titulo": f"{artigo.get('titulo') or ''} {artigo.get('titulo_nome') or ''}".strip(),
                    "capitulo": f"{artigo.get('capitulo') or ''} {artigo.get('capitulo_nome') or ''}".strip(),
                    "secao": f"{artigo.get('secao') or ''} {artigo.get('secao_nome') or ''}".strip(),
                    "fonte": artigo["diploma_nome"],
                },
            )
        )

    return documentos


def construir_vectordb(incluir_revogados: bool = False):
    """Recria a coleção de legislação com todos os diplomas configurados."""
    documentos, identificadores = [], []

    for sigla, arquivo in DIPLOMAS_INDEXADOS.items():
        caminho = os.path.join(PASTA_DADOS, arquivo)
        if not os.path.exists(caminho):
            print(f"⚠️  {arquivo} não encontrado — rode `python baixar_legislacao.py`")
            continue

        do_diploma = preparar_documentos(carregar_artigos(arquivo), sigla, incluir_revogados)
        documentos.extend(do_diploma)
        # a sigla evita colisão: existe Art. 71 no CP e na CLT
        identificadores.extend(f"{sigla}:{doc.metadata['artigo']}" for doc in do_diploma)
        print(f"  {sigla}: {len(do_diploma)} artigos vigentes")

    # recriar=True apaga a coleção anterior, evitando artigos duplicados a cada reindexação
    vectorstore = criar_vectorstore(recriar=True)
    vectorstore.add_documents(documentos, ids=identificadores)

    criar_indice_hnsw()
    print(f"✅ {len(documentos)} artigos indexados na coleção '{NOME_COLECAO}' (PostgreSQL/pgvector)")


def criar_indice_hnsw():
    """Cria o índice HNSW (distância de cosseno) — acelera a busca conforme a base cresce."""
    import psycopg

    try:
        with psycopg.connect(URL_POSTGRES_BRUTA, connect_timeout=20) as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_embedding_hnsw "
                    "ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops)"
                )
        print("✅ Índice HNSW verificado/criado")
    except Exception as erro:  # o app funciona sem o índice, apenas mais devagar
        print(f"⚠️  Não foi possível criar o índice HNSW: {erro}")


if __name__ == "__main__":
    construir_vectordb()
