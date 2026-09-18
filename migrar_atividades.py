"""Migração idempotente das atividades conhecidas para o Google Sheets.

Uso: GOOGLE_APPLICATION_CREDENTIALS=/caminho/chave.json python migrar_atividades.py
O script apenas acrescenta atividades ausentes; nunca limpa ou substitui linhas.
"""
import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = os.getenv("GOOGLE_SHEETS_ID", "1tjN1xi_Qx5OJz9mD-h4ylwQ7M6tc8dD_MaeX-rgpw3k")
HEADERS = ["id","login","nome","tipo","regiao","tarefa","criterio_conclusao","status","data","horario","janela","prazo_original","novo_prazo","recorrencia","concluida_em","justificativa_atraso","observacao","criada_em","atualizada_em","atualizada_por"]
BASE = [
 ("genilson","Genilson Almeida","supervisor","Conferir prints de NR35, certidão e quebras","Confirmar o envio e registrar qualquer pendência.","12:00","08:00 às 12:00"),
 ("genilson","Genilson Almeida","supervisor","Conferir prints de NR35, certidão e quebras","Confirmar o envio e registrar qualquer pendência.","15:00","12:00 às 15:00"),
 ("genilson","Genilson Almeida","supervisor","Conferir prints de NR35, certidão e quebras","Confirmar o envio e registrar qualquer pendência.","18:00","15:00 às 18:00"),
 ("genilson","Genilson Almeida","supervisor","Acompanhar ações de certificado","Atualizar o andamento e registrar a tratativa realizada.","18:00","Fechamento do dia"),
 ("genilson","Genilson Almeida","supervisor","Garantir tratativas de IQI e pendências de e-mail","Confirmar que as pendências entraram na rota e receberam tratativa.","18:00","Fechamento do dia"),
 ("genilson","Genilson Almeida","supervisor","Acompanhar abertura de demandas","Conferir as demandas abertas em cada fechamento de janela.","18:00","Fechamento do dia"),
 ("genilson","Genilson Almeida","supervisor","Acompanhar ações das equipes — Consultivo e TNPS","Registrar o acompanhamento e as ações orientadas às equipes.","18:00","Fechamento do dia"),
 ("genilson","Genilson Almeida","supervisor","Acompanhar retorno de credenciada TC1","Registrar retorno recebido ou pendência de SLA.","18:00","Fechamento do dia"),
 ("alexandre","Alexandre Sousa","coordenador","Pré-matinal","Confirmar realização e principais direcionamentos.","08:00","Antes das 08:00"),
 ("alexandre","Alexandre Sousa","coordenador","Acompanhar Retrofit","Registrar andamento, responsável e próximo passo.","18:00","Fechamento do dia"),
 ("alexandre","Alexandre Sousa","coordenador","Acompanhar monitorias Remon","Confirmar monitorias realizadas e pendências.","18:00","Fechamento do dia"),
 ("alexandre","Alexandre Sousa","coordenador","Acompanhar vistorias IQI","Confirmar vistorias realizadas e tratativas.","18:00","Fechamento do dia"),
 ("alexandre","Alexandre Sousa","coordenador","Acompanhar atendimento do almoxarifado","Registrar atendimento e pendências.","18:00","Fechamento do dia"),
 ("alexandre","Alexandre Sousa","coordenador","Acompanhar equipamentos suspeitos","Registrar análise, tratativa e responsável.","18:00","Fechamento do dia"),
 ("alexandre","Alexandre Sousa","coordenador","Acompanhar lançamento de material","Confirmar os lançamentos previstos.","18:00","Fechamento do dia"),
 ("alexandre","Alexandre Sousa","coordenador","Acompanhar retorno de credenciada — SLA","Registrar retorno ou escalonamento necessário.","18:00","Fechamento do dia"),
 ("alexandre","Alexandre Sousa","coordenador","Acompanhar ações com as equipes","Registrar ações realizadas conforme prioridade do momento.","18:00","Fechamento do dia"),
]

def main():
    path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
    client = gspread.authorize(Credentials.from_service_account_file(path, scopes=scopes))
    ws = client.open_by_key(SHEET_ID).worksheet("tarefas")
    values = ws.get_all_values()
    headers = values[0] if values else []
    if not headers:
        ws.append_row(HEADERS); headers = HEADERS
    missing = [h for h in HEADERS if h not in headers]
    if missing:
        headers += missing; ws.update(range_name=f"A1:{gspread.utils.rowcol_to_a1(1,len(headers))}", values=[headers])
    records = ws.get_all_records(numericise_ignore=["all"])
    existing = {(str(r.get("login","")),str(r.get("tarefa","")),str(r.get("janela",""))) for r in records}
    stamp = datetime.now(ZoneInfo("America/Sao_Paulo")); day=stamp.strftime("%d/%m/%Y"); created=0
    for login,nome,tipo,tarefa,criterio,hora,janela in BASE:
        if (login,tarefa,janela) in existing: continue
        row={"id":str(uuid.uuid4()),"login":login,"nome":nome,"tipo":tipo,"regiao":"ABCDM","tarefa":tarefa,"criterio_conclusao":criterio,"status":"Aberta","data":day,"horario":hora,"janela":janela,"prazo_original":f"{day} {hora}","recorrencia":"Dias úteis","criada_em":stamp.strftime("%d/%m/%Y %H:%M:%S"),"atualizada_em":stamp.strftime("%d/%m/%Y %H:%M:%S"),"atualizada_por":"migração"}
        ws.append_row([str(row.get(h,"")) for h in headers], value_input_option="USER_ENTERED"); created += 1
    print(f"Migração concluída: {created} atividade(s) acrescentada(s); nenhuma linha removida.")

if __name__ == "__main__": main()
