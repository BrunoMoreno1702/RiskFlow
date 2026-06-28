import json
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from database.connection import get_connection


st.set_page_config(page_title="Fraudes - Visão Executiva", layout="wide")


MESES_PT = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}


CORES_GRAFICOS = {
    "linha": "#3D5A6C",
    "bandeira": "#6F8F72",
    "estabelecimento": "#8A7356",
}


METRICS_PATH = Path("ml/artifacts/metrics.json")


SELECT_DASHBOARD_SQL = """
SELECT
    id_transacao,
    id_cliente,
    estabelecimento,
    bandeira_cartao,
    indicativo_fraude,
    probabilidade_fraude_ml,
    indicativo_fraude_ml,
    data_hora_transacao,
    data_predicao_ml
FROM dbo.transactions_prod;
"""


@st.cache_data(ttl=60)
def load_transactions_dataframe() -> pd.DataFrame:
    connection = get_connection()

    try:
        df = pd.read_sql(SELECT_DASHBOARD_SQL, connection)
    finally:
        connection.close()

    if df.empty:
        return df

    df["data_hora_transacao"] = pd.to_datetime(
        df["data_hora_transacao"],
        errors="coerce"
    )

    df["data_predicao_ml"] = pd.to_datetime(
        df["data_predicao_ml"],
        errors="coerce"
    )

    df["indicativo_fraude"] = pd.to_numeric(
        df["indicativo_fraude"],
        errors="coerce"
    ).fillna(0).astype(int)

    df["indicativo_fraude_ml"] = pd.to_numeric(
        df["indicativo_fraude_ml"],
        errors="coerce"
    )

    df["probabilidade_fraude_ml"] = pd.to_numeric(
        df["probabilidade_fraude_ml"],
        errors="coerce"
    )

    return df


@st.cache_data(ttl=60)
def load_model_metrics() -> dict:
    if not METRICS_PATH.exists():
        return {}

    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def format_number(value: int | float) -> str:
    return f"{int(value):,}".replace(",", ".")


def format_percent(value: float | int | None, decimal_places: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"

    value = float(value)

    if 0 <= value <= 1:
        value = value * 100

    return f"{value:.{decimal_places}f}%".replace(".", ",")


def clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def render_card(title: str, value: str, subtitle: str, accent_color: str = "#3D5A6C"):
    st.markdown(
        f"""
        <div class="card" style="border-top: 4px solid {accent_color};">
            <div class="card-title">{title}</div>
            <div class="card-value">{value}</div>
            <div class="card-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_info_panel(title: str, text: str):
    text = clean_text(text)

    st.markdown(
        f"""
        <div class="info-panel">
            <div class="info-panel-title">{title}</div>
            <div class="info-panel-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def apply_custom_style():
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 2.2rem;
                padding-bottom: 2rem;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #3F5FE8 0%, #3148B8 100%);
            }

            [data-testid="stSidebar"] * {
                color: white;
            }

            .sidebar-title {
                font-size: 25px;
                font-weight: 800;
                margin-bottom: 8px;
                line-height: 1.3;
            }

            .sidebar-subtitle {
                font-size: 13px;
                opacity: 0.85;
                margin-bottom: 28px;
                line-height: 1.4;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] {
                width: 100%;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label {
                width: 100% !important;
                min-width: 100% !important;
                background-color: rgba(255, 255, 255, 0.12);
                padding: 12px 14px !important;
                border-radius: 10px;
                margin-bottom: 10px;
                border: 1px solid rgba(255, 255, 255, 0.14);
                transition: all 0.2s ease;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
                background-color: rgba(255, 255, 255, 0.22);
                border: 1px solid rgba(255, 255, 255, 0.35);
            }

            .main-title {
                display: block;
                font-size: 34px;
                font-weight: 800;
                color: #2F3A4A;
                margin: 0 0 6px 0;
                padding-top: 6px;
                line-height: 1.25;
                overflow: visible;
            }

            .main-subtitle {
                font-size: 15px;
                color: #6B7280;
                margin-bottom: 26px;
                line-height: 1.5;
            }

            .card {
                background-color: #FFFFFF;
                padding: 24px 24px;
                border-radius: 16px;
                border-left: 1px solid #E5E7EB;
                border-right: 1px solid #E5E7EB;
                border-bottom: 1px solid #E5E7EB;
                box-shadow: 0px 8px 22px rgba(15, 23, 42, 0.06);
                min-height: 135px;
            }

            .card-title {
                font-size: 14px;
                color: #6B7280;
                margin-bottom: 10px;
                font-weight: 600;
            }

            .card-value {
                font-size: 31px;
                font-weight: 800;
                color: #263238;
                margin-bottom: 7px;
                line-height: 1.2;
            }

            .card-subtitle {
                font-size: 13px;
                color: #9CA3AF;
                line-height: 1.4;
            }

            .info-panel {
                background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
                padding: 22px 24px;
                border-radius: 16px;
                border: 1px solid #E5E7EB;
                box-shadow: 0px 8px 22px rgba(15, 23, 42, 0.05);
                margin-top: 18px;
            }

            .info-panel-title {
                font-size: 18px;
                font-weight: 800;
                color: #2F3A4A;
                margin-bottom: 8px;
            }

            .info-panel-text {
                font-size: 14px;
                color: #64748B;
                line-height: 1.6;
            }

            h3 {
                color: #2F3A4A;
                line-height: 1.35;
            }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-title">Painel de Fraudes</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="sidebar-subtitle">Monitoramento executivo de transações, risco e análise inteligente.</div>',
            unsafe_allow_html=True
        )

        pagina = st.radio(
            "Navegação",
            [
                "Visão Geral",
                "Dashboards",
                "Sistema de Risco",
            ],
            label_visibility="collapsed",
        )

    return pagina


def render_visao_geral(df: pd.DataFrame):
    st.markdown('<div class="main-title">Visão Geral</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="main-subtitle">Resumo executivo das transações processadas e monitoradas pelo projeto.</div>',
        unsafe_allow_html=True
    )

    total_fraudes = int((df["indicativo_fraude_ml"] == 1).sum())
    total_clientes = int(df["id_cliente"].nunique())
    total_transacoes = int(len(df))

    taxa_fraude = (
        total_fraudes / total_transacoes * 100
        if total_transacoes > 0
        else 0
    )

    col_card_1, col_card_2, col_card_3 = st.columns(3)

    with col_card_1:
        render_card(
            title="Fraudes detectadas",
            value=format_number(total_fraudes),
            subtitle="Transações classificadas como fraude pelo sistema de risco",
            accent_color="#3D5A6C",
        )

    with col_card_2:
        render_card(
            title="Clientes Open Finance",
            value=format_number(total_clientes),
            subtitle="Clientes que compartilharam seus dados de transações para análise",
            accent_color="#6F8F72",
        )

    with col_card_3:
        render_card(
            title="Transações analisadas",
            value=format_number(total_transacoes),
            subtitle="Total de registros processados",
            accent_color="#8A7356",
        )

    risco_medio = df["probabilidade_fraude_ml"].dropna().mean()
    transacoes_avaliadas = int(df["probabilidade_fraude_ml"].notna().sum())

    texto_resumo = (
        f"A base possui {format_number(total_transacoes)} transações analisadas, "
        f"envolvendo {format_number(total_clientes)} clientes únicos. "
        f"Até o momento, foram detectadas {format_number(total_fraudes)} fraudes, "
        f"o que representa uma taxa aproximada de {format_percent(taxa_fraude)} "
        f"sobre o volume total processado."
    )

    if transacoes_avaliadas > 0:
        texto_resumo += (
            f" O sistema de análise de risco já avaliou "
            f"{format_number(transacoes_avaliadas)} transações, "
            f"com risco médio estimado de {format_percent(risco_medio)}."
        )

    render_info_panel(
        title="Resumo operacional",
        text=texto_resumo,
    )


def render_dashboards(df: pd.DataFrame):
    st.markdown('<div class="main-title">Dashboards</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="main-subtitle">Análise visual das transações classificadas como fraude.</div>',
        unsafe_allow_html=True
    )

    df_fraudes = df[df["indicativo_fraude"] == 1].copy()
    df_fraudes = df_fraudes.dropna(subset=["data_hora_transacao"])

    if df_fraudes.empty:
        st.warning("Sem dados de fraude para exibir nos dashboards.")
        return

    serie_tempo = (
        df_fraudes.assign(
            mes_num=df_fraudes["data_hora_transacao"].dt.month,
            mes_nome=df_fraudes["data_hora_transacao"].dt.month.map(MESES_PT),
        )
        .groupby(["mes_num", "mes_nome"], as_index=False)
        .size()
        .rename(columns={"size": "qtd_fraudes"})
        .sort_values("mes_num")
    )

    fraude_por_bandeira = (
        df_fraudes.assign(
            bandeira_cartao=df_fraudes["bandeira_cartao"].fillna("Não informado")
        )
        .groupby("bandeira_cartao", as_index=False)
        .size()
        .rename(columns={"size": "qtd_fraudes"})
        .sort_values("qtd_fraudes", ascending=False)
    )

    fraude_por_estabelecimento = (
        df_fraudes.assign(
            estabelecimento=df_fraudes["estabelecimento"].fillna("Não informado")
        )
        .groupby("estabelecimento", as_index=False)
        .size()
        .rename(columns={"size": "qtd_fraudes"})
        .sort_values("qtd_fraudes", ascending=False)
        .head(10)
    )

    line = (
        alt.Chart(serie_tempo)
        .mark_line(
            point=True,
            color=CORES_GRAFICOS["linha"],
            strokeWidth=3,
        )
        .encode(
            x=alt.X(
                "mes_nome:N",
                sort=list(MESES_PT.values()),
                title="Mês",
            ),
            y=alt.Y(
                "qtd_fraudes:Q",
                title="Quantidade de fraudes",
            ),
            tooltip=[
                alt.Tooltip("mes_nome:N", title="Mês"),
                alt.Tooltip("qtd_fraudes:Q", title="Quantidade de fraudes"),
            ],
        )
        .properties(height=300)
    )

    bar_bandeira = (
        alt.Chart(fraude_por_bandeira)
        .mark_bar(
            size=100,
            color=CORES_GRAFICOS["bandeira"],
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=alt.X(
                "bandeira_cartao:N",
                sort=alt.SortField(
                    field="qtd_fraudes",
                    order="descending",
                ),
                title="Bandeira",
            ),
            y=alt.Y(
                "qtd_fraudes:Q",
                title="Quantidade de fraudes",
            ),
            tooltip=[
                alt.Tooltip("bandeira_cartao:N", title="Bandeira"),
                alt.Tooltip("qtd_fraudes:Q", title="Quantidade de fraudes"),
            ],
        )
        .properties(height=350)
    )

    bar_estabelecimento = (
        alt.Chart(fraude_por_estabelecimento)
        .mark_bar(
            size=20,
            color=CORES_GRAFICOS["estabelecimento"],
            cornerRadiusTopRight=4,
            cornerRadiusBottomRight=4,
        )
        .encode(
            x=alt.X(
                "qtd_fraudes:Q",
                title="Quantidade de fraudes",
            ),
            y=alt.Y(
                "estabelecimento:N",
                sort="-x",
                title="Estabelecimento",
            ),
            tooltip=[
                alt.Tooltip("estabelecimento:N", title="Estabelecimento"),
                alt.Tooltip("qtd_fraudes:Q", title="Quantidade de fraudes"),
            ],
        )
        .properties(height=350)
    )

    col_dashboard, col_vazia = st.columns([4, 1])

    with col_dashboard:
        with st.container(border=True):
            st.subheader("Evolução mensal de fraudes")
            st.altair_chart(line, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.container(border=True):
            st.subheader("Fraudes por bandeira")
            st.altair_chart(bar_bandeira, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.container(border=True):
            st.subheader("Top 10 estabelecimentos com fraude")
            st.altair_chart(bar_estabelecimento, use_container_width=True)


def render_sistema_risco(df: pd.DataFrame):
    st.markdown('<div class="main-title">Sistema de Risco</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="main-subtitle">Resumo da análise inteligente utilizada para identificar transações com maior risco de fraude.</div>',
        unsafe_allow_html=True
    )

    metrics = load_model_metrics()

    accuracy = metrics.get("accuracy")
    roc_auc = metrics.get("roc_auc")
    pr_auc = metrics.get("pr_auc")
    model_name = metrics.get("model_name", "Regressão Logística")

    transacoes_com_score = int(df["probabilidade_fraude_ml"].notna().sum())
    fraudes_previstas = int((df["indicativo_fraude_ml"] == 1).sum())
    risco_medio = df["probabilidade_fraude_ml"].dropna().mean()

    ultima_predicao = df["data_predicao_ml"].dropna().max()

    if pd.isna(ultima_predicao):
        ultima_predicao_formatada = "N/A"
    else:
        ultima_predicao_formatada = ultima_predicao.strftime("%d/%m/%Y %H:%M")

    col_card_1, col_card_2, col_card_3, col_card_4 = st.columns(4)

    with col_card_1:
        render_card(
            title="Técnica utilizada",
            value=model_name,
            subtitle="Análise supervisionada",
            accent_color="#3D5A6C",
        )

    with col_card_2:
        render_card(
            title="Acurácia",
            value=format_percent(accuracy),
            subtitle="Resultado médio de validação",
            accent_color="#6F8F72",
        )

    with col_card_3:
        render_card(
            title="ROC AUC",
            value=format_percent(roc_auc),
            subtitle="Separação entre transações normais e suspeitas",
            accent_color="#8A7356",
        )

    with col_card_4:
        render_card(
            title="PR AUC",
            value=format_percent(pr_auc),
            subtitle="Desempenho na identificação de fraudes",
            accent_color="#596B7A",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_info_1, col_info_2 = st.columns([2, 1])

    with col_info_1:
        texto_sistema = """
        O sistema avalia cada transação considerando o comportamento do cliente,
        o horário da compra e o histórico recente de movimentações. A partir dessa análise,
        ele calcula o nível de risco e indica se a transação parece normal ou suspeita.

        Sempre que uma nova análise é executada, os resultados são atualizados na base de dados,
        permitindo que o painel mostre informações mais recentes sobre risco e possíveis fraudes.
        """

        render_info_panel(
            title="Como o sistema de análise de risco avalia as transações",
            text=texto_sistema,
        )

    with col_info_2:
        texto_execucao = f"""
                Transações avaliadas pelo sistema: {format_number(transacoes_com_score)}<br>
                Transações suspeitas indicadas pelo sistema: {format_number(fraudes_previstas)}<br>
                Risco médio calculado: {format_percent(risco_medio)}<br>
                Data da última análise executada: {ultima_predicao_formatada}
                """

        render_info_panel(
            title="Execução da análise",
            text=texto_execucao,
        )

    if not metrics:
        st.warning(
            "O arquivo de métricas não foi encontrado ou não pôde ser lido. "
            "Execute o treino novamente para gerar os indicadores do sistema de risco."
        )


def main():
    apply_custom_style()

    pagina = render_sidebar()

    df = load_transactions_dataframe()

    if df.empty:
        st.warning("Sem dados para exibir.")
        return

    if pagina == "Visão Geral":
        render_visao_geral(df)

    elif pagina == "Dashboards":
        render_dashboards(df)

    elif pagina == "Sistema de Risco":
        render_sistema_risco(df)


if __name__ == "__main__":
    main()