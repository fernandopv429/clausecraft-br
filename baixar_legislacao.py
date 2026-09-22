# baixar_codigo_penal.py
"""
Baixa o texto compilado da legislação brasileira direto do Planalto e gera os JSONs em `dados/`.

Uso:
    python baixar_legislacao.py            # todos os diplomas
    python baixar_legislacao.py clt        # só a CLT

Rode sempre que quiser atualizar a base com as alterações legislativas mais recentes.
"""

import argparse
import json
import os
import re
import urllib.request
from html.parser import HTMLParser

from config import PASTA_DADOS

# Cada diploma segue a mesma estrutura hierárquica do Planalto, muda só a URL e o rótulo.
DIPLOMAS = {
    "cp": {
        "sigla": "CP",
        "nome": "Código Penal — Decreto-Lei nº 2.848/1940",
        "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm",
        "arquivo": "codigo_penal.json",
    },
    "clt": {
        "sigla": "CLT",
        "nome": "Consolidação das Leis do Trabalho — Decreto-Lei nº 5.452/1943",
        "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452compilado.htm",
        "arquivo": "clt.json",
    },
}

TAGS_BLOCO = {"p", "br", "div", "tr", "table", "td", "li", "h1", "h2", "h3", "h4", "h5"}

ROMANO = r"[IVXLC]+"
ROTULO = {"titulo": "Título", "capitulo": "Capítulo", "secao": "Seção"}

RE_PARTE = re.compile(r"^(?:PARTE|LIVRO)\s+([IVXLC]+|GERAL|ESPECIAL)\b", re.I)
RE_TITULO = re.compile(rf"^T[ÍI]TULO\s+({ROMANO})\b(.*)$", re.I)
RE_CAPITULO = re.compile(rf"^CAP[ÍI]TULO\s+({ROMANO})\b(.*)$", re.I)
RE_SECAO = re.compile(rf"^SE[ÇC][ÃA]O\s+({ROMANO})\b(.*)$", re.I)
# o Planalto às vezes duplica o ponto ("Art. . 189") ou omite ("Art 187")
RE_ARTIGO = re.compile(r"^Art(?:\s*\.){0,2}\s*(\d+)\s*[ºo°]?((?:-[A-Z])+)?(?![0-9A-Za-zà-úÀ-Ú])")
RE_NOTA = re.compile(r"^\((Redação|Incluíd|Vide|Vigência|Renumerad|Revogad|Expressão)", re.I)
RE_ESTRUTURA = re.compile(
    r"^(§|Par[áa]grafo|Pena|Multa|Deten[çc][ãa]o|Reclus[ãa]o|[IVXLC]+\s*[-–]|[a-z]\))", re.I
)


class _ExtratorTexto(HTMLParser):
    """Converte o HTML do Planalto em texto corrido, um parágrafo por linha."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.ignorar = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.ignorar += 1
        if tag in TAGS_BLOCO:
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.ignorar:
            self.ignorar -= 1
        if tag in TAGS_BLOCO:
            self.partes.append("\n")

    def handle_data(self, data):
        if not self.ignorar:
            self.partes.append(data.replace("\n", " ").replace("\r", " "))


def baixar_html(url: str) -> str:
    """Baixa a página do Planalto (codificação cp1252)."""
    requisicao = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(requisicao, timeout=120) as resposta:
        return resposta.read().decode("cp1252", errors="replace")


def html_para_linhas(html: str) -> list[str]:
    extrator = _ExtratorTexto()
    extrator.feed(html)
    texto = "".join(extrator.partes).replace("\xa0", " ")
    texto = re.sub(r"[ \t]+", " ", texto)
    return [linha.strip() for linha in texto.split("\n") if linha.strip()]


def _limpa(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def extrair_artigos(linhas: list[str]) -> list[dict]:
    """Percorre o texto e devolve um registro por artigo, com título/capítulo/seção."""
    # nem todo diploma tem PARTE/LIVRO (a CLT começa direto no TÍTULO I)
    inicio = next(
        (i for i, linha in enumerate(linhas) if RE_PARTE.match(linha) or RE_TITULO.match(linha)),
        0,
    )
    linhas = linhas[inicio:]

    artigos: list[dict] = []
    contexto = {
        "parte": None,
        "titulo": None, "titulo_nome": None,
        "capitulo": None, "capitulo_nome": None,
        "secao": None, "secao_nome": None,
    }
    atual = None
    rubrica_pendente = None

    def proxima_relevante(i: int) -> str:
        for linha in linhas[i + 1:]:
            if RE_NOTA.match(linha):
                continue
            return linha
        return ""

    def fechar():
        nonlocal atual
        if not atual:
            return
        corpo = _limpa(" ".join(atual.pop("_buffer")))
        abertura = _limpa(atual.pop("_abertura")).lstrip("-–. ")
        # o texto compilado termina com a assinatura do decreto; não faz parte do art. 361
        corpo = re.sub(r"^Art(?:\s*\.){1,2}\s*", "Art. ", corpo)  # o Planalto duplica o ponto em alguns artigos
        atual["texto"] = re.split(r"Rio de Janeiro, 7 de dezembro de 1940", corpo)[0].strip()
        atual["revogado"] = bool(re.match(r"^\(\s*Revogad", abertura))
        artigos.append(atual)
        atual = None

    for i, linha in enumerate(linhas):
        if RE_PARTE.match(linha):
            fechar()
            achado_parte = RE_PARTE.match(linha)
            contexto.update(
                parte=f"{linha.split()[0].upper()} {achado_parte.group(1).upper()}",
                titulo=None, titulo_nome=None, capitulo=None,
                capitulo_nome=None, secao=None, secao_nome=None,
            )
            rubrica_pendente = None
            continue

        for regex, chave in ((RE_TITULO, "titulo"), (RE_CAPITULO, "capitulo"), (RE_SECAO, "secao")):
            achou = regex.match(linha)
            if not achou:
                continue
            fechar()
            resto = _limpa(re.sub(r"\(.*?\)", "", achou.group(2) or ""))
            nome = resto or _limpa(re.sub(r"\(.*?\)", "", proxima_relevante(i)))
            contexto[chave] = f"{ROTULO[chave]} {achou.group(1).upper()}"
            contexto[f"{chave}_nome"] = nome
            if chave == "titulo":
                contexto.update(capitulo=None, capitulo_nome=None, secao=None, secao_nome=None)
            if chave == "capitulo":
                contexto.update(secao=None, secao_nome=None)
            rubrica_pendente = None
            break
        else:
            achou = RE_ARTIGO.match(linha)
            if achou:
                fechar()
                numero = achou.group(1) + (achou.group(2).upper() if achou.group(2) else "")
                atual = {
                    "parte": contexto["parte"],
                    "titulo": contexto["titulo"],
                    "titulo_nome": contexto["titulo_nome"],
                    "capitulo": contexto["capitulo"],
                    "capitulo_nome": contexto["capitulo_nome"],
                    "secao": contexto["secao"],
                    "secao_nome": contexto["secao_nome"],
                    "artigo": f"Art. {numero}",
                    "rubrica": rubrica_pendente,
                    "_buffer": [linha],
                    "_abertura": linha[achou.end():],
                }
                rubrica_pendente = None
                continue

            # nomen juris: linha curta que antecede imediatamente um artigo
            sem_nota = _limpa(re.sub(r"\(.*?\)", "", linha))
            if (
                sem_nota
                and len(sem_nota) < 130
                and not RE_ESTRUTURA.match(sem_nota)
                and proxima_relevante(i).startswith("Art")
            ):
                fechar()
                rubrica_pendente = sem_nota.rstrip(":.")
                continue

            if atual:
                atual["_buffer"].append(linha)

    fechar()
    return artigos


def baixar_diploma(chave: str):
    """Baixa, converte e salva um diploma em dados/<arquivo>.json."""
    diploma = DIPLOMAS[chave]
    print(f"⬇️  {diploma['nome']}")

    artigos = extrair_artigos(html_para_linhas(baixar_html(diploma["url"])))
    for artigo in artigos:
        artigo["diploma"] = diploma["sigla"]
        artigo["diploma_nome"] = diploma["nome"]

    os.makedirs(PASTA_DADOS, exist_ok=True)
    destino = os.path.join(PASTA_DADOS, diploma["arquivo"])
    with open(destino, "w", encoding="utf-8") as arquivo:
        json.dump(artigos, arquivo, ensure_ascii=False, indent=2)

    revogados = sum(1 for a in artigos if a["revogado"])
    print(f"✅ {len(artigos)} artigos em {destino} ({revogados} revogados)\n")
    return artigos


def main():
    parser = argparse.ArgumentParser(description="Baixa a legislação do Planalto")
    parser.add_argument(
        "diplomas", nargs="*", choices=[*DIPLOMAS, []],
        help=f"quais baixar ({', '.join(DIPLOMAS)}); vazio baixa todos",
    )
    escolhidos = parser.parse_args().diplomas or list(DIPLOMAS)
    for chave in escolhidos:
        baixar_diploma(chave)


if __name__ == "__main__":
    main()
