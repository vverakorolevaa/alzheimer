# План проекта Altchgamer

## Цель

Разработать приложение для **ранней диагностики болезни Альцгеймера**
на основе мультимодальных данных: МРТ головного мозга + клинические тесты.
Приложение должно различать три состояния: CN (норма), MCI (предстадия), AD (болезнь).

## Что отличает проект от аналогов

| Признак | Стандартный подход | Altchgamer |
|---|---|---|
| Данные | Одна модальность | МРТ + клиника (две модальности) |
| Fusion | Нет / конкатенация | Gated Fusion с интерпретируемыми весами |
| Классы | 2 (AD vs. норма) | 3 (CN / MCI / AD — ранняя диагностика) |
| Split | Случайный | Donor-level (нет утечки данных) |
| Интерфейс | Jupyter notebook | CLI-приложение |
| Интерпретируемость | Нет | Gate-веса, ROI-важность, UMAP |

## Этапы выполнения

### Этап 1: Слой данных
- [x] `config.py` — все константы и пути
- [x] `data_loader_oasis.py` — загрузка и объединение CSV
- [x] `generate_synthetic_oasis.py` — тестовые данные (300 пациентов, реалистичные)

### Этап 2: Модель
- [x] `multimodal_classifier.py` — двуголовая нейросеть с Gated Fusion
  - [x] MRIEncoder (20 → 256 → 128 → 128)
  - [x] ClinicalEncoder (6 → 64 → 128)
  - [x] GatedFusion (gate + weighted sum)
  - [x] MultimodalADNet (3-class output)
  - [x] MultimodalClassifier (donor-level split, weighted loss, базовые модели для сравнения)

### Этап 3: Визуализация
- [x] `visualizer_multimodal.py`
  - [x] Кривая обучения
  - [x] Multi-head ROC (Fusion vs MRI-only vs Clinical-only)
  - [x] Confusion matrix (3 класса)
  - [x] Gate-веса по классам (боксплот)
  - [x] ROI importance (барплот)
  - [x] Biomarker trajectory (CN→MCI→AD)
  - [x] UMAP/t-SNE эмбеддингов

### Этап 4: Приложение и отчёт
- [x] `cli.py` — команды: generate-synthetic, classify-oasis, report
- [x] `build_presentation.py` — 12 слайдов PowerPoint
- [x] `docs/functional_scheme.md`
- [x] `docs/literature_review.md`
- [x] `docs/plan.md`

### Этап 5: Реальные данные (в процессе)
- [ ] Зарегистрироваться на oasis-brains.org ✓ (сделано)
- [ ] Дождаться одобрения доступа (1–3 дня)
- [ ] Скачать данные OASIS-3:
  - `oasis3_freesurfer.csv` → переименовать/адаптировать в `mri_features.csv`
  - `oasis3_cognition.csv` + `oasis3_demographics.csv` → `clinical.csv`
- [ ] Запустить `python cli.py classify-oasis` на реальных данных
- [ ] Сравнить результаты с синтетическими

### Этап 6: Улучшения (опционально)
- [ ] Лонгитюдный анализ: предсказание перехода MCI → AD
- [ ] Cross-attention вместо Gated Fusion (если данных станет больше)
- [ ] Добавить 3D-CNN энкодер для сырых МРТ-снимков (NIfTI)
- [ ] Leave-One-Donor-Out CV для более строгой валидации

## Конфигурация (config.py)

```
padj < 0.05, |log2FC| > 1.0   — пороги для DEG (scRNA-seq)
MULTIMODAL_EMBED_DIM = 128     — размер эмбеддингов
MULTIMODAL_EPOCHS    = 50      — эпохи обучения
MULTIMODAL_BATCH     = 32      — размер батча
MULTIMODAL_TEST_SIZE = 0.2     — доля тестовой выборки (по пациентам)
```

## Структура файлов

```
Altchgamer/
├── cli.py                      — точка входа
├── config.py                   — все настройки
│
├── data_loader_oasis.py        — загрузка OASIS-3
├── generate_synthetic_oasis.py — тестовые данные
├── multimodal_classifier.py    — двуголовая модель
├── visualizer_multimodal.py    — 7 графиков
│
├── data_loader.py              — загрузка GSE138852 (scRNA-seq)
├── preprocessor.py             — нормализация scRNA-seq
├── gene_analyzer.py            — DEG-анализ
├── visualizer.py               — volcano, heatmap, UMAP
├── ensemble_classifier.py      — 3-головый ансамбль scRNA-seq
├── enrichment_analysis.py      — Enrichr API
│
├── build_presentation.py       — PowerPoint-отчёт
├── docs/                       — документация
│   ├── functional_scheme.md
│   ├── plan.md
│   └── literature_review.md
│
└── data/
    ├── oasis/                  — данные OASIS-3
    │   ├── mri_features.csv
    │   └── clinical.csv
    └── GSE138852_*/            — данные scRNA-seq
```
