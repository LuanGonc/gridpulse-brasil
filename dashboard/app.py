import io
import os
import time
from urllib.parse import urlparse

import boto3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from plotly.subplots import make_subplots


load_dotenv()


AWS_PROFILE = os.getenv("AWS_PROFILE")
AWS_REGION = os.getenv("AWS_REGION")
ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "gridpulse_gold")
ATHENA_OUTPUT_LOCATION = os.getenv("ATHENA_OUTPUT_LOCATION")


RISK_ORDER = ["BAIXO", "MEDIO", "ALTO"]


def validate_environment() -> None:
    required_vars = {
        "AWS_PROFILE": AWS_PROFILE,
        "AWS_REGION": AWS_REGION,
        "ATHENA_DATABASE": ATHENA_DATABASE,
        "ATHENA_OUTPUT_LOCATION": ATHENA_OUTPUT_LOCATION,
    }

    missing_vars = [name for name, value in required_vars.items() if not value]

    if missing_vars:
        raise EnvironmentError(
            f"As seguintes variáveis estão ausentes no .env: {', '.join(missing_vars)}"
        )


@st.cache_resource
def get_boto3_session() -> boto3.Session:
    return boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=AWS_REGION,
    )


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    parsed = urlparse(s3_uri)

    if parsed.scheme != "s3":
        raise ValueError(f"URI S3 inválida: {s3_uri}")

    bucket = parsed.netloc
    key = parsed.path.lstrip("/")

    return bucket, key


def wait_for_athena_query(
    athena_client,
    query_execution_id: str,
    poll_interval_seconds: int = 2,
) -> None:
    while True:
        response = athena_client.get_query_execution(
            QueryExecutionId=query_execution_id
        )

        status = response["QueryExecution"]["Status"]["State"]

        if status == "SUCCEEDED":
            return

        if status in {"FAILED", "CANCELLED"}:
            reason = response["QueryExecution"]["Status"].get(
                "StateChangeReason",
                "Motivo não informado.",
            )

            raise RuntimeError(
                f"Query Athena terminou com status {status}. Motivo: {reason}"
            )

        time.sleep(poll_interval_seconds)


def read_athena_result_csv_from_s3(s3_client, output_location: str) -> pd.DataFrame:
    bucket, key = parse_s3_uri(output_location)

    response = s3_client.get_object(
        Bucket=bucket,
        Key=key,
    )

    content = response["Body"].read()

    return pd.read_csv(io.BytesIO(content))


@st.cache_data(ttl=3600)
def run_athena_query(query: str) -> pd.DataFrame:
    session = get_boto3_session()

    athena_client = session.client("athena")
    s3_client = session.client("s3")

    start_response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            "Database": ATHENA_DATABASE,
        },
        ResultConfiguration={
            "OutputLocation": ATHENA_OUTPUT_LOCATION,
        },
    )

    query_execution_id = start_response["QueryExecutionId"]

    wait_for_athena_query(
        athena_client=athena_client,
        query_execution_id=query_execution_id,
    )

    execution_response = athena_client.get_query_execution(
        QueryExecutionId=query_execution_id
    )

    output_location = execution_response["QueryExecution"]["ResultConfiguration"][
        "OutputLocation"
    ]

    return read_athena_result_csv_from_s3(
        s3_client=s3_client,
        output_location=output_location,
    )


def load_risk_data() -> pd.DataFrame:
    query = """
        SELECT
            area_carga,
            data_referencia,
            qtd_medicoes_demanda,
            qtd_observacoes_clima,
            qtd_estacoes,
            carga_media_mwmed,
            carga_minima_mwmed,
            carga_maxima_mwmed,
            amplitude_carga_mwmed,
            temperatura_media_c,
            temperatura_max_observada_c,
            temperatura_min_observada_c,
            umidade_media_pct,
            precipitacao_total_mm,
            radiacao_media_kj_m2,
            vento_velocidade_media_ms,
            risk_score,
            nivel_risco,
            ano,
            mes
        FROM gridpulse_gold.dias_criticos_demanda_clima
        ORDER BY data_referencia
    """

    df = run_athena_query(query)

    df["data_referencia"] = pd.to_datetime(df["data_referencia"])

    numeric_columns = [
        "qtd_medicoes_demanda",
        "qtd_observacoes_clima",
        "qtd_estacoes",
        "carga_media_mwmed",
        "carga_minima_mwmed",
        "carga_maxima_mwmed",
        "amplitude_carga_mwmed",
        "temperatura_media_c",
        "temperatura_max_observada_c",
        "temperatura_min_observada_c",
        "umidade_media_pct",
        "precipitacao_total_mm",
        "radiacao_media_kj_m2",
        "vento_velocidade_media_ms",
        "risk_score",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["nivel_risco"] = pd.Categorical(
        df["nivel_risco"],
        categories=RISK_ORDER,
        ordered=True,
    )

    return df


def build_time_series_chart(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=df["data_referencia"],
            y=df["carga_media_mwmed"],
            mode="lines",
            name="Carga média (MWmed)",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=df["data_referencia"],
            y=df["temperatura_media_c"],
            mode="lines",
            name="Temperatura média (°C)",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Carga média x Temperatura média",
        hovermode="x unified",
        legend_title_text="Métrica",
    )

    fig.update_xaxes(title_text="Data")
    fig.update_yaxes(title_text="Carga média (MWmed)", secondary_y=False)
    fig.update_yaxes(title_text="Temperatura média (°C)", secondary_y=True)

    return fig


def build_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    monthly_df = (
        df.groupby(["area_carga", "ano", "mes"], observed=True)
        .agg(
            qtd_dias=("data_referencia", "count"),
            risco_medio=("risk_score", "mean"),
            maior_risco=("risk_score", "max"),
            carga_media_mensal_mwmed=("carga_media_mwmed", "mean"),
            temperatura_media_mensal_c=("temperatura_media_c", "mean"),
        )
        .reset_index()
    )

    monthly_df["ano_mes"] = monthly_df["ano"].astype(str) + "-" + monthly_df["mes"].astype(str)

    return monthly_df


def main() -> None:
    st.set_page_config(
        page_title="GridPulse Brasil",
        page_icon="⚡",
        layout="wide",
    )

    validate_environment()

    st.title("⚡ GridPulse Brasil")
    st.caption(
        "Lakehouse AWS para análise de demanda elétrica, clima e risco de pico de carga."
    )

    with st.spinner("Carregando dados do Athena..."):
        df = load_risk_data()

    st.sidebar.header("Filtros")

    areas = sorted(df["area_carga"].dropna().unique())
    selected_area = st.sidebar.selectbox("Área de carga", areas)

    filtered_df = df[df["area_carga"] == selected_area].copy()

    months = sorted(filtered_df["mes"].dropna().unique())
    selected_months = st.sidebar.multiselect(
        "Meses",
        options=months,
        default=months,
    )

    risk_levels = [level for level in RISK_ORDER if level in df["nivel_risco"].dropna().unique()]
    selected_risk_levels = st.sidebar.multiselect(
        "Níveis de risco",
        options=risk_levels,
        default=risk_levels,
    )

    filtered_df = filtered_df[
        filtered_df["mes"].isin(selected_months)
        & filtered_df["nivel_risco"].isin(selected_risk_levels)
    ].copy()

    if filtered_df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    total_days = len(filtered_df)
    high_risk_days = int((filtered_df["nivel_risco"] == "ALTO").sum())
    avg_risk = filtered_df["risk_score"].mean()
    max_risk = filtered_df["risk_score"].max()

    correlation = filtered_df["carga_media_mwmed"].corr(
        filtered_df["temperatura_media_c"]
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Dias analisados", f"{total_days}")
    col2.metric("Dias de risco alto", f"{high_risk_days}")
    col3.metric("Risco médio", f"{avg_risk:.1f}")
    col4.metric("Maior risco", f"{max_risk:.0f}")
    col5.metric("Correlação carga x temp.", f"{correlation:.2f}")

    st.divider()

    st.subheader("Série temporal")

    time_series_fig = build_time_series_chart(filtered_df)
    st.plotly_chart(time_series_fig, use_container_width=True)

    st.subheader("Distribuição dos níveis de risco")

    risk_distribution = (
        filtered_df["nivel_risco"]
        .value_counts()
        .reindex(RISK_ORDER)
        .dropna()
        .reset_index()
    )

    risk_distribution.columns = ["nivel_risco", "qtd_dias"]

    risk_fig = px.bar(
        risk_distribution,
        x="nivel_risco",
        y="qtd_dias",
        text="qtd_dias",
        title="Quantidade de dias por nível de risco",
    )

    st.plotly_chart(risk_fig, use_container_width=True)

    st.subheader("Resumo mensal")

    monthly_df = build_monthly_summary(filtered_df)

    monthly_fig = px.line(
        monthly_df,
        x="ano_mes",
        y="risco_medio",
        markers=True,
        title="Risco médio mensal",
    )

    st.plotly_chart(monthly_fig, use_container_width=True)

    st.dataframe(
        monthly_df.sort_values(["ano", "mes"]),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Top dias críticos")

    top_days_df = filtered_df.sort_values(
        ["risk_score", "carga_maxima_mwmed"],
        ascending=[False, False],
    )[
        [
            "data_referencia",
            "area_carga",
            "risk_score",
            "nivel_risco",
            "carga_media_mwmed",
            "carga_maxima_mwmed",
            "temperatura_media_c",
            "temperatura_max_observada_c",
            "qtd_estacoes",
        ]
    ].head(20)

    st.dataframe(
        top_days_df,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Dados filtrados")

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()