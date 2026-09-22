# main.py

import argparse
import os

from crew import obter_equipe
from gerar_docx import markdown_para_docx
from roteador import classificar_materia

RELATO_EXEMPLO = (
    "Trabalhei como porteiro em um condomínio de São Paulo de 03/02/2020 até ser dispensado "
    "sem justa causa em 15/04/2024. Fazia escala 12x36, sempre das 19h às 7h, e quase nunca "
    "conseguia tirar o intervalo de refeição. Nunca recebi hora extra e não me pagaram as "
    "verbas rescisórias até hoje. Meu salário era R$ 1.800,00."
)


def executar(relato_do_cliente: str, trilha: str | None = None, saida: str = "peca.docx"):
    trilha = trilha or classificar_materia(relato_do_cliente)
    print(f"🧭 Trilha: {trilha}")

    resultado = obter_equipe(trilha).kickoff(inputs={"relato_do_cliente": relato_do_cliente})
    texto = resultado if isinstance(resultado, str) else str(resultado)

    print("-" * 60)
    print(texto)
    print("-" * 60)

    # o .docx é a entrega de verdade: leva logo no cabeçalho e contatos no rodapé
    caminho = markdown_para_docx(texto, os.path.abspath(saida))
    print(f"📄 Peça timbrada: {caminho}")
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assistente jurídico — penal e trabalhista")
    parser.add_argument("relato", nargs="*", help="o relato do cliente")
    parser.add_argument(
        "--trilha", choices=["penal", "trabalhista"],
        help="força a trilha em vez de deixar o roteador classificar",
    )
    parser.add_argument("--saida", default="peca.docx", help="arquivo .docx de saída")
    argumentos = parser.parse_args()
    executar(" ".join(argumentos.relato) or RELATO_EXEMPLO, argumentos.trilha, argumentos.saida)
