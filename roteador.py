# roteador.py
"""Escolhe a trilha do caso — penal ou trabalhista — antes de montar a equipe.

O roteamento é uma chamada curta e isolada ao LLM, e não uma decisão diluída no meio
da cadeia de agentes: assim a escolha fica explícita, barata e auditável no log.
"""

import re

from crewai import LLM

from config import MODELO_LLM

TRILHAS = ("penal", "trabalhista")

PROMPT = """Classifique o relato abaixo em UMA palavra, sem explicação:

- "penal" se os fatos descrevem crime (furto, roubo, estelionato, ameaça, lesão, injúria, golpe);
- "trabalhista" se descrevem relação de emprego (demissão, horas extras, verbas rescisórias,
  assédio no trabalho, acidente de trabalho, rescisão indireta, adicional, FGTS).

Relato:
{relato}

Responda apenas: penal OU trabalhista"""

# rede de segurança caso o LLM devolva algo inesperado
PISTAS_TRABALHISTAS = re.compile(
    r"\b(demiss|demiti|dispensad|rescis|horas? extras?|verbas? rescis|FGTS|CTPS|patrão|patrao|"
    r"empregador|empresa em que trabalh|jornada|adicional noturno|insalubrid|periculosid|"
    r"aviso prévio|aviso previo|justa causa|sindicato|convenção coletiva|convencao coletiva)\b",
    re.I,
)


def classificar_materia(relato: str) -> str:
    """Devolve 'penal' ou 'trabalhista'."""
    resposta = LLM(model=MODELO_LLM, temperature=0).call(PROMPT.format(relato=relato))
    escolha = str(resposta).strip().lower()

    for trilha in TRILHAS:
        if trilha in escolha:
            return trilha

    return "trabalhista" if PISTAS_TRABALHISTAS.search(relato) else "penal"
