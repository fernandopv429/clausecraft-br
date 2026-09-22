# tarefa_cct.py

from crewai import Task

from agents.agente_fundamentacao_trabalhista import agente_fundamentacao_trabalhista
from tasks.tarefa_triagem import tarefa_triagem

tarefa_cct = Task(
    agent=agente_fundamentacao_trabalhista,
    context=[tarefa_triagem],
    description=(
        "Agora levante as cláusulas da convenção coletiva aplicáveis ao caso.\n\n"
        "Antes de buscar, defina dois parâmetros:\n"
        "- `ramo_empregadora`: a atividade preponderante da EMPRESA que contratou, extraída da ficha"
        " (ex.: 'empresa de vigilância patrimonial', 'empresa de asseio e conservação', 'restaurante')."
        " É o ramo da empregadora que define a convenção — nunca a função do trabalhador. Se a ficha"
        " não informar o ramo, passe o que souber e registre a dúvida nas observações;\n"
        "- `data_referencia`: a data da rescisão no formato AAAA-MM-DD — é ela que decide qual"
        " convenção vale. Sem data, avise que a vigência precisa ser confirmada.\n\n"
        "Busque um tema por vez: hora extra, adicional noturno, intervalo, periculosidade,"
        " insalubridade, piso salarial, escala 12x36, multa convencional, vale-transporte e"
        " auxílio-alimentação — apenas os que os fatos justificarem.\n\n"
        "Para o piso, busque por 'salários profissionais tabela por função' — o valor do porteiro,"
        " controlador de acesso ou vigilante está numa tabela densa que não aparece em busca genérica"
        " por 'piso salarial'.\n"
        "Atenção ao piso: quando a convenção traz uma tabela de salários profissionais por função"
        " além do salário normativo geral, vale o piso da função do reclamante — para porteiro,"
        " controlador de acesso ou vigilante, use o salário profissional da função, que é maior,"
        " e não o normativo mínimo da categoria.\n\n"
        "**Se não houver convenção indexada para a categoria ou para a data**, a ferramenta avisa."
        " Nesse caso: NÃO use a convenção de outra categoria nem de outro período — citar CCT que não"
        " se aplica é erro grave que passa despercebido na revisão. Devolva `clausulas` vazio e"
        " descreva em `observacoes` quais pedidos ficaram sem base convencional.\n\n"
        "A categoria não é definida pela função do trabalhador, e sim pela atividade preponderante"
        " do empregador: porteiro de empresa de asseio segue a convenção de asseio, e não a de"
        " porteiros. Se a ficha não disser o ramo da empregadora, registre isso nas observações.\n\n"
        "Esta tarefa trata só da convenção coletiva: os artigos da CLT já foram levantados na etapa"
        " anterior e não devem ser repetidos aqui.\n"
        "Não invente percentual nem número de cláusula: use somente o que a ferramenta devolver."
    ),
    expected_output=(
        "```json\n"
        "{\n"
        '  "categoria": "porteiros",\n'
        '  "convencao": "CONVENÇÃO COLETIVA DE TRABALHO 2024/2024",\n'
        '  "vigencia": "2024-01-01 a 2024-12-31",\n'
        '  "clausulas": [\n'
        "    {\n"
        '      "clausula": "CLÁUSULA DÉCIMA SEXTA",\n'
        '      "titulo": "HORAS EXTRAS",\n'
        '      "conteudo_relevante": "adicional de 50% sobre o valor da hora normal",\n'
        '      "uso_na_peca": "fixa o percentual do pedido de horas extras"\n'
        "    }\n"
        "  ],\n"
        '  "observacoes": "campo livre para pendências de vigência ou cláusula não localizada"\n'
        "}\n"
        "```"
    ),
)
