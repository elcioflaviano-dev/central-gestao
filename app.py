import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Central de Gestão", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

def tela_login():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.subheader("Acesso Operacional")
        with st.form("form_login"):
            usuario = st.text_input("Login")
            senha = st.text_input("Senha", type="password")
            botao = st.form_submit_button("Entrar")
            
            if botao:
                df_usuarios = conn.read(worksheet="usuarios", ttl=0).dropna(how="all")
                if df_usuarios.empty:
                    st.error("Aba 'usuarios' está vazia ou não foi encontrada.")
                    return
                
                df_usuarios["login"] = df_usuarios["login"].astype(str).str.strip()
                df_usuarios["senha"] = df_usuarios["senha"].astype(str).str.strip()
                
                match = df_usuarios[(df_usuarios["login"] == usuario) & (df_usuarios["senha"] == senha)]
                
                if not match.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario
                    st.session_state.tipo = match.iloc[0]["tipo"].strip().lower()
                    st.session_state.nome_usuario = match.iloc[0]["nome"]
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
        # Carrega as duas abas
        df_tarefas = conn.read(worksheet="tarefas", ttl=0).dropna(how="all")
        df_usuarios = conn.read(worksheet="usuarios", ttl=0).dropna(how="all")
        
        # Garante a estrutura correta de colunas
        colunas_necessarias = ["login", "nome", "regiao", "tarefa", "status", "horario"]
        for col in colunas_necessarias:
            if col not in df_tarefas.columns:
                df_tarefas[col] = ""
        df_tarefas = df_tarefas[colunas_necessarias]

        # Gera a lista de técnicos dinamicamente para o dropdown
        tecnicos_df = df_usuarios[df_usuarios["tipo"].str.lower() == "tecnico"]
        lista_tecnicos = tecnicos_df["login"].astype(str).tolist()

        if st.session_state.tipo == "gestor":
            st.title("Painel de Controle - Gestão de Obrigações")
            
            st.subheader("Delegar Nova Tarefa")
            with st.form("nova_tarefa", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                if not lista_tecnicos:
                    st.warning("Cadastre usuários do tipo 'tecnico' na aba 'usuarios'.")
                    novo_login = None
                else:
                    novo_login = col1.selectbox("Selecionar Colaborador", lista_tecnicos)
                    
                nova_tarefa = col2.text_input("Descrição da Obrigação / Ordem de Serviço")
                
                col3, col4 = st.columns(2)
                nova_regiao = col3.selectbox("Região", ["ABCDM", "Guarulhos", "São Paulo"])
                novo_horario = col4.text_input("Horário Programado (ex: 14:00)")
                
                if st.form_submit_button("Atribuir Tarefa") and novo_login:
                    if nova_tarefa:
                        nome_tecnico = tecnicos_df[tecnicos_df["login"] == novo_login].iloc[0]["nome"]
                        novo_dado = pd.DataFrame([{
                            "login": novo_login, "nome": nome_tecnico, 
                            "regiao": nova_regiao, "tarefa": nova_tarefa, 
                            "status": "Pendente", "horario": novo_horario
                        }])
                        df_atualizado = pd.concat([df_tarefas, novo_dado], ignore_index=True)
                        conn.update(worksheet="tarefas", data=df_atualizado)
                        st.success(f"Obrigação enviada para {nome_tecnico}!")
                        st.rerun()
                    else:
                        st.warning("Preencha a descrição da tarefa.")

            st.markdown("---")
            st.subheader("Tabela Geral de Performance")
            df_editado = st.data_editor(df_tarefas, num_rows="dynamic", use_container_width=True)
            if st.button("Salvar Alterações Globais"):
                conn.update(worksheet="tarefas", data=df_editado)
                st.success("Planilha atualizada!")
                st.rerun()

        elif st.session_state.tipo == "tecnico":
            st.title("Minhas Obrigações")
            minhas_tarefas = df_tarefas[df_tarefas["login"] == st.session_state.usuario]
            
            if minhas_tarefas.empty:
                st.info("Nenhuma obrigação atribuída no momento.")
            else:
                for index, row in minhas_tarefas.iterrows():
                    cor_status = "🟢" if row["status"] == "Realizado" else "🔴"
                    with st.expander(f"{cor_status} {row['tarefa']} - {row['regiao']} (Horário: {row['horario']})"):
                        st.write(f"**Status atual:** {row['status']}")
                        if row["status"] != "Realizado":
                            if st.button("Marcar como Realizado", key=f"btn_{index}"):
                                df_tarefas.at[index, "status"] = "Realizado"
                                conn.update(worksheet="tarefas", data=df_tarefas)
                                st.success("Baixa confirmada!")
                                st.rerun()
                        else:
                            st.write("✅ Esta tarefa já foi concluída.")

    except Exception as e:
        st.error(f"Erro ao carregar dados. Verifique se as abas 'tarefas' e 'usuarios' estão nomeadas corretamente. Detalhes: {e}")
