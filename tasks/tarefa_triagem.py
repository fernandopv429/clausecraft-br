# tarefa_triagem.py

from crewai import Task

from agents.agente_triagem import agente_triagem

tarefa_triagem = Task(
    agent=agente_triagem,
    description=(
        "O cliente relatou o seguinte caso:\n\n"
        "{relato_do_cliente}\n\n"
        "Interprete o relato à luz do direito brasileiro e produza uma ficha estruturada em JSON com:\n"
        "- `tipo_de_caso`: o fato em linguagem jurídica (ex.: 'furto qualificado', 'rescisão indireta');\n"
        "- `ramo_do_direito`: penal, civil, trabalhista, consumidor, família, administrativo etc.;\n"
        "- `materia_penal`: true/false — se os fatos, em tese, configuram crime;\n"
        "- `resumo_dos_fatos`: síntese objetiva, apenas com o que foi relatado;\n"
        "- `partes`: quem é vítima/requerente e quem é o autor do fato, com o que se sabe de cada um;\n"
        "- `data_dos_fatos` e `comarca_uf`: se informados, senão null;\n"
        "- `providencias_ja_tomadas`: boletim de ocorrência, notificação, reclamação etc.;\n"
        "- `informacoes_faltantes`: dados que precisam ser confirmados com o cliente.\n\n"
        "Não invente fatos. Use exclusivamente o direito brasileiro."
    ),
    expected_output=(
        "```json\n"
        "{\n"
        '  "tipo_de_caso": "Furto qualificado",\n'
        '  "ramo_do_direito": "Direito Penal",\n'
        '  "materia_penal": true,\n'
        '  "resumo_dos_fatos": "O cliente teve a residência invadida durante a madrugada...",\n'
        '  "partes": {"vitima": "cliente e familiares", "autor_do_fato": "desconhecido"},\n'
        '  "data_dos_fatos": "2026-03-12",\n'
        '  "comarca_uf": "São Paulo/SP",\n'
        '  "providencias_ja_tomadas": ["boletim de ocorrência registrado"],\n'
        '  "informacoes_faltantes": ["valor dos bens subtraídos", "número do BO"]\n'
        "}\n"
        "```"
    ),
)
