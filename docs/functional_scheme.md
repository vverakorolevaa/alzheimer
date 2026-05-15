# Функциональная схема приложения Altchgamer

## Архитектура

```
python cli.py <команда>
        |
        +-- generate-synthetic  → generate_synthetic_oasis.py
        |                           → data/oasis/mri_features.csv
        |                           → data/oasis/clinical.csv
        |
        +-- classify-oasis      → [1] OASISLoader
        |                           [2] MultimodalClassifier (Gated Fusion)
        |                           [3] MultimodalVisualizer (7 графиков)
        |
        +-- report              → BuildPresentation → results/report.pptx
        |
        +-- download            → GEO API → data/  (scRNA-seq)
        +-- analyze             → DEG-анализ GSE138852 (исследовательский)
```

## Основной пайплайн: диагностика AD

```
Данные OASIS-3
  mri_features.csv          clinical.csv
  (FreeSurfer ROI, 20 признаков)  (возраст, MMSE, CDR, APOE4, диагноз)
        │                               │
        ▼                               ▼
  OASISLoader.load()      ←──── merge по subject_id + session_id
        │
        ▼
  get_feature_matrices()
  X_mri (n×20)   X_clin (n×6)   y (0/1/2)   groups (subject_id)
        │                │
        ▼                ▼
  GroupShuffleSplit (donor-level split — один пациент не попадает в оба сплита)
        │
        ├── Train ────────────────────────────────────────────────┐
        │                                                         │
        │   RobustScaler(X_mri)     StandardScaler(X_clin)        │
        │         │                        │                      │
        │   MRIEncoder                ClinicalEncoder             │
        │   Lin→BN→ReLU→Drop×2        Lin→ReLU→Drop              │
        │   20→256→128→128             6→64→128                   │
        │         │                        │                      │
        │         └──────── GatedFusion ───┘                      │
        │             gate = σ(W·[e_mri; e_clin])                 │
        │             fused = gate·e_mri + (1−gate)·e_clin        │
        │                        │                                │
        │                 FC 128→64→3                             │
        │                        │                                │
        │              CN / MCI / AD                              │
        │                                                         │
        └── Test ─────────────────────────────────────────────────┘
              Accuracy, ROC-AUC (macro OvR),
              Confusion Matrix, Classification Report
```

## Визуализации (7 графиков)

```
results/
  training_loss.png       — кривая обучения по эпохам
  multihead_roc.png       — ROC: Fusion vs MRI-only vs Clinical-only (3 класса)
  confusion_matrix.png    — матрица ошибок CN/MCI/AD (нормированная)
  gate_weights.png        — gate-значения по классам (боксплот)
  roi_importance.png      — важность МРТ-регионов (барплот)
  biomarker_trajectory.png— биомаркеры CN→MCI→AD (bar + trend)
  fusion_umap.png         — UMAP/t-SNE фьюженных эмбеддингов
  report.pptx             — PowerPoint-презентация (12 слайдов)
```

## Структура нейросети

```
MultimodalADNet
├── MRIEncoder
│   └── Linear(20→256) → BN → ReLU → Dropout(0.3)
│       → Linear(256→128) → BN → ReLU → Dropout(0.3)
│       → Linear(128→128)
├── ClinicalEncoder
│   └── Linear(6→64) → ReLU → Dropout(0.3) → Linear(64→128)
├── GatedFusion
│   └── gate_fc: Linear(256→128) → Sigmoid
│       fused = gate * e_mri + (1−gate) * e_clin
└── Classifier
    └── Linear(128→64) → ReLU → Dropout(0.3) → Linear(64→3)
```

## Исследовательский пайплайн (GSE138852)

```
data/GSE138852_counts.csv + metadata.csv
        │
        ▼
  DataLoader → AnnData (клетки × гены)
        │
  Preprocessor (фильтрация, нормализация, log1p)
        │
  GeneAnalyzer (Mann-Whitney U + BH FDR по типам клеток)
        │
  Visualizer (volcano, heatmap, UMAP, barplot)
        │
  EnsembleClassifier (3 головы: Expression, Composition, Gene2Vec)
        │
  EnrichmentAnalyzer (Enrichr API: GO, KEGG)
```
