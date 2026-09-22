# busca_jurisprudencia_mcp.py
"""Acesso ao MCP do juscraper: jurisprudência direto do site dos tribunais."""

import json
import urllib.error
import urllib.request

from crewai.tools import tool

from config import URL_MCP_JUSCRAPER

TEMPO_LIMITE = 180  # a raspagem do tribunal é lenta em consulta ampla
LIMITE_EMENTA = 700  # ementa inteira estoura o contexto do agente sem acrescentar muito
MAX_RESULTADOS = 5

TRIBUNAIS = (
    "tjsp tjac tjal tjam tjap tjba tjce tjdft tjes tjgo tjms tjmt tjpa tjpb tjpe "
    "tjpi tjpr tjrj tjrn tjro tjrr tjrs tjsc tjto trf3 trf5"
).split()


def _chamar(ferramenta: str, argumentos: dict) -> dict:
    """Faz uma chamada JSON-RPC ao MCP (o servidor é público e não exige sessão)."""
    corpo = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": ferramenta, "arguments": argumentos},
        }
    ).encode("utf-8")

    requisicao = urllib.request.Request(
        URL_MCP_JUSCRAPER,
        data=corpo,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
    )

    with urllib.request.urlopen(requisicao, timeout=TEMPO_LIMITE) as resposta:
        envelope = json.loads(resposta.read().decode("utf-8"))

    if "error" in envelope:
        raise RuntimeError(envelope["error"].get("message", "erro no MCP"))

    texto = "".join(bloco.get("text", "") for bloco in envelope.get("result", {}).get("content", []))
    return json.loads(texto) if texto.strip().startswith("{") else {"texto": texto}


@tool("Busca de acórdãos nos tribunais")
def buscar_acordaos(pesquisa: str, tribunal: str = "tjsp", comarca: str = "") -> list[dict]:
    """
    Busca acórdãos de 2º grau direto na jurisprudência do tribunal (via MCP do juscraper).

    Cobre 24 tribunais de justiça estaduais e os TRF3 e TRF5.
    NÃO cobre Justiça do Trabalho: para TRT e TST, use outra fonte.

    Args:
        pesquisa (str): termos de busca, como se digitaria no site do tribunal
            (ex.: "furto qualificado rompimento de obstáculo repouso noturno").
        tribunal (str): sigla em minúsculas; padrão 'tjsp'.
        comarca (str): filtra por comarca, quando fizer sentido.

    Returns:
        list[dict]: acórdãos com número do processo, órgão julgador, relator, data e ementa.
    """
    if tribunal not in TRIBUNAIS:
        return [{"erro": f"tribunal {tribunal!r} não disponível", "disponiveis": TRIBUNAIS}]

    argumentos = {"tribunal": tribunal, "pesquisa": pesquisa, "paginas": 1}
    if comarca:
        argumentos["comarca"] = comarca

    try:
        dados = _chamar("buscar_jurisprudencia", argumentos)
    except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as erro:
        return [{"erro": f"o MCP de jurisprudência não respondeu: {erro}"}]

    resultados = dados.get("resultados", [])
    if not resultados:
        return [{"aviso": f"Nenhum acórdão encontrado no {tribunal.upper()} para essa pesquisa."}]

    return [
        {
            "processo": r.get("processo"),
            "classe_assunto": r.get("classe_assunto"),
            "orgao_julgador": r.get("orgao_julgador"),
            "relator": r.get("relatora") or r.get("relator"),
            "comarca": r.get("comarca"),
            "data_julgamento": r.get("data_julgamento"),
            "ementa": (r.get("ementa") or "")[:LIMITE_EMENTA],
            "tribunal": tribunal.upper(),
        }
        for r in resultados[:MAX_RESULTADOS]
    ]
