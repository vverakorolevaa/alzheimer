"""
Мини-панель генов-биомаркеров для ранней диагностики болезни Альцгеймера.

НОВИЗНА проекта
---------------
Из ~14 000 генов транскриптома мы отбираем МИНИМАЛЬНУЮ панель из нескольких
генов (config.PANEL_SIZE), которая отличает больных AD от здоровых. Большой
транскриптом измеряется только дорогим scRNA-seq; маленькую же панель реально
поставить на дешёвую клиническую платформу (qPCR / NanoString). Это путь к
ранней, доступной диагностике — поймать болезнь, пока её ещё можно лечить.

ЧЕСТНОСТЬ ВАЛИДАЦИИ
------------------
Данные GSE138852 — это 6 батчей, по 2 донора в каждом: 3 батча AD и 3 контроля.
Клетки одного пациента сильно похожи между собой. Если разбивать train/test
по отдельным клеткам (как в наивном подходе), модель выучит «личность» донора,
а не биологию болезни — и AUC окажется завышен. Поэтому мы валидируем НА УРОВНЕ
ДОНОРА: на каждом фолде целые батчи (оба донора) уходят в тест и моделью не
виданы. Это честная оценка того, как панель сработает на НОВОМ пациенте.

Запуск: python cli.py panel
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.feature_selection import f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

from config import (
    CONDITION_COL, DISEASE_LABEL, CONTROL_LABEL,
    CELL_TYPE_COL, RESULTS_FOLDER,
    PANEL_SIZE, PANEL_RANDOM_SEED,
)

# Низкокачественные «типы клеток» — артефакты, исключаем из анализа
DROP_CELL_TYPES = {"doublet", "unID"}

# Гены, у которых связь с болезнью Альцгеймера известна по литературе —
# нужны только для биологической интерпретации найденной панели.
KNOWN_AD_GENES = {
    # классические гены риска / патологии AD
    "APOE", "APP", "PSEN1", "PSEN2", "MAPT", "CLU", "BIN1", "PICALM",
    "CR1", "ABCA7", "TREM2", "CD33", "SORL1", "INPP5D", "MEF2C",
    "PLCG2", "SPP1", "GFAP", "VGF", "RBFOX1", "CST3", "B2M", "HSP90AA1",
    # гены, надёжно ассоциированные с AD в транскриптомных работах
    "LINGO1",   # негативный регулятор миелинизации, терапевтическая мишень AD
    "NEAT1",    # lncRNA, стабильно повышена при AD
    "RORA",     # циркадный фактор, ассоциирован с AD
    "NRXN1",    # нейрексин, синаптическая дисфункция при AD
    "HSPA1A",   # белок теплового шока, протеостаз при нейродегенерации
}

# Размеры панели для оценки «качество vs число генов»
PANEL_SIZE_SWEEP = [1, 2, 3, 5, 8, 12, 20, 50]

# Предфильтр: оставляем топ-N самых вариабельных генов (без учёта меток —
# утечки нет), чтобы ускорить отбор. Снижает 14k генов до управляемого числа.
PREFILTER_HVG = 2000


def _donor_batch(barcode):
    """Из баркода 'AAACCTGG..._AD5_AD6' извлекает батч-донора 'AD5_AD6'."""
    parts = barcode.split("_", 1)
    return parts[1] if len(parts) == 2 else parts[0]


def _make_donor_folds(groups):
    """
    Строит сбалансированные фолды: в тесте 1 AD-батч + 1 контроль-батч,
    в трейне — остальные. Возвращает список (train_mask, test_mask, test_batches).
    """
    batches    = sorted(set(groups))
    ad_batches = [b for b in batches if b.upper().startswith("AD")]
    ct_batches = [b for b in batches if not b.upper().startswith("AD")]

    folds = []
    for ad_b, ct_b in zip(ad_batches, ct_batches):
        test_batches = {ad_b, ct_b}
        test_mask  = np.isin(groups, list(test_batches))
        train_mask = ~test_mask
        folds.append((train_mask, test_mask, test_batches))
    return folds


def _rank_genes(X_tr, y_tr, k):
    """Топ-k генов по ANOVA F-критерию, посчитанному ТОЛЬКО на трейне."""
    F, _ = f_classif(X_tr, y_tr)
    F = np.nan_to_num(F, nan=0.0)
    return np.argsort(F)[::-1][:k]


def _cv_auc_for_k(X, y, groups, folds, k):
    """Средний донор-уровневый AUC для панели размера k."""
    aucs = []
    for train_mask, test_mask, _ in folds:
        X_tr, X_te = X[train_mask], X[test_mask]
        y_tr, y_te = y[train_mask], y[test_mask]

        top_idx = _rank_genes(X_tr, y_tr, k)

        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X_tr[:, top_idx])
        X_te_s = scaler.transform(X_te[:, top_idx])

        clf = LogisticRegression(max_iter=1000, class_weight="balanced",
                                 random_state=PANEL_RANDOM_SEED)
        clf.fit(X_tr_s, y_tr)
        proba = clf.predict_proba(X_te_s)[:, 1]
        aucs.append(roc_auc_score(y_te, proba))
    return float(np.mean(aucs)), float(np.std(aucs)), aucs


def run_panel():
    from data_loader  import DataLoader
    from preprocessor import Preprocessor

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    print("=" * 60)
    print("  Отбор мини-панели генов-биомаркеров AD (честная валидация)")
    print("=" * 60)

    # ── Данные ─────────────────────────────────────────────────────────
    adata = DataLoader().load()
    adata = Preprocessor().preprocess(adata)

    keep = ~adata.obs[CELL_TYPE_COL].isin(DROP_CELL_TYPES).values
    adata = adata[keep].copy()
    print(f"\nПосле удаления артефактов {DROP_CELL_TYPES}: "
          f"{adata.n_obs} клеток, {adata.n_vars} генов")

    X_full    = np.asarray(adata.X, dtype=np.float32)
    gene_names = np.array(adata.var_names)
    y = (adata.obs[CONDITION_COL].values == DISEASE_LABEL).astype(int)
    groups = np.array([_donor_batch(bc) for bc in adata.obs_names])

    print(f"Классы: AD={int(y.sum())}  контроль={int((1 - y).sum())}")
    print(f"Батчи-доноры: {sorted(set(groups))}")

    # ── Предфильтр по вариабельности (без меток — утечки нет) ───────────
    var = X_full.var(axis=0)
    hvg_idx = np.argsort(var)[::-1][:PREFILTER_HVG]
    X = X_full[:, hvg_idx]
    hvg_names = gene_names[hvg_idx]
    print(f"Предфильтр HVG: {X.shape[1]} самых вариабельных генов")

    folds = _make_donor_folds(groups)
    print(f"\nДонор-уровневых фолдов: {len(folds)} "
          f"(в каждом тесте — целые батчи, моделью не виданы)")

    # ── Свип размера панели: качество vs число генов ───────────────────
    print("\n[1/3] Зависимость AUC от размера панели (донор-уровневый CV):")
    sweep = []
    for k in PANEL_SIZE_SWEEP:
        if k > X.shape[1]:
            continue
        mean_auc, std_auc, _ = _cv_auc_for_k(X, y, groups, folds, k)
        sweep.append({"genes": k, "auc_mean": mean_auc, "auc_std": std_auc})
        print(f"  {k:3d} ген(ов): AUC = {mean_auc:.3f} ± {std_auc:.3f}")
    sweep_df = pd.DataFrame(sweep)

    # Базлайн: полная HVG-модель (все 2000 генов) для сравнения
    base_mean, base_std, _ = _cv_auc_for_k(X, y, groups, folds, X.shape[1])
    print(f"  Все {X.shape[1]} HVG (базлайн): AUC = {base_mean:.3f} ± {base_std:.3f}")

    # ── Итоговая панель PANEL_SIZE + её честный AUC ─────────────────────
    print(f"\n[2/3] Итоговая панель из {PANEL_SIZE} генов:")
    panel_mean, panel_std, panel_aucs = _cv_auc_for_k(X, y, groups, folds, PANEL_SIZE)

    # Стабильность: как часто ген попадает в топ across фолдов
    selection_counts = np.zeros(X.shape[1], dtype=int)
    for train_mask, _, _ in folds:
        top_idx = _rank_genes(X[train_mask], y[train_mask], PANEL_SIZE)
        selection_counts[top_idx] += 1

    # Финальный отбор — на ВСЕХ данных (для перечисления генов панели)
    final_idx = _rank_genes(X, y, PANEL_SIZE)
    F_all, _  = f_classif(X, y)
    F_all = np.nan_to_num(F_all, nan=0.0)

    panel = []
    for rank, gi in enumerate(final_idx, 1):
        gname = hvg_names[gi]
        # направление: выше у AD (+) или ниже (-)
        mean_ad = X[y == 1, gi].mean()
        mean_ct = X[y == 0, gi].mean()
        panel.append({
            "rank": rank,
            "gene": gname,
            "F_score": round(float(F_all[gi]), 1),
            "direction": "up_in_AD" if mean_ad > mean_ct else "down_in_AD",
            "log2FC": round(float(np.log2(mean_ad + 1) - np.log2(mean_ct + 1)), 3),
            "folds_selected": int(selection_counts[gi]),
            "known_AD_gene": gname in KNOWN_AD_GENES,
        })
    panel_df = pd.DataFrame(panel)

    print(f"\n  Честный AUC панели (донор-уровень): {panel_mean:.3f} ± {panel_std:.3f}")
    print(f"  По фолдам: {[round(a, 3) for a in panel_aucs]}")
    print("\n  Состав панели:")
    print(panel_df.to_string(index=False))

    n_known = panel_df["known_AD_gene"].sum()
    print(f"\n  Из них известных AD-генов по литературе: {n_known}/{PANEL_SIZE}")

    # ── Сохранение ─────────────────────────────────────────────────────
    print("\n[3/3] Сохранение результатов")
    panel_csv = os.path.join(RESULTS_FOLDER, "biomarker_panel.csv")
    panel_df.to_csv(panel_csv, index=False)
    sweep_df.to_csv(os.path.join(RESULTS_FOLDER, "panel_size_sweep.csv"), index=False)
    _plot(sweep_df, base_mean, panel_df, panel_mean, panel_std)

    print(f"  Панель:  {panel_csv}")
    print("=" * 60)
    print(f"  ИТОГ: панель из {PANEL_SIZE} генов даёт AUC {panel_mean:.3f} "
          f"против {base_mean:.3f} у полной модели ({X.shape[1]} генов)")
    print("=" * 60)

    return {"panel": panel_df, "panel_auc": panel_mean, "panel_auc_std": panel_std,
            "baseline_auc": base_mean, "sweep": sweep_df}


def _plot(sweep_df, base_auc, panel_df, panel_mean, panel_std):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # (1) AUC vs размер панели
    ax = axes[0]
    ax.errorbar(sweep_df["genes"], sweep_df["auc_mean"],
                yerr=sweep_df["auc_std"], marker="o", color="#8E44AD",
                capsize=4, lw=2, label="Мини-панель")
    ax.axhline(base_auc, color="#27AE60", ls="--", lw=1.5,
               label=f"Полная модель ({base_auc:.3f})")
    ax.axvline(PANEL_SIZE, color="#E74C3C", ls=":", lw=1.5,
               label=f"Выбрано: {PANEL_SIZE} генов")
    ax.set_xscale("log")
    ax.set_xlabel("Число генов в панели")
    ax.set_ylabel("ROC-AUC (донор-уровневый CV)")
    ax.set_title("Качество диагностики vs размер панели", fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # (2) Состав панели: F-score, цвет по направлению
    ax = axes[1]
    colors = ["#E74C3C" if d == "up_in_AD" else "#3498DB"
              for d in panel_df["direction"]]
    y_pos = np.arange(len(panel_df))[::-1]
    ax.barh(y_pos, panel_df["F_score"], color=colors, alpha=0.85)
    labels = [g + (" *" if k else "")
              for g, k in zip(panel_df["gene"], panel_df["known_AD_gene"])]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("F-критерий (сила различия AD vs контроль)")
    ax.set_title(f"Панель из {PANEL_SIZE} генов  (AUC {panel_mean:.3f}±{panel_std:.3f})\n"
                 "красный — выше у AD, синий — ниже;  * — известный AD-ген",
                 fontweight="bold", fontsize=10)
    ax.grid(alpha=0.3, axis="x")

    path = os.path.join(RESULTS_FOLDER, "biomarker_panel.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  График:  {path}")


def main():
    run_panel()


if __name__ == "__main__":
    main()
