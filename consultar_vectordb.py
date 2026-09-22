# consultar_vectordb.py
"""Consulta rápida à base do Código Penal — útil para testar a indexação.

Uso:
    python consultar_vectordb.py "furto de celular com uso de aplicativo bancário"
"""

import sys

from config import TOP_K, criar_vectorstore


def consultar(pergunta: str, k: int = TOP_K) -> list[dict]:
    banco = criar_vectorstore()

    return [
        {
            "artigo": doc.metadata.get("artigo"),
            "rubrica": doc.metadata.get("rubrica"),
            "titulo": doc.metadata.get("titulo"),
            "capitulo": doc.metadata.get("capitulo"),
            "texto": doc.page_content,
        }
        for doc in banco.similarity_search(pergunta, k=k)
    ]


if __name__ == "__main__":
    pergunta = " ".join(sys.argv[1:]) or "Qual artigo do Código Penal trata de furto?"
    for resultado in consultar(pergunta):
        print(f"\n### {resultado['artigo']} — {resultado['rubrica']}")
        print(f"{resultado['titulo']} / {resultado['capitulo']}")
        print(resultado["texto"][:400], "...")
