import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Central de Gestão ABC", layout="wide")

# Conecta ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Controle de sessão (Login)
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = None

def tela_login():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.subheader("Acesso à Central de Gestão")
        with st.form("form_login"):
            usuario = st.text_input("Login")
            senha = st.text_input("Senha", type="password")
            botao = st.form_submit_button("Entrar")
            
            if botao:
                if usuario == "admin" and senha == "1234":
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")

if not st.session_state.autenticado:
    tela_login()
else:
    st.sidebar.write(f"Conectado como: **{st.session_state.usuario}**")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.usuario = None
        st.rerun()

    st.title("Central de Gestão Operacional")

    # Leitura da planilha
    try:
        df = conn.read(ttl=0)
        
        # Garante a ordem prioritária das colunas
        ordem_prioritaria = ["login", "nome"]
        outras = [c for c in df.columns if c not in ordem_prioritaria]
        colunas_finais = [c for c in ordem_prioritaria if c in df.columns] + outras
        df = df[colunas_finais]

        st.subheader("Tabela Geral de Performance")
        st.dataframe(df, use_container_width=True)
    except Exception as erro:
        st.warning("Aguardando carregar dados da planilha...")

    # Formulário para adicionar novos registros
    st.markdown("---")
    st.subheader("Adicionar Registro")
    with st.form("novo_registro", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        novo_login = col_a.text_input("Login")
        novo_nome = col_b.text_input("Nome")
        
        col_c, col_d = st.columns(2)
        nova_regiao = col_c.text_input("Região")
        novos_pontos = col_d.number_input("Pontos", min_value=0, step=1)
        
        salvar = st.form_submit_button("Gravar na Planilha")
        
        if salvar:
            if novo_login and novo_nome:
                novo_df = pd.DataFrame([{
                    "login": novo_login,
                    "nome": novo_nome,
                    "regiao": nova_regiao,
                    "pontos": novos_pontos
                }])
                df_atualizado = pd.concat([df, novo_df], ignore_index=True)
                conn.update(data=df_atualizado)
                st.success("Registro adicionado com sucesso!")
                st.rerun()
            else:
                st.warning("Preencha ao menos Login e Nome.")
