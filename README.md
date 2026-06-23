# ML_Fraude

Projeto com API + ETL + Machine Learning supervisionado para detecção de fraude em transações.

A API gera transações sintéticas, o ETL carrega em camadas (`transactions_origin` e `transactions_prod`) e o modelo usa a coluna `indicativo_fraude` para treino e predição.

# Tecnologias utilizadas

- **Python**
- **FastAPI + Uvicorn**
- **SQL Server** 
- **Pandas + NumPy**
- **Scikit-learn**
- **Python-dotenv**
- **Babel**
- **joblib**

# Pré-requisitos

- Python instalado
- SQL Server rodando local
- Driver ODBC do SQL Server instalado (ex.: `ODBC Driver 18 for SQL Server`)

# Scrpts SQL

Criação das tabelas origin e prod:

```sql
CREATE TABLE dbo.transactions_origin (
    transaction_id VARCHAR(50) NOT NULL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    merchant VARCHAR(120) NOT NULL,
    category VARCHAR(80) NOT NULL,
    [timestamp] DATETIME2(7) NOT NULL,
    is_fraud BIT NOT NULL
);

CREATE TABLE dbo.transactions_prod (
    id_transacao VARCHAR(50) NOT NULL PRIMARY KEY,
    id_cliente VARCHAR(50) NOT NULL,
    valor DECIMAL(18,2) NOT NULL,
    estabelecimento VARCHAR(120) NOT NULL,
    categoria VARCHAR(80) NOT NULL,
    data_hora_transacao DATETIME2(7) NOT NULL,
    hora_transacao TIME(0) NOT NULL,
    dia_transacao VARCHAR(5) NOT NULL,
    mes_transacao VARCHAR(20) NOT NULL,
    indicativo_fraude BIT NOT NULL
);
```

# Como rodar o projeto localmente

1. Clone o repositório e entre na pasta raiz.

2. Crie e ative o ambiente virtual:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

3. Instale as dependências:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

4. Crie o arquivo .env na raiz:

API_URL=http://127.0.0.1:8000/transactions
SQL_DRIVER=ODBC Driver 18 for SQL Server
SQL_SERVER=localhost
SQL_DATABASE=ml_previsao_fraude
SQL_TRUSTED_CONNECTION=yes
SQL_ENCRYPT=yes
SQL_TRUST_SERVER_CERTIFICATE=yes

5. Suba a API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

6. Rode o ETL:

Observação sobre volume de dados:
- A geração de fraude é probabilística (nem todo cliente terá fraude).
- Para aumentar a chance de aparecerem casos de fraude no lote, o recomendado é rodar com pelo menos 50 customers.

```powershell
.\.venv\Scripts\python.exe -m etl.run_etl --customers 50
```
  
7. Treine o modelo supervisionado:

```powershell
.\.venv\Scripts\python.exe -m ml.train_supervised
```

Arquivos gerados no treino:

- `ml/artifacts/fraud_model.joblib`
- `ml/artifacts/metrics.json`
