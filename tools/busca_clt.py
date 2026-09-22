# busca_clt.py

from crewai.tools import tool

from config import TOP_K, criar_vectorstore

LIMITE_TEXTO = 1200  # artigo longo estoura o contexto do agente sem acrescentar

def _abrir_banco():
    """A instância é compartilhada por todas as ferramentas (ver config.criar_vectorstore)."""
    return criar_vectorstore()


@tool("Busca na CLT")
def buscar_artigos_clt(consulta: str) -> list[dict]:
    """
    Busca semântica nos artigos da CLT (Decreto-Lei nº 5.452/1943, texto compilado).

    Args:
        consulta (str): descrição do ponto em linguagem natural
            (ex.: "intervalo intrajornada não concedido", "prazo para pagamento das verbas rescisórias").

    Returns:
        list[dict]: artigos mais relevantes, com título, capítulo e texto legal.
    """
    documentos = _abrir_banco().similarity_search(
        consulta, k=TOP_K, filter={"diploma": {"$eq": "CLT"}}
    )

    return [
        {
            "artigo": doc.metadata.get("artigo"),
            "rubrica": doc.metadata.get("rubrica"),
            "titulo": doc.metadata.get("titulo"),
            "capitulo": doc.metadata.get("capitulo"),
            "texto": " ".join(doc.page_content.split())[:LIMITE_TEXTO],
            "fonte": doc.metadata.get("fonte"),
        }
        for doc in documentos
    ]
