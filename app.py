# app.py

import os

import streamlit as st

from config import (
    MODELO_LLM,
    NOME_COLECAO,
    URL_POSTGRES,
    criar_vectorstore,
    validar_ambiente,
)
from crew import obter_equipe
from gerar_docx import markdown_para_docx
from roteador import classificar_materia

st.set_page_config(page_title="Assistente Jurídico (Brasil)", page_icon="⚖️", layout="wide")


def _liberado() -> bool:
    """Trava por senha. Sem APP_SENHA definida o app fica aberto (uso local)."""
    senha_esperada = os.getenv("APP_SENHA", "")
    if not senha_esperada:
        return True
    if st.session_state.get("autenticado"):
        return True

    st.title("⚖️ Assistente Jurídico")
    st.caption("Acesso restrito.")
    with st.form("acesso"):
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if senha == senha_esperada:
                st.session_state["autenticado"] = True
                st.rerun()
            st.error("Senha incorreta.")
    return False


if not _liberado():
    st.stop()

_faltando = validar_ambiente()
if _faltando:
    st.error(
        "Configuração incompleta — defina estas variáveis de ambiente no painel de deploy:\n\n"
        + "\n".join(f"- `{item}`" for item in _faltando)
    )
    st.stop()

st.title("⚖️ Assistente Jurídico — Legislação Brasileira")
st.markdown(
    "Descreva o caso em linguagem comum. O assistente identifica a matéria e segue a trilha correspondente:\n\n"
    "- **Penal** — artigos do Código Penal, jurisprudência e notícia-crime, representação ou queixa-crime;\n"
    "- **Trabalhista** — cláusulas da convenção coletiva vigente na data da rescisão, jurisprudência "
    "do TST e reclamação trabalhista."
)

@st.cache_resource(show_spinner=False)
def _verificar_base() -> str:
    """Confere se a coleção pgvector responde antes de liberar o formulário."""
    if not URL_POSTGRES:
        return "POSTGRES_URL não configurada no arquivo .env."
    try:
        criar_vectorstore().similarity_search("furto", k=1)
    except Exception as erro:  # conexão, extensão ausente ou coleção vazia
        return str(erro)
    return ""


falha = _verificar_base()
if falha:
    st.error(
        f"Não foi possível consultar a base do Código Penal (coleção `{NOME_COLECAO}`): {falha}\n\n"
        "Verifique a `POSTGRES_URL` no `.env` e rode `python construir_vectordb.py`."
    )

with st.sidebar:
    st.subheader("Configuração")
    st.write(f"**Modelo:** `{MODELO_LLM}`")
    st.write("**Base legal:** Código Penal (texto compilado do Planalto)")
    st.write(f"**Vetores:** PostgreSQL/pgvector — coleção `{NOME_COLECAO}`")
    st.write("**CCTs:** SESVESP, SIEMACO e SINDEEPRES (2020–2026/27)")
    st.caption(
        "Para atualizar a legislação: `python baixar_codigo_penal.py` e depois "
        "`python construir_vectordb.py`."
    )

with st.form("formulario_juridico"):
    relato = st.text_area("📝 Descreva o caso:", height=250)
    escolha_trilha = st.radio(
        "Trilha:", ["Detectar automaticamente", "Penal", "Trabalhista"], horizontal=True
    )
    enviado = st.form_submit_button("🔍 Analisar caso")

if enviado:
    if not relato.strip():
        st.warning("Descreva o caso para que a análise possa ser feita.")
    else:
        with st.spinner("🧭 Identificando a matéria..."):
            trilha = (
                classificar_materia(relato)
                if escolha_trilha == "Detectar automaticamente"
                else escolha_trilha.lower()
            )
        st.info(f"Trilha: **{trilha}**")

        with st.spinner("🔎 Analisando os fatos e preparando a peça..."):
            resultado = obter_equipe(trilha).kickoff(inputs={"relato_do_cliente": relato})

        st.success("✅ Análise concluída.")
        st.subheader("📄 Resultado")
        texto = resultado if isinstance(resultado, str) else str(resultado)
        st.markdown(texto)

        # .docx timbrado: cabeçalho e rodapé do escritório são imagens e só existem no Word
        import io, tempfile

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temporario:
            markdown_para_docx(texto, temporario.name)
        with open(temporario.name, "rb") as arquivo:
            st.download_button(
                "⬇️ Baixar peça timbrada (.docx)",
                io.BytesIO(arquivo.read()),
                file_name="peca.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        st.download_button("⬇️ Baixar como texto (.md)", texto, file_name="peca.md")

st.divider()
st.caption(
    "⚠️ Conteúdo gerado por IA, sujeito a erros. Não substitui a análise de advogado inscrito na OAB. "
    "Confira sempre o texto legal no Planalto e a jurisprudência nos sites oficiais dos tribunais "
    "antes de protocolar qualquer peça."
)
