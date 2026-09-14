import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Central de Gestão", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

USUARIOS = {
    "admin": {"senha": "1234", "tipo": "gestor", "nome": "Elcio"},
    "tec01": {"senha": "1234", "tipo": "tecnico", "nome": "Carlos Silva"},
    "tec02": {"senha": "1234", "tipo": "tecnico", "nome": "Ana Souza"}
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = None
    st.session_state.tipo = None

def tela_login():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.subheader("Acesso Operacional")
        with st.form("form_login"):
            usuario = st.text_input("Login")
            senha = st.text_input("Senha", type="password")
            botao = st.form_submit_button("Entrar")
            
            if botao:
                if usuario in USUARIOS and USUARIOS[usuario]["senha"] == senha:
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario
                    st.session_state.tipo = USUARIOS[usuario]["tipo"]
                    st.session_state.nome_usuario = USUARIOS[usuario]["nome"]
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")

if not st.session_state.autenticado:
    tela_login()
else:
    st.sidebar.write(f"Olá, **{st.session_state.nome_usuario}**")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    try:
        df = conn.read(ttl=0).dropna(how="all")
        
        # Estrutura com horário programado
        colunas_necessarias = ["login", "nome", "regiao", "tarefa", "status", "horario"]
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = ""
                
        df = df[colunas_necessarias]

        # VISÃO DO GESTOR (ADMIN)
        if st.session_state.tipo == "gestor":
            st.title("Painel de Controle - Visão Geral")
            
            st.subheader("Delegar Nova Tarefa")
            with st.form("nova_tarefa", clear_on_submit=True):
                col1, col2 = st.columns(2)
                novo_login = col1.selectbox("Selecionar Técnico", ["tec01", "tec02"])
                nova_tarefa = col2.text_input("Descrição da Tarefa / Ordem de Serviço")
                
                col3, col4 = st.columns(2)
                nova_regiao = col3.selectbox("Região", ["ABCDM", "Guarulhos", "São Paulo"])
                novo_horario = col4.text_input("Horário Programado (ex: 14:00)")
                
                if st.form_submit_button("Atribuir Tarefa"):
                    if nova_tarefa:
                        novo_nome = USUARIOS[novo_login]["nome"]
                        novo_dado = pd.DataFrame([{
                            "login": novo_login, "nome": novo_nome, 
                            "regiao": nova_regiao, "tarefa": nova_tarefa, 
                            "status": "Pendente", "horario": novo_horario
                        }])
                        df_atualizado = pd.concat([df, novo_dado], ignore_index=True)
                        conn.update(data=df_atualizado)
                        st.success(f"Tarefa enviada para {novo_nome}!")
                        st.rerun()
                    else:
                        st.warning("Preencha a descrição da tarefa.")

            st.markdown("---")
            st.subheader("Tabela Geral de Performance")
            df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("Salvar Alterações Globais na Planilha"):
                conn.update(data=df_editado)
                st.success("Planilha atualizada!")
                st.rerun()

        # VISÃO DO TÉCNICO
        elif st.session_state.tipo == "tecnico":
            st.title("Minhas Ordens de Serviço")
            minhas_tarefas = df[df["login"] == st.session_state.usuario]
            
            if minhas_tarefas.empty:
                st.info("Nenhuma tarefa atribuída no momento.")
            else:
                for index, row in minhas_tarefas.iterrows():
                    cor_status = "🟢" if row["status"] == "Realizado" else "🔴"
                    
                    with st.expander(f"{cor_status} {row['tarefa']} - {row['regiao']} (Horário: {row['horario']})"):
                        st.write(f"**Status atual:** {row['status']}")
                        
                        if row["status"] != "Realizado":
                            if st.button("Marcar como Realizado", key=f"btn_{index}"):
                                df.at[index, "status"] = "Realizado"
                                conn.update(data=df)
                                st.success("Baixa confirmada!")
                                st.rerun()
                        else:
                            st.write("✅ Esta tarefa já foi concluída.")

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
