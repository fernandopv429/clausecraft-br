# tarefa_jurisprudencia_trabalhista.py

from crewai import Task

from agents.agente_jurisprudencia import agente_jurisprudencia
from tasks.tarefa_cct import tarefa_cct
from tasks.tarefa_clt import tarefa_clt
from tasks.tarefa_triagem import tarefa_triagem

tarefa_jurisprudencia_trabalhista = Task(
    agent=agente_jurisprudencia,
    context=[tarefa_triagem, tarefa_clt, tarefa_cct],
    description=(
        "Pesquise jurisprudência trabalhista brasileira sobre as teses do caso.\n\n"
        "Priorize súmulas e orientações jurisprudenciais do TST e teses de recursos repetitivos;"
        " depois, acórdãos de TRTs.\n\n"
        "Atenção: a busca de acórdãos nos tribunais **não alcança a Justiça do Trabalho** — ela cobre"
        " TJs estaduais e TRF3/TRF5. Para matéria trabalhista, use a busca na web. Se ela estiver"
        " indisponível, diga isso com todas as letras e não invente julgado.\n\n"
        "Escreva um texto corrido relacionando cada julgado às teses do caso, inclusive os"
        " entendimentos desfavoráveis ao reclamante."
    ),
    expected_output=(
        "Texto em português com 2 a 4 parágrafos sobre os julgados trabalhistas mais relevantes,"
        " cada citação com tribunal, identificação e link."
        " Se nada relevante for encontrado, informar isso de forma explícita."
    ),
)
