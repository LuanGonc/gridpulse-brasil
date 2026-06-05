import os
import re
import shutil
import unicodedata
from pathlib import Path

import boto3
import pandas as pd
from dotenv import load_dotenv


load_dotenv()


AWS_PROFILE = os.getenv("AWS_PROFILE")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")


BRONZE_BASE_PATH = Path("data", "bronze", "inmet", "dados_historicos")
SILVER_BASE_PATH = Path("data", "silver", "inmet", "observacoes_horarias")


TARGET_YEAR = 2025

TARGET_UFS = {
    "RJ", "SP", "MG", "ES", "GO", "MT", "MS", "DF",
    "PR", "SC", "RS",
    "BA", "SE", "AL", "PE", "PB", "RN", "CE", "PI", "MA",
    "AM", "RR", "AP", "PA", "TO", "RO", "AC",
}


FINAL_COLUMNS = [
    "area_carga",
    "regiao_inmet",
    "uf",
    "estacao_nome",
    "codigo_estacao",
    "latitude",
    "longitude",
    "altitude_m",
    "data_hora_utc",
    "data_referencia",
    "ano",
    "mes",
    "precipitacao_total_mm",
    "temperatura_ar_c",
    "temperatura_max_c",
    "temperatura_min_c",
    "umidade_relativa_pct",
    "umidade_max_pct",
    "umidade_min_pct",
    "radiacao_global_kj_m2",
    "vento_velocidade_ms",
    "vento_direcao_graus",
    "pressao_atm_estacao_mb",
    "_source_file",
]


NUMERIC_COLUMNS = [
    "latitude",
    "longitude",
    "altitude_m",
    "precipitacao_total_mm",
    "temperatura_ar_c",
    "temperatura_max_c",
    "temperatura_min_c",
    "umidade_relativa_pct",
    "umidade_max_pct",
    "umidade_min_pct",
    "radiacao_global_kj_m2",
    "vento_velocidade_ms",
    "vento_direcao_graus",
    "pressao_atm_estacao_mb",
]


CRITICAL_COLUMNS = [
    "uf",
    "codigo_estacao",
    "data_hora_utc",
]


def validate_environment() -> None:
    required_vars = {
        "AWS_PROFILE": AWS_PROFILE,
        "AWS_REGION": AWS_REGION,
        "S3_BUCKET": S3_BUCKET,
    }

    missing_vars = [name for name, value in required_vars.items() if not value]

    if missing_vars:
        raise EnvironmentError(
            f"As seguintes variáveis estão ausentes no .env: {', '.join(missing_vars)}"
        )


def normalize_text(value: str) -> str:
    value = str(value).strip().upper()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))

    value = re.sub(r"\s+", " ", value)

    return value


def normalize_number(value: object) -> float | None:
    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return None


def find_latest_extracted_dir(year: int) -> Path:
    year_path = BRONZE_BASE_PATH / f"ano={year}"

    if not year_path.exists():
        raise FileNotFoundError(f"Pasta do ano não encontrada: {year_path}")

    extracted_dirs = sorted(
        year_path.glob("ingestion_timestamp=*/extracted"),
        reverse=True,
    )

    if not extracted_dirs:
        raise FileNotFoundError(
            f"Nenhuma pasta extracted encontrada dentro de {year_path}"
        )

    return extracted_dirs[0]


def find_inmet_csv_files(extracted_dir: Path) -> list[Path]:
    csv_files = list(extracted_dir.rglob("*.CSV")) + list(extracted_dir.rglob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {extracted_dir}")

    return csv_files


def parse_station_metadata(file_path: Path) -> dict:
    metadata = {
        "regiao_inmet": None,
        "uf": None,
        "estacao_nome": None,
        "codigo_estacao": None,
        "latitude": None,
        "longitude": None,
        "altitude_m": None,
    }

    with file_path.open("r", encoding="latin1") as file:
        header_lines = [next(file).strip() for _ in range(8)]

    for line in header_lines:
        parts = line.split(";")

        if len(parts) < 2:
            continue

        key = normalize_text(parts[0].replace(":", ""))
        value = parts[1].strip()

        if key == "REGIAO":
            metadata["regiao_inmet"] = value
        elif key == "UF":
            metadata["uf"] = value
        elif key == "ESTACAO":
            metadata["estacao_nome"] = value
        elif key in {"CODIGO WMO", "CODIGO (WMO)"}:
            metadata["codigo_estacao"] = value
        elif key == "LATITUDE":
            metadata["latitude"] = normalize_number(value)
        elif key == "LONGITUDE":
            metadata["longitude"] = normalize_number(value)
        elif key == "ALTITUDE":
            metadata["altitude_m"] = normalize_number(value)

    return metadata


def detect_column_mapping(columns: list[str]) -> dict:
    mapping = {}

    for column in columns:
        normalized = normalize_text(column)

        if normalized == "DATA":
            mapping[column] = "data_medicao"
        elif "HORA" in normalized and "UTC" in normalized:
            mapping[column] = "hora_utc"
        elif "PRECIPITACAO TOTAL" in normalized:
            mapping[column] = "precipitacao_total_mm"
        elif "TEMPERATURA DO AR" in normalized and "BULBO SECO" in normalized:
            mapping[column] = "temperatura_ar_c"
        elif "TEMPERATURA MAXIMA" in normalized:
            mapping[column] = "temperatura_max_c"
        elif "TEMPERATURA MINIMA" in normalized:
            mapping[column] = "temperatura_min_c"
        elif normalized.startswith("UMIDADE RELATIVA DO AR"):
            mapping[column] = "umidade_relativa_pct"
        elif "UMIDADE REL. MAX" in normalized:
            mapping[column] = "umidade_max_pct"
        elif "UMIDADE REL. MIN" in normalized:
            mapping[column] = "umidade_min_pct"
        elif "RADIACAO GLOBAL" in normalized:
            mapping[column] = "radiacao_global_kj_m2"
        elif "VENTO" in normalized and "VELOCIDADE" in normalized:
            mapping[column] = "vento_velocidade_ms"
        elif "VENTO" in normalized and "DIRECAO" in normalized:
            mapping[column] = "vento_direcao_graus"
        elif "PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO" in normalized:
            mapping[column] = "pressao_atm_estacao_mb"

    return mapping


def build_datetime_utc(df: pd.DataFrame) -> pd.Series:
    date_as_text = df["data_medicao"].astype(str).str.strip()

    hour_as_text = (
        df["hora_utc"]
        .astype(str)
        .str.extract(r"(\d{2})(\d{2})", expand=True)
    )

    hour = hour_as_text[0]
    minute = hour_as_text[1]

    datetime_text = date_as_text + " " + hour + ":" + minute

    return pd.to_datetime(
        datetime_text,
        errors="coerce",
        utc=True,
    )


def map_uf_to_area_carga(uf: str | None) -> str | None:
    if uf in {"RJ", "SP", "MG", "ES", "GO", "MT", "MS", "DF"}:
        return "SECO"

    if uf in {"PR", "SC", "RS"}:
        return "S"

    if uf in {"BA", "SE", "AL", "PE", "PB", "RN", "CE", "PI", "MA"}:
        return "NE"

    if uf in {"AM", "RR", "AP", "PA", "TO", "RO", "AC"}:
        return "N"

    return None


def read_single_inmet_file(file_path: Path) -> pd.DataFrame | None:
    metadata = parse_station_metadata(file_path)

    uf = metadata["uf"]

    if uf not in TARGET_UFS:
        return None

    df = pd.read_csv(
        file_path,
        sep=";",
        skiprows=8,
        encoding="latin1",
        decimal=",",
        na_values=["", "NULL", "null", "-9999"],
        low_memory=False,
    )

    df = df.dropna(axis=1, how="all")

    unnamed_columns = [
        column for column in df.columns if str(column).startswith("Unnamed")
    ]

    if unnamed_columns:
        df = df.drop(columns=unnamed_columns)

    column_mapping = detect_column_mapping(list(df.columns))

    df = df.rename(columns=column_mapping)

    required_raw_columns = ["data_medicao", "hora_utc"]

    missing_columns = [
        column for column in required_raw_columns if column not in df.columns
    ]

    if missing_columns:
        print(f"Aviso: arquivo ignorado por falta de colunas {missing_columns}: {file_path}")
        return None

    for final_column in FINAL_COLUMNS:
        if final_column not in df.columns:
            df[final_column] = pd.NA

    df["regiao_inmet"] = metadata["regiao_inmet"]
    df["uf"] = metadata["uf"]
    df["estacao_nome"] = metadata["estacao_nome"]
    df["codigo_estacao"] = metadata["codigo_estacao"]
    df["latitude"] = metadata["latitude"]
    df["longitude"] = metadata["longitude"]
    df["altitude_m"] = metadata["altitude_m"]
    df["area_carga"] = map_uf_to_area_carga(metadata["uf"])
    df["_source_file"] = file_path.as_posix()

    df["data_hora_utc"] = build_datetime_utc(df)
    df["data_referencia"] = df["data_hora_utc"].dt.date
    df["ano"] = df["data_hora_utc"].dt.strftime("%Y")
    df["mes"] = df["data_hora_utc"].dt.strftime("%m")

    for column in NUMERIC_COLUMNS:
        df[column] = df[column].apply(normalize_number)

    df = df[FINAL_COLUMNS].copy()

    before = len(df)

    df = df.dropna(subset=CRITICAL_COLUMNS)

    after = len(df)

    if before != after:
        print(f"Aviso: {before - after} linhas removidas por nulos críticos em {file_path.name}")

    return df


def transform_inmet_files(csv_files: list[Path]) -> pd.DataFrame:
    dataframes = []

    total_files = len(csv_files)
    processed_files = 0
    ignored_files = 0

    for index, file_path in enumerate(csv_files, start=1):
        if index % 50 == 0:
            print(f"Processando arquivo {index}/{total_files}...")

        station_df = read_single_inmet_file(file_path)

        if station_df is None or station_df.empty:
            ignored_files += 1
            continue

        dataframes.append(station_df)
        processed_files += 1

    if not dataframes:
        raise ValueError("Nenhum dado válido foi processado.")

    print(f"Arquivos totais encontrados: {total_files}")
    print(f"Arquivos processados: {processed_files}")
    print(f"Arquivos ignorados: {ignored_files}")

    df = pd.concat(dataframes, ignore_index=True)

    before_dedup = len(df)

    df = df.sort_values("_source_file")
    df = df.drop_duplicates(
        subset=["codigo_estacao", "data_hora_utc"],
        keep="last",
    )

    after_dedup = len(df)

    print(f"Registros antes da deduplicação: {before_dedup}")
    print(f"Registros após deduplicação: {after_dedup}")
    print(f"Duplicatas removidas: {before_dedup - after_dedup}")

    return df


def write_silver_parquet(df: pd.DataFrame) -> Path:
    if SILVER_BASE_PATH.exists():
        shutil.rmtree(SILVER_BASE_PATH)

    SILVER_BASE_PATH.mkdir(parents=True, exist_ok=True)

    df.to_parquet(
        SILVER_BASE_PATH,
        engine="pyarrow",
        index=False,
        partition_cols=["area_carga", "uf", "ano", "mes"],
    )

    return SILVER_BASE_PATH


def upload_directory_to_s3(local_base_path: Path, bucket: str, s3_prefix: str) -> None:
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    s3_client = session.client("s3")

    files_to_upload = [
        file_path
        for file_path in local_base_path.rglob("*")
        if file_path.is_file()
    ]

    if not files_to_upload:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em {local_base_path}")

    for file_path in files_to_upload:
        relative_path = file_path.relative_to(local_base_path).as_posix()
        s3_key = f"{s3_prefix}/{relative_path}"

        s3_client.upload_file(
            Filename=str(file_path),
            Bucket=bucket,
            Key=s3_key,
        )

        print(f"Upload: {file_path} -> s3://{bucket}/{s3_key}")


def main() -> None:
    validate_environment()

    print("Iniciando transformação INMET Bronze -> Silver...")
    print(f"Ano alvo: {TARGET_YEAR}")
    print(f"UFs alvo: {sorted(TARGET_UFS)}")

    extracted_dir = find_latest_extracted_dir(TARGET_YEAR)
    print(f"Pasta extracted usada: {extracted_dir}")

    csv_files = find_inmet_csv_files(extracted_dir)
    print(f"Arquivos CSV encontrados: {len(csv_files)}")

    silver_df = transform_inmet_files(csv_files)

    print("Resumo da Silver INMET:")
    print(f"Linhas finais: {len(silver_df)}")
    print(f"Estações finais: {silver_df['codigo_estacao'].nunique()}")
    print(f"Período inicial: {silver_df['data_hora_utc'].min()}")
    print(f"Período final: {silver_df['data_hora_utc'].max()}")
    print("Tipos finais:")
    print(silver_df.dtypes)

    silver_path = write_silver_parquet(silver_df)
    print(f"Silver INMET salva localmente em: {silver_path}")

    upload_directory_to_s3(
        local_base_path=silver_path,
        bucket=S3_BUCKET,
        s3_prefix="silver/inmet/observacoes_horarias",
    )

    print("Transformação INMET Bronze -> Silver finalizada com sucesso.")


if __name__ == "__main__":
    main()