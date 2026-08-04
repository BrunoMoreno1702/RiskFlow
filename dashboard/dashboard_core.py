import json
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from database.connection import get_connection


MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}

CORES = {
    "azul": "#3D5A6C",
    "verde": "#6F8F72",
    "marrom": "#8A7356",
    "cinza": "#596B7A",
}

LOGO_PATH = Path("dashboard/logo_riskflow.png")
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

    df["data_hora_transacao"] = pd.to_datetime(df["data_hora_transacao"], errors="coerce")
    df["data_predicao_ml"] = pd.to_datetime(df["data_predicao_ml"], errors="coerce")

    df["indicativo_fraude"] = pd.to_numeric(df["indicativo_fraude"], errors="coerce").fillna(0).astype(int)
    df["indicativo_fraude_ml"] = pd.to_numeric(df["indicativo_fraude_ml"], errors="coerce")
    df["probabilidade_fraude_ml"] = pd.to_numeric(df["probabilidade_fraude_ml"], errors="coerce")

    return df


@st.cache_data(ttl=60)
def load_model_metrics() -> dict:
    if not METRICS_PATH.exists():
        return {}

    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


@st.cache_data(ttl=60)
def prepare_dashboard_data(df: pd.DataFrame):
    df_fraudes = df[df["indicativo_fraude"] == 1].dropna(subset=["data_hora_transacao"]).copy()

    if df_fraudes.empty:
        return None, None, None

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
        df_fraudes.assign(bandeira_cartao=df_fraudes["bandeira_cartao"].fillna("Não informado"))
        .groupby("bandeira_cartao", as_index=False)
        .size()
        .rename(columns={"size": "qtd_fraudes"})
        .sort_values("qtd_fraudes", ascending=False)
    )

    fraude_por_estabelecimento = (
        df_fraudes.assign(estabelecimento=df_fraudes["estabelecimento"].fillna("Não informado"))
        .groupby("estabelecimento", as_index=False)
        .size()
        .rename(columns={"size": "qtd_fraudes"})
        .sort_values("qtd_fraudes", ascending=False)
        .head(10)
    )

    return serie_tempo, fraude_por_bandeira, fraude_por_estabelecimento


def format_number(value: int | float) -> str:
    return f"{int(value):,}".replace(",", ".")


def format_percent(value: float | int | None, decimal_places: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"

    value = float(value)

    if 0 <= value <= 1:
        value *= 100

    return f"{value:.{decimal_places}f}%".replace(".", ",")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def render_sidebar() -> str:
    with st.sidebar:
        st.image(str(LOGO_PATH), width=225)

        st.markdown(
            '<div class="sidebar-title">RiskFlow</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="sidebar-subtitle">Análise inteligente de risco em transações financeiras.</div>',
            unsafe_allow_html=True,
        )

        return st.radio(
            "Navegação",
            ["Visão Geral", "Dashboards", "Sistema de Risco"],
            label_visibility="collapsed",
        )


def render_header(title: str, subtitle: str):
    st.markdown(f'<div class="main-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="main-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def render_card(title: str, value: str, subtitle: str, color: str):
    st.markdown(
        f"""
        <div class="card" style="border-top: 4px solid {color};">
            <div class="card-title">{title}</div>
            <div class="card-value">{value}</div>
            <div class="card-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_info_panel(title: str, text: str):
    st.markdown(
        f"""
        <div class="info-panel">
            <div class="info-panel-title">{title}</div>
            <div class="info-panel-text">{clean_text(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_visao_geral(df: pd.DataFrame):
    render_header(
        "Visão Geral",
        "Resumo executivo das transações processadas e monitoradas pelo projeto.",
    )

    total_transacoes = len(df)
    total_clientes = df["id_cliente"].nunique()
    total_fraudes = int((df["indicativo_fraude"] == 1).sum())
    taxa_fraude = total_fraudes / total_transacoes * 100 if total_transacoes else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        render_card(
            "Fraudes confirmadas na base",
            format_number(total_fraudes),
            "Transações classificadas como fraude",
            CORES["azul"],
        )

    with col2:
        render_card(
            "Clientes Open Finance",
            format_number(total_clientes),
            "Clientes únicos identificados na base",
            CORES["verde"],
        )

    with col3:
        render_card(
            "Transações analisadas",
            format_number(total_transacoes),
            "Total de registros processados",
            CORES["marrom"],
        )

    transacoes_avaliadas = int(df["probabilidade_fraude_ml"].notna().sum())
    risco_medio = df["probabilidade_fraude_ml"].dropna().mean()

    texto_resumo = (
        f"Hoje, nossa análise acompanha {format_number(total_transacoes)} transações "
        f"de {format_number(total_clientes)} clientes que compartilharam seus dados via Open Finance. "
        f"Ao analisar essas movimentações, identificamos {format_number(total_fraudes)} ocorrências de fraude, "
        f"o que representa cerca de {format_percent(taxa_fraude)} das transações analisadas. "
        f"O sistema de análise de risco já avaliou {format_number(transacoes_avaliadas)} transações, "
        f"com risco médio estimado de {format_percent(risco_medio)}."
    )

    render_info_panel("Resumo operacional", texto_resumo)


def render_dashboards(df: pd.DataFrame):
    serie_tempo, fraude_por_bandeira, fraude_por_estabelecimento = prepare_dashboard_data(df)

    if serie_tempo is None:
        render_header(
            "Dashboards",
            "Análise visual das transações classificadas como fraude.",
        )

        st.warning("Sem dados de fraude para exibir nos dashboards.")
        return

    grafico_linha = (
        alt.Chart(serie_tempo)
        .mark_line(point=True, color=CORES["azul"], strokeWidth=3)
        .encode(
            x=alt.X("mes_nome:N", sort=list(MESES_PT.values()), title="Mês"),
            y=alt.Y("qtd_fraudes:Q", title="Quantidade de fraudes"),
            tooltip=[
                alt.Tooltip("mes_nome:N", title="Mês"),
                alt.Tooltip("qtd_fraudes:Q", title="Quantidade de fraudes"),
            ],
        )
        .properties(height=300)
    )

    grafico_bandeira = (
        alt.Chart(fraude_por_bandeira)
        .mark_bar(
            size=100,
            color=CORES["verde"],
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=alt.X(
                "bandeira_cartao:N",
                sort=alt.SortField(field="qtd_fraudes", order="descending"),
                title="Bandeira",
            ),
            y=alt.Y("qtd_fraudes:Q", title="Quantidade de fraudes"),
            tooltip=[
                alt.Tooltip("bandeira_cartao:N", title="Bandeira"),
                alt.Tooltip("qtd_fraudes:Q", title="Quantidade de fraudes"),
            ],
        )
        .properties(height=350)
    )

    grafico_estabelecimento = (
        alt.Chart(fraude_por_estabelecimento)
        .mark_bar(
            size=20,
            color=CORES["marrom"],
            cornerRadiusTopRight=4,
            cornerRadiusBottomRight=4,
        )
        .encode(
            x=alt.X("qtd_fraudes:Q", title="Quantidade de fraudes"),
            y=alt.Y("estabelecimento:N", sort="-x", title="Estabelecimento"),
            tooltip=[
                alt.Tooltip("estabelecimento:N", title="Estabelecimento"),
                alt.Tooltip("qtd_fraudes:Q", title="Quantidade de fraudes"),
            ],
        )
        .properties(height=350)
    )

    render_header(
        "Dashboards",
        "Análise visual das transações classificadas como fraude.",
    )

    col_dashboard, _ = st.columns([4, 1])

    with col_dashboard:
        with st.container(border=True):
            st.subheader("Evolução mensal de fraudes")
            st.altair_chart(grafico_linha, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.container(border=True):
            st.subheader("Fraudes por bandeira")
            st.altair_chart(grafico_bandeira, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.container(border=True):
            st.subheader("Top 10 estabelecimentos com fraude")
            st.altair_chart(grafico_estabelecimento, use_container_width=True)


def render_sistema_risco(df: pd.DataFrame):
    render_header(
        "Sistema de Risco",
        "Resumo da análise inteligente utilizada para identificar transações com maior risco de fraude.",
    )

    metrics = load_model_metrics()

    transacoes_com_score = int(df["probabilidade_fraude_ml"].notna().sum())
    transacoes_suspeitas = int((df["indicativo_fraude_ml"] == 1).sum())
    risco_medio = df["probabilidade_fraude_ml"].dropna().mean()
    ultima_predicao = df["data_predicao_ml"].dropna().max()

    ultima_predicao_formatada = (
        "N/A"
        if pd.isna(ultima_predicao)
        else ultima_predicao.strftime("%d/%m/%Y %H:%M")
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_card(
            "Técnica utilizada",
            metrics.get("model_name", "Regressão Logística"),
            "Análise supervisionada",
            CORES["azul"],
        )

    with col2:
        render_card(
            "Acurácia",
            format_percent(metrics.get("accuracy")),
            "Resultado médio de validação",
            CORES["verde"],
        )

    with col3:
        render_card(
            "ROC AUC",
            format_percent(metrics.get("roc_auc")),
            "Separação entre transações normais e suspeitas",
            CORES["marrom"],
        )

    with col4:
        render_card(
            "PR AUC",
            format_percent(metrics.get("pr_auc")),
            "Desempenho na identificação de fraudes",
            CORES["cinza"],
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_info_1, col_info_2 = st.columns([2, 1])

    with col_info_1:
        render_info_panel(
            "Como o sistema de análise de risco avalia as transações",
            """
            O sistema avalia cada transação considerando o comportamento do cliente,
            o horário da compra e o histórico recente de movimentações. A partir dessa análise,
            ele calcula o nível de risco e indica se a transação parece normal ou suspeita.

            Sempre que uma nova análise é executada, os resultados são atualizados na base de dados,
            permitindo que o painel mostre informações mais recentes sobre risco e possíveis fraudes.
            """,
        )

    with col_info_2:
        render_info_panel(
            "Execução da análise",
            f"""
            Transações avaliadas pelo sistema: {format_number(transacoes_com_score)}<br>
            Transações suspeitas indicadas pelo sistema: {format_number(transacoes_suspeitas)}<br>
            Risco médio calculado: {format_percent(risco_medio)}<br>
            Data da última análise executada: {ultima_predicao_formatada}
            """,
        )

    if not metrics:
        st.warning(
            "O arquivo de métricas não foi encontrado ou não pôde ser lido. "
            "Execute o treino novamente para gerar os indicadores do sistema de risco."
        )