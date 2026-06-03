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


if __name__ == "__main__":
    main()