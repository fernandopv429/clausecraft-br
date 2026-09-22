# tarefa_redacao.py

from crewai import Task

from agents.agente_redator import agente_redator
from tasks.tarefa_jurisprudencia import tarefa_jurisprudencia
from tasks.tarefa_tipificacao import tarefa_tipificacao
from tasks.tarefa_triagem import tarefa_triagem

tarefa_redacao = Task(
    agent=agente_redator,
    context=[tarefa_triagem, tarefa_tipificacao, tarefa_jurisprudencia],
    description=(
        "Com a ficha da triagem, os artigos do Código Penal e a jurisprudência levantada,"
        " redija a peça adequada conforme a praxe forense brasileira.\n\n"
        "Escolha o tipo de peça a partir do caso:\n"
        "- notícia-crime / requerimento de instauração de inquérito policial ao Delegado de Polícia"
        " (art. 5º, II, do Código de Processo Penal), na ação penal pública incondicionada;\n"
        "- representação criminal, quando a ação penal pública for condicionada;\n"
        "- queixa-crime dirigida ao juízo competente (art. 41 do CPP), na ação penal privada;\n"
        "- notificação extrajudicial, quando a via adequada não for penal.\n\n"
        "A peça deve conter: endereçamento à autoridade competente; qualificação completa das partes"
        " (nome, nacionalidade, estado civil, profissão, RG, CPF e endereço); exposição dos fatos;"
        " fundamentação jurídica citando os artigos do Código Penal identificados e a jurisprudência;"
        " pedidos; rol de testemunhas; local e data; e espaço para assinatura do advogado com número da OAB.\n\n"
        "Use [colchetes] em todo dado que ainda precisa ser preenchido pelo cliente."
        " Ao final, acrescente a seção 'Observações ao cliente' com as pendências e os próximos passos."
    ),
    expected_output=(
        "A peça completa em português, formatada em Markdown, contendo:\n"
        "- endereçamento e tipo da peça;\n"
        "- qualificação das partes;\n"
        "- DOS FATOS;\n"
        "- DO DIREITO (artigos do Código Penal e jurisprudência);\n"
        "- DOS PEDIDOS / REQUERIMENTOS;\n"
        "- rol de testemunhas, local, data e assinatura;\n"
        "- seção final 'Observações ao cliente'."
    ),
)
