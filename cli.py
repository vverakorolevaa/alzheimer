"""
Alzheimer — CLI для диагностики болезни Альцгеймера.

Команды:
  python cli.py generate-synthetic   # создать тестовые данные OASIS-3
  python cli.py classify-oasis       # мультимодальный классификатор (МРТ + клиника)
  python cli.py report               # сгенерировать PowerPoint-отчёт
  python cli.py download             # скачать данные GSE138852 (исследовательский анализ)
  python cli.py analyze              # DEG-анализ на GSE138852
  python cli.py --help
"""

import argparse
import os
import sys
import warnings
warnings.filterwarnings("ignore")


# ── setup-kaggle ──────────────────────────────────────────────────────

def cmd_setup_kaggle(args):
    import shutil
    from data_loader_kaggle import KaggleOASISLoader
    from config import KAGGLE_LONG_FILE, KAGGLE_CROSS_FILE

    src_long  = "/Users/vera/Downloads/archive/oasis_longitudinal.csv"
    src_cross = "/Users/vera/Downloads/archive/oasis_cross-sectional.csv"

    _banner("Настройка данных OASIS (Kaggle)")
    loader = KaggleOASISLoader()
    loader.copy_from_downloads(src_long, src_cross)
    print("Готово! Запустите: python cli.py classify-kaggle")


# ── classify-kaggle ───────────────────────────────────────────────────

def cmd_classify_kaggle(args):
    import numpy as np
    from data_loader_kaggle    import KaggleOASISLoader
    from multimodal_classifier import MultimodalClassifier
    from visualizer_multimodal import MultimodalVisualizer
    from config import RESULTS_FOLDER

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    _banner("Мультимодальная диагностика AD — OASIS (Kaggle)")

    print("\n[1/4] Загрузка данных")
    loader = KaggleOASISLoader()
    loader.load()
    loader.print_summary()
    X_mri, X_clin, y, groups, mri_cols, clin_cols = loader.get_feature_matrices()

    print("\n[2/4] Обучение (Gated Fusion: МРТ + клиника)")
    clf     = MultimodalClassifier()
    metrics = clf.train(X_mri, X_clin, y, groups,
                        mri_names=mri_cols, clin_names=clin_cols)

    print("\n[3/4] Визуализация")
    viz = MultimodalVisualizer()
    viz.plot_training_loss(metrics["losses"])
    viz.plot_multihead_roc(
        metrics["y_true"], metrics["probs"],
        metrics["probs_mri_only"], metrics["probs_clin_only"],
    )
    viz.plot_confusion_matrix(metrics["y_true"], metrics["preds"])
    viz.plot_gate_weights(metrics["gates"], metrics["y_true"])
    importances = np.std(metrics["embeddings"][:, :len(mri_cols)], axis=0)
    viz.plot_roi_importance(mri_cols, importances)
    viz.plot_biomarker_trajectory(loader.df)
    viz.plot_fusion_umap(metrics["embeddings"], metrics["y_true"])

    print(f"\n[4/4] Accuracy: {metrics['accuracy']:.3f}  "
          f"ROC-AUC: {metrics['roc_auc']:.3f}")
    _done(RESULTS_FOLDER)


# ── generate-synthetic ────────────────────────────────────────────────

def cmd_generate_synthetic(args):
    from generate_synthetic_oasis import generate
    _banner("Генерация синтетических данных OASIS-3")
    generate()
    print("\nДалее запустите: python cli.py classify-oasis")


# ── classify-oasis ────────────────────────────────────────────────────

def cmd_classify_oasis(args):
    import numpy as np
    from data_loader_oasis       import OASISLoader
    from multimodal_classifier   import MultimodalClassifier
    from visualizer_multimodal   import MultimodalVisualizer
    from config import RESULTS_FOLDER

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    _banner("Мультимодальная диагностика AD: МРТ + клинические данные")

    print("\n[1/4] Загрузка данных OASIS-3")
    loader = OASISLoader()
    loader.load()
    loader.print_summary()
    X_mri, X_clin, y, groups, mri_cols, clin_cols = loader.get_feature_matrices()

    print("\n[2/4] Обучение мультимодальной сети (Gated Fusion)")
    clf     = MultimodalClassifier()
    metrics = clf.train(X_mri, X_clin, y, groups,
                        mri_names=mri_cols, clin_names=clin_cols)

    print("\n[3/4] Визуализация")
    viz = MultimodalVisualizer()
    viz.plot_training_loss(metrics["losses"])
    viz.plot_multihead_roc(
        metrics["y_true"],
        metrics["probs"],
        metrics["probs_mri_only"],
        metrics["probs_clin_only"],
    )
    viz.plot_confusion_matrix(metrics["y_true"], metrics["preds"])
    viz.plot_gate_weights(metrics["gates"], metrics["y_true"])

    # Важность МРТ-признаков: std активаций по тестовой выборке
    importances = np.std(metrics["embeddings"][:, :len(mri_cols)], axis=0)
    if len(importances) != len(mri_cols):
        importances = np.ones(len(mri_cols))
    viz.plot_roi_importance(mri_cols, importances)

    viz.plot_biomarker_trajectory(loader.df)
    viz.plot_fusion_umap(metrics["embeddings"], metrics["y_true"])

    print("\n[4/4] Результаты")
    print(f"  Accuracy:  {metrics['accuracy']:.3f}")
    print(f"  ROC-AUC:   {metrics['roc_auc']:.3f}")
    _done(RESULTS_FOLDER)


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
    _banner("Исследовательский анализ scRNA-seq (GSE138852)")

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
    print("  Отчёт: python cli.py report")
    print("=" * 60)


# ── Точка входа ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="altchgamer",
        description="Мультимодальная диагностика болезни Альцгеймера",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Быстрый старт (реальные данные Kaggle):
  python cli.py setup-kaggle         # скопировать файлы из Downloads
  python cli.py classify-kaggle      # обучить и оценить модель
  python cli.py report               # сгенерировать отчёт

Исследовательский анализ (scRNA-seq):
  python cli.py download             # скачать GSE138852
  python cli.py analyze              # DEG + ансамблевый классификатор
        """,
    )

    sub = parser.add_subparsers(dest="command", metavar="команда")
    sub.required = True

    sub.add_parser("setup-kaggle",
                   help="Скопировать файлы OASIS из Downloads в data/kaggle/")
    sub.add_parser("classify-kaggle",
                   help="Мультимодальный классификатор на реальных данных OASIS (Kaggle)")
    sub.add_parser("generate-synthetic",
                   help="Сгенерировать синтетические данные OASIS-3")
    sub.add_parser("classify-oasis",
                   help="Мультимодальный классификатор на синтетических данных")
    sub.add_parser("report",   help="Сгенерировать PowerPoint-отчёт")
    sub.add_parser("download", help="Скачать scRNA-seq данные GSE138852")
    sub.add_parser("analyze",  help="DEG-анализ на GSE138852 (исследовательский)")

    args = parser.parse_args()
    {
        "setup-kaggle":       cmd_setup_kaggle,
        "classify-kaggle":    cmd_classify_kaggle,
        "generate-synthetic": cmd_generate_synthetic,
        "classify-oasis":     cmd_classify_oasis,
        "report":             cmd_report,
        "download":           cmd_download,
        "analyze":            cmd_analyze,
    }[args.command](args)


if __name__ == "__main__":
    main()
