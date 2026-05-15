"""
Запускает полный анализ.

Рекомендуемый способ запуска — через CLI:
  python cli.py --help
  python cli.py download
  python cli.py analyze
  python cli.py report
"""

from cli import cmd_analyze


def main():
    class _Args:
        pass
    cmd_analyze(_Args())


if __name__ == "__main__":
    main()
