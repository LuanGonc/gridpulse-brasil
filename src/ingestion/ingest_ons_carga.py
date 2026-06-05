import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
import requests
from dotenv import load_dotenv


load_dotenv()


AWS_PROFILE = os.getenv("AWS_PROFILE")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")

ONS_CARGA_URL = "https://apicarga.ons.org.br/prd/cargaverificada"


def fetch_ons_carga(dat_inicio: str, dat_fim: str, cod_areacarga: str) -> list[dict]:
    params = {
        "dat_inicio": dat_inicio,
        "dat_fim": dat_fim,
        "cod_areacarga": cod_areacarga,
    }

    response = requests.get(ONS_CARGA_URL, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError("A resposta da API não veio como lista de registros.")

    return data


def save_json_locally(data: list[dict], area: str, dat_inicio: str, dat_fim: str) -> Path:
    ingestion_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    output_dir = Path(
        "data",
        "bronze",
        "ons",
        "carga_verificada",
        f"area={area}",
        f"dat_inicio={dat_inicio}",
        f"dat_fim={dat_fim}",
        f"ingestion_timestamp={ingestion_timestamp}",
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "data.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return output_path


def upload_file_to_s3(local_path: Path, bucket: str) -> str:
    s3_key = local_path.as_posix().replace("data/", "")

    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    s3_client = session.client("s3")

    s3_client.upload_file(
        Filename=str(local_path),
        Bucket=bucket,
        Key=s3_key,
    )

    return f"s3://{bucket}/{s3_key}"


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


def main() -> None:
    validate_environment()

    area = "SECO"
    dat_inicio = "2026-05-01"
    dat_fim = "2026-05-02"

    print("Iniciando ingestão da carga verificada do ONS...")
    print(f"Área: {area}")
    print(f"Período: {dat_inicio} até {dat_fim}")

    data = fetch_ons_carga(
        dat_inicio=dat_inicio,
        dat_fim=dat_fim,
        cod_areacarga=area,
    )

    print(f"Registros recebidos: {len(data)}")

    local_path = save_json_locally(
        data=data,
        area=area,
        dat_inicio=dat_inicio,
        dat_fim=dat_fim,
    )

    print(f"Arquivo salvo localmente em: {local_path}")

    s3_uri = upload_file_to_s3(
        local_path=local_path,
        bucket=S3_BUCKET,
    )

    print(f"Arquivo enviado para: {s3_uri}")
    print("Ingestão finalizada com sucesso.")
import argparse
import calendar
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import boto3
import requests
from dotenv import load_dotenv


load_dotenv()


AWS_PROFILE = os.getenv("AWS_PROFILE")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")

ONS_CARGA_URL = "https://apicarga.ons.org.br/prd/cargaverificada"


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


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def generate_month_windows(start_date: date, end_date: date) -> list[tuple[str, str]]:
    windows = []

    current_date = start_date

    while current_date <= end_date:
        last_day_of_month = calendar.monthrange(
            current_date.year,
            current_date.month,
        )[1]

        month_end_date = date(
            current_date.year,
            current_date.month,
            last_day_of_month,
        )

        window_end_date = min(month_end_date, end_date)

        windows.append(
            (
                current_date.isoformat(),
                window_end_date.isoformat(),
            )
        )

        current_date = window_end_date + timedelta(days=1)

    return windows


def fetch_ons_carga(dat_inicio: str, dat_fim: str, cod_areacarga: str) -> list[dict]:
    params = {
        "dat_inicio": dat_inicio,
        "dat_fim": dat_fim,
        "cod_areacarga": cod_areacarga,
    }

    response = requests.get(ONS_CARGA_URL, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError("A resposta da API não veio como lista de registros.")

    return data


def save_json_locally(data: list[dict], area: str, dat_inicio: str, dat_fim: str) -> Path:
    ingestion_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    output_dir = Path(
        "data",
        "bronze",
        "ons",
        "carga_verificada",
        f"area={area}",
        f"dat_inicio={dat_inicio}",
        f"dat_fim={dat_fim}",
        f"ingestion_timestamp={ingestion_timestamp}",
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "data.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return output_path


def upload_file_to_s3(local_path: Path, bucket: str) -> str:
    s3_key = local_path.as_posix().replace("data/", "")

    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    s3_client = session.client("s3")

    s3_client.upload_file(
        Filename=str(local_path),
        Bucket=bucket,
        Key=s3_key,
    )

    return f"s3://{bucket}/{s3_key}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingestão Bronze da carga verificada do ONS."
    )

    parser.add_argument(
        "--area",
        required=True,
        help="Código da área de carga. Exemplo: SECO, S, NE, N.",
    )

    parser.add_argument(
        "--start",
        required=True,
        help="Data inicial no formato YYYY-MM-DD.",
    )

    parser.add_argument(
        "--end",
        required=True,
        help="Data final no formato YYYY-MM-DD.",
    )

    return parser.parse_args()


def main() -> None:
    validate_environment()

    args = parse_args()

    area = args.area.upper()
    start_date = parse_date(args.start)
    end_date = parse_date(args.end)

    if start_date > end_date:
        raise ValueError("A data inicial não pode ser maior que a data final.")

    windows = generate_month_windows(start_date, end_date)

    print("Iniciando ingestão da carga verificada do ONS...")
    print(f"Área: {area}")
    print(f"Período total: {start_date} até {end_date}")
    print(f"Janelas mensais geradas: {len(windows)}")

    total_records = 0
    uploaded_files = 0

    for dat_inicio, dat_fim in windows:
        print()
        print(f"Buscando período: {dat_inicio} até {dat_fim}")

        data = fetch_ons_carga(
            dat_inicio=dat_inicio,
            dat_fim=dat_fim,
            cod_areacarga=area,
        )

        print(f"Registros recebidos: {len(data)}")

        if not data:
            print("Aviso: nenhum registro retornado para esse período. Pulando upload.")
            continue

        local_path = save_json_locally(
            data=data,
            area=area,
            dat_inicio=dat_inicio,
            dat_fim=dat_fim,
        )

        print(f"Arquivo salvo localmente em: {local_path}")

        s3_uri = upload_file_to_s3(
            local_path=local_path,
            bucket=S3_BUCKET,
        )

        print(f"Arquivo enviado para: {s3_uri}")

        total_records += len(data)
        uploaded_files += 1

    print()
    print("Ingestão finalizada.")
    print(f"Total de registros recebidos: {total_records}")
    print(f"Total de arquivos enviados: {uploaded_files}")


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()