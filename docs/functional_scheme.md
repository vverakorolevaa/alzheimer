# Функциональная схема приложения Altchgamer

## Архитектура

```
python cli.py <команда>
        |
        +-- download   → DataLoader → GEO API → data/
        |
        +-- analyze    → [1] DataLoader
        |                  [2] Preprocessor
        |                  [3] GeneAnalyzer  →  DEG-таблицы (CSV)
        |                  [4] Visualizer    →  графики (PNG)
        |                  [5] EnsembleClassifier
        |                  [6] EnrichmentAnalyzer → Enrichr API
        |
        +-- classify   → DataLoader → Preprocessor → GeneAnalyzer
        |                → EnsembleClassifier
        |
        +-- report     → BuildPresentation → results/report.pptx
```

## Модуль EnsembleClassifier — три параллельных головы

```
Входные данные (AnnData: клетки × гены)
        |
        +--[Модальность 1]-- Топ-DEG гены ──────────► ExpressionHead (MLP 500→256→64→2)
        |                                                        |
        +--[Модальность 2]-- Клеточный состав ──────► CompositionHead (MLP 8→32→16→2)
        |                    (доли типов клеток                  |
        |                     в образце донора)                  |
        +--[Предобученная]-- Gene2Vec эмбеддинги ──► EmbeddingHead  (MLP 200→128→64→2)
             модель          (Du et al., 2019)                   |
             ↑                                                    |
             Кэш: ~/.cache/altchgamer/gene2vec.txt               |
                                                                  ↓
                                              Avg((p1 + p2 + p3) / 3) → AD / Здоровый
```

## Поток данных

| Шаг | Вход | Выход | Модуль |
|-----|------|-------|--------|
| Загрузка | CSV файлы GEO | AnnData | data_loader.py |
| Предобработка | AnnData (сырой) | AnnData (норм.) | preprocessor.py |
| DEG-анализ | AnnData | DataFrame по типам клеток | gene_analyzer.py |
| Визуализация | AnnData + DEG | PNG-файлы | visualizer.py |
| Gene2Vec | DEG-гены | float32 матрица (N × 200) | gene_embeddings.py |
| Состав | AnnData obs | float32 матрица (N × n_ct) | gene_embeddings.py |
| Ансамбль | 3 матрицы | Метрики + .pt файлы | ensemble_classifier.py |
| Enrichr | Список генов | GO/KEGG таблицы | enrichment_analysis.py |
| Отчёт | PNG + CSV | report.pptx | build_presentation.py |

## Структура файлов проекта

```
Altchgamer/
├── cli.py                    # точка входа (argparse CLI)
├── main.py                   # обратная совместимость
├── config.py                 # все параметры в одном месте
├── data_loader.py            # загрузка GSE138852
├── preprocessor.py           # фильтрация, нормализация, log1p
├── gene_analyzer.py          # DEG: Mann-Whitney + BH FDR
├── visualizer.py             # volcano, heatmap, UMAP, barplot
├── gene_embeddings.py        # Gene2Vec + клеточный состав
├── ensemble_classifier.py    # три головы + ансамбль
├── enrichment_analysis.py    # Enrichr API (GO, KEGG)
├── build_presentation.py     # PowerPoint-отчёт
├── download_data.py          # скачивание данных GEO
├── requirements.txt
└── docs/
    ├── functional_scheme.md
    ├── literature_review.md
    └── plan.md
```
