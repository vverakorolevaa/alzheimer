"""
Alzheimer — CLI для анализа дифференциальной экспрессии генов
при болезни Альцгеймера (scRNA-seq, GSE138852).

Команды:
  python cli.py download    # скачать данные GSE138852 с NCBI GEO
  python cli.py analyze     # DEG-анализ + ансамблевый классификатор + Enrichr
  python cli.py panel       # отбор мини-панели генов-биомаркеров (новизна)
  python cli.py --help
"""

import argparse
import os
import warnings
warnings.filterwarnings("ignore")


# ── download ──────────────────────────────────────────────────────────

def cmd_download(args):
    import download_data
    download_data.main()


# ── analyze ───────────────────────────────────────────────────────────

def cmd_analyze(args):
    import pandas as pd
    from data_loader         import DataLoader
    from preprocessor        import Preprocessor
    from gene_analyzer       import GeneAnalyzer
    from visualizer          import Visualizer
    from ensemble_classifier import EnsembleClassifier
    from enrichment_analysis import EnrichmentAnalyzer
    from config import RESULTS_FOLDER

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    _banner("Анализ дифференциальной экспрессии генов (GSE138852)")

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

    print("\n[5/6] Ансамблевый классификатор")
    clf     = EnsembleClassifier()
    metrics = clf.train(adata, deg_results)
    _print_metrics(metrics)

    print("\n[6/6] Enrichr API — биологические пути")
    enricher = EnrichmentAnalyzer()
    most_ct  = summary.iloc[0]["Тип клеток"]
    top_genes = analyzer.get_top_degs(most_ct, n=100)["gene"].tolist()
    enricher.run(top_genes, cell_type=most_ct)

    _done(RESULTS_FOLDER)


# ── panel ─────────────────────────────────────────────────────────────

def cmd_panel(args):
    import biomarker_panel
    biomarker_panel.main()


# ── report ────────────────────────────────────────────────────────────

def cmd_report(args):
    import build_presentation
    build_presentation.main()


# ── Утилиты ───────────────────────────────────────────────────────────

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
    print("=" * 60)


# ── Точка входа ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="alzheimer",
        description="Анализ дифференциальной экспрессии генов при болезни Альцгеймера",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Быстрый старт:
  python cli.py download             # скачать GSE138852 с NCBI GEO (~2 GB)
  python cli.py analyze              # DEG + ансамблевый классификатор + Enrichr
  python cli.py panel                # отбор мини-панели генов-биомаркеров
        """,
    )

    sub = parser.add_subparsers(dest="command", metavar="команда")
    sub.required = True

    sub.add_parser("download", help="Скачать scRNA-seq данные GSE138852")
    sub.add_parser("analyze",  help="DEG-анализ + классификатор + pathway enrichment")
    sub.add_parser("panel",    help="Отбор мини-панели генов-биомаркеров для ранней диагностики")
    sub.add_parser("report",   help="Сгенерировать PowerPoint-презентацию")

    args = parser.parse_args()
    {
        "download": cmd_download,
        "analyze":  cmd_analyze,
        "panel":    cmd_panel,
        "report":   cmd_report,
    }[args.command](args)


if __name__ == "__main__":
    main()
