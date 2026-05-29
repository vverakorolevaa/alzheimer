"""
AD Blood Stage — CLI для стадийной диагностики болезни Альцгеймера
по экспрессии генов крови (датасет GSE63060, когорта AddNeuroMed).

Команды:
  python cli.py download    # скачать GSE63060 (series matrix + аннотацию GPL6947)
  python cli.py panel       # отбор мини-панели генов + обучение 3-классовой модели
  python cli.py report      # собрать презентацию (.pptx)
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


def cmd_report(args):
    import build_presentation
    build_presentation.main()


def main():
    parser = argparse.ArgumentParser(
        prog="ad-blood-stage",
        description="Стадийная диагностика болезни Альцгеймера по генам крови",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Быстрый старт:
  python cli.py download      # скачать GSE63060 с NCBI GEO (~70 МБ)
  python cli.py panel         # отбор панели + обучение модели (норма/MCI/деменция)
  streamlit run app.py        # веб-интерфейс поддержки решения врача
        """,
    )
    sub = parser.add_subparsers(dest="command", metavar="команда")
    sub.required = True
    sub.add_parser("download", help="Скачать данные GSE63060 (кровь) с NCBI GEO")
    sub.add_parser("panel",    help="Отбор мини-панели генов + 3-классовая модель")
    sub.add_parser("report",   help="Сгенерировать презентацию (.pptx)")

    args = parser.parse_args()
    {"download": cmd_download, "panel": cmd_panel, "report": cmd_report}[args.command](args)


if __name__ == "__main__":
    main()
