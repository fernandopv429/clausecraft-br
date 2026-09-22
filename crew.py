# crew.py

from crewai import Crew

from agents.agente_fundamentacao_trabalhista import agente_fundamentacao_trabalhista
from agents.agente_jurisprudencia import agente_jurisprudencia
from agents.agente_redator import agente_redator
from agents.agente_redator_trabalhista import agente_redator_trabalhista
from agents.agente_tipificacao import agente_tipificacao
from agents.agente_triagem import agente_triagem
from tasks.tarefa_cct import tarefa_cct
from tasks.tarefa_clt import tarefa_clt
from tasks.tarefa_jurisprudencia import tarefa_jurisprudencia
from tasks.tarefa_jurisprudencia_trabalhista import tarefa_jurisprudencia_trabalhista
from tasks.tarefa_redacao import tarefa_redacao
from tasks.tarefa_redacao_trabalhista import tarefa_redacao_trabalhista
from tasks.tarefa_tipificacao import tarefa_tipificacao
from tasks.tarefa_triagem import tarefa_triagem

equipe_penal = Crew(
    agents=[agente_triagem, agente_tipificacao, agente_jurisprudencia, agente_redator],
    tasks=[tarefa_triagem, tarefa_tipificacao, tarefa_jurisprudencia, tarefa_redacao],
    verbose=True,
)

equipe_trabalhista = Crew(
    agents=[agente_triagem, agente_fundamentacao_trabalhista, agente_jurisprudencia, agente_redator_trabalhista],
    tasks=[
        tarefa_triagem,
        tarefa_clt,
        tarefa_cct,
        tarefa_jurisprudencia_trabalhista,
        tarefa_redacao_trabalhista,
    ],
    verbose=True,
)

EQUIPES = {"penal": equipe_penal, "trabalhista": equipe_trabalhista}


def obter_equipe(trilha: str) -> Crew:
    """Devolve a equipe da trilha ('penal' ou 'trabalhista')."""
    if trilha not in EQUIPES:
        raise ValueError(f"trilha desconhecida: {trilha!r} — use 'penal' ou 'trabalhista'")
    return EQUIPES[trilha]
