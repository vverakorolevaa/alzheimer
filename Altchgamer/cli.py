"""
Altchgamer — CLI-приложение для анализа болезни Альцгеймера.

Использование:
  python cli.py download            # скачать данные GSE138852
  python cli.py analyze             # полный анализ (DEG + визуализация + ансамбль + Enrichr)
  python cli.py classify            # только классификатор (нужен предыдущий analyze)
  python cli.py report              # сгенерировать PowerPoint-отчёт
  python cli.py --help
"""

import argparse
import os
import sys
import warnings
warnings.filterwarnings("ignore")


# ── Команда: download ─────────────────────────────────────────────────

def cmd_download(args):
    import download_data
    download_data.main()


# ── Команда: analyze ──────────────────────────────────────────────────

def cmd_analyze(args):
    import pandas as pd
    from data_loader        import DataLoader
    from preprocessor       import Preprocessor
    from gene_analyzer      import GeneAnalyzer
    from visualizer         import Visualizer
    from ensemble_classifier import EnsembleClassifier
    from enrichment_analysis import EnrichmentAnalyzer
    from config import RESULTS_FOLDER

    os.makedirs(RESULTS_FOLDER, exist_ok=True)

    _banner("Анализ экспрессии генов при болезни Альцгеймера")

    print("\n[1/6] Загрузка данных")
    loader = DataLoader()
    adata  = loader.load()
    loader.print_summary()

    print("\n[2/6] Предобработка")
    adata = Preprocessor().preprocess(adata)

    print("\n[3/6] Поиск DEG (Mann-Whitney U + FDR Бенджамини-Хохберга)")
    analyzer    = GeneAnalyzer(adata)
    deg_results = analyzer.run_all()

    all_degs = []
    for ct, df in deg_results.items():
        df["cell_type"] = ct
        df.to_csv(os.path.join(RESULTS_FOLDER, f"DEGs_{ct}.csv"), index=False)
        all_degs.append(df[df["significant"]])
    pd.concat(all_degs).to_csv(os.path.join(RESULTS_FOLDER, "DEGs_all.csv"), index=False)

    summary = analyzer.summary_table()
    print("\nИтоговая таблица:")
    print(summary.to_string(index=False))
    summary.to_csv(os.path.join(RESULTS_FOLDER, "summary_by_cell_type.csv"), index=False)

    print("\n[4/6] Визуализация")
    viz = Visualizer()
    viz.deg_barplot(summary)
    for ct, df in deg_results.items():
        viz.volcano_plot(df, ct)
    for ct in summary.head(3)["Тип клеток"].tolist():
        viz.heatmap(adata, deg_results[ct], ct)
    viz.umap_plot(adata)

    print("\n[5/6] Мультимодальный ансамблевый классификатор")
    clf     = EnsembleClassifier()
    metrics = clf.train(adata, deg_results)
    _print_metrics(metrics)

    print("\n[6/6] Enrichr API — биологические пути")
    enricher = EnrichmentAnalyzer()
    most_ct  = summary.iloc[0]["Тип клеток"]
    top_genes = analyzer.get_top_degs(most_ct, n=100)["gene"].tolist()
    enricher.run(top_genes, cell_type=most_ct)

    _done(RESULTS_FOLDER)


def cmd_classify(args):
    import pandas as pd
    from data_loader         import DataLoader
    from preprocessor        import Preprocessor
    from gene_analyzer       import GeneAnalyzer
    from ensemble_classifier import EnsembleClassifier
    from config import RESULTS_FOLDER

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    _banner("Мультимодальный классификатор (отдельный запуск)")

    loader = DataLoader()
    adata  = loader.load()
    adata  = Preprocessor().preprocess(adata)

    analyzer    = GeneAnalyzer(adata)
    deg_results = analyzer.run_all()

    clf     = EnsembleClassifier()
    metrics = clf.train(adata, deg_results)
    _print_metrics(metrics)
    _done(RESULTS_FOLDER)


def cmd_report(args):
    import build_presentation
    build_presentation.main()


def _banner(title):
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def _print_metrics(metrics):
    print("\n  Результаты классификации:")
    for head, m in metrics.items():
        print(f"    {head:25s}: acc={m['accuracy']:.3f}  AUC={m['roc_auc']:.3f}")


def _done(folder):
    print("\n" + "=" * 60)
    print(f"  Готово! Результаты: {folder}/")
    print("  Отчёт: python cli.py report")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        prog="altchgamer",
        description="Анализ болезни Альцгеймера: DEG + мультимодальный ансамбль + Enrichr",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python cli.py download            # скачать данные
  python cli.py analyze             # полный анализ
  python cli.py classify            # только классификатор
  python cli.py report              # сгенерировать отчёт
        """,
    )

    sub = parser.add_subparsers(dest="command", metavar="команда")
    sub.required = True

    sub.add_parser("download", help="Скачать данные GSE138852 с GEO")
    sub.add_parser("analyze",  help="Полный анализ: DEG + визуализация + классификатор + Enrichr")
    sub.add_parser("classify", help="Только мультимодальный ансамблевый классификатор")
    sub.add_parser("report",   help="Сгенерировать PowerPoint-отчёт")

    args = parser.parse_args()

    dispatch = {
        "download": cmd_download,
        "analyze":  cmd_analyze,
        "classify": cmd_classify,
        "report":   cmd_report,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
