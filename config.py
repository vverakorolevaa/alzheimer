# Все настройки проекта в одном месте

# ── GSE63060 (AddNeuroMed, КРОВЬ, микрочип) — ОСНОВНОЙ датасет ──────────
# Экспрессия генов в периферической крови, три класса (стадии):
#   CTL — норма, MCI — промежуточная (умеренные когнитивные нарушения),
#   AD  — деменция при болезни Альцгеймера.
# Кровь берётся у ЖИВОГО пациента → инструмент применим для скрининга,
# в отличие от биопсии мозга. Это снимает главный недостаток старой модели.
GEO_ACCESSION = "GSE63060"
PLATFORM      = "GPL6947"          # Illumina HumanHT-12 V3.0 expression beadchip

DATA_DIR         = "data"
SERIES_MATRIX_GZ = "data/GSE63060_series_matrix.txt.gz"
GPL_ANNOT_GZ     = "data/GPL6947.annot.gz"

# Готовые таблицы после парсинга (создаются загрузчиком):
EXPR_FILE   = "data/GSE63060_expression.csv"   # образцы × гены (после probe→gene)
LABELS_FILE = "data/GSE63060_labels.csv"       # образец, стадия

# URL для скачивания (FTP NCBI поверх HTTPS); запасные варианты — в download_data.py
SERIES_MATRIX_URL = (
    "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE63nnn/GSE63060/matrix/"
    "GSE63060_series_matrix.txt.gz"
)
GPL_ANNOT_URL = (
    "https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL6nnn/GPL6947/annot/"
    "GPL6947.annot.gz"
)

# ── Классы (стадии): порядковая шкала норма < MCI < деменция ────────────
STAGES         = ["CTL", "MCI", "AD"]
STAGE_CODE     = {"CTL": 0, "MCI": 1, "AD": 2}
STAGE_RU       = {"CTL": "Норма", "MCI": "MCI (промежуточная)", "AD": "Деменция (AD)"}
STAGE_RU_SHORT = {"CTL": "Норма", "MCI": "MCI", "AD": "Деменция"}
STAGE_COLOR    = {"CTL": "#2ECC71", "MCI": "#F39C12", "AD": "#E74C3C"}

# ── Отбор мини-панели и честная валидация ──────────────────────────────
RESULTS_FOLDER    = "results"
PANEL_SIZE        = 15      # генов в итоговой диагностической панели
PANEL_SIZE_SWEEP  = [5, 8, 10, 12, 15, 20, 30, 50]
PREFILTER_HVG     = 3000    # предфильтр по вариабельности (без меток — без утечки)
CV_FOLDS          = 5       # фолдов в стратифицированной кросс-валидации
CV_REPEATS        = 5       # повторов CV для доверительных интервалов (95% ДИ)
PANEL_RANDOM_SEED = 42

# ── Наследие: GSE138852 (scRNA-seq, мозг) — архив в legacy/ ────────────
# Оставлено для совместимости со старыми (заархивированными) скриптами.
DATA_FILE = "data/GSE138852_counts.csv"
META_FILE = "data/GSE138852_metadata.csv"
CONDITION_COL = "oupSample.batchCond"
CELL_TYPE_COL = "oupSample.cellType"
DISEASE_LABEL = "AD"
CONTROL_LABEL = "ct"
