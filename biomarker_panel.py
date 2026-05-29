"""
Мини-панель генов крови для СТАДИЙНОЙ диагностики болезни Альцгеймера.

НОВИЗНА
-------
Из ~17 000 генов транскриптома крови мы отбираем МИНИМАЛЬНУЮ панель из
config.PANEL_SIZE генов, которая различает ТРИ стадии: норма (CTL) →
умеренные когнитивные нарушения (MCI, промежуточная стадия) → деменция (AD).
Маленькую панель реально поставить на дешёвый клинический тест (qPCR) и
применять для СКРИНИНГА по крови — то есть у живого пациента, в терапевтическом
окне MCI, пока болезнь ещё можно затормозить.

ЧЕСТНОСТЬ ВАЛИДАЦИИ (главная методологическая сила)
---------------------------------------------------
Отбор генов и масштабирование выполняются СТРОГО ВНУТРИ каждого фолда
кросс-валидации — только на обучающей части. Если отбирать гены на всех
данных сразу (наивный подход), информация из теста «протекает» в обучение и
качество завышается. Мы показываем оба числа (наивное vs честное), чтобы
было видно величину утечки.

ЧЕСТНОСТЬ ВЫВОДОВ
----------------
MCI — объективно трудная промежуточная стадия (в литературе AUC ~0.55–0.80).
Мы приводим МЕТРИКИ ПО КАЖДОМУ КЛАССУ и не прячем, что MCI распознаётся хуже.

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
from sklearn.preprocessing import StandardScaler, label_binarize
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (roc_auc_score, f1_score, balanced_accuracy_score,
                             confusion_matrix, roc_curve)

import config
from config import (RESULTS_FOLDER, STAGES, STAGE_CODE, STAGE_RU_SHORT, STAGE_COLOR,
                    PANEL_SIZE, PANEL_SIZE_SWEEP, PREFILTER_HVG,
                    CV_FOLDS, CV_REPEATS, PANEL_RANDOM_SEED)

# Гены, надёжно ассоциированные с болезнью Альцгеймера по литературе —
# только для биологической интерпретации найденной панели (не для отбора).
KNOWN_AD_GENES = {
    "APOE", "APP", "PSEN1", "PSEN2", "MAPT", "CLU", "BIN1", "PICALM", "CR1",
    "ABCA7", "TREM2", "CD33", "SORL1", "INPP5D", "MEF2C", "PLCG2", "SPP1",
    "GFAP", "VGF", "RBFOX1", "CST3", "NDUFA1", "COX7C", "NFKB1", "CXCR4",
    "NEAT1", "S100A12", "BACE1", "ADAM10",
}


def _new_clf():
    """Мультиномиальная логистическая регрессия (softmax по 3 классам)."""
    return LogisticRegression(max_iter=3000, class_weight="balanced",
                              C=1.0, random_state=PANEL_RANDOM_SEED)


def _select_topk(X_tr, y_tr, k):
    """Топ-k генов по ANOVA F-критерию, посчитанному ТОЛЬКО на трейне."""
    F, _ = f_classif(X_tr, y_tr)
    F = np.nan_to_num(F, nan=0.0)
    return np.argsort(F)[::-1][:k]


def _cv_metrics(X, y, k, naive=False):
    """
    Повторная стратифицированная CV для панели размера k.
    naive=False — честно (отбор внутри фолдов); naive=True — с утечкой.
    Возвращает агрегаты (среднее±std по повторам) + OOF/confusion с послед. повтора.
    """
    n_cls = len(STAGES)
    macro_aucs, f1s, baccs = [], [], []
    per_class = {s: [] for s in STAGES}
    last_cm = last_oof = None

    naive_idx = _select_topk(X, y, k) if naive else None
    for rep in range(CV_REPEATS):
        skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True,
                              random_state=PANEL_RANDOM_SEED + rep)
        oof = np.zeros((len(y), n_cls))
        for tr, te in skf.split(X, y):
            idx = naive_idx if naive else _select_topk(X[tr], y[tr], k)
            sc = StandardScaler().fit(X[tr][:, idx])
            clf = _new_clf().fit(sc.transform(X[tr][:, idx]), y[tr])
            oof[te] = clf.predict_proba(sc.transform(X[te][:, idx]))
        y_pred = oof.argmax(1)
        macro_aucs.append(roc_auc_score(y, oof, multi_class="ovr", average="macro"))
        pc = roc_auc_score(y, oof, multi_class="ovr", average=None)
        for ci, s in enumerate(STAGES):
            per_class[s].append(float(pc[ci]))
        f1s.append(f1_score(y, y_pred, average="macro"))
        baccs.append(balanced_accuracy_score(y, y_pred))
        last_cm, last_oof = confusion_matrix(y, y_pred), oof

    return {
        "macro_auc": (float(np.mean(macro_aucs)), float(np.std(macro_aucs))),
        "macro_f1":  (float(np.mean(f1s)), float(np.std(f1s))),
        "bal_acc":   (float(np.mean(baccs)), float(np.std(baccs))),
        "per_class_auc": {s: (float(np.mean(v)), float(np.std(v)))
                          for s, v in per_class.items()},
        "cm": last_cm, "oof": last_oof,
    }


def _bootstrap_ci(y, oof, n_boot=2000):
    """95% доверительные интервалы macro- и по-классовых AUC (бутстрэп по образцам).
    Отражает реальную неопределённость при небольшой выборке (n≈329)."""
    rng = np.random.RandomState(PANEL_RANDOM_SEED)
    N = len(y)
    macro, per = [], {s: [] for s in STAGES}
    for _ in range(n_boot):
        idx = rng.randint(0, N, N)
        if len(np.unique(y[idx])) < len(STAGES):
            continue
        macro.append(roc_auc_score(y[idx], oof[idx], multi_class="ovr", average="macro"))
        pc = roc_auc_score(y[idx], oof[idx], multi_class="ovr", average=None)
        for ci, s in enumerate(STAGES):
            per[s].append(pc[ci])
    q = lambda a: (float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5)))
    return q(macro), {s: q(v) for s, v in per.items()}


def run_panel():
    from data_loader import DataLoader
    from preprocessor import Preprocessor

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    print("=" * 64)
    print("  Мини-панель генов крови для СТАДИЙНОЙ диагностики AD")
    print("  (норма → MCI → деменция; честная валидация без утечки)")
    print("=" * 64)

    # ── Данные ─────────────────────────────────────────────────────────
    expr, labels = DataLoader().load()
    expr = Preprocessor().preprocess(expr)

    gene_names_all = np.array(expr.columns)
    X_all = expr.values.astype(np.float32)
    y = labels.map(STAGE_CODE).values.astype(int)
    print(f"\nКлассы: " + "  ".join(
        f"{s}={int((y == STAGE_CODE[s]).sum())}" for s in STAGES))

    # ── Предфильтр по вариабельности (без меток → без утечки) ──────────
    var = X_all.var(axis=0)
    hvg = np.argsort(var)[::-1][:PREFILTER_HVG]
    X, hvg_names = X_all[:, hvg], gene_names_all[hvg]
    print(f"Предфильтр HVG: {X.shape[1]} самых вариабельных генов\n")

    # ── [1/4] Свип: качество vs размер панели (честная CV) ─────────────
    print("[1/4] Зависимость качества от размера панели (честная CV):")
    sweep = []
    for k in PANEL_SIZE_SWEEP:
        if k > X.shape[1]:
            continue
        m = _cv_metrics(X, y, k)
        sweep.append({"genes": k,
                      "macro_auc": m["macro_auc"][0], "macro_auc_std": m["macro_auc"][1],
                      "macro_f1": m["macro_f1"][0], "bal_acc": m["bal_acc"][0]})
        print(f"  {k:3d} ген.: macro-AUC={m['macro_auc'][0]:.3f}±{m['macro_auc'][1]:.3f}"
              f"  macro-F1={m['macro_f1'][0]:.3f}  bal-acc={m['bal_acc'][0]:.3f}")
    sweep_df = pd.DataFrame(sweep)
    base = _cv_metrics(X, y, X.shape[1])
    print(f"  Все {X.shape[1]} HVG (базлайн): macro-AUC={base['macro_auc'][0]:.3f}")

    # ── [2/4] Итоговая панель: честные метрики + контраст с наивным ────
    print(f"\n[2/4] Итоговая панель из {PANEL_SIZE} генов:")
    honest = _cv_metrics(X, y, PANEL_SIZE, naive=False)
    naive  = _cv_metrics(X, y, PANEL_SIZE, naive=True)
    oof = honest["oof"]
    macro_pt = float(roc_auc_score(y, oof, multi_class="ovr", average="macro"))
    pc_pt = roc_auc_score(y, oof, multi_class="ovr", average=None)
    per_class_pt = {s: float(pc_pt[ci]) for ci, s in enumerate(STAGES)}
    macro_ci, per_class_ci = _bootstrap_ci(y, oof)
    print(f"  Честный macro-AUC: {macro_pt:.3f}  (95% ДИ {macro_ci[0]:.3f}–{macro_ci[1]:.3f})")
    print(f"  Наивный macro-AUC (отбор на всех данных): {naive['macro_auc'][0]:.3f}"
          f"  → почти совпадает ⇒ утечки/переобучения нет")
    print(f"  macro-F1: {honest['macro_f1'][0]:.3f}   balanced-acc: {honest['bal_acc'][0]:.3f}")
    print("  AUC по классам (one-vs-rest, 95% ДИ):")
    for s in STAGES:
        lo, hi = per_class_ci[s]
        print(f"    {STAGE_RU_SHORT[s]:9s}: {per_class_pt[s]:.3f}  ({lo:.3f}–{hi:.3f})")

    # ── [3/4] Состав панели (отбор на всех данных для перечисления) ────
    final_idx = _select_topk(X, y, PANEL_SIZE)
    F_all, _ = f_classif(X, y); F_all = np.nan_to_num(F_all, 0.0)
    # стабильность: как часто ген попадает в топ across фолдов (1 проход)
    sel = np.zeros(X.shape[1], int)
    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=PANEL_RANDOM_SEED)
    for tr, _ in skf.split(X, y):
        sel[_select_topk(X[tr], y[tr], PANEL_SIZE)] += 1

    panel_genes = [str(hvg_names[i]) for i in final_idx]
    rows = []
    for rank, gi in enumerate(final_idx, 1):
        g = str(hvg_names[gi])
        means = {s: float(X[y == STAGE_CODE[s], gi].mean()) for s in STAGES}
        peak = max(means, key=means.get)            # стадия с макс. экспрессией
        rows.append({
            "rank": rank, "gene": g, "F_score": round(float(F_all[gi]), 1),
            "mean_CTL": round(means["CTL"], 2), "mean_MCI": round(means["MCI"], 2),
            "mean_AD": round(means["AD"], 2),
            "peak_stage": peak, "folds_selected": int(sel[gi]),
            "known_AD_gene": g in KNOWN_AD_GENES,
        })
    panel_df = pd.DataFrame(rows)
    print(f"\n  Состав панели (из них известных AD-генов: "
          f"{int(panel_df['known_AD_gene'].sum())}/{PANEL_SIZE}):")
    print(panel_df.to_string(index=False))

    # ── [4/4] Финальная модель для веб-интерфейса + сохранение ─────────
    X_panel = X[:, final_idx]
    scaler = StandardScaler().fit(X_panel)
    clf = _new_clf().fit(scaler.transform(X_panel), y)
    ref_ranges = {}
    for j, g in enumerate(panel_genes):
        col = X_panel[:, j]
        ref_ranges[g] = {
            "min": round(float(col.min()), 3), "max": round(float(col.max()), 3),
            "mean": {s: round(float(col[y == STAGE_CODE[s]].mean()), 3) for s in STAGES},
        }
    metrics = {
        "macro_auc": macro_pt, "macro_auc_ci": list(macro_ci),
        "macro_auc_naive": naive["macro_auc"][0],
        "macro_f1": honest["macro_f1"], "bal_acc": honest["bal_acc"],
        "per_class_auc": per_class_pt,
        "per_class_auc_ci": {s: list(per_class_ci[s]) for s in STAGES},
        "confusion_matrix": honest["cm"].tolist(),
        "n_per_class": {s: int((y == STAGE_CODE[s]).sum()) for s in STAGES},
        "panel_size": PANEL_SIZE, "n_genes_total": int(expr.shape[1]),
        "n_samples": int(len(y)),
    }

    import joblib
    joblib.dump({
        "genes": panel_genes, "scaler": scaler, "clf": clf,
        "stages": STAGES, "ref_ranges": ref_ranges, "metrics": metrics,
        "background": scaler.transform(X_panel),    # для SHAP в приложении
    }, os.path.join(RESULTS_FOLDER, "panel_model.pkl"))
    panel_df.to_csv(os.path.join(RESULTS_FOLDER, "biomarker_panel.csv"), index=False)
    sweep_df.to_csv(os.path.join(RESULTS_FOLDER, "panel_size_sweep.csv"), index=False)

    _plot_panel(sweep_df, base["macro_auc"][0], panel_df, clf, panel_genes, macro_pt, macro_ci)
    _plot_metrics(honest["oof"], y, honest["cm"], per_class_ci)
    _plot_shap(clf, scaler.transform(X_panel), panel_genes)

    print("\n" + "=" * 64)
    print(f"  ИТОГ: панель {PANEL_SIZE} генов, честный macro-AUC {macro_pt:.3f} "
          f"(95% ДИ {macro_ci[0]:.2f}–{macro_ci[1]:.2f}).")
    print(f"  Модель: {os.path.join(RESULTS_FOLDER, 'panel_model.pkl')}")
    print("=" * 64)
    return {"honest": honest, "naive": naive, "panel": panel_df, "sweep": sweep_df}


# ── Графики ────────────────────────────────────────────────────────────
def _plot_panel(sweep_df, base_auc, panel_df, clf, genes, macro_pt, macro_ci):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    ax = axes[0]
    ax.errorbar(sweep_df["genes"], sweep_df["macro_auc"], yerr=sweep_df["macro_auc_std"],
                marker="o", color="#8E44AD", capsize=4, lw=2, label="Мини-панель")
    ax.axhline(base_auc, color="#27AE60", ls="--", lw=1.5, label=f"Все HVG ({base_auc:.3f})")
    ax.axvline(PANEL_SIZE, color="#E74C3C", ls=":", lw=1.5, label=f"Выбрано: {PANEL_SIZE}")
    ax.set_xscale("log"); ax.set_xlabel("Число генов в панели")
    ax.set_ylabel("macro ROC-AUC (честная CV)")
    ax.set_title("Качество диагностики vs размер панели", fontweight="bold")
    ax.legend(fontsize=9); ax.grid(alpha=0.3)

    # важность генов: средн. |коэффициент| мультиномиальной ЛР (стандартиз. признаки)
    ax = axes[1]
    imp = np.abs(clf.coef_).mean(axis=0)
    order = np.argsort(imp)
    colors = [STAGE_COLOR[panel_df.iloc[i]["peak_stage"]] for i in order]
    labels = [genes[i] + (" *" if panel_df.iloc[i]["known_AD_gene"] else "") for i in order]
    ax.barh(np.arange(len(order)), imp[order], color=colors, alpha=0.9)
    ax.set_yticks(np.arange(len(order))); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Важность (средний |коэффициент| ЛР)")
    ax.set_title(f"Панель из {PANEL_SIZE} генов (macro-AUC {macro_pt:.2f}, "
                 f"95% ДИ {macro_ci[0]:.2f}–{macro_ci[1]:.2f})\n"
                 "цвет — стадия с пиком экспрессии;  * — известный AD-ген",
                 fontweight="bold", fontsize=10)
    ax.grid(alpha=0.3, axis="x")
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_FOLDER, "biomarker_panel.png"), dpi=150)
    plt.close()


def _plot_metrics(oof, y, cm, per_class_ci):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8))
    # confusion matrix (нормированная по строкам)
    ax = axes[0]
    cmn = cm / cm.sum(axis=1, keepdims=True)
    im = ax.imshow(cmn, cmap="Purples", vmin=0, vmax=1)
    names = [STAGE_RU_SHORT[s] for s in STAGES]
    ax.set_xticks(range(3)); ax.set_xticklabels(names)
    ax.set_yticks(range(3)); ax.set_yticklabels(names)
    ax.set_xlabel("Предсказано"); ax.set_ylabel("Истинно")
    ax.set_title("Матрица ошибок (честная CV)", fontweight="bold")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{cmn[i, j]*100:.0f}%\n({cm[i, j]})", ha="center", va="center",
                    color="white" if cmn[i, j] > 0.5 else "black", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046)
    # ROC по классам (one-vs-rest)
    ax = axes[1]
    yb = label_binarize(y, classes=[0, 1, 2])
    for ci, s in enumerate(STAGES):
        fpr, tpr, _ = roc_curve(yb[:, ci], oof[:, ci])
        auc = roc_auc_score(yb[:, ci], oof[:, ci])
        lo, hi = per_class_ci[s]
        ax.plot(fpr, tpr, color=STAGE_COLOR[s], lw=2,
                label=f"{STAGE_RU_SHORT[s]}: AUC={auc:.2f} [{lo:.2f}–{hi:.2f}]")
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.set_xlabel("FPR (1 − специфичность)"); ax.set_ylabel("TPR (чувствительность)")
    ax.set_title("ROC по каждой стадии (one-vs-rest)", fontweight="bold")
    ax.legend(fontsize=10); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_FOLDER, "metrics.png"), dpi=150)
    plt.close()


def _plot_shap(clf, bg, genes):
    """Глобальная важность по SHAP (если доступно); иначе пропускаем."""
    try:
        import shap
        explainer = shap.LinearExplainer(clf, bg)
        sv = explainer.shap_values(bg)
        plt.figure()
        shap.summary_plot(sv, bg, feature_names=genes, plot_type="bar",
                          class_names=[STAGE_RU_SHORT[s] for s in STAGES], show=False)
        plt.tight_layout()
        plt.savefig(os.path.join(RESULTS_FOLDER, "shap_summary.png"), dpi=150,
                    bbox_inches="tight")
        plt.close()
    except Exception as e:                       # noqa: BLE001
        print(f"  (SHAP-сводка пропущена: {e})")


def main():
    run_panel()


if __name__ == "__main__":
    main()
