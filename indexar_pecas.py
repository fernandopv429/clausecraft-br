# indexar_pecas.py
"""Indexa as peças-modelo mascaradas na coleção `pecas_modelo` do PostgreSQL."""

import json
import os

from langchain_core.documents import Document

from config import COLECAO_PECAS, PASTA_DADOS, criar_vectorstore

ARQUIVO = os.path.join(PASTA_DADOS, "pecas_modelo.json")


def indexar():
    if not os.path.exists(ARQUIVO):
        raise SystemExit(f"❌ {ARQUIVO} não encontrado — rode `python preparar_pecas.py` antes")

    with open(ARQUIVO, "r", encoding="utf-8") as arquivo:
        capitulos = json.load(arquivo)

    documentos, identificadores = [], []
    for i, capitulo in enumerate(capitulos):
        documentos.append(
            Document(
                page_content=f"{capitulo['capitulo']}\n\n{capitulo['texto']}",
                metadata={
                    "capitulo": capitulo["capitulo"],
                    "variante": capitulo["variante"],
                    "total_variantes": capitulo["total_variantes"],
                    "ocorrencias": capitulo["ocorrencias"],
                    "origem": ", ".join(sorted(set(capitulo["origem"])))[:300],
                },
            )
        )
        identificadores.append(f"peca-{i:04d}")

    criar_vectorstore(recriar=True, colecao=COLECAO_PECAS).add_documents(
        documentos, ids=identificadores
    )
    print(f"✅ {len(documentos)} capítulos indexados na coleção '{COLECAO_PECAS}'")


if __name__ == "__main__":
    indexar()
