# План проекта: Мультимодальная ранняя диагностика болезни Альцгеймера

## Цель

Разработать приложение для **ранней диагностики болезни Альцгеймера** по двум источникам данных:
МРТ головного мозга (FreeSurfer биомаркеры) + клинические тесты (MMSE, CDR).

Приложение классифицирует пациентов по трём стадиям: **CN** (норма), **MCI** (лёгкие нарушения — ключевое «окно»), **AD** (деменция).

---

## Что отличает проект от стандартного подхода

| Признак | Стандартный подход | Этот проект |
|---|---|---|
| Данные | Одна модальность | МРТ + клиника (две модальности) |
| Объединение | Нет / конкатенация | **Gated Fusion** с интерпретируемыми весами |
| Классы | 2 (AD vs. норма) | **3 (CN / MCI / AD)** — ранняя диагностика |
| Разделение данных | Случайное | **Donor-level split** — нет утечки данных |
| Интерфейс | Jupyter notebook | **CLI-приложение** с командами |
| Интерпретируемость | Отсутствует | Gate-веса, ROI-важность, UMAP, 7 графиков |
| Данные | Ограниченный доступ | **OASIS (Kaggle)** — открытые, доступны без регистрации |

---

## Этапы выполнения

### Этап 1: Данные — ВЫПОЛНЕНО
- [x] `config.py` — все константы, пути, гиперпараметры
- [x] `data_loader_kaggle.py` — загрузка OASIS с Kaggle
  - [x] oasis_longitudinal.csv (150 пациентов, продольные)
  - [x] oasis_cross-sectional.csv (436 пациентов, поперечные)
  - [x] объединение датасетов, возраст ≥ 60, медианное заполнение пропусков
  - [x] унификация меток: Group/CDR → 0=CN, 1=MCI, 2=AD
- [x] `generate_synthetic_oasis.py` — тестовые данные для отладки
- [x] `data_loader_oasis.py` — загрузка синтетических данных

### Этап 2: Модель — ВЫПОЛНЕНО
- [x] `multimodal_classifier.py` — двуголовая нейросеть с Gated Fusion
  - [x] **MRIEncoder**: Linear(3→256)→BN→ReLU→Drop→Linear(256→128)→BN→ReLU→Drop→Linear(128→128)
  - [x] **ClinicalEncoder**: Linear(6→64)→ReLU→Drop→Linear(64→128)
  - [x] **GatedFusion**: gate=σ(W·[e_mri;e_clin]), fused=gate·e_mri+(1-gate)·e_clin
  - [x] **MultimodalADNet**: 3 класса (CN/MCI/AD)
  - [x] **Базовые модели**: MRI-only и Clinical-only для сравнения
  - [x] **Donor-level split**: GroupShuffleSplit по subject_id
  - [x] **Weighted CrossEntropyLoss**: компенсация дисбаланса классов
  - [x] Регуляризация: BatchNorm + Dropout(0.3) + weight_decay=1e-4

### Этап 3: Визуализация — ВЫПОЛНЕНО
- [x] `visualizer_multimodal.py` — 7 графиков
  - [x] training_loss.png — кривая обучения
  - [x] multihead_roc.png — ROC: Fusion vs MRI-only vs Clinical-only
  - [x] confusion_matrix.png — матрица ошибок CN/MCI/AD
  - [x] gate_weights.png — gate-значения по классам (боксплот)
  - [x] roi_importance.png — важность МРТ-признаков
  - [x] biomarker_trajectory.png — динамика биомаркеров CN→MCI→AD
  - [x] fusion_umap.png — UMAP эмбеддингов

### Этап 4: Приложение и отчёт — ВЫПОЛНЕНО
- [x] `cli.py` — команды: setup-kaggle, classify-kaggle, report, classify-oasis, download, analyze
- [x] `build_presentation.py` — PowerPoint-презентация (12 слайдов)
- [x] Проверена работа: `python cli.py setup-kaggle` → `python cli.py classify-kaggle`

### Этап 5: Исследовательский анализ scRNA-seq — ВЫПОЛНЕНО
- [x] `data_loader.py`, `preprocessor.py` — загрузка и предобработка GSE138852
- [x] `gene_analyzer.py` — DEG: Mann-Whitney U + BH FDR-коррекция
- [x] `visualizer.py` — volcano, heatmap, UMAP, barplot
- [x] `ensemble_classifier.py` — три головы: Expression / Composition / Gene2Vec
- [x] `enrichment_analysis.py` — Enrichr API (GO, KEGG)

### Этап 6: Документация — ВЫПОЛНЕНО
- [x] `docs/functional_scheme.md` — полная схема пайплайна
- [x] `docs/literature_review.md` — 10 разделов, все источники
- [x] `docs/plan.md` — этот файл

### Этап 7: Подготовка к защите — В ПРОЦЕССЕ (12 дней)
- [ ] Текст доклада (speaker notes) — обновить под новую схему
- [ ] Презентация — улучшить слайды, добавить функциональную схему
- [ ] PDF-версии документов (чёрно-белые, жирные заголовки)

---

## Конфигурация (config.py)

```
MULTIMODAL_EMBED_DIM = 128     размер эмбеддингов (МРТ и клиника → 128 чисел)
MULTIMODAL_EPOCHS    = 50      эпохи обучения
MULTIMODAL_BATCH     = 32      размер батча
MULTIMODAL_TEST_SIZE = 0.2     20% пациентов — тест (donor-level)
MULTIMODAL_LR        = 1e-3    скорость обучения
weight_decay         = 1e-4    L2-регуляризация
Dropout              = 0.3     30% нейронов отключены при обучении
```

---

## Метрики качества

| Метрика | Что означает | Цель |
|---|---|---|
| ROC-AUC (macro OvR) | Способность различать все 3 класса | > 0.85 |
| Accuracy | Доля правильных ответов | > 0.75 |
| Fusion AUC > MRI-only AUC | Доказательство пользы мультимодальности | обязательно |
| Confusion matrix | Какие стадии путает модель | MCI ≠ CN и AD |

---

## Возможные улучшения (опционально)

- Лонгитюдный анализ: предсказание перехода MCI → AD по серии визитов
- Cross-attention вместо Gated Fusion при большем объёме данных
- 3D-CNN энкодер для сырых МРТ-снимков (NIfTI) — требует полного OASIS-3
- Leave-One-Donor-Out CV для более строгой оценки
- Интеграция с настоящей медицинской PACS-системой

---

## Запуск приложения

```bash
# Реальные данные (Kaggle OASIS)
python cli.py setup-kaggle      # скопировать файлы из Downloads
python cli.py classify-kaggle   # обучить и оценить модель
python cli.py report            # создать report.pptx

# Синтетические данные (для тестирования)
python cli.py generate-synthetic
python cli.py classify-oasis

# Исследовательский анализ (scRNA-seq)
python cli.py download          # скачать GSE138852
python cli.py analyze           # DEG + визуализации + Enrichr
```
