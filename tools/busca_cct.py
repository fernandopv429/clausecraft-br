# busca_cct.py

from datetime import date, datetime

from crewai.tools import tool

from cct_store import buscar_clausulas, categorias_no_banco, mapear_categoria

LIMITE_TEXTO = 900   # o trecho relevante da cláusula cabe aqui; o inteiro fica no banco
MAX_RESULTADOS = 5


@tool("Busca em Convenções Coletivas de Trabalho")
def buscar_clausula_cct(
    consulta: str,
    ramo_empregadora: str = "",
    data_referencia: str = "",
    categoria: str = "",
) -> list[dict]:
    """
    Busca cláusulas nas CCTs do escritório (SESVESP/vigilância, SIEMACO/asseio, SINDEEPRES/porteiros).

    Args:
        consulta: o que se procura, em linguagem natural
            (ex.: "percentual de hora extra", "piso salarial", "intervalo intrajornada").
        ramo_empregadora: atividade preponderante da EMPRESA empregadora
            (ex.: "empresa de vigilância patrimonial", "empresa de asseio e conservação",
            "empresa de prestação de serviços a terceiros", "restaurante", "construtora").
            É ela, e não a função do trabalhador, que define a convenção aplicável.
        categoria: informe só se já souber o recorte ('vigilancia', 'asseio', 'porteiros');
            normalmente deixe vazio e preencha `ramo_empregadora`.
        data_referencia: data no formato AAAA-MM-DD — normalmente a data da rescisão.
            Filtra apenas as convenções em vigor nessa data. Vazio busca em todas as vigências.

    Returns:
        list[dict]: cláusulas com número, título, texto, convenção de origem e período de vigência.
    """
    disponiveis = categorias_no_banco()

    if not categoria:
        categoria = mapear_categoria(ramo_empregadora) or ""
        if not categoria:
            return [
                {
                    "erro": "a atividade da empregadora não corresponde a nenhuma convenção indexada.",
                    "ramo_informado": ramo_empregadora or "(não informado)",
                    "categorias_disponiveis": disponiveis,
                    "orientacao": "A base cobre apenas vigilância, asseio/conservação e prestação de "
                    "serviços a terceiros, no Estado de São Paulo. Para qualquer outro ramo "
                    "(restaurante, comércio, transporte, construção), NÃO use nenhuma dessas "
                    "convenções: fundamente só na CLT e registre que a CCT da categoria precisa "
                    "ser juntada e conferida antes do protocolo.",
                }
            ]

    if categoria and categoria not in disponiveis:
        return [
            {
                "erro": f"não há convenção indexada para a categoria {categoria!r}.",
                "categorias_disponiveis": disponiveis,
                "orientacao": "Sem a CCT correta na base, NÃO use a convenção de outra categoria. "
                "Fundamente o pedido só na CLT e registre nas observações que o percentual "
                "convencional precisa ser conferido na CCT aplicável.",
            }
        ]

    vigente_em: date | None = None
    if data_referencia:
        try:
            vigente_em = datetime.strptime(data_referencia.strip(), "%Y-%m-%d").date()
        except ValueError:
            return [{"erro": "data_referencia deve estar no formato AAAA-MM-DD"}]

    # janela maior que a da legislação: tabelas de piso são densas e afundam no ranking
    resultados = buscar_clausulas(
        consulta=consulta,
        categoria=categoria or None,
        vigente_em=vigente_em,
        limite=MAX_RESULTADOS,
    )

    if not resultados:
        return [
            {
                "aviso": "Nenhuma cláusula encontrada para essa categoria nessa data de vigência.",
                "categorias_disponiveis": disponiveis,
                "orientacao": "NÃO recorra à convenção de outro período ou de outra categoria. "
                "Fundamente na CLT e registre a pendência para conferência humana.",
            }
        ]

    return [
        {
            "clausula": r["clausula_ref"],
            "titulo": r["clausula_titulo"],
            "texto": " ".join(r["conteudo"].split())[:LIMITE_TEXTO],
            "convencao": r["titulo"],
            "categoria": r["categoria"],
            "registro_mte": r["registro_mte"],
            "vigencia": f"{r['vigencia_inicio']} a {r['vigencia_fim']}",
            "similaridade": round(float(r["similaridade"]), 3),
        }
        for r in resultados
    ]
