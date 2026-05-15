# Все настройки проекта в одном месте

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
