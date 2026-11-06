"""
AD Blood Stage — CLI для стадийной диагностики болезни Альцгеймера
по экспрессии генов крови (датасет GSE63060, когорта AddNeuroMed).

Команды:
  python cli.py download    # скачать GSE63060 и GSE63061 (+ аннотации платформ)
  python cli.py panel       # отбор мини-панели генов + обучение 3-классовой модели
  python cli.py external    # проверка модели на независимой когорте GSE63061
  python cli.py compare     # сравнение логистической регрессии с другими моделями
  python cli.py --help

Веб-интерфейс:  streamlit run app.py
"""

import argparse
import warnings
warnings.filterwarnings("ignore")


def cmd_download(args):
    import download_data
    download_data.main()


def cmd_panel(args):
    import biomarker_panel
    biomarker_panel.main()


def cmd_external(args):
    import external_validation
    external_validation.main()


def cmd_compare(args):
    import compare_models
    compare_models.main()


def main():
    parser = argparse.ArgumentParser(
        prog="ad-blood-stage",
        description="Стадийная диагностика болезни Альцгеймера по генам крови",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Быстрый старт:
  python cli.py download      # скачать GSE63060 и GSE63061 с NCBI GEO (~150 МБ)
  python cli.py panel         # отбор панели + обучение модели (норма/MCI/деменция)
  python cli.py external      # проверка на независимой когорте GSE63061
  python cli.py compare       # сравнение с другими моделями
  streamlit run app.py        # веб-интерфейс поддержки решения врача
        """,
    )
    sub = parser.add_subparsers(dest="command", metavar="команда")
    sub.required = True
    sub.add_parser("download", help="Скачать данные GSE63060 и GSE63061 с NCBI GEO")
    sub.add_parser("panel",    help="Отбор мини-панели генов + 3-классовая модель")
    sub.add_parser("external", help="Проверка на независимой когорте GSE63061")
    sub.add_parser("compare",  help="Сравнение с другими моделями машинного обучения")

    args = parser.parse_args()
    {"download": cmd_download, "panel": cmd_panel,
     "external": cmd_external, "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    main()
