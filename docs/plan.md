# План проекта Altchgamer

## Цель

Разработать терминальное приложение для анализа молекулярных механизмов болезни Альцгеймера на основе данных одноклеточного РНК-секвенирования (scRNA-seq). Приложение должно быть воспроизводимым, научно обоснованным и отличаться от существующих решений за счёт мультимодального ансамблевого классификатора с предобученными эмбеддингами генов.

## Что отличает проект от аналогов

| Признак | Стандартный pipeline | Altchgamer |
|---------|---------------------|------------|
| Интерфейс | Jupyter notebook | CLI-приложение (subcommands) |
| Классификатор | Один MLP | Ансамбль из 3 голов |
| Модальности | Только транскриптомика | Транскриптомика + клеточный состав |
| Предобученная модель | Нет | Gene2Vec (Du et al., 2019) |
| Отчёт | Нет | Автоматический PowerPoint |

## Этапы выполнения

### Этап 1: Данные и предобработка
- [x] Скрипт загрузки данных GSE138852 с GEO
- [x] Класс DataLoader (CSV → AnnData)
- [x] Класс Preprocessor (фильтрация, нормализация, log1p)

### Этап 2: DEG-анализ
- [x] GeneAnalyzer: Mann-Whitney U + BH FDR по каждому типу клеток
- [x] Экспорт таблиц в CSV
- [x] Сводная таблица по типам клеток

### Этап 3: Визуализация
- [x] Volcano plot (для каждого типа клеток)
- [x] Heatmap топ-DEG генов
- [x] UMAP-карта клеток
- [x] Bar plot DEG по типам клеток

### Этап 4: Мультимодальный ансамбль
- [x] Head 1: Expression MLP (топ-DEG транскриптомика)
- [x] Head 2: Composition MLP (клеточный состав образца — вторая модальность)
- [x] Head 3: Gene2Vec Embedding MLP (предобученная модель Du et al., 2019)
- [x] Ансамбль: усреднение softmax-вероятностей трёх голов
- [x] Метрики и сравнительный график голов vs. ансамбль

### Этап 5: Биологическая интерпретация
- [x] EnrichmentAnalyzer: интеграция с Enrichr API
- [x] Запросы по GO Biological Process и KEGG

### Этап 6: CLI и отчёт
- [x] cli.py: argparse subcommands (download, analyze, classify, report)
- [x] build_presentation.py: автоматический PowerPoint-отчёт
- [x] Документация (functional_scheme.md, literature_review.md, plan.md)

### Этап 7: Git и публикация
- [x] Инициализация репозитория, .gitignore
- [x] Push на GitHub

## Использование приложения

```bash
# Установка зависимостей
pip install -r requirements.txt

# 1. Скачать данные
python cli.py download

# 2. Полный анализ
python cli.py analyze

# 3. Только классификатор (если данные уже есть)
python cli.py classify

# 4. Сгенерировать отчёт
python cli.py report

# Справка
python cli.py --help
```

## Технический стек

- **Python 3.10+**
- **scanpy / anndata** — работа с scRNA-seq данными
- **scipy / statsmodels** — DEG (Mann-Whitney + BH FDR)
- **PyTorch** — три MLP-головы
- **scikit-learn** — масштабирование, метрики, train/test split
- **matplotlib / seaborn** — визуализация
- **requests** — Gene2Vec download, Enrichr API
- **python-pptx** — PowerPoint-отчёт

## Параметры (config.py)

| Параметр | Значение | Описание |
|----------|----------|----------|
| PVALUE_THRESHOLD | 0.05 | Порог FDR для DEG |
| LOG2FC_THRESHOLD | 1.0 | Порог fold change |
| CLASSIFIER_TOP_GENES | 500 | Генов для Head 1 |
| CLASSIFIER_EPOCHS | 30 | Эпохи обучения |
| GENE2VEC_DIM | 200 | Размерность Gene2Vec |
| GENE2VEC_TOP | 100 | Генов для Head 3 |
