"""
Gene2Vec: предобученные 200-мерные эмбеддинги генов.
Источник: Du et al. "Gene2vec: distributed representation of genes based on
co-expression." BMC Genomics, 2019.

Эмбеддинги кэшируются в ~/.cache/altchgamer/gene2vec.txt.
"""

import os
import numpy as np
import requests
from pathlib import Path
from config import GENE2VEC_URL, GENE2VEC_DIM, GENE2VEC_TOP, CONDITION_COL

CACHE_DIR = Path.home() / ".cache" / "altchgamer"


def load_gene2vec(verbose=True):
    """Загружает предобученные Gene2Vec эмбеддинги (скачивает при первом запуске)."""
    cache_path = CACHE_DIR / "gene2vec.txt"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not cache_path.exists():
        if verbose:
            print("  Скачиваю Gene2Vec (Du et al., 2019) — первый запуск, ~50 МБ...")
        try:
            resp = requests.get(GENE2VEC_URL, stream=True, timeout=180)
            resp.raise_for_status()
            with open(cache_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
            if verbose:
                print(f"  Кэшировано: {cache_path}")
        except Exception as e:
            if verbose:
                print(f"  Не удалось скачать Gene2Vec: {e}")
                print("  Голова 3 будет работать со случайной инициализацией.")
            return {}

    embeddings = {}
    try:
        with open(cache_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == GENE2VEC_DIM + 1:
                    embeddings[parts[0]] = np.array(parts[1:], dtype=np.float32)
    except Exception as e:
        if verbose:
            print(f"  Ошибка чтения Gene2Vec: {e}")
        return {}

    if verbose:
        print(f"  Gene2Vec загружен: {len(embeddings):,} генов × {GENE2VEC_DIM} измерений")
    return embeddings


def compute_cell_embeddings(adata, deg_results, gene2vec):
    """
    Строит матрицу эмбеддингов клеток через Gene2Vec.

    Для каждой клетки: взвешенная сумма эмбеддингов DEG-генов,
    где вес = нормированный уровень экспрессии гена в данной клетке.
    Результат: матрица (n_cells - GENE2VEC_DIM).

    Если Gene2Vec недоступен — возвращает нулевую матрицу (голова будет
    обучаться со случайными весами, но это не приводит к ошибке).
    """
    all_degs = []
    for df in deg_results.values():
        sig = df[df["significant"]]["gene"].tolist()
        all_degs.extend(sig[:GENE2VEC_TOP])
    all_degs = list(dict.fromkeys(all_degs))  # уникальные, сохраняя порядок

    genes_ok = [g for g in all_degs if g in gene2vec and g in adata.var_names]

    if not genes_ok:
        print("  Gene2Vec: нет пересечения с DEG-генами, используется нулевая матрица.")
        return np.zeros((adata.n_obs, GENE2VEC_DIM), dtype=np.float32)

    gene_idx   = [list(adata.var_names).index(g) for g in genes_ok]
    X_expr     = np.asarray(adata.X[:, gene_idx], dtype=np.float32)   # (cells × genes)
    emb_matrix = np.array([gene2vec[g] for g in genes_ok], dtype=np.float32)  # (genes × 200)

    col_max = X_expr.max(axis=0, keepdims=True) + 1e-8
    X_norm  = X_expr / col_max

    cell_embs = X_norm @ emb_matrix  # (cells × 200)
    print(f"  Gene2Vec: эмбеддинги для {len(genes_ok)} генов → матрица {cell_embs.shape}")
    return cell_embs


def compute_composition_features(adata):
    """
    Вторая модальность: клеточный состав образца.

    Для каждой клетки добавляем вектор — доли клеточных типов
    в том образце, из которого эта клетка.
    Это контекстуальная информация об иммунном/клеточном окружении.

    Возвращает: матрица (n_cells - n_cell_types), список cell_type_names.
    """
    from config import CELL_TYPE_COL

    cell_types = sorted(adata.obs[CELL_TYPE_COL].unique())
    n_ct = len(cell_types)
    ct_index = {ct: i for i, ct in enumerate(cell_types)}

    composition = np.zeros((adata.n_obs, n_ct), dtype=np.float32)

    donor_candidates = [c for c in adata.obs.columns
                        if any(kw in c.lower() for kw in ("donor", "sample", "subject", "patient", "batch"))]

    if donor_candidates:
        sample_col = donor_candidates[0]
        obs_arr = adata.obs[CELL_TYPE_COL].values
        sample_arr = adata.obs[sample_col].values
        idx_arr = np.arange(adata.n_obs)

        for sample in np.unique(sample_arr):
            mask = sample_arr == sample
            sample_cts = obs_arr[mask]
            total = mask.sum()
            for ct in cell_types:
                frac = (sample_cts == ct).sum() / total
                composition[mask, ct_index[ct]] = frac
        print(f"  Состав: {len(np.unique(sample_arr))} образцов, {n_ct} типов клеток")
    else:
        obs_cts = adata.obs[CELL_TYPE_COL].values
        for ct in cell_types:
            composition[:, ct_index[ct]] = (obs_cts == ct).mean()
        print(f"  Состав (глобальный fallback): {n_ct} типов клеток")

    return composition, cell_types
