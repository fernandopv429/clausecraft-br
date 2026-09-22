# tarefa_jurisprudencia.py

from crewai import Task

from agents.agente_jurisprudencia import agente_jurisprudencia
from tasks.tarefa_tipificacao import tarefa_tipificacao
from tasks.tarefa_triagem import tarefa_triagem

tarefa_jurisprudencia = Task(
    agent=agente_jurisprudencia,
    context=[tarefa_triagem, tarefa_tipificacao],
    description=(
        "Pesquise jurisprudência brasileira sobre os pontos controvertidos do caso e sobre"
        " os artigos do Código Penal apontados na tipificação.\n\n"
        "Comece pela busca de acórdãos no tribunal: ela consulta o site do próprio TJ e devolve"
        " ementa, número do processo, câmara e data. Use a sigla do tribunal do estado da comarca"
        " indicada na ficha (São Paulo → tjsp, Rio de Janeiro → tjrj, e assim por diante).\n"
        "Faça uma busca por tese controvertida, com os termos que um advogado digitaria no site.\n\n"
        "Priorize STF e STJ (súmulas, teses de recursos repetitivos e repercussão geral) e,"
        " na sequência, tribunais estaduais e federais. Use a ferramenta de busca; não cite"
        " julgado que não tenha aparecido nos resultados.\n\n"
        "Depois, escreva um texto corrido em português jurídico explicando como cada julgado"
        " se relaciona com o caso — inclusive entendimentos desfavoráveis ao cliente, se houver."
    ),
    expected_output=(
        "Um texto em português com 2 a 4 parágrafos analisando os julgados brasileiros mais relevantes,"
        " cada citação acompanhada de tribunal, identificação do julgado e link."
        " Caso nada relevante seja encontrado, informar isso de forma explícita."
    ),
)
