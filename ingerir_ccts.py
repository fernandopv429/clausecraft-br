# ingerir_ccts.py
"""
Lê as CCTs em PDF, quebra por cláusula e grava no PostgreSQL com os metadados
extraídos do próprio documento (padrão do sistema Mediador/MTE).

Uso:
    python ingerir_ccts.py                 # ingere tudo que ainda não foi ingerido
    python ingerir_ccts.py --refazer       # apaga e reingere tudo
"""

import argparse
import hashlib
import os
import re
from datetime import date

from pypdf import PdfReader

from cct_store import (
    conectar,
    criar_schema,
    documento_ja_ingerido,
    gravar_documento,
    registro_ja_ingerido,
)

PASTA_CCTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados", "ccts")

# A categoria é o nome da pasta, não uma lista fixa: para cobrir uma convenção nova basta
# criar `dados/ccts/<categoria>/` e soltar o PDF lá.
APELIDOS_CATEGORIA = {
    "sesvesp_vigilantes": "vigilancia",
    "siemaco_asseio": "asseio",
    "sindeepres_porteiros": "porteiros",
}


def categorias_disponiveis() -> dict[str, str]:
    """Mapeia pasta -> categoria, lendo o que existe em dados/ccts/."""
    if not os.path.isdir(PASTA_CCTS):
        return {}
    return {
        pasta: APELIDOS_CATEGORIA.get(pasta, pasta)
        for pasta in sorted(os.listdir(PASTA_CCTS))
        if os.path.isdir(os.path.join(PASTA_CCTS, pasta))
    }

MAX_CARACTERES = 3000  # cláusulas muito longas são subdivididas

RE_CLAUSULA = re.compile(
    r"^\s*CL[ÁA]USULA\s+([A-ZÀ-Ú\d\ºªa-z]+(?:\s+[A-ZÀ-Ú\d\ºªa-z]+){0,3}?)\s*[-–—]\s*(.+)$",
    re.MULTILINE,
)
RE_REGISTRO = re.compile(r"N[ÚU]MERO DE REGISTRO NO MTE:\s*([A-Z]{2}\d+/\d{4})", re.I)
# no padrão Mediador, os dois entes vêm antes de "celebram": primeiro o laboral, depois o patronal
RE_SINDICATOS = re.compile(
    r"(SIND[^;]{10,300}?),\s*CNPJ[^;]{10,200};.{0,80}?\bE\b.{0,80}?(SIND[^;]{10,300}?),\s*CNPJ",
    re.I | re.S,
)
RE_ABRANGENCIA = re.compile(r"abrang[êe]r[áa]?\s+a\(s\)\s+categoria[^.]{20,600}?\.", re.I | re.S)
RE_TITULO = re.compile(r"^\s*((?:TERMO ADITIVO A )?CONVEN[ÇC][ÃA]O COLETIVA DE TRABALHO[^\n]*)", re.I | re.MULTILINE)
# a janela após "no período de" contém as duas datas da vigência, às vezes quebradas por \n
RE_JANELA_VIGENCIA = re.compile(r"vig[êe]ncia.{0,300}?per[íi]odo de(.{0,200})", re.I | re.S)
RE_DATA = re.compile(
    r"\d{1,2}\s*[ºo°]?\s*de\s+[a-zà-ú]+\s+de\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}", re.I
)

MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


# cabeçalho/rodapé que o sistema Mediador imprime em toda página e que polui as cláusulas
RUIDOS_PDF = [
    re.compile(r"\d{2}/\d{2}/\d{4},?\s*\d{2}:\d{2}\s*Mediador\s*-\s*Extrato[^\n]*"),
    re.compile(r"www3?\.mte\.gov\.br/sistemas/mediador/\S*"),
    re.compile(r"Confira a autenticidade no endereço[^\n]*"),
    re.compile(r"^\s*\d{1,3}\s*/\s*\d{1,3}\s*$", re.MULTILINE),
]


def limpar_ruido(texto: str) -> str:
    """Remove cabeçalho, rodapé e numeração de página repetidos em cada folha do PDF."""
    for padrao in RUIDOS_PDF:
        texto = padrao.sub(" ", texto)
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    return re.sub(r"\n{3,}", "\n\n", texto)


def extrair_texto(caminho: str) -> str:
    leitor = PdfReader(caminho)
    bruto = "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)
    return limpar_ruido(bruto)


def _data_por_extenso(texto: str) -> date | None:
    """Converte '01º de janeiro de 2026' (ou '01/01/2026') em date."""
    texto = re.sub(r"\s+", " ", texto).strip()

    numerica = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
    if numerica:
        dia, mes, ano = (int(g) for g in numerica.groups())
        return date(ano, mes, dia)

    extenso = re.search(r"(\d{1,2})\s*[ºo°]?\s*de\s+([a-zà-ú]+)\s+de\s+(\d{4})", texto, re.I)
    if extenso:
        dia, mes, ano = extenso.group(1), extenso.group(2).lower(), extenso.group(3)
        if mes in MESES:
            return date(int(ano), MESES[mes], int(dia))
    return None


def extrair_metadados(texto: str, arquivo: str, categoria: str) -> dict:
    """Puxa registro no MTE, título e janela de vigência do próprio texto da CCT."""
    registro = RE_REGISTRO.search(texto)
    titulo = RE_TITULO.search(texto)

    inicio = fim = None
    janela = RE_JANELA_VIGENCIA.search(texto)
    if janela:
        datas = [_data_por_extenso(d) for d in RE_DATA.findall(janela.group(1))]
        datas = [d for d in datas if d]
        if datas:
            inicio = datas[0]
            fim = datas[1] if len(datas) > 1 else None

    titulo_limpo = re.sub(r"\s+", " ", titulo.group(1)).strip() if titulo else arquivo
    ehaditivo = "TERMO ADITIVO" in titulo_limpo.upper()

    sindicatos = RE_SINDICATOS.search(texto)
    laboral = patronal = None
    if sindicatos:
        primeiro = re.sub(r"\s+", " ", sindicatos.group(1)).strip()[:250]
        segundo = re.sub(r"\s+", " ", sindicatos.group(2)).strip()[:250]
        # a ordem varia no documento; quem fala em "empresas" é o patronal,
        # quem fala em "empregados/trabalhadores" é o laboral
        def eh_patronal(nome: str) -> bool:
            return bool(re.search(r"\bEMPRES|PATRON", nome, re.I)) and not re.search(
                r"EMPREGADOS? (EM|D[EO])|TRABALHADORES", nome, re.I
            )

        if eh_patronal(primeiro) and not eh_patronal(segundo):
            laboral, patronal = segundo, primeiro
        else:
            laboral, patronal = primeiro, segundo

    abrangencia = RE_ABRANGENCIA.search(texto)
    base_territorial = re.sub(r"\s+", " ", abrangencia.group(0)).strip()[:400] if abrangencia else None

    return {
        "arquivo": arquivo,
        "categoria": categoria,
        "tipo": "termo_aditivo" if ehaditivo else "cct",
        "titulo": titulo_limpo[:300],
        "registro_mte": registro.group(1) if registro else None,
        "vigencia_inicio": inicio,
        "vigencia_fim": fim,
        "sindicato_laboral": laboral,
        "sindicato_patronal": patronal,
        "base_territorial": base_territorial,
        "abrangencia": "estadual",
        "municipios": None,
    }


def quebrar_por_clausula(texto: str) -> list[dict]:
    """Divide o texto em cláusulas; cláusulas longas viram vários pedaços."""
    ocorrencias = list(RE_CLAUSULA.finditer(texto))
    if not ocorrencias:
        return [
            {"clausula_ref": None, "clausula_titulo": None, "conteudo": texto[i:i + MAX_CARACTERES]}
            for i in range(0, len(texto), MAX_CARACTERES)
            if texto[i:i + MAX_CARACTERES].strip()
        ]

    pedacos = []
    preambulo = texto[: ocorrencias[0].start()].strip()
    if preambulo:
        pedacos.append({"clausula_ref": None, "clausula_titulo": "Preâmbulo", "conteudo": preambulo[:MAX_CARACTERES]})

    for i, achado in enumerate(ocorrencias):
        fim = ocorrencias[i + 1].start() if i + 1 < len(ocorrencias) else len(texto)
        corpo = texto[achado.start():fim].strip()
        referencia = f"CLÁUSULA {achado.group(1).strip().upper()}"
        titulo = re.sub(r"\s+", " ", achado.group(2)).strip()[:200]

        for j in range(0, len(corpo), MAX_CARACTERES):
            trecho = corpo[j:j + MAX_CARACTERES].strip()
            if trecho:
                pedacos.append({"clausula_ref": referencia, "clausula_titulo": titulo, "conteudo": trecho})

    return pedacos


def atualizar_metadados():
    """Reprocessa só os metadados dos documentos já ingeridos (não gera embeddings)."""
    atualizados = 0
    with conectar() as conexao, conexao.cursor() as cursor:
        cursor.execute("SELECT id, arquivo, categoria FROM cct_documentos ORDER BY id")
        documentos = cursor.fetchall()

    for documento_id, arquivo, categoria in documentos:
        pasta = next(p for p, c in categorias_disponiveis().items() if c == categoria)
        caminho = os.path.join(PASTA_CCTS, pasta, arquivo)
        if not os.path.exists(caminho):
            print(f"⚠️  {arquivo} — arquivo não encontrado")
            continue

        meta = extrair_metadados(extrair_texto(caminho), arquivo, categoria)
        with conectar() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                """
                UPDATE cct_documentos
                   SET titulo = %s, tipo = %s, registro_mte = %s,
                       vigencia_inicio = %s, vigencia_fim = %s,
                       sindicato_laboral = %s, sindicato_patronal = %s, base_territorial = %s
                 WHERE id = %s
                """,
                (meta["titulo"], meta["tipo"], meta["registro_mte"],
                 meta["vigencia_inicio"], meta["vigencia_fim"], meta["sindicato_laboral"],
                 meta["sindicato_patronal"], meta["base_territorial"], documento_id),
            )
        atualizados += 1
        print(f"🔄 {arquivo[:45]:<47} {meta['vigencia_inicio']} a {meta['vigencia_fim']}")

    print(f"\n{atualizados} documentos atualizados")


def ingerir(refazer: bool = False):
    criar_schema()

    if refazer:
        with conectar() as conexao, conexao.cursor() as cursor:
            cursor.execute("TRUNCATE cct_chunks, cct_documentos RESTART IDENTITY CASCADE")
        print("🗑️  Tabelas de CCT limpas")

    total_docs = total_clausulas = 0

    for pasta, categoria in categorias_disponiveis().items():
        caminho_pasta = os.path.join(PASTA_CCTS, pasta)
        if not os.path.isdir(caminho_pasta):
            continue

        for arquivo in sorted(os.listdir(caminho_pasta)):
            if not arquivo.lower().endswith(".pdf"):
                continue

            caminho = os.path.join(caminho_pasta, arquivo)
            with open(caminho, "rb") as f:
                hash_arquivo = hashlib.sha256(f.read()).hexdigest()

            if documento_ja_ingerido(hash_arquivo):
                print(f"⏭️  {arquivo} — já ingerido")
                continue

            texto = extrair_texto(caminho)
            if len(texto.strip()) < 500:
                print(f"⚠️  {arquivo} — texto insuficiente ({len(texto)} chars), possivelmente PDF escaneado")
                continue

            meta = extrair_metadados(texto, arquivo, categoria)

            duplicata = registro_ja_ingerido(meta["registro_mte"])
            if duplicata:
                print(f"⏭️  {arquivo} — mesmo registro MTE de '{duplicata}'")
                continue

            meta["hash_arquivo"] = hash_arquivo
            chunks = quebrar_por_clausula(texto)

            gravar_documento(meta, chunks)
            total_docs += 1
            total_clausulas += len(chunks)

            vigencia = (
                f"{meta['vigencia_inicio']} a {meta['vigencia_fim']}"
                if meta["vigencia_inicio"] else "vigência não detectada"
            )
            print(f"✅ {arquivo[:45]:<47} {len(chunks):>3} cláusulas | {vigencia} | {meta['registro_mte'] or 's/ registro'}")

    print(f"\n{total_docs} documentos e {total_clausulas} cláusulas ingeridos")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingere as CCTs no PostgreSQL")
    parser.add_argument("--refazer", action="store_true", help="apaga tudo e reingere")
    parser.add_argument(
        "--so-metadados", action="store_true",
        help="só reprocessa metadados dos documentos já ingeridos, sem gerar embeddings",
    )
    argumentos = parser.parse_args()
    if argumentos.so_metadados:
        atualizar_metadados()
    else:
        ingerir(refazer=argumentos.refazer)
