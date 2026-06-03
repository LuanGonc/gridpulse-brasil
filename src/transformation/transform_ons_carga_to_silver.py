import json
import os
import shutil
from pathlib import Path

import boto3
import pandas as pd
from dotenv import load_dotenv


load_dotenv()


AWS_PROFILE = os.getenv("AWS_PROFILE")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")


BRONZE_BASE_PATH = Path("data", "bronze", "ons", "carga_verificada")
SILVER_BASE_PATH = Path("data", "silver", "ons", "carga_verificada")


REQUIRED_SOURCE_COLUMNS = [
    "cod_areacarga",
    "dat_referencia",
    "din_referenciautc",
    "val_cargaglobal",
]


OPTIONAL_SOURCE_COLUMNS = [
    "val_cargaglobalsmmg",
    "val_cargammgd",
    "val_cargaglobalcons",
    "val_consistencia",
    "val_cargasupervisionada",
    "val_carganaosupervisionada",
]


COLUMN_RENAME_MAP = {
    "cod_areacarga": "area_carga",
    "dat_referencia": "data_referencia",
    "din_referenciautc": "referencia_utc",
    "val_cargaglobal": "carga_global_mwmed",
    "val_cargaglobalsmmg": "carga_global_sem_mmgd_mwmed",
    "val_cargammgd": "carga_mmgd_mwmed",
    "val_cargaglobalcons": "carga_global_consistida_mwmed",
    "val_consistencia": "consistencia_mwmed",
    "val_cargasupervisionada": "carga_supervisionada_mwmed",
    "val_carganaosupervisionada": "carga_nao_supervisionada_mwmed",
}


NUMERIC_COLUMNS = [
    "carga_global_mwmed",
    "carga_global_sem_mmgd_mwmed",
    "carga_mmgd_mwmed",
    "carga_global_consistida_mwmed",
    "consistencia_mwmed",
    "carga_supervisionada_mwmed",
    "carga_nao_supervisionada_mwmed",
]


CRITICAL_COLUMNS = [
    "area_carga",
    "data_referencia",
    "referencia_utc",
    "carga_global_mwmed",
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


def find_bronze_json_files() -> list[Path]:
    json_files = list(BRONZE_BASE_PATH.rglob("data.json"))

    if not json_files:
        raise FileNotFoundError(
            f"Nenhum arquivo data.json encontrado em {BRONZE_BASE_PATH}"
        )

    return json_files


def extract_ingestion_timestamp_from_path(file_path: Path) -> str | None:
    for part in file_path.parts:
        if part.startswith("ingestion_timestamp="):
            return part.replace("ingestion_timestamp=", "")

    return None


def read_bronze_files(json_files: list[Path]) -> pd.DataFrame:
    all_records = []

    for file_path in json_files:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError(f"O arquivo {file_path} não contém uma lista JSON.")

        ingestion_timestamp = extract_ingestion_timestamp_from_path(file_path)

        for record in data:
            record["_source_file"] = file_path.as_posix()
            record["_ingestion_timestamp"] = ingestion_timestamp
            all_records.append(record)

    if not all_records:
        raise ValueError("Nenhum registro encontrado nos arquivos Bronze.")

    return pd.json_normalize(all_records)


def validate_source_schema(df: pd.DataFrame) -> None:
    missing_columns = [
        column for column in REQUIRED_SOURCE_COLUMNS if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "As seguintes colunas obrigatórias não foram encontradas no Bronze: "
            + ", ".join(missing_columns)
        )

def add_missing_optional_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in OPTIONAL_SOURCE_COLUMNS:
        if column not in df.columns:
            print(f"Aviso: coluna opcional ausente no Bronze: {column}")
            df[column] = pd.NA

    return df


def transform_to_silver(df: pd.DataFrame) -> pd.DataFrame:
    validate_source_schema(df)

    df = add_missing_optional_columns(df)

    selected_columns = REQUIRED_SOURCE_COLUMNS + OPTIONAL_SOURCE_COLUMNS + [
        "_source_file",
        "_ingestion_timestamp",
    ]

    df = df[selected_columns].copy()

    df = df.rename(columns=COLUMN_RENAME_MAP)

    df["data_referencia"] = pd.to_datetime(
        df["data_referencia"],
        errors="coerce",
    ).dt.date

    df["referencia_utc"] = pd.to_datetime(
        df["referencia_utc"],
        errors="coerce",
        utc=True,
    )

    df["data_ingestao_utc"] = pd.to_datetime(
        df["_ingestion_timestamp"],
        format="%Y-%m-%dT%H-%M-%SZ",
        errors="coerce",
        utc=True,
    )

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    null_counts = df[CRITICAL_COLUMNS].isna().sum()
    columns_with_nulls = null_counts[null_counts > 0]

    if not columns_with_nulls.empty:
        raise ValueError(
            "Existem nulos em colunas críticas:\n"
            + columns_with_nulls.to_string()
        )

    before_dedup = len(df)

    df = df.sort_values("data_ingestao_utc")
    df = df.drop_duplicates(
        subset=["area_carga", "referencia_utc"],
        keep="last",
    )

    after_dedup = len(df)
    removed_duplicates = before_dedup - after_dedup

    df["ano"] = df["referencia_utc"].dt.strftime("%Y")
    df["mes"] = df["referencia_utc"].dt.strftime("%m")

    df = df[
        [
            "area_carga",
            "data_referencia",
            "referencia_utc",
            "ano",
            "mes",
            "carga_global_mwmed",
            "carga_global_sem_mmgd_mwmed",
            "carga_mmgd_mwmed",
            "carga_global_consistida_mwmed",
            "consistencia_mwmed",
            "carga_supervisionada_mwmed",
            "carga_nao_supervisionada_mwmed",
            "data_ingestao_utc",
            "_source_file",
        ]
    ]

    print("Resumo da transformação:")
    print(f"Registros antes da deduplicação: {before_dedup}")
    print(f"Registros após deduplicação: {after_dedup}")
    print(f"Duplicatas removidas: {removed_duplicates}")
    print()
    print("Tipos finais:")
    print(df.dtypes)

    return df


def write_silver_parquet(df: pd.DataFrame) -> Path:
    if SILVER_BASE_PATH.exists():
        shutil.rmtree(SILVER_BASE_PATH)

    SILVER_BASE_PATH.mkdir(parents=True, exist_ok=True)

    df.to_parquet(
        SILVER_BASE_PATH,
        engine="pyarrow",
        index=False,
        partition_cols=["area_carga", "ano", "mes"],
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

    print("Iniciando transformação Bronze -> Silver...")

    json_files = find_bronze_json_files()
    print(f"Arquivos Bronze encontrados: {len(json_files)}")

    bronze_df = read_bronze_files(json_files)
    print(f"Registros brutos carregados: {len(bronze_df)}")
    print(f"Colunas encontradas no Bronze: {list(bronze_df.columns)}")

    silver_df = transform_to_silver(bronze_df)

    silver_path = write_silver_parquet(silver_df)
    print(f"Silver salvo localmente em: {silver_path}")

    upload_directory_to_s3(
        local_base_path=silver_path,
        bucket=S3_BUCKET,
        s3_prefix="silver/ons/carga_verificada",
    )

    print("Transformação Bronze -> Silver finalizada com sucesso.")


if __name__ == "__main__":
    main()