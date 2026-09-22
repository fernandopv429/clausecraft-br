# busca_jurisprudencia.py

import os

from crewai.tools import tool
from tavily import TavilyClient

from config import FONTES_JURISPRUDENCIA


def _e_fonte_confiavel(url: str) -> bool:
    """Confere se a URL pertence a uma das fontes brasileiras configuradas."""
    return any(dominio in url for dominio in FONTES_JURISPRUDENCIA)


@tool("Busca de jurisprudência brasileira")
def buscar_jurisprudencia(consulta: str) -> list[dict]:
    """
    Pesquisa julgados brasileiros (STF, STJ, tribunais e repositórios nacionais) via Tavily.

    Args:
        consulta (str): tese ou fato a pesquisar
            (ex.: "furto qualificado por rompimento de obstáculo jurisprudência STJ").

    Returns:
        list[dict]: acórdãos/ementas com título, resumo e link.
    """
    chave = os.getenv("TAVILY_API_KEY")
    if not chave:
        # sem chave a busca fica indisponível, mas o restante do fluxo continua
        return [
            {
                "titulo": "Busca de jurisprudência indisponível",
                "resumo": "Configure TAVILY_API_KEY no arquivo .env para pesquisar julgados brasileiros.",
                "link": None,
            }
        ]

    cliente = TavilyClient(api_key=chave)

    # restringe a busca às fontes brasileiras configuradas em config.py
    filtro_sites = " OR ".join(f"site:{dominio}" for dominio in FONTES_JURISPRUDENCIA)
    resposta = cliente.search(query=f"{filtro_sites} {consulta}", max_results=10)

    julgados = [
        {
            "titulo": item.get("title"),
            "resumo": item.get("content"),
            "link": item.get("url"),
        }
        for item in resposta.get("results", [])
        if _e_fonte_confiavel(item.get("url", ""))
    ]

    return julgados or [
        {
            "titulo": "Nenhuma jurisprudência encontrada",
            "resumo": "A busca não retornou julgados nas fontes brasileiras configuradas.",
            "link": None,
        }
    ]
