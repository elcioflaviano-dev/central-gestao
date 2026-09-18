# Central de Gestão ABC — Streamlit + Google Sheets

Esta versão usa a planilha Google Sheets como banco compartilhado, preserva as linhas existentes e acrescenta somente colunas ausentes.

## Configuração no Streamlit Cloud

1. Compartilhe a planilha com `app-gestao@portal-iq-app.iam.gserviceaccount.com` como Editor.
2. Abra **Settings → Secrets** no aplicativo Streamlit.
3. Copie os campos do JSON para o modelo abaixo. Não envie o JSON ao GitHub.

```toml
GOOGLE_SHEETS_ID = "1tjN1xi_Qx5OJz9mD-h4ylwQ7M6tc8dD_MaeX-rgpw3k"

[gcp_service_account]
type = "service_account"
project_id = "VALOR_DO_JSON"
private_key_id = "VALOR_DO_JSON"
private_key = """-----BEGIN PRIVATE KEY-----
VALOR_DO_JSON
-----END PRIVATE KEY-----
"""
client_email = "app-gestao@portal-iq-app.iam.gserviceaccount.com"
client_id = "VALOR_DO_JSON"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "VALOR_DO_JSON"
universe_domain = "googleapis.com"
```

## Abas

O sistema utiliza `usuarios`, `tarefas` e `historico`. Abas ou colunas ausentes são criadas sem apagar os cadastros atuais.

A aba `usuarios` precisa conter: `login`, `senha`, `nome`, `tipo`, `regiao`, `ativo`. Os tipos aceitos são `gestor`, `supervisor` e `coordenador`.

## Execução local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_APPLICATION_CREDENTIALS=/caminho/credencial.json
streamlit run app.py
```

Use senhas individuais. Se uma chave privada for publicada, revogue-a no Google Cloud e gere uma nova.
