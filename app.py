import io
import re
import calendar
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Painel Executivo - Prévia Diária",
    page_icon="📊",
    layout="wide"
)

# --- URL DA PLANILHA DO GOOGLE SHEETS ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1bF7cQaoEkj-UuKCGmJ4PThoy-CdSPlVg8i3XEB6cu58/edit?gid=0#gid=0"

# --- FUNÇÕES DE NAVEGAÇÃO ---
def ir_para_passo_2():
    st.session_state["pagina_atual"] = "2. Dados Operacionais por Base"

def ir_para_passo_3():
    st.session_state["pagina_atual"] = "3. Visualização da Prévia"

# --- FUNÇÃO DE FORMATAÇÃO PADRÃO BRASILEIRO ---
def fmt_br(val, decimais=0):
    try:
        if pd.isna(val):
            val = 0.0
        if decimais > 0:
            s = f"{float(val):,.{decimais}f}"
            s = s.replace(",", "X").replace(".", ",").replace("X", ".")
            return s
        else:
            return f"{int(round(float(val), 0)):,}".replace(".", ".")
    except Exception:
        return str(val)

# --- CSS DE ESTILIZAÇÃO PROFISSIONAL EXECUTIVA ---
st.markdown("""
<style>
    .reportview-container .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 11px;
        text-align: center;
        margin-bottom: 1rem;
    }
    .custom-table th {
        border: 1px solid #7f8c8d;
        padding: 5px 3px;
        font-weight: 700;
    }
    .custom-table td {
        border: 1px solid #bdc3c7;
        padding: 4px 3px;
    }
    .th-data { background-color: #f2f4f4; color: #2c3e50; }
    .th-qtd-os { background-color: #a9dfbf; color: #145a32; }
    .th-consult { background-color: #d5dbdb; color: #212f3d; }
    .th-prod { background-color: #a0824b; color: #ffffff; }
    .th-quebra-claro { background-color: #f9e79f; color: #7d6608; }
    .th-ganho { background-color: #a9dfbf; color: #145a32; }
    .th-gpon { background-color: #f9e79f; color: #7d6608; }
    .th-mig { background-color: #f5b7b1; color: #78281f; }
    .th-retorno { background-color: #a9dfbf; color: #145a32; }
    .th-pme { background-color: #aed6f1; color: #1b4f72; }
    
    .col-destaque-amarelo { background-color: #fcf3cf !important; font-weight: bold; color: #7d6608; }
    .col-destaque-azul { background-color: #d4efdf !important; font-weight: bold; color: #145a32; }
    
    .tr-base { background-color: #eafaf1; font-weight: bold; color: #145a32; font-size: 13px; }
    .tr-sup { background-color: #ffffff; color: #2c3e50; font-size: 11px; }
    .tr-total { background-color: #d4efdf; font-weight: 900; color: #145a32; font-size: 13px; border-top: 2px solid #27ae60; }
    .red-text { color: #c0392b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def carregar_config_equipe():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_eq = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Config_Equipe")
        return df_eq
    except Exception:
        return pd.DataFrame(columns=["Base", "Supervisor", "Montados", "Parados"])

# --- INICIALIZAÇÃO DE ESTADO E NAVEGAÇÃO ---
etapas = ["1. Upload de Arquivos", "2. Dados Operacionais por Base", "3. Visualização da Prévia"]

if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "3. Visualização da Prévia"

# --- MENU LATERAL E LOGO ---
try:
    st.sidebar.image("novo-logo-totale.png", use_container_width=True)
except Exception:
    pass

st.sidebar.title("Navegação")
st.sidebar.radio(
    "Ir para:",
    etapas,
    key="pagina_atual"
)

bases_config = [
    {"label": "ABCDM", "projeto": "NET-ABCDM"},
    {"label": "Guarulhos", "projeto": "NET-Guarulhos"},
    {"label": "Leste", "projeto": "NET-LESTE"}
]

data_selecionada = None
if st.session_state["pagina_atual"] == "3. Visualização da Prévia":
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Histórico (Previas_Diarias)")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_historico_previas = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Previas_Diarias")
    except Exception:
        df_historico_previas = pd.DataFrame()

    if df_historico_previas is not None and not df_historico_previas.empty and "Data" in df_historico_previas.columns:
        datas_disponiveis = sorted(df_historico_previas["Data"].astype(str).unique().tolist(), reverse=True)
        data_selecionada = st.sidebar.selectbox("Selecionar Data:", datas_disponiveis)
    else:
        data_selecionada = "26/10/2026"

# ==============================================================================
# PÁGINAS 1 E 2 (Mantidas para compatibilidade de fluxo)
# ==============================================================================
if st.session_state["pagina_atual"] == "1. Upload de Arquivos":
    st.subheader("📁 Passo 1: Upload e Cruzamento das Bases")
    st.info("ℹ️ Você pode ir direto para a **Visualização da Prévia** no menu lateral para consultar qualquer data gravada na aba `Previas_Diarias` do Google Sheets[cite: 16].")

elif st.session_state["pagina_atual"] == "2. Dados Operacionais por Base":
    st.subheader("⚙️ Passo 2: Dados Operacionais por Base")
    st.info("ℹ️ Para consultar dados já salvos, acesse diretamente a **Visualização da Prévia** no menu lateral.")

# ==============================================================================
# PÁGINA 3: VISUALIZAÇÃO DA PRÉVIA (LENDO DIRETAMENTE DE 'Previas_Diarias')
# ==============================================================================
elif st.session_state["pagina_atual"] == "3. Visualização da Prévia":
    st.subheader("📊 Passo 3: Apresentação da Prévia Diária - Diretoria")

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_previas = conn.read(spreadsheet=GOOGLE_SHEET_URL, worksheet="Previas_Diarias")
    except Exception as e:
        st.error(f"Erro ao ler a aba 'Previas_Diarias' do Google Sheets: {e}")
        df_previas = pd.DataFrame()

    data_formatada = data_selecionada if data_selecionada else "26/10/2026"

    def gerar_cabecalho_html():
        return f"""
        <table class="custom-table">
            <thead>
                <tr>
                    <th rowspan="2" class="th-data">{data_formatada}</th>
                    <th rowspan="2" class="th-data">Parados</th>
                    <th rowspan="2" class="th-data col-destaque-amarelo">Montados</th>
                    <th colspan="2" class="th-qtd-os">QTDE. DE O.S. OUTUBRO</th>
                    <th colspan="4" class="th-consult">CONSULTIVO OUTUBRO</th>
                    <th colspan="10" class="th-prod">PRODUTIVIDADE (Projeção)</th>
                    <th rowspan="2" class="th-prod">ND</th>
                    <th colspan="2" class="th-quebra-claro">QUEBRA CLARO</th>
                    <th rowspan="2" class="th-ganho">GANHO<br>O.S.</th>
                    <th colspan="2" class="th-gpon">GPON</th>
                    <th colspan="3" class="th-mig">MIGRAÇÃO</th>
                    <th rowspan="2" class="th-retorno">RETORNO<br>WO</th>
                    <th colspan="3" class="th-pme">PME</th>
                </tr>
                <tr>
                    <th class="th-qtd-os">Meta</th>
                    <th class="th-qtd-os">Projeção</th>
                    <th class="th-consult">Meta</th>
                    <th class="th-consult">Projeção</th>
                    <th class="th-consult">Hoje</th>
                    <th class="th-consult">O.S</th>
                    <th class="th-prod">TOTAL O.S.</th>
                    <th class="th-prod">O.S. ABERTA</th>
                    <th class="th-prod">Pontos</th>
                    <th class="th-prod">Efic. (%)</th>
                    <th class="th-prod col-destaque-azul">Média O.S.</th>
                    <th class="th-prod">O.S. Exec.</th>
                    <th class="th-prod col-destaque-amarelo">O.S Sem Consult</th>
                    <th class="th-prod">Quebra INS (%)</th>
                    <th class="th-prod">Quebra SERV (%)</th>
                    <th class="th-prod">Quebra ND (%)</th>
                    <th class="th-quebra-claro">O.S. Canc.</th>
                    <th class="th-quebra-claro">Saiu TOA</th>
                    <th class="th-gpon">Total O.S.</th>
                    <th class="th-gpon">Quebra</th>
                    <th class="th-mig">Total O.S.</th>
                    <th class="th-mig">Quebra</th>
                    <th class="th-mig">Canc.</th>
                    <th class="th-pme">WO</th>
                    <th class="th-pme">Quebra</th>
                    <th class="th-pme">Canc.</th>
                </tr>
            </thead>
            <tbody>
        """

    if df_previas is not None and not df_previas.empty and "Data" in df_previas.columns and "Base" in df_previas.columns:
        df_dia = df_previas[df_previas["Data"].astype(str).str.strip() == str(data_formatada).strip()].copy()
    else:
        df_dia = pd.DataFrame()

    tabela_html = [gerar_cabecalho_html()]

    # Acumuladores globais para a linha de TOTAL
    g_parados = 0; g_montados = 0; g_meta_os = 0; g_proj_os = 0
    g_meta_cons = 0; g_proj_cons = 0; g_hoje_cons = 0; g_os_cons = 0
    g_tot_os = 0; g_aberta = 0; g_pontos = 0; g_efic_soma = 0.0
    g_media_os_soma = 0.0; g_proj_dia = 0; g_os_sem_c = 0
    g_q_ins_soma = 0.0; g_q_serv_soma = 0.0; g_q_nd_soma = 0.0; g_nd = 0
    g_canc = 0; g_saiu_toa = 0; g_ganho = 0; g_gpon = 0; g_q_gpon_soma = 0.0
    g_mig = 0; g_q_mig_soma = 0.0; g_mig_canc = 0; g_retorno = 0
    g_pme = 0; g_q_pme_soma = 0.0; g_pme_canc = 0

    qtd_bases_validas = 0

    for item in bases_config:
        b_label = item["label"]
        row_b = df_dia[df_dia["Base"].astype(str).str.upper().str.strip() == b_label.upper()]
        
        if not row_b.empty:
            r = row_b.iloc[0]
            p_base = float(r.get("Parados", 0))
            m_base = float(r.get("Montados", 0))
            meta_os = float(r.get("Meta O.S.", 0))
            proj_os = float(r.get("Projeção O.S.", 0))
            meta_c = float(r.get("Meta Consultivo", 0))
            proj_c = float(r.get("Projeção Consultivo", 0))
            hoje_c = float(r.get("Hoje Consultivo", 0))
            os_c = float(r.get("O.S. Consultivo", 0))
            tot_os = float(r.get("Total O.S.", 0))
            os_aberta = float(r.get("O.S. Aberta", 0))
            pontos = float(r.get("Pontos", 0))
            efic = float(r.get("Efic (%)", 0))
            media_os = float(r.get("Média O.S.", 0))
            os_exec = float(r.get("O.S. Exec. (Proj)", 0))
            os_sem_c = float(r.get("O.S. Sem Consult", 0))
            q_ins = float(r.get("Quebra INS (%)", 0))
            q_serv = float(r.get("Quebra SERV (%)", 0))
            q_nd = float(r.get("Quebra ND (%)", 0))
            nd = float(r.get("ND", 0)) if "ND" in r else 0
            os_canc = float(r.get("O.S. Canc.", 0))
            saiu_toa = float(r.get("Saiu TOA", 0))
            ganho = float(r.get("Ganho O.S.", 0))
            gpon_tot = float(r.get("GPON Total", 0))
            gpon_q = float(r.get("GPON Quebra (%)", 0))
            mig_tot = float(r.get("Migração Total", 0))
            mig_q = float(r.get("Migração Quebra (%)", 0))
            mig_canc = float(r.get("Migração Canc.", 0))
            retorno = float(r.get("Retorno WO", 0))
            pme_tot = float(r.get("PME WO", 0))
            pme_q = float(r.get("PME Quebra (%)", 0))
            pme_canc = float(r.get("PME Canc.", 0))

            g_parados += p_base
            g_montados += m_base
            g_meta_os += meta_os
            g_proj_os += proj_os
            g_meta_cons += meta_c
            g_proj_cons += proj_c
            g_hoje_cons += hoje_c
            g_os_cons += os_c
            g_tot_os += tot_os
            g_aberta += os_aberta
            g_pontos += pontos
            g_efic_soma += efic
            g_media_os_soma += media_os
            g_proj_dia += os_exec
            g_os_sem_c += os_sem_c
            g_q_ins_soma += q_ins
            g_q_serv_soma += q_serv
            g_q_nd_soma += q_nd
            g_nd += nd
            g_canc += os_canc
            g_saiu_toa += saiu_toa
            g_ganho += ganho
            g_gpon += gpon_tot
            g_q_gpon_soma += gpon_q
            g_mig += mig_tot
            g_q_mig_soma += mig_q
            g_mig_canc += mig_canc
            g_retorno += retorno
            g_pme += pme_tot
            g_q_pme_soma += pme_q
            g_pme_canc += pme_canc
            qtd_bases_validas += 1

            tabela_html.append(
                f'<tr class="tr-base">'
                f'<td style="text-align: left; padding-left: 8px;">{b_label}</td>'
                f'<td>{fmt_br(p_base)}</td>'
                f'<td class="col-destaque-amarelo">{fmt_br(m_base)}</td>'
                f'<td>{fmt_br(meta_os)}</td>'
                f'<td class="red-text">{fmt_br(proj_os)}</td>'
                f'<td>{fmt_br(meta_c)}</td>'
                f'<td class="red-text">{fmt_br(proj_c)}</td>'
                f'<td>{fmt_br(hoje_c)}</td>'
                f'<td>{fmt_br(os_c)}</td>'
                f'<td>{fmt_br(tot_os)}</td>'
                f'<td>{fmt_br(os_aberta)}</td>'
                f'<td>{fmt_br(pontos)}</td>'
                f'<td>{fmt_br(efic, 1)}%</td>'
                f'<td class="col-destaque-azul">{fmt_br(media_os, 2)}</td>'
                f'<td>{fmt_br(os_exec)}</td>'
                f'<td class="col-destaque-amarelo">{fmt_br(os_sem_c)}</td>'
                f'<td>{fmt_br(q_ins, 1)}%</td>'
                f'<td>{fmt_br(q_serv, 1)}%</td>'
                f'<td>{fmt_br(q_nd, 1)}%</td>'
                f'<td>{fmt_br(nd)}</td>'
                f'<td>{fmt_br(os_canc)}</td>'
                f'<td>{fmt_br(saiu_toa)}</td>'
                f'<td>{fmt_br(ganho)}</td>'
                f'<td>{fmt_br(gpon_tot)}</td>'
                f'<td>{fmt_br(gpon_q, 1)}%</td>'
                f'<td>{fmt_br(mig_tot)}</td>'
                f'<td>{fmt_br(mig_q, 1)}%</td>'
                f'<td>{fmt_br(mig_canc)}</td>'
                f'<td>{fmt_br(retorno)}</td>'
                f'<td>{fmt_br(pme_tot)}</td>'
                f'<td>{fmt_br(pme_q, 1)}%</td>'
                f'<td>{fmt_br(pme_canc)}</td>'
                f'</tr>'
            )

    div_v = max(1, qtd_bases_validas)
    g_efic_media = g_efic_soma / div_v
    g_media_os_media = g_media_os_soma / div_v
    g_q_ins_media = g_q_ins_soma / div_v
    g_q_serv_media = g_q_serv_soma / div_v
    g_q_nd_media = g_q_nd_soma / div_v
    g_q_gpon_media = g_q_gpon_soma / div_v
    g_q_mig_media = g_q_mig_soma / div_v
    g_q_pme_media = g_q_pme_soma / div_v

    tabela_html.append(
        f'<tr class="tr-total">'
        f'<td style="text-align: left; padding-left: 8px;">TOTAL INSTALAÇÃO</td>'
        f'<td>{fmt_br(g_parados)}</td>'
        f'<td class="col-destaque-amarelo">{fmt_br(g_montados)}</td>'
        f'<td>{fmt_br(g_meta_os)}</td>'
        f'<td class="red-text">{fmt_br(g_proj_os)}</td>'
        f'<td>{fmt_br(g_meta_cons)}</td>'
        f'<td class="red-text">{fmt_br(g_proj_cons)}</td>'
        f'<td>{fmt_br(g_hoje_cons)}</td>'
        f'<td>{fmt_br(g_os_cons)}</td>'
        f'<td>{fmt_br(g_tot_os)}</td>'
        f'<td>{fmt_br(g_aberta)}</td>'
        f'<td>{fmt_br(g_pontos)}</td>'
        f'<td>{fmt_br(g_efic_media, 1)}%</td>'
        f'<td class="col-destaque-azul">{fmt_br(g_media_os_media, 2)}</td>'
        f'<td>{fmt_br(g_proj_dia)}</td>'
        f'<td class="col-destaque-amarelo">{fmt_br(g_os_sem_c)}</td>'
        f'<td>{fmt_br(g_q_ins_media, 1)}%</td>'
        f'<td>{fmt_br(g_q_serv_media, 1)}%</td>'
        f'<td>{fmt_br(g_q_nd_media, 1)}%</td>'
        f'<td>{fmt_br(g_nd)}</td>'
        f'<td>{fmt_br(g_canc)}</td>'
        f'<td>{fmt_br(g_saiu_toa)}</td>'
        f'<td>{fmt_br(g_ganho)}</td>'
        f'<td>{fmt_br(g_gpon)}</td>'
        f'<td>{fmt_br(g_q_gpon_media, 1)}%</td>'
        f'<td>{fmt_br(g_mig)}</td>'
        f'<td>{fmt_br(g_q_mig_media, 1)}%</td>'
        f'<td>{fmt_br(g_mig_canc)}</td>'
        f'<td>{fmt_br(g_retorno)}</td>'
        f'<td>{fmt_br(g_pme)}</td>'
        f'<td>{fmt_br(g_q_pme_media, 1)}%</td>'
        f'<td>{fmt_br(g_pme_canc)}</td>'
        f'</tr>'
        f'</tbody>'
        f'</table>'
    )

    st.markdown("".join(tabela_html), unsafe_allow_html=True)
    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # --- BLOCOS INDEPENDENTES POR BASE COM OS SUPERVISORES ---
    st.markdown("### 🏢 Detalhamento Operacional Separado por Base")
    df_config_eq = carregar_config_equipe()

    for item in bases_config:
        b_label = item["label"]
        b_proj = item["projeto"]
        row_b = df_dia[df_dia["Base"].astype(str).str.upper().str.strip() == b_label.upper()]
        
        if not row_b.empty:
            r = row_b.iloc[0]
            with st.expander(f"📂 Base: {b_label} (Clique para Expandir/Recolher Detalhamento)"):
                tabela_bloco_html = [
                    gerar_cabecalho_html(),
                    f'<tr class="tr-base">'
                    f'<td style="text-align: left; padding-left: 8px;">{b_label}</td>'
                    f'<td>{fmt_br(r.get("Parados", 0))}</td>'
                    f'<td class="col-destaque-amarelo">{fmt_br(r.get("Montados", 0))}</td>'
                    f'<td>{fmt_br(r.get("Meta O.S.", 0))}</td>'
                    f'<td class="red-text">{fmt_br(r.get("Projeção O.S.", 0))}</td>'
                    f'<td>{fmt_br(r.get("Meta Consultivo", 0))}</td>'
                    f'<td class="red-text">{fmt_br(r.get("Projeção Consultivo", 0))}</td>'
                    f'<td>{fmt_br(r.get("Hoje Consultivo", 0))}</td>'
                    f'<td>{fmt_br(r.get("O.S. Consultivo", 0))}</td>'
                    f'<td>{fmt_br(r.get("Total O.S.", 0))}</td>'
                    f'<td>{fmt_br(r.get("O.S. Aberta", 0))}</td>'
                    f'<td>{fmt_br(r.get("Pontos", 0))}</td>'
                    f'<td>{fmt_br(r.get("Efic (%)", 0), 1)}%</td>'
                    f'<td class="col-destaque-azul">{fmt_br(r.get("Média O.S.", 0), 2)}</td>'
                    f'<td>{fmt_br(r.get("O.S. Exec. (Proj)", 0))}</td>'
                    f'<td class="col-destaque-amarelo">{fmt_br(r.get("O.S. Sem Consult", 0))}</td>'
                    f'<td>{fmt_br(r.get("Quebra INS (%)", 0), 1)}%</td>'
                    f'<td>{fmt_br(r.get("Quebra SERV (%)", 0), 1)}%</td>'
                    f'<td>{fmt_br(r.get("Quebra ND (%)", 0), 1)}%</td>'
                    f'<td>{fmt_br(r.get("ND", 0))}</td>'
                    f'<td>{fmt_br(r.get("O.S. Canc.", 0))}</td>'
                    f'<td>{fmt_br(r.get("Saiu TOA", 0))}</td>'
                    f'<td>{fmt_br(r.get("Ganho O.S.", 0))}</td>'
                    f'<td>{fmt_br(r.get("GPON Total", 0))}</td>'
                    f'<td>{fmt_br(r.get("GPON Quebra (%)", 0), 1)}%</td>'
                    f'<td>{fmt_br(r.get("Migração Total", 0))}</td>'
                    f'<td>{fmt_br(r.get("Migração Quebra (%)", 0), 1)}%</td>'
                    f'<td>{fmt_br(r.get("Migração Canc.", 0))}</td>'
                    f'<td>{fmt_br(r.get("Retorno WO", 0))}</td>'
                    f'<td>{fmt_br(r.get("PME WO", 0))}</td>'
                    f'<td>{fmt_br(r.get("PME Quebra (%)", 0), 1)}%</td>'
                    f'<td>{fmt_br(r.get("PME Canc.", 0))}</td>'
                    f'</tr>'
                ]

                df_b_eq = df_config_eq[df_config_eq["Base"].astype(str).str.upper() == b_proj.upper()] if not df_config_eq.empty else pd.DataFrame()
                if not df_b_eq.empty and "Supervisor" in df_b_eq.columns:
                    for _, sup_row in df_b_eq.iterrows():
                        s_nome = str(sup_row["Supervisor"]).strip()
                        p_sup = sup_row.get("Parados", 0)
                        m_sup = sup_row.get("Montados", r.get("Montados", 0))
                        primeiro_nome = s_nome.split()[0]
                        
                        tabela_bloco_html.append(
                            f'<tr class="tr-sup">'
                            f'<td style="text-align: left; padding-left: 20px;">{primeiro_nome}</td>'
                            f'<td>{fmt_br(p_sup)}</td>'
                            f'<td class="col-destaque-amarelo">{fmt_br(m_sup)}</td>'
                            f'<td></td><td></td><td></td><td></td><td></td><td></td>'
                            f'<td></td><td></td><td></td><td></td><td></td><td></td><td></td>'
                            f'<td></td><td></td><td></td><td></td><td></td><td></td><td></td>'
                            f'<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>'
                            f'</tr>'
                        )

                tabela_bloco_html.append('</tbody></table>')
                st.markdown("".join(tabela_bloco_html), unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
