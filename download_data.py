"""
Скачивает данные GSE138852 с базы GEO.
Запуск: python download_data.py

Датасет: Mathys et al., Nature 2019
80 пациентов (48 с болезнью Альцгеймера + 32 здоровых)
Регион мозга: энторинальная кора
"""

import os
import requests
import GEOparse


GEO_ACCESSION = "GSE138852"
OUTPUT_DIR    = "data"

COUNTS_URL = (
    "https://www.ncbi.nlm.nih.gov/geo/download/"
    "?acc=GSE138852&format=file&file=GSE138852_counts.csv.gz"
)


def download_metadata():
    """Скачивает метаданные через GEOparse."""
    print(f"Скачиваю метаданные {GEO_ACCESSION} с GEO...")
    gse = GEOparse.get_GEO(geo=GEO_ACCESSION, destdir=OUTPUT_DIR, silent=True)

    import pandas as pd
    rows = []
    for gsm_name, gsm in gse.gsms.items():
        row = {"sample": gsm_name}
        # Берём нужные поля из метаданных
        for key in ["title", "characteristics_ch1"]:
            val = gsm.metadata.get(key, [""])[0]
            row[key] = val
        rows.append(row)

    meta = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, f"{GEO_ACCESSION}_metadata.csv")
    meta.to_csv(path, index=False)
    print(f"  Метаданные сохранены: {path}")
    return path


def check_counts_file():
    """Проверяет, есть ли файл с матрицей экспрессии."""
    path = os.path.join(OUTPUT_DIR, "GSE138852_counts.csv")
    if os.path.exists(path):
        print(f"  Файл counts уже есть: {path}")
        return True

    print("\nФайл GSE138852_counts.csv не найден.")
    print("Скачайте его вручную:")
    print("  1. Откройте: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE138852")
    print("  2. В разделе 'Supplementary files' найдите GSE138852_counts.csv.gz")
    print("  3. Распакуйте и положите в папку data/")
    return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=== Загрузка данных GSE138852 ===\n")

    try:
        download_metadata()
    except Exception as e:
        print(f"  Не удалось скачать метаданные автоматически: {e}")
        print("  Метаданные нужно скачать вручную с GEO.")

    check_counts_file()
    print("\nГотово!")


if __name__ == "__main__":
    main()
