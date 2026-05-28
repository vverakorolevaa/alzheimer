# Мультимодальная ранняя диагностика болезни Альцгеймера

Курсовой проект по биоинформатике. ML-система для классификации стадий болезни Альцгеймера по МРТ-данным и клиническим тестам.

## Проблема и цель

Болезнь Альцгеймера поражает **55+ миллионов человек** (ВОЗ, 2023). Патологические изменения в мозге начинаются за **10–20 лет** до первых симптомов — к моменту клинического диагноза необратимо утрачено **30–40% нейронов гиппокампа** (Jack et al., 2018).

Стадии: **CN** (норма) → **MCI** (лёгкие когнитивные нарушения) → **AD** (деменция).

MCI — «окно терапии»: 15% пациентов в год переходят в AD, и именно здесь вмешательство ещё эффективно. **Цель проекта**: автоматически выявить стадию MCI по неинвазивным данным — МРТ и когнитивным тестам.

## Почему этот подход

Существующие системы используют одну модальность — только МРТ или только клинику. Каждая из них неполна: у одних пациентов атрофия мозга заметна раньше когнитивных симптомов, у других — наоборот. Простая конкатенация признаков даёт фиксированные веса без адаптации к пациенту.

Три ключевых решения этого проекта:

| Решение | Почему важно |
|---|---|
| **Gated Fusion** | адаптивный вес МРТ vs. клиники для каждого пациента отдельно |
| **Donor-level split** | корректная валидация: все визиты одного пациента — только в train или только в test |
| **Интерпретируемость** | gate-вес показывает врачу, на что опиралась модель |

Gated Fusion ранее применялся в NLP (Arevalo et al., 2017), но в нейродиагностике AD — впервые.

## Данные

### OASIS (клинический пайплайн)

Открытый датасет с Kaggle, без ограничений доступа:

- **oasis_longitudinal.csv** — 150 пациентов, повторные визиты; метка: Group (Nondemented / Converted / Demented)
- **oasis_cross-sectional.csv** — 436 пациентов, один визит; метка: производная от CDR

После объединения и фильтрации (возраст ≥ 60): **~586 визитов**.

**МРТ-признаки** (FreeSurfer): `eTIV` — объём черепа, `nWBV` — нормированный объём мозга, `ASF` — масштабный коэффициент.  
nWBV снижается на 0.5–1%/год при MCI и 1.5–2%/год при AD (Fox et al., 1999).

**Клинические признаки**: возраст, пол, образование, SES, MMSE.  
MMSE (Folstein, 1975): когнитивный тест 0–30; ниже 26 — риск MCI.

> **Примечание**: CDR намеренно исключён из признаков — в датасете OASIS метка диагноза частично производна от CDR, поэтому его включение создаёт утечку данных. После исключения CDR Clinical-only AUC снизился с 0.997 до 0.920 — как и ожидалось.

### GSE138852 (молекулярный пайплайн)

Mathys H. et al. (2019). *Nature*, 570, 332–337.  
80 пациентов (48 AD + 32 контроля), 80 000+ клеток мозга, энторинальная кора. Одноклеточное РНК-секвенирование.

## Архитектура

### MultimodalADNet (клинический пайплайн)

```
МРТ (eTIV, nWBV, ASF)      Клиника (возраст, пол, обр., SES, MMSE)
         │                                    │
   MRIEncoder                          ClinicalEncoder
  3→256→128→128                           6→64→128
  BN+ReLU+Drop(0.3)                    ReLU+Drop(0.3)
         │                                    │
         └──────────── GatedFusion ───────────┘
                  gate = σ(W · [e_mri ; e_clin])
                  fused = gate · e_mri + (1−gate) · e_clin
                               │
                      Classifier: 128→64→3
                               │
                    P(CN)   P(MCI)   P(AD)
                               │
                            argmax → диагноз
```

**Gate-механизм**: вычисляется отдельно для каждого пациента.  
- gate → 1: модель доверяет МРТ (выраженная атрофия)  
- gate → 0: модель доверяет клинике (снижение MMSE без явной атрофии на ранней стадии)

Для сравнения обучаются два baseline: MRI-only и Clinical-only — однородные сети с той же глубиной.

### Ансамблевый классификатор (scRNA-seq пайплайн)

Три головы с усреднением предсказаний:

- **Expression head**: топ-500 дифференциально экспрессированных генов → MLP
- **Composition head**: состав клеточных типов (8 измерений) → MLP
- **Gene2Vec head**: эмбеддинги генов 200-dim (Du et al., 2019) → MLP

## Методики

### Предотвращение переобучения

Пять мер применяются одновременно:

1. **Donor-level split** — `GroupShuffleSplit` по `subject_id`: все визиты одного пациента строго в train или строго в test. Без этого продольный датасет даёт утечку (Varoquaux, 2018, *NeuroImage*).
2. **Dropout(0.3)** — случайное отключение 30% нейронов при обучении
3. **BatchNorm** — нормализация активаций, стабилизация обучения (Ioffe & Szegedy, 2015)
4. **L2-регуляризация** — `weight_decay=1e-4` в Adam
5. **Weighted CrossEntropyLoss** — компенсация дисбаланса классов (CN > MCI > AD)

### DEG-анализ (scRNA-seq)

1. Разделение клеток по типу (нейроны, астроциты, микроглия и др.)
2. Тест Манна–Уитни (U-test) для каждого гена: AD vs. контроль
3. Поправка Бенджамини–Хохберга (FDR < 0.05)
4. Порог значимости: |log2FC| > 1.0
5. Обогащение путей: Enrichr API (GO_Biological_Process, KEGG)

### Метрики

- **ROC-AUC macro OvR** — основная метрика. AUC > 0.85 клинически приемлемо.
- **Accuracy** — вспомогательная (менее информативна при дисбалансе)
- **Confusion matrix** — нормированная, для анализа ошибок по классам

## Результаты

| Модель | AUC |
|---|---|
| MRI-only | 0.59–0.72 |
| Clinical-only | ~0.92 |
| **Fusion (MultimodalADNet)** | **0.98–0.999** |

- Fusion AUC стабильно превышает оба baseline — мультимодальность подтверждена
- Gate-веса биологически валидны: выше при AD (выраженная атрофия), ниже при MCI
- nWBV — самый важный МРТ-биомаркер; согласуется с Fox et al. (1999)

> AUC на синтетических данных близок к 1.0 — синтетические распределения чёткие. На реальных Kaggle-данных без CDR ожидаемый AUC 0.82–0.90 (уровень литературы).

## Визуализации (папка `results/`)

| Файл | Что показывает |
|---|---|
| `training_loss.png` | Кривая обучения по эпохам |
| `multihead_roc.png` | ROC-кривые: Fusion vs MRI-only vs Clinical-only |
| `confusion_matrix.png` | Нормированная матрица ошибок CN/MCI/AD |
| `gate_weights.png` | Боксплот gate-весов по диагнозам |
| `roi_importance.png` | Важность МРТ-признаков (|W|·std) |
| `biomarker_trajectory.png` | Динамика nWBV/MMSE по стадиям CN→MCI→AD |
| `fusion_umap.png` | UMAP 256-мерных эмбеддингов — кластеры CN/MCI/AD |

## Структура проекта

```
alzheimer/
├── cli.py                      — точка входа; 7 команд
├── config.py                   — все гиперпараметры и пути
├── app.py                      — веб-интерфейс (Streamlit)
│
├── Пайплайн OASIS (клинический)
│   ├── data_loader_kaggle.py   — загрузка OASIS-1 + OASIS-2, donor-level split
│   ├── data_loader_oasis.py    — загрузка синтетических данных
│   ├── generate_synthetic_oasis.py — синтетика для тестирования
│   ├── multimodal_classifier.py — MRIEncoder + ClinicalEncoder + GatedFusion
│   └── visualizer_multimodal.py — 7 визуализаций
│
├── Пайплайн GSE138852 (scRNA-seq)
│   ├── data_loader.py          — загрузка GSE138852
│   ├── preprocessor.py         — scanpy: нормализация, фильтрация
│   ├── gene_analyzer.py        — DEG: Mann-Whitney U + BH FDR
│   ├── ensemble_classifier.py  — 3-головый ансамбль
│   ├── gene_embeddings.py      — Gene2Vec (Du et al., 2019)
│   ├── enrichment_analysis.py  — Enrichr API
│   └── visualizer.py           — volcano, heatmap, UMAP, barplot
│
├── build_presentation.py       — PowerPoint (12 слайдов + notes)
├── requirements.txt
├── results/                    — PNG + multimodal_model.pt + scalers
└── docs/                       — документация (не в git)
```

## Установка

```bash
git clone https://github.com/vverakorolevaa/alzheimer
cd alzheimer
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск

### Реальные данные (Kaggle OASIS)

```bash
# Скачать данные: kaggle.com → "OASIS Alzheimer's Detection" → Download
python cli.py setup-kaggle --archive ~/Downloads/archive
python cli.py classify-kaggle
python cli.py report
```

### Синтетические данные (без скачивания)

```bash
python cli.py generate-synthetic
python cli.py classify-oasis
python cli.py report
```

### Веб-интерфейс

```bash
streamlit run app.py
# открывается http://localhost:8501
```

Три режима: демо одиночного пациента (слайдеры → диагноз), обучение на синтетике, обучение на Kaggle.

### Исследовательский анализ scRNA-seq

```bash
python cli.py download    # GSE138852 с NCBI GEO (~2 GB)
python cli.py analyze     # DEG + ансамблевый классификатор + Enrichr
```

## Технологический стек

| Библиотека | Применение |
|---|---|
| PyTorch | MRIEncoder, ClinicalEncoder, GatedFusion |
| scikit-learn | GroupShuffleSplit, ROC-AUC, confusion matrix |
| pandas, numpy | предобработка табличных данных OASIS |
| scanpy, anndata | scRNA-seq: нормализация, PCA, UMAP, DEG |
| GEOparse | загрузка GSE138852 с NCBI GEO |
| umap-learn | UMAP-проекция эмбеддингов |
| matplotlib, seaborn | 7 визуализаций |
| streamlit | веб-интерфейс |
| python-pptx | автогенерация PowerPoint-отчёта |

## Направления развития

- **3D-CNN на NIfTI-снимках** — вместо трёх FreeSurfer-чисел использовать полные МРТ-объёмы OASIS-3; ожидаемый прирост AUC до 0.95+
- **Лонгитюдный анализ** — предсказание перехода MCI → AD по серии визитов одного пациента (LSTM / Transformer по времени)
- **Cross-attention Fusion** — замена Gated Fusion на cross-attention при большем объёме данных
- **Leave-One-Donor-Out CV** — более строгая оценка на малых датасетах
- **Добавление APOE4** — генетический фактор риска; требует датасета с генотипированием (ADNI)

## Литература

- Jack C.R. et al. (2018). NIA-AA Research Framework. *Alzheimers Dement*, 14(4), 535–562.
- Fox N.C. et al. (1999). Progressive atrophy of the entorhinal cortex. *Brain*, 122, 2327–2337.
- Zhang D. et al. (2011). Multimodal classification of AD. *NeuroImage*, 55(3), 856–867.
- Spasov S. et al. (2019). Deep learning for MCI to AD conversion. *NeuroImage*, 189, 276–287.
- Arevalo J. et al. (2017). Gated Multimodal Units. *arXiv* 1702.01992.
- Mathys H. et al. (2019). Single-cell transcriptomic analysis of AD. *Nature*, 570, 332–337.
- Marcus D.S. et al. (2007). OASIS: Cross-sectional. *J Cogn Neurosci*, 19(9), 1498–1507.
- Marcus D.S. et al. (2010). OASIS: Longitudinal. *J Cogn Neurosci*, 22(12), 2677–2684.
- Varoquaux G. (2018). Cross-validation failure. *NeuroImage*, 180, 68–77.
