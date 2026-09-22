# busca_codigo_penal.py

from crewai.tools import tool

from config import TOP_K, criar_vectorstore

LIMITE_TEXTO = 1200  # artigo longo estoura o contexto do agente sem acrescentar

def _abrir_banco():
    """A instância é compartilhada por todas as ferramentas (ver config.criar_vectorstore)."""
    return criar_vectorstore()


@tool("Busca no Código Penal brasileiro")
def buscar_artigos_codigo_penal(consulta: str) -> list[dict]:
    """
    Busca semântica nos artigos do Código Penal brasileiro (Decreto-Lei nº 2.848/1940).

    Args:
        consulta (str): descrição do fato em linguagem natural
            (ex.: "invasão de residência à noite com subtração de joias").

    Returns:
        list[dict]: artigos mais relevantes, com rubrica, título, capítulo e texto legal.
    """
    # o filtro impede que artigo da CLT apareça numa tipificação penal
    documentos = _abrir_banco().similarity_search(
        consulta, k=TOP_K, filter={"diploma": {"$eq": "CP"}}
    )

    return [
        {
            "artigo": doc.metadata.get("artigo"),
            "rubrica": doc.metadata.get("rubrica"),
            "parte": doc.metadata.get("parte"),
            "titulo": doc.metadata.get("titulo"),
            "capitulo": doc.metadata.get("capitulo"),
            "secao": doc.metadata.get("secao"),
            "texto": " ".join(doc.page_content.split())[:LIMITE_TEXTO],
            "fonte": doc.metadata.get("fonte"),
        }
        for doc in documentos
    ]
