# Все настройки проекта в одном месте

# ── GSE138852 (scRNA-seq, исследовательский анализ) ───────────────────
DATA_FILE = "data/GSE138852_counts.csv"
META_FILE = "data/GSE138852_metadata.csv"

CONDITION_COL  = "oupSample.batchCond"
CELL_TYPE_COL  = "oupSample.cellType"
DISEASE_LABEL  = "AD"
CONTROL_LABEL  = "ct"

PVALUE_THRESHOLD = 0.05
LOG2FC_THRESHOLD = 1.0
TOP_GENES_COUNT  = 40

CLASSIFIER_TEST_SIZE = 0.2
CLASSIFIER_TOP_GENES = 500
CLASSIFIER_EPOCHS    = 30

RESULTS_FOLDER = "results"

# Gene2Vec (Du et al., 2019) — предобученные эмбеддинги генов
GENE2VEC_URL = (
    "https://github.com/jingcheng-du/Gene2Vec/raw/master/"
    "pre_trained_emb/gene2vec_dim_200_iter_9.txt"
)
GENE2VEC_DIM  = 200
GENE2VEC_TOP  = 100

# ── OASIS-3 (МРТ + клиника, диагностическое приложение) ──────────────
OASIS_MRI_FILE      = "data/oasis/mri_features.csv"
OASIS_CLINICAL_FILE = "data/oasis/clinical.csv"

# FreeSurfer ROI-признаки (объёмы в мм³, толщина коры в мм)
MRI_KEY_ROIS = [
    "lh_hippocampus", "rh_hippocampus",
    "lh_amygdala", "rh_amygdala",
    "lh_entorhinal_thickness", "rh_entorhinal_thickness",
    "lh_parahippocampal_thickness", "rh_parahippocampal_thickness",
    "lh_fusiform_thickness", "rh_fusiform_thickness",
    "lh_inferior_temporal_thickness", "rh_inferior_temporal_thickness",
    "lh_middle_temporal_thickness", "rh_middle_temporal_thickness",
    "lh_precuneus_thickness", "rh_precuneus_thickness",
    "left_lateral_ventricle", "right_lateral_ventricle",
    "third_ventricle", "total_brain_vol",
]

CLINICAL_FEATURES = ["age", "sex", "apoe4", "education_years", "mmse", "cdr"]

DX_LABELS = {0: "CN", 1: "MCI", 2: "AD"}
DX_COLORS = {0: "#2ECC71", 1: "#F39C12", 2: "#E74C3C"}

MULTIMODAL_EMBED_DIM = 128
MULTIMODAL_EPOCHS    = 50
MULTIMODAL_TEST_SIZE = 0.2
MULTIMODAL_BATCH     = 32
