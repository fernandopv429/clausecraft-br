# tarefa_clt.py

from crewai import Task

from agents.agente_fundamentacao_trabalhista import agente_fundamentacao_trabalhista
from tasks.tarefa_triagem import tarefa_triagem

tarefa_clt = Task(
    agent=agente_fundamentacao_trabalhista,
    context=[tarefa_triagem],
    description=(
        "Com base na ficha da triagem, levante os artigos da CLT que amparam cada pedido do caso.\n\n"
        "Use a ferramenta de busca na CLT uma vez por tema presente nos fatos: jornada, horas extras,"
        " intervalo intrajornada, adicional noturno, insalubridade, periculosidade, escala 12x36,"
        " verbas rescisórias, multas dos artigos 467 e 477, competência e ônus da prova.\n\n"
        "Cite o número exato do artigo e transcreva o trecho que interessa (inclusive o parágrafo)."
        " Não use artigo que não tenha vindo da ferramenta."
    ),
    expected_output=(
        "```json\n"
        "{\n"
        '  "artigos_clt": [\n'
        "    {\n"
        '      "artigo": "Art. 71",\n'
        '      "tema": "intervalo intrajornada",\n'
        '      "texto_relevante": "§ 4º A não concessão ou a concessão parcial do intervalo intrajornada '
        'mínimo implica o pagamento, de natureza indenizatória, do período suprimido com acréscimo de 50%",\n'
        '      "uso_na_peca": "fundamenta o pedido de pagamento do intervalo suprimido"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "```"
    ),
)
