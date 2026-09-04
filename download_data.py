"""
Скачивание данных GSE63060 (когорта AddNeuroMed) с NCBI GEO.

Качаем два файла в data/:
  1. GSE63060_series_matrix.txt.gz — экспрессия (probe × образец) + метаданные
     образцов (включая диагноз CTL/MCI/AD).
  2. GPL6947.annot.gz — аннотация платформы Illumina (probe → ген), нужна,
     чтобы перевести зонды в названия генов.

Данные открытые, без разрешений и заявок. Запуск: python cli.py download
"""

import os
import config

# Запасные зеркала (если основной FTP-поверх-HTTPS недоступен из РФ)
SERIES_MATRIX_ALT = [
    config.SERIES_MATRIX_URL,
    config.SERIES_MATRIX_URL.replace("ftp.ncbi.nlm.nih.gov", "ftp.ncbi.nih.gov"),
]
GPL_ANNOT_ALT = [
    config.GPL_ANNOT_URL,
    config.GPL_ANNOT_URL.replace("ftp.ncbi.nlm.nih.gov", "ftp.ncbi.nih.gov"),
]


def _download(urls, dest):
    """Скачать первый доступный из urls в dest (потоково, с прогрессом)."""
    import requests

    if os.path.exists(dest) and os.path.getsize(dest) > 1024:
        print(f"  уже есть: {dest} ({os.path.getsize(dest) / 1e6:.1f} МБ)")
        return dest

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last_err = None
    for url in urls:
        try:
            print(f"  качаю: {url}")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                done = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            pct = 100 * done / total
                            print(f"\r    {done/1e6:6.1f}/{total/1e6:6.1f} МБ "
                                  f"({pct:4.1f}%)", end="", flush=True)
                print()
            print(f"  готово: {dest} ({os.path.getsize(dest)/1e6:.1f} МБ)")
            return dest
        except Exception as e:               # noqa: BLE001
            last_err = e
            print(f"\n  не вышло ({e}), пробую следующий источник…")
            if os.path.exists(dest):
                os.remove(dest)
    raise RuntimeError(f"Не удалось скачать {dest}: {last_err}")


def main():
    print("=" * 60)
    print(f"  Скачивание {config.GEO_ACCESSION} (AddNeuroMed, кровь) с NCBI GEO")
    print("=" * 60)
    _download(SERIES_MATRIX_ALT, config.SERIES_MATRIX_GZ)
    _download(GPL_ANNOT_ALT, config.GPL_ANNOT_GZ)
    print("\nГотово. Дальше: python cli.py panel")


if __name__ == "__main__":
    main()
