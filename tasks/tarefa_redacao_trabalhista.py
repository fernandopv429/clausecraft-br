# tarefa_redacao_trabalhista.py

from crewai import Task

from agents.agente_redator_trabalhista import agente_redator_trabalhista
from tasks.tarefa_cct import tarefa_cct
from tasks.tarefa_clt import tarefa_clt
from tasks.tarefa_jurisprudencia_trabalhista import tarefa_jurisprudencia_trabalhista
from tasks.tarefa_triagem import tarefa_triagem

tarefa_redacao_trabalhista = Task(
    agent=agente_redator_trabalhista,
    context=[tarefa_triagem, tarefa_clt,
        tarefa_cct, tarefa_jurisprudencia_trabalhista],
    description=(
        "Com a ficha da triagem, os artigos da CLT, as cláusulas da convenção coletiva e a jurisprudência,"
        " redija a RECLAMAÇÃO TRABALHISTA.\n\n"
        "Para os capítulos principais (endereçamento e qualificação, jornada, horas extras,"
        " dano moral, verbas rescisórias e pedidos), consulte antes a ferramenta de modelos do"
        " escritório e siga a estrutura e o vocabulário que encontrar ali — trocando os fatos"
        " pelos deste caso. Se não houver modelo para um capítulo, redija no mesmo tom dos demais.\n\n"
        "Estrutura obrigatória:\n"
        "- endereçamento ao Juízo da Vara do Trabalho competente;\n"
        "- qualificação do reclamante (nacionalidade, estado civil, função, RG, CPF, PIS, CTPS,"
        " endereço e e-mail) e das reclamadas (razão social, CNPJ, endereço);\n"
        "- da competência (artigo 651 da CLT);\n"
        "- do valor da causa como mera estimativa (artigo 852-B, I, da CLT);\n"
        "- da justiça gratuita (artigo 790, §§ 3º e 4º, da CLT e artigo 98 do CPC);\n"
        "- do contrato de trabalho: admissão, função, salário e modalidade de rescisão;\n"
        "- **um capítulo para cada item recebido da fundamentação**: escreva um capítulo por artigo"
        " da CLT e um por cláusula da CCT que vieram na etapa anterior. Não resuma, não agrupe e não"
        " descarte item algum — se a fundamentação trouxe adicional noturno, intervalo intrajornada e"
        " escala 12x36, cada um vira seu próprio capítulo com o respectivo pedido;\n"
        "- em cada capítulo, o artigo da CLT dá o fundamento legal e a cláusula da CCT dá o percentual,"
        " o piso ou o prazo — atribua cada número à sua fonte correta, citando a cláusula pelo nome"
        " (ex.: 'Cláusula Décima Sexta da CCT 2024, vigente de 01/01/2024 a 31/12/2024');\n"
        "- dos pedidos, em lista numerada;\n"
        "- das provas, honorários, local, data e assinatura com OAB.\n\n"
        "Só inclua capítulo cujo fato conste da ficha de triagem — pedido sem fato que o sustente"
        " fica de fora, e a pendência vai para as observações finais.\n\n"
        "Se a etapa da convenção não trouxe cláusula alguma, escreva a peça **apenas com a CLT** e"
        " abra as observações finais com a advertência de que os percentuais convencionais"
        " (hora extra, adicional noturno, piso, multas) precisam ser conferidos na CCT aplicável"
        " antes do protocolo. Jamais cite número de cláusula que não veio da fundamentação.\n\n"
        "Os [colchetes] servem apenas para dado pessoal que o cliente ainda precisa fornecer"
        " (nome, RG, CPF, endereço, CNPJ da reclamada, valor da causa).\n"
        "**Nunca** use colchete para número de artigo, número de cláusula, percentual ou vigência:"
        " esses dados vieram da etapa de fundamentação e devem ser transcritos literalmente."
        " Se algum deles não tiver sido encontrado, escreva o pedido sem ele e registre a falta"
        " nas observações — jamais um placeholder no corpo da peça.\n\n"
        "Encerre com a seção 'Observações ao cliente'."
    ),
    expected_output=(
        "A reclamação trabalhista completa em Markdown, com endereçamento, qualificação,"
        " capítulos de fundamentação citando CLT e cláusulas da CCT com vigência,"
        " lista de pedidos, provas, data, assinatura e a seção final 'Observações ao cliente'."
    ),
)
