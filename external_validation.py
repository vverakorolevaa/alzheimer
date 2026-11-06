"""
Внешняя проверка панели на НЕЗАВИСИМОЙ когорте GSE63061 (AddNeuroMed, batch 2).

Зачем: кросс-валидация на GSE63060 оценивает модель на тех же людях, той же
лаборатории и том же чипе. Настоящая проверка обобщаемости — другие люди и
другой чип (GSE63061: Illumina HumanHT-12 v4, платформа GPL10558).

Что делается:
  1. скачиваем GSE63061 + аннотацию GPL10558 (если ещё нет);
  2. зонды → гены тем же способом, что и для GSE63060 (зонд с макс. дисперсией);
  3. берём 15 генов панели из results/panel_model.pkl;
  4. обучаем ту же логистическую регрессию на ВСЕХ данных GSE63060;
  5. применяем к GSE63061 (только CTL/MCI/AD, пограничные группы исключены);
  6. сохраняем метрики (results/external_metrics.json) и пациентов GSE63061,
     пересчитанных в шкалу GSE63060 (results/external_patients.csv), —
     приложение показывает их как «случайный реальный пациент».

Важно про шкалу: у v3 и v4 чипов разные абсолютные уровни сигнала, поэтому
каждый датасет стандартизуется отдельно (z-score внутри датасета). Для
сравнения показан и вариант «без адаптации» — он показывает, почему модель
нельзя применять к данным другой лаборатории/платформы без калибровки.

Запуск (после python cli.py download и python cli.py panel):
    python cli.py external
"""

import os
import json
import gzip
from collections import Counter

import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, confusion_matrix

import config
import data_loader as dl
from download_data import _download, _mirrors

EXT_MATRIX = config.EXT_SERIES_MATRIX_GZ
EXT_ANNOT = config.EXT_GPL_ANNOT_GZ


def _read_status(path):
    """{GSM: исходная строка статуса} — чтобы явно исключить пограничные группы."""
    ids = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("!Sample_geo_accession"):
                ids = dl._split_tsv(line)[1:]
            elif line.startswith("!Sample_characteristics_ch1") and "status:" in line:
                vals = [v.split(":", 1)[1].strip() for v in dl._split_tsv(line)[1:]]
                return dict(zip(ids, vals))
    raise RuntimeError("Не нашёл строку status в series matrix")


def load_external():
    _download(_mirrors(config.EXT_SERIES_MATRIX_URL), EXT_MATRIX)
    _download(_mirrors(config.EXT_GPL_ANNOT_URL), EXT_ANNOT)
    expr, _, _ = dl._parse_series_matrix(EXT_MATRIX)
    status = _read_status(EXT_MATRIX)
    print("Статусы в GSE63061:", dict(Counter(status.values())))
    keep = [g for g, s in status.items() if s in config.STAGES]

    p2s = dl._load_probe_to_symbol(EXT_ANNOT)
    expr = expr.apply(pd.to_numeric, errors="coerce").dropna(how="all")
    syms = pd.Series([p2s.get(p, "") for p in expr.index], index=expr.index)
    ok = syms.ne("") & (syms.str.upper() != "NAN")
    expr, syms = expr[ok], syms[ok]
    pick = (pd.DataFrame({"sym": syms.values, "var": expr.var(axis=1).values},
                         index=expr.index)
            .sort_values("var", ascending=False).groupby("sym").head(1))
    genes = expr.loc[pick.index]
    genes.index = pick["sym"].values
    X = genes.T.loc[keep]
    y = np.array([config.STAGE_CODE[status[s]] for s in keep])
    return X, y, keep


def _report(name, y, P):
    pc = roc_auc_score(y, P, multi_class="ovr", average=None)
    impaired = (y > 0).astype(int)
    m = y > 0
    print(f"\n{name}")
    print(f"  macro ROC-AUC: {roc_auc_score(y, P, multi_class='ovr'):.3f}")
    for i, s in enumerate(config.STAGES):
        print(f"    AUC {config.STAGE_RU_SHORT[s]:9s}: {pc[i]:.3f}")
    print(f"  норма vs нарушение: {roc_auc_score(impaired, 1 - P[:, 0]):.3f}")
    print(f"  MCI vs деменция:    "
          f"{roc_auc_score((y[m] == 2).astype(int), P[m, 2] / (P[m, 1] + P[m, 2])):.3f}")
    print(f"  balanced accuracy:  {balanced_accuracy_score(y, P.argmax(1)):.3f}")
    cm = confusion_matrix(y, P.argmax(1))
    print("  матрица ошибок (строки — истина CTL/MCI/AD):")
    print("   ", cm.tolist())
    return {
        "macro_auc": float(roc_auc_score(y, P, multi_class="ovr")),
        "per_class_auc": {s: float(pc[i]) for i, s in enumerate(config.STAGES)},
        "ctl_vs_impaired_auc": float(roc_auc_score(impaired, 1 - P[:, 0])),
        "mci_vs_ad_auc": float(roc_auc_score((y[m] == 2).astype(int),
                                             P[m, 2] / (P[m, 1] + P[m, 2]))),
        "bal_acc": float(balanced_accuracy_score(y, P.argmax(1))),
        "confusion_matrix": cm.tolist(),
    }


def _bootstrap(y, P, n=2000, seed=config.PANEL_RANDOM_SEED):
    rng = np.random.RandomState(seed)
    vals = []
    for _ in range(n):
        i = rng.randint(0, len(y), len(y))
        if len(np.unique(y[i])) == 3:
            vals.append(roc_auc_score(y[i], P[i], multi_class="ovr"))
    return np.percentile(vals, [2.5, 97.5])


def main():
    model = joblib.load(os.path.join(config.RESULTS_FOLDER, "panel_model.pkl"))
    panel = model["genes"]

    X_tr = pd.read_csv(config.EXPR_FILE, index_col=0)
    y_tr = (pd.read_csv(config.LABELS_FILE, index_col=0)["stage"]
            .map(config.STAGE_CODE).values)
    X_ext, y_ext, gsm = load_external()
    print("Образцы GSE63061 (CTL/MCI/AD):",
          {config.STAGES[k]: int(v) for k, v in sorted(Counter(y_ext).items())})

    missing = [g for g in panel if g not in X_ext.columns]
    if missing:
        print("Нет в GSE63061:", missing)
    genes = [g for g in panel if g in X_ext.columns]

    clf = LogisticRegression(max_iter=3000, class_weight="balanced", C=1.0,
                             random_state=config.PANEL_RANDOM_SEED)

    # A. стандартизация внутри каждого датасета (основной вариант)
    A = StandardScaler().fit_transform(X_tr[genes].values)
    B = StandardScaler().fit_transform(X_ext[genes].values)
    P = clf.fit(A, y_tr).predict_proba(B)
    res = _report("A. z-score внутри каждого датасета (основной результат)", y_ext, P)
    lo, hi = _bootstrap(y_ext, P)
    res["macro_auc_ci"] = [float(lo), float(hi)]
    print(f"  95% ДИ macro ROC-AUC (бутстрэп): {lo:.3f}–{hi:.3f}")

    # B. без адаптации: масштаб обучающего датасета применён к новому чипу
    sc = StandardScaler().fit(X_tr[genes].values)
    P2 = clf.fit(sc.transform(X_tr[genes].values), y_tr).predict_proba(
        sc.transform(X_ext[genes].values))
    res_raw = _report("B. без адаптации шкалы (для сравнения: так делать нельзя)",
                      y_ext, P2)

    # средние уровни генов по группам — проверка направления эффекта
    means = pd.DataFrame({s: X_ext.loc[y_ext == config.STAGE_CODE[s], genes].mean()
                          for s in config.STAGES}).round(2)
    print("\nСредние уровни генов панели в GSE63061:")
    print(means.to_string())
    os.makedirs(config.RESULTS_FOLDER, exist_ok=True)
    means.to_csv(os.path.join(config.RESULTS_FOLDER, "external_GSE63061_means.csv"))

    # метрики — для README и приложения
    summary = {
        "dataset": config.EXT_ACCESSION, "platform": config.EXT_PLATFORM,
        "n_per_class": {s: int((y_ext == config.STAGE_CODE[s]).sum())
                        for s in config.STAGES},
        "per_dataset_zscore": res, "no_rescaling": res_raw,
    }
    with open(os.path.join(config.RESULTS_FOLDER, "external_metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # пациенты GSE63061 в шкале GSE63060: z внутри GSE63061 → среднее/σ GSE63060.
    # Модель приложения (обучена на всём GSE63060) даёт на них ровно вариант A.
    mu, sd = X_tr[genes].mean(), X_tr[genes].std(ddof=0)
    z = (X_ext[genes] - X_ext[genes].mean()) / X_ext[genes].std(ddof=0)
    calibrated = (z * sd + mu).round(3)
    calibrated.insert(0, "true_stage", [config.STAGES[k] for k in y_ext])
    calibrated.insert(0, "sample", gsm)
    calibrated.to_csv(os.path.join(config.RESULTS_FOLDER, "external_patients.csv"),
                      index=False)
    print(f"\nСохранено: results/external_metrics.json, results/external_patients.csv "
          f"({len(calibrated)} пациентов в шкале {config.GEO_ACCESSION})")


if __name__ == "__main__":
    main()
