import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
import requests
from dotenv import load_dotenv


load_dotenv()


AWS_PROFILE = os.getenv("AWS_PROFILE")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")


INMET_HISTORICAL_URL_TEMPLATE = (
    "https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip"
)


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


def build_output_paths(year: int) -> tuple[Path, Path, Path]:
    ingestion_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    base_dir = Path(
        "data",
        "bronze",
        "inmet",
        "dados_historicos",
        f"ano={year}",
        f"ingestion_timestamp={ingestion_timestamp}",
    )

    zip_path = base_dir / f"inmet_dados_historicos_{year}.zip"
    extracted_dir = base_dir / "extracted"

    return base_dir, zip_path, extracted_dir


def download_inmet_zip(year: int, zip_path: Path) -> None:
    url = INMET_HISTORICAL_URL_TEMPLATE.format(year=year)

    print(f"Baixando dados históricos do INMET: {url}")

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zip_path.open("wb") as file:
        file.write(response.content)

    print(f"Arquivo ZIP salvo em: {zip_path}")
    print(f"Tamanho do arquivo: {zip_path.stat().st_size / 1024 / 1024:.2f} MB")


def extract_zip(zip_path: Path, extracted_dir: Path) -> list[Path]:
    extracted_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extracted_dir)

    extracted_files = [path for path in extracted_dir.rglob("*") if path.is_file()]

    print(f"Arquivos extraídos: {len(extracted_files)}")

    for file_path in extracted_files[:10]:
        print(f" - {file_path}")

    if len(extracted_files) > 10:
        print(" ...")

    return extracted_files


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


def main() -> None:
    validate_environment()

    year = 2025

    print("Iniciando ingestão Bronze dos dados históricos do INMET...")
    print(f"Ano: {year}")

    base_dir, zip_path, extracted_dir = build_output_paths(year)

    download_inmet_zip(year=year, zip_path=zip_path)

    extracted_files = extract_zip(
        zip_path=zip_path,
        extracted_dir=extracted_dir,
    )

    s3_uri = upload_file_to_s3(
        local_path=zip_path,
        bucket=S3_BUCKET,
    )

    print(f"ZIP enviado para: {s3_uri}")
    print(f"Pasta local da ingestão: {base_dir}")
    print(f"Arquivos extraídos localmente: {len(extracted_files)}")
    print("Ingestão Bronze do INMET finalizada com sucesso.")


if __name__ == "__main__":
    main()
    