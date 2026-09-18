import json
import os
import uuid
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_ID", "1tjN1xi_Qx5OJz9mD-h4ylwQ7M6tc8dD_MaeX-rgpw3k")
TZ = ZoneInfo("America/Sao_Paulo")
STATUS = ["Aberta", "Em andamento", "Concluída", "Atrasada"]
JANELAS = ["08:00 às 12:00", "12:00 às 15:00", "15:00 às 18:00", "Fechamento do dia"]
TASK_COLUMNS = ["id", "login", "nome", "tipo", "regiao", "tarefa", "criterio_conclusao", "status", "data", "horario", "janela", "prazo_original", "novo_prazo", "recorrencia", "concluida_em", "justificativa_atraso", "observacao", "criada_em", "atualizada_em", "atualizada_por"]
USER_COLUMNS = ["login", "senha", "nome", "tipo", "regiao", "ativo"]
ROLE_TEXT = {
    "gestor": "Define prioridades, acompanha Supervisor e Coordenador e atua nas exceções da operação.",
    "gerente": "Define prioridades, acompanha Supervisor e Coordenador e atua nas exceções da operação.",
    "supervisor": "Garante a execução diária da equipe, acompanha as janelas e fecha suas próprias demandas.",
    "coordenador": "Coordena os processos operacionais, acompanha o Supervisor e fecha suas próprias demandas.",
}

st.set_page_config(page_title="Central de Gestão ABC", page_icon="📋", layout="wide")
st.markdown("""
<style>
#MainMenu,footer{visibility:hidden}.block-container{padding-top:1.2rem;max-width:1250px}
[data-testid="stSidebar"]{background:#f4f7fb;border-right:1px solid #dde5ef}
.role-card{background:linear-gradient(135deg,#0b4f8a,#1479bc);color:white;padding:18px 22px;border-radius:14px;margin-bottom:18px}
.role-card h3{color:white;margin:0 0 6px}.role-card p{margin:0}.stButton>button{border-radius:9px;font-weight:600}
@media(max-width:640px){.block-container{padding:.8rem}.role-card{padding:14px}}
</style>""", unsafe_allow_html=True)

def now(): return datetime.now(TZ)

def credentials_info():
    if "gcp_service_account" in st.secrets:
        return dict(st.secrets["gcp_service_account"])
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw: return json.loads(raw)
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f: return json.load(f)
    raise RuntimeError("Credencial ausente. Configure [gcp_service_account] no Secrets do Streamlit.")

@st.cache_resource(show_spinner=False)
def spreadsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
    creds = Credentials.from_service_account_info(credentials_info(), scopes=scopes)
    return gspread.authorize(creds).open_by_key(SPREADSHEET_ID)

def worksheet(name, headers):
    book = spreadsheet()
    try: ws = book.worksheet(name)
    except gspread.WorksheetNotFound: ws = book.add_worksheet(title=name, rows=1000, cols=max(20, len(headers)))
    values = ws.get_all_values()
    if not values: ws.append_row(headers, value_input_option="RAW")
    else:
        current = values[0]
        missing = [h for h in headers if h not in current]
        if missing:
            end = gspread.utils.rowcol_to_a1(1, len(current) + len(missing))
            ws.update(range_name=f"A1:{end}", values=[current + missing])
    return ws

def read_df(name, headers):
    ws = worksheet(name, headers)
    df = pd.DataFrame(ws.get_all_records(numericise_ignore=["all"]))
    for col in headers:
        if col not in df.columns: df[col] = ""
    return df.fillna(""), ws

def ensure_task_ids(df, ws):
    if df.empty: return df
    id_col = ws.row_values(1).index("id") + 1
    for pos, value in enumerate(df["id"].astype(str), start=2):
        if not value.strip():
            value = str(uuid.uuid4()); ws.update_cell(pos, id_col, value); df.at[pos - 2, "id"] = value
    return df

def append_row(ws, row):
    headers = ws.row_values(1)
    ws.append_row([str(row.get(h, "")) for h in headers], value_input_option="USER_ENTERED")

def update_task(ws, task_id, changes):
    values = ws.get_all_values()
    if not values or "id" not in values[0]: return False
    header, id_idx = values[0], values[0].index("id")
    for row_number, row in enumerate(values[1:], start=2):
        if len(row) > id_idx and row[id_idx] == task_id:
            for field, value in changes.items():
                if field in header: ws.update_cell(row_number, header.index(field) + 1, str(value))
            return True
    return False

def normalize_status(value):
    value = str(value).strip().lower()
    return {"pendente":"Aberta", "realizado":"Concluída", "concluido":"Concluída", "concluída":"Concluída", "em andamento":"Em andamento", "atrasada":"Atrasada"}.get(value, "Aberta")

def effective_status(row):
    status = normalize_status(row.get("status", ""))
    if status == "Concluída": return status
    deadline = str(row.get("novo_prazo") or row.get("prazo_original") or "").strip()
    if not deadline: deadline = f"{row.get('data','')} {row.get('horario','')}".strip()
    parsed = pd.to_datetime(deadline, dayfirst=True, errors="coerce")
    if pd.notna(parsed):
        local = parsed.to_pydatetime()
        if local.tzinfo is None: local = local.replace(tzinfo=TZ)
        if local < now(): return "Atrasada"
    return status

def ensure_recurring_today(tasks, ws):
    """Cria a agenda do dia a partir das rotinas sem alterar dias anteriores."""
    if tasks.empty: return False
    today = now().date()
    today_text = today.strftime("%d/%m/%Y")
    existing = {(str(r.get("login", "")), str(r.get("tarefa", "")), str(r.get("janela", ""))) for _, r in tasks[tasks["data"].astype(str) == today_text].iterrows()}
    created = False
    recurring = tasks[tasks["recorrencia"].astype(str).str.lower().isin(["diária", "diaria", "dias úteis", "dias uteis"])]
    recurring = recurring.drop_duplicates(subset=["login", "tarefa", "janela"], keep="last")
    for _, row in recurring.iterrows():
        recurrence = str(row.get("recorrencia", "")).lower()
        if "úteis" in recurrence or "uteis" in recurrence:
            if today.weekday() >= 5: continue
        key = (str(row.get("login", "")), str(row.get("tarefa", "")), str(row.get("janela", "")))
        if key in existing: continue
        stamp = now().strftime("%d/%m/%Y %H:%M:%S")
        hour = str(row.get("horario", "") or "18:00")
        new_row = {h: row.get(h, "") for h in TASK_COLUMNS}
        new_row.update({"id": str(uuid.uuid4()), "status": "Aberta", "data": today_text,
                        "prazo_original": f"{today_text} {hour}", "novo_prazo": "",
                        "concluida_em": "", "justificativa_atraso": "", "observacao": "",
                        "criada_em": stamp, "atualizada_em": stamp, "atualizada_por": "automação diária"})
        append_row(ws, new_row); created = True
    return created

def login_screen():
    st.title("Central de Gestão ABC")
    _, center, _ = st.columns([1, 1.2, 1])
    with center, st.form("login"):
        st.subheader("Acesso à agenda eletrônica")
        login = st.text_input("Login"); password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar", use_container_width=True)
    if submitted:
        users, _ = read_df("usuarios", USER_COLUMNS)
        if users.empty: st.error("A aba 'usuarios' está vazia."); return
        users["login"] = users["login"].astype(str).str.strip()
        users["senha"] = users["senha"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        match = users[(users["login"] == login.strip()) & (users["senha"] == password.strip())]
        if match.empty: st.error("Login ou senha inválidos.")
        else:
            user = match.iloc[0]
            st.session_state.user = {k:str(user.get(k, "")).strip() for k in USER_COLUMNS}; st.rerun()

def task_form(users, task_ws):
    executors = users[users["tipo"].astype(str).str.lower().isin(["supervisor", "coordenador"])]
    with st.expander("➕ Nova atividade"), st.form("new_task", clear_on_submit=True):
        labels = {f"{r['nome']} — {str(r['tipo']).title()}":r for _,r in executors.iterrows()}
        chosen = st.selectbox("Responsável", list(labels)) if labels else None
        title = st.text_input("Atividade"); criterion = st.text_area("Critério de conclusão")
        c1,c2,c3 = st.columns(3)
        task_date = c1.date_input("Data", value=date.today()); window = c2.selectbox("Janela", JANELAS); task_time = c3.time_input("Prazo", value=time(18,0))
        recurrence = st.selectbox("Recorrência", ["Não repetir", "Diária", "Dias úteis", "Semanal"])
        if st.form_submit_button("Cadastrar atividade", use_container_width=True):
            if not chosen or not title.strip(): st.warning("Informe o responsável e a atividade.")
            else:
                p=labels[chosen]; stamp=now().strftime("%d/%m/%Y %H:%M:%S"); deadline=f"{task_date:%d/%m/%Y} {task_time:%H:%M}"
                append_row(task_ws,{"id":str(uuid.uuid4()),"login":p["login"],"nome":p["nome"],"tipo":p["tipo"],"regiao":p.get("regiao","ABCDM"),"tarefa":title.strip(),"criterio_conclusao":criterion.strip(),"status":"Aberta","data":f"{task_date:%d/%m/%Y}","horario":f"{task_time:%H:%M}","janela":window,"prazo_original":deadline,"recorrencia":recurrence,"criada_em":stamp,"atualizada_em":stamp,"atualizada_por":st.session_state.user["login"]})
                st.success("Atividade cadastrada sem alterar os registros existentes."); st.rerun()

def metrics(df):
    counts=df["status_exibido"].value_counts() if not df.empty else {}
    for col,label in zip(st.columns(4),STATUS): col.metric(label,int(counts.get(label,0)))

def render_tasks(df, ws):
    if df.empty: st.info("Nenhuma atividade encontrada para este perfil."); return
    for _,row in df.iterrows():
        status=row["status_exibido"]; icon={"Aberta":"⚪","Em andamento":"🔵","Concluída":"🟢","Atrasada":"🔴"}[status]
        with st.expander(f"{icon} {row['tarefa']} — {status}"):
            st.caption(f"{row.get('janela','') or row.get('horario','')} | Responsável: {row.get('nome','')}")
            if row.get("criterio_conclusao"): st.write(f"**Considerada concluída quando:** {row['criterio_conclusao']}")
            new_status=st.selectbox("Status",STATUS,index=STATUS.index(status),key=f"s_{row['id']}")
            note=st.text_area("Observação",value=str(row.get("observacao","")),key=f"o_{row['id']}")
            justification=""
            if status=="Atrasada" or new_status=="Atrasada": justification=st.text_area("Justificativa do atraso",value=str(row.get("justificativa_atraso","")),key=f"j_{row['id']}")
            if st.button("Salvar atualização",key=f"save_{row['id']}"):
                if new_status=="Atrasada" and not justification.strip(): st.warning("Informe a justificativa do atraso.")
                else:
                    stamp=now().strftime("%d/%m/%Y %H:%M:%S")
                    changes={"status":new_status,"observacao":note,"justificativa_atraso":justification,"atualizada_em":stamp,"atualizada_por":st.session_state.user["login"]}
                    if new_status=="Concluída" and not row.get("concluida_em"): changes["concluida_em"]=stamp
                    update_task(ws,row["id"],changes)
                    _,hws=read_df("historico",["data_hora","tarefa_id","usuario","acao","detalhes"])
                    append_row(hws,{"data_hora":stamp,"tarefa_id":row["id"],"usuario":st.session_state.user["login"],"acao":"Atualização","detalhes":f"Status: {new_status}"})
                    st.success("Atualização salva no Google Sheets."); st.rerun()

def main():
    try: spreadsheet()
    except Exception as exc:
        st.error(f"Não foi possível conectar ao Google Sheets: {exc}"); st.info("No Streamlit Cloud, configure a credencial em Settings → Secrets."); st.stop()
    if "user" not in st.session_state: login_screen(); return
    user=st.session_state.user; role=user.get("tipo","").lower()
    st.sidebar.write(f"Olá, **{user.get('nome') or user.get('login')}**")
    if st.sidebar.button("Sair",use_container_width=True): del st.session_state.user; st.rerun()
    st.markdown(f"<div class='role-card'><h3>{role.title() or 'Usuário'}</h3><p>{ROLE_TEXT.get(role,'Acompanhar e concluir as atividades atribuídas.')}</p></div>",unsafe_allow_html=True)
    tasks,task_ws=read_df("tarefas",TASK_COLUMNS); users,_=read_df("usuarios",USER_COLUMNS); tasks=ensure_task_ids(tasks,task_ws)
    if ensure_recurring_today(tasks, task_ws):
        tasks,_ = read_df("tarefas", TASK_COLUMNS)
    tasks["status_exibido"]=tasks.apply(effective_status,axis=1) if not tasks.empty else pd.Series(dtype=str)
    manager=role in ["gestor","gerente"]; visible=tasks if manager else tasks[tasks["login"].astype(str).str.strip()==user.get("login","")]
    st.title("Central de acompanhamento" if manager else "Minha agenda"); metrics(visible)
    if manager:
        task_form(users,task_ws); options=["Todos"]+sorted([x for x in visible["nome"].astype(str).unique() if x]); selected=st.selectbox("Filtrar responsável",options)
        if selected!="Todos": visible=visible[visible["nome"]==selected]
    tabs=st.tabs(["Atividades","Fechamento do dia","Resumo semanal"] if manager else ["Atividades","Fechamento do dia"])
    with tabs[0]: render_tasks(visible.sort_values(["data","horario"],ascending=True),task_ws)
    with tabs[1]:
        st.subheader("Fechamento do dia"); metrics(visible); pending=visible[visible["status_exibido"]!="Concluída"]; st.write(f"**Pendências para fechamento:** {len(pending)}")
        if not pending.empty: st.dataframe(pending[["nome","tarefa","janela","status_exibido"]],hide_index=True,use_container_width=True)
    if manager:
        with tabs[2]:
            st.subheader("Resumo semanal")
            if visible.empty: st.info("Ainda não há atividades.")
            else: st.dataframe(visible.groupby(["nome","status_exibido"]).size().unstack(fill_value=0),use_container_width=True)

if __name__=="__main__": main()
