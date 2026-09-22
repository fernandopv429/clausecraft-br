# tarefa_tipificacao.py

from crewai import Task

from agents.agente_tipificacao import agente_tipificacao
from tasks.tarefa_triagem import tarefa_triagem

tarefa_tipificacao = Task(
    agent=agente_tipificacao,
    context=[tarefa_triagem],
    description=(
        "Com base na ficha da triagem, use a ferramenta de busca no Código Penal brasileiro"
        " para localizar os artigos aplicáveis aos fatos.\n\n"
        "Faça quantas buscas forem necessárias (uma por conduta identificada) e selecione"
        " os artigos realmente pertinentes — inclusive qualificadoras, causas de aumento"
        " e dispositivos da Parte Geral (tentativa, concurso de crimes, concurso de pessoas).\n\n"
        "Se o caso não for penal, ou se depender de legislação extravagante (Lei nº 11.343/2006,"
        " Lei nº 11.340/2006, Lei nº 10.826/2003, CDC, CLT, CTB etc.), diga isso expressamente"
        " no campo `observacoes` — a base indexada cobre apenas o Código Penal.\n\n"
        "Nunca cite artigo, pena ou redação que não tenha vindo da ferramenta."
    ),
    expected_output=(
        "```json\n"
        "{\n"
        '  "artigos": [\n'
        "    {\n"
        '      "artigo": "Art. 155",\n'
        '      "rubrica": "Furto",\n'
        '      "titulo": "Título II DOS CRIMES CONTRA O PATRIMÔNIO",\n'
        '      "dispositivo_aplicavel": "§ 4º, incisos I e IV",\n'
        '      "pena": "reclusão, de 2 (dois) a 8 (oito) anos, e multa",\n'
        '      "justificativa": "A subtração ocorreu mediante rompimento de obstáculo e durante o repouso noturno."\n'
        "    }\n"
        "  ],\n"
        '  "observacoes": "Eventual emprego de arma de fogo atrai a Lei nº 10.826/2003, fora da base indexada."\n'
        "}\n"
        "```"
    ),
)
