# busca_pecas.py

from crewai.tools import tool

from config import COLECAO_PECAS, criar_vectorstore

LIMITE_TEXTO = 1500


@tool("Busca nos modelos de peça do escritório")
def buscar_capitulo_modelo(consulta: str) -> list[dict]:
    """
    Busca capítulos de peças já redigidas pelo escritório, para servir de modelo de redação.

    Use para ver como a casa costuma escrever determinado capítulo (jornada, dano moral,
    verbas rescisórias, pedidos) e seguir esse padrão — os textos estão anonimizados,
    com [NOME], [CPF] e [ENDEREÇO] no lugar dos dados de cliente.

    Args:
        consulta (str): o capítulo ou a tese procurada
            (ex.: "descaracterização da escala 12x36", "dano moral por assédio").

    Returns:
        list[dict]: capítulos com título, texto-modelo e quantas peças usaram aquele texto.
    """
    documentos = criar_vectorstore(colecao=COLECAO_PECAS).similarity_search(consulta, k=3)

    return [
        {
            "capitulo": doc.metadata.get("capitulo"),
            "texto_modelo": " ".join(doc.page_content.split())[:LIMITE_TEXTO],
            "usado_em_pecas": doc.metadata.get("ocorrencias"),
            "variante": f"{doc.metadata.get('variante')} de {doc.metadata.get('total_variantes')}",
        }
        for doc in documentos
    ]
