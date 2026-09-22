# preparar_pecas.py
"""
Lê as peças-modelo em .docx, quebra por capítulo, MASCARA os dados pessoais e
remove capítulos repetidos, gerando `dados/pecas_modelo.json`.

Os .docx originais ficam fora do repositório (config.PASTA_PECAS): eles contêm nome,
CPF e endereço de cliente. Só a versão mascarada é gravada e indexada.

Uso:
    python preparar_pecas.py            # gera o JSON e imprime o relatório de máscara
    python preparar_pecas.py --auditar  # só audita o que sobrou, sem gravar
"""

import argparse
import difflib
import json
import os
import re
import unicodedata
import zipfile

from config import PASTA_DADOS, PASTA_PECAS

ARQUIVO_SAIDA = os.path.join(PASTA_DADOS, "pecas_modelo.json")

RE_CAPITULO = re.compile(r"^(?:DA|DO|DAS|DOS)\s+[A-ZÀ-Ú0-9]")
LIMITE_IDENTICO = 0.98  # acima disso o capítulo é considerado o mesmo texto
LIMITE_FREQUENCIA_NOME = 12  # candidato que aparece mais que isso é palavra comum, não nome

# dado pessoal que sai por padrão; a ordem importa (CNPJ antes de CPF)
MASCARAS = [
    (re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"), "[CNPJ]"),
    (re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}"), "[CPF]"),
    (re.compile(r"\d{3}\.\d{5}\.\d{2}-\d"), "[PIS]"),
    (re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b"), "[PROCESSO]"),
    (re.compile(r"\b\d{5}-?\d{3}\b"), "[CEP]"),
    (re.compile(r"[\w.\-+]+@[\w.\-]+\.\w{2,}"), "[EMAIL]"),
    (re.compile(r"\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}"), "[TELEFONE]"),
    (re.compile(r"(RG|CTPS|PIS|Série|Serie)\s*(n[ºo°.]*)?\s*[\d.\-/]{4,}", re.I), r"\1 [NÚMERO]"),
    (re.compile(r"\b\d{2}/\d{2}/\d{4}\b"), "[DATA]"),
    (re.compile(r"OAB[/\s]*[A-Z]{2}\s*n?[ºo°.]*\s*[\d.]+", re.I), "OAB/[UF] [NÚMERO]"),
    # endereço residencial e da empresa: vai do marcador até o CEP ou o fim da qualificação
    (
        re.compile(
            r"((?:residente\s+e\s+)?domiciliad[oa]s?|com\s+sede|com\s+endereço|estabelecid[oa])"
            r"\s+(?:na|no|à|a|em)\s+.{5,180}?"
            r"(?=,?\s*(?:CEP|\[CEP\]|por seu|vem,|neste ato|e-?mail|\[EMAIL\]|$))",
            re.I | re.S,
        ),
        r"\1 [ENDEREÇO]",
    ),
    # filiação: nome dos pais do reclamante
    (re.compile(r"(filh[oa]\s+de)\s+[^,;\n]{5,100}", re.I), r"\1 [FILIAÇÃO]"),
    # qualquer logradouro, com ou sem marcador antes ("situada na Rua X, 769, Consolação, São Paulo/SP")
    (
        re.compile(
            # o endereço termina no CEP, na UF ("/SP", "- SP"), em ponto-e-vírgula ou fim de frase
            r"\b(?:Rua|Avenida|Av\.|Alameda|Travessa|Praça|Rodovia|Estrada)\s+[^;\n]{2,140}?"
            r"(?=\s*(?:,?\s*CEP|\[CEP\]|/\s*[A-Z]{2}\b|-\s*[A-Z]{2}\b|por seu|pelos motivos|;|\.|$))",
            re.I,
        ),
        "[ENDEREÇO]",
    ),
]

# palavras que parecem nome próprio mas são vocabulário jurídico
NAO_SAO_NOMES = {
    "excelentissimo", "senhor", "doutor", "juiz", "juiza", "vara", "trabalho", "justica",
    "reclamante", "reclamada", "reclamado", "consolidacao", "leis", "codigo", "processo",
    "civil", "federal", "constituicao", "sumula", "tribunal", "superior", "regional",
    "convencao", "coletiva", "clausula", "lei", "artigo", "paragrafo", "sao", "paulo",
    "brasil", "brasileiro", "brasileira", "estado", "ltda", "sociedade", "empresa",
    "condominio", "servicos", "seguranca", "limpeza", "portaria", "termos", "pede",
    "deferimento", "advogado", "oab", "cpf", "rg", "ctps", "pis", "fgts", "inss", "cct",
    # siglas jurídicas que aparecem poucas vezes e passariam pelo filtro de frequência
    "cpc", "clt", "tst", "trt", "stf", "stj", "cnj", "art", "inc", "acp", "dejt", "ccb",
    "sesvesp", "siemaco", "sindeepres", "pje", "esocial", "caged", "rais", "dsr", "jcj",
}


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def extrair_texto_docx(caminho: str) -> str:
    """Lê o texto do .docx sem dependência externa (docx é um zip com XML)."""
    with zipfile.ZipFile(caminho) as pacote:
        xml = pacote.read("word/document.xml").decode("utf-8")

    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    texto = re.sub(r"<[^>]+>", "", xml)
    for entidade, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&#8217;", "'")):
        texto = texto.replace(entidade, char)

    linhas = [re.sub(r"[ \t]+", " ", l).strip() for l in texto.split("\n")]
    return "\n".join(l for l in linhas if l)


def nomes_proprios(texto: str, arquivo: str) -> set[str]:
    """Levanta nomes de pessoas e empresas a partir da qualificação e do nome do arquivo."""
    candidatos: set[str] = set()

    # a qualificação vai do início até o título da peça
    corte = re.search(r"RECLAMA[ÇC][ÃA]O TRABALHISTA", texto, re.I)
    cabecalho = texto[: corte.start()] if corte else texto[:2000]

    # "FULANO DE TAL, brasileiro, ..." — o marcador pode vir algumas vírgulas depois
    # (ex.: "JOSÉ CARLOS ALVES TEIXEIRA, nascido em 10/05/1980, brasileiro, solteiro")
    for padrao in (
        r"([A-ZÀ-Ú][A-Za-zà-úÀ-Ú'`]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ú][A-Za-zà-úÀ-Ú'`]+){1,6})\s*,"
        r"(?:[^,\n]{0,70},){0,3}\s*(?:brasileir|nascid|portador|inscrit|solteir|casad)",
        r"em face (?:de|da|do)\s+([A-ZÀ-Ú][\w\sÀ-Úà-ú.'&-]{3,60}?)\s*,",
        r"([A-ZÀ-Ú][\w\sÀ-Úà-ú.'&-]{3,60}?)\s*,?\s*(?:pessoa jurídica|inscrita no CNPJ)",
    ):
        for achado in re.findall(padrao, cabecalho, re.I):
            candidatos.add(achado.strip())

    # linhas de qualificação em caixa alta: sequência de palavras maiúsculas que não é
    # vocabulário jurídico é, quase sempre, nome de pessoa ou de empresa.
    # Vale para o texto inteiro: as reclamadas às vezes são listadas depois do título da peça.
    for linha in texto.split("\n"):
        if not re.search(r"brasileir|nascid|portador|inscrit|CPF|CTPS|CNPJ|RECLAMADA", linha, re.I):
            continue
        for sequencia in re.findall(r"\b([A-ZÀ-Ú][A-ZÀ-Ú'`.]{1,}(?:\s+[A-ZÀ-Ú][A-ZÀ-Ú'`.]{1,}){1,6})\b", linha):
            partes = [p for p in sequencia.split() if sem_acento(p).lower() not in NAO_SAO_NOMES]
            if len(partes) >= 2:
                candidatos.add(" ".join(partes))

    # o nome do arquivo costuma trazer "Fulano x Empresa"
    base = re.sub(r"\.docx$", "", os.path.basename(arquivo), flags=re.I)
    base = re.sub(r"^\d+\s*-\s*|inicial|petição|peticao", " ", base, flags=re.I)
    for parte in re.split(r"\bx\b|[_\-()]", base):
        parte = parte.strip()
        if len(parte) > 2 and not parte.isdigit():
            candidatos.add(parte)

    # quebra em palavras isoladas, descartando vocabulário jurídico
    palavras: set[str] = set()
    for candidato in candidatos:
        for palavra in re.split(r"[\s.]+", candidato):
            palavra = palavra.strip(",;:'\"")
            # 3 letras entram porque razão social costuma ser sigla (XRS, ATS)
            if len(palavra) >= 3 and sem_acento(palavra).lower() not in NAO_SAO_NOMES:
                palavras.add(palavra)

    # trechos em caixa alta ("NÃO RECEBEU O PAGAMENTO") jogam palavra comum na lista.
    # Nome de parte aparece poucas vezes — a peça usa "reclamante"/"reclamada" —,
    # enquanto vocabulário jurídico se repete dezenas de vezes.
    return {
        palavra
        for palavra in palavras
        if len(re.findall(rf"\b{re.escape(palavra)}\b", texto, re.I)) <= LIMITE_FREQUENCIA_NOME
    }


def mascarar(texto: str, nomes: set[str]) -> str:
    """Troca dados pessoais por marcadores. Nomes viram [NOME]."""
    for padrao, substituto in MASCARAS:
        texto = padrao.sub(substituto, texto)

    for nome in sorted(nomes, key=len, reverse=True):
        texto = re.sub(rf"\b{re.escape(nome)}\b", "[NOME]", texto, flags=re.I)

    return re.sub(r"(\[NOME\]\s*){2,}", "[NOME] ", texto)


def quebrar_por_capitulo(texto: str) -> list[dict]:
    """Divide a peça em capítulos; o texto antes do primeiro vira 'ENDEREÇAMENTO E QUALIFICAÇÃO'."""
    linhas = texto.split("\n")
    capitulos, atual = [], {"capitulo": "ENDEREÇAMENTO E QUALIFICAÇÃO", "linhas": []}

    for linha in linhas:
        if RE_CAPITULO.match(linha) and len(linha) < 120:
            if atual["linhas"]:
                capitulos.append(atual)
            atual = {"capitulo": re.sub(r"\s+", " ", linha).strip(), "linhas": []}
        else:
            atual["linhas"].append(linha)

    if atual["linhas"]:
        capitulos.append(atual)

    return [
        {"capitulo": c["capitulo"], "texto": "\n".join(c["linhas"]).strip()}
        for c in capitulos
        if "\n".join(c["linhas"]).strip()
    ]


def deduplicar(capitulos: list[dict]) -> list[dict]:
    """Mantém uma versão canônica por capítulo e guarda as variantes que divergem de fato."""
    agrupados: dict[str, list[dict]] = {}

    for item in capitulos:
        chave = sem_acento(item["capitulo"]).upper()
        grupo = agrupados.setdefault(chave, [])

        for existente in grupo:
            similaridade = difflib.SequenceMatcher(
                None, existente["texto"].split(), item["texto"].split(), autojunk=False
            ).ratio()
            if similaridade >= LIMITE_IDENTICO:
                existente["ocorrencias"] += 1
                existente["origem"].append(item["origem"])
                break
        else:
            grupo.append({**item, "ocorrencias": 1, "origem": [item["origem"]]})

    finais = []
    for grupo in agrupados.values():
        for i, item in enumerate(grupo, start=1):
            item["variante"] = i
            item["total_variantes"] = len(grupo)
            finais.append(item)
    return finais


def auditar(capitulos: list[dict]) -> dict:
    """Procura dado pessoal que possa ter escapado da máscara."""
    tudo = "\n".join(c["texto"] for c in capitulos)
    residuos = {
        "CPF": re.findall(r"\d{3}\.\d{3}\.\d{3}-\d{2}", tudo),
        "CNPJ": re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", tudo),
        "e-mail": re.findall(r"[\w.\-+]+@[\w.\-]+\.\w{2,}", tudo),
        "data completa": re.findall(r"\b\d{2}/\d{2}/\d{4}\b", tudo),
    }
    # nomes próprios que sobraram: pares de palavras capitalizadas fora do vocabulário jurídico
    suspeitos = {
        par
        for par in re.findall(r"\b([A-ZÀ-Ú][a-zà-ú]{2,}\s+[A-ZÀ-Ú][a-zà-ú]{2,})\b", tudo)
        if sem_acento(par.split()[0]).lower() not in NAO_SAO_NOMES
    }
    return {"residuos": {k: v for k, v in residuos.items() if v}, "suspeitos": sorted(suspeitos)[:25]}


def preparar(gravar: bool = True):
    if not PASTA_PECAS:
        raise SystemExit(
            "❌ defina PASTA_PECAS com o caminho dos .docx originais "
            "(ex.: PASTA_PECAS=~/peticoes python preparar_pecas.py)"
        )
    if not os.path.isdir(PASTA_PECAS):
        raise SystemExit(f"❌ pasta das peças não encontrada: {PASTA_PECAS}")

    arquivos = sorted(
        os.path.join(raiz, nome)
        for raiz, _, nomes in os.walk(PASTA_PECAS)
        for nome in nomes
        if nome.lower().endswith(".docx") and not nome.startswith("~$")
    )

    capitulos = []
    for caminho in arquivos:
        texto = extrair_texto_docx(caminho)
        nomes = nomes_proprios(texto, caminho)
        origem = os.path.basename(caminho)

        # fatiar antes de mascarar: nome de empresa que coincide com palavra do título
        # (VALE, TRANSPORTE, SEGURANÇA) apagaria o cabeçalho do capítulo e fundiria seções
        do_arquivo = quebrar_por_capitulo(texto)
        for item in do_arquivo:
            item["texto"] = mascarar(item["texto"], nomes)
            item["origem"] = origem
        capitulos.extend(do_arquivo)
        print(f"📄 {origem[:46]:<48} {len(do_arquivo):>3} capítulos | {len(nomes)} nomes mascarados")

    finais = deduplicar(capitulos)
    identicos = sum(1 for c in finais if c["ocorrencias"] > 1)
    print(f"\n{len(capitulos)} capítulos lidos → {len(finais)} após deduplicação "
          f"({identicos} apareciam repetidos em mais de uma peça)")

    relatorio = auditar(finais)
    if relatorio["residuos"]:
        print("\n⚠️  Dado pessoal que escapou da máscara:")
        for tipo, itens in relatorio["residuos"].items():
            print(f"   {tipo}: {len(itens)} — ex.: {itens[0]}")
    else:
        print("\n✅ Nenhum CPF, CNPJ, e-mail ou data completa restante")

    if relatorio["suspeitos"]:
        print(f"\n🔎 Possíveis nomes remanescentes (confira antes de indexar): "
              f"{', '.join(relatorio['suspeitos'][:12])}")

    if gravar:
        os.makedirs(PASTA_DADOS, exist_ok=True)
        with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as arquivo:
            json.dump(finais, arquivo, ensure_ascii=False, indent=2)
        print(f"\n💾 {ARQUIVO_SAIDA}")

    return finais


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepara as peças-modelo (mascara e deduplica)")
    parser.add_argument("--auditar", action="store_true", help="não grava, só audita")
    preparar(gravar=not parser.parse_args().auditar)
