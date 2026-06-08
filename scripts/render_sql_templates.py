import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


S3_BUCKET = os.getenv("S3_BUCKET")

if not S3_BUCKET:
    raise EnvironmentError(
        "Variável S3_BUCKET não encontrada no .env. "
        "Configure S3_BUCKET antes de gerar os SQLs."
    )


TEMPLATE_DIR = Path("sql", "gold")
OUTPUT_DIR = Path("sql", "generated", "gold")


def render_sql_templates() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sql_files = sorted(TEMPLATE_DIR.glob("*.sql"))

    if not sql_files:
        raise FileNotFoundError(f"Nenhum arquivo SQL encontrado em {TEMPLATE_DIR}")

    for template_path in sql_files:
        content = template_path.read_text(encoding="utf-8")

        rendered_content = content.replace("{{S3_BUCKET}}", S3_BUCKET)

        output_path = OUTPUT_DIR / template_path.name
        output_path.write_text(rendered_content, encoding="utf-8")

        print(f"Gerado: {output_path}")


if __name__ == "__main__":
    render_sql_templates()