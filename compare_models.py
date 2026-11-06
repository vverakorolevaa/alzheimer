"""
Сравнение логистической регрессии с другими моделями машинного обучения.

Зачем: на защите спросят «почему логистическая регрессия, а не нейросеть,
случайный лес или SVM?». Здесь все модели проверяются одинаково:
  • GSE63060 — та же кросс-валидация 5×5 без утечки, что в biomarker_panel.py
    (предфильтр 3000 HVG → отбор 15 генов по ANOVA внутри каждого фолда →
    стандартизация внутри фолда → модель);
  • GSE63061 — внешняя проверка на тех же 15 генах итоговой панели
    (z-score внутри каждого датасета, как в external_validation.py).

Отдельно проверяется «модель одного числа»: вместо 15 генов берётся только
первая главная компонента панели (общий уровень сигнала). Если она почти
не уступает 15 генам — значит, панель по сути измеряет один показатель.

Запуск (после download, panel и external):  python cli.py compare
"""

import os
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.base import clone
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, balanced_accuracy_score

import config
from biomarker_panel import _select_topk
from data_loader import DataLoader
from preprocessor import Preprocessor

SEED = config.PANEL_RANDOM_SEED


def _models():
    lr = LogisticRegression(max_iter=3000, class_weight="balanced", C=1.0,
                            random_state=SEED)
    return {
        "Логистическая регрессия (в проекте)": make_pipeline(StandardScaler(), clone(lr)),
        "Логистическая регрессия по 1 числу (PC1)":
            make_pipeline(StandardScaler(), PCA(n_components=1), clone(lr)),
        "Случайный лес":
            make_pipeline(StandardScaler(), RandomForestClassifier(
                n_estimators=500, min_samples_leaf=3, class_weight="balanced",
                random_state=SEED, n_jobs=-1)),
        "Градиентный бустинг":
            make_pipeline(StandardScaler(), HistGradientBoostingClassifier(
                max_depth=3, learning_rate=0.05, max_iter=200,
                class_weight="balanced", random_state=SEED)),
        "SVM (RBF-ядро)":
            make_pipeline(StandardScaler(), SVC(kernel="rbf", C=1.0, probability=True,
                                                class_weight="balanced", random_state=SEED)),
        "k ближайших соседей (k=15)":
            make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=15)),
        "Нейросеть (MLP 32 нейрона)":
            make_pipeline(StandardScaler(), MLPClassifier(
                hidden_layer_sizes=(32,), alpha=1e-2, max_iter=2000,
                early_stopping=True, random_state=SEED)),
    }


def _cv(model, X, y, k):
    aucs, baccs = [], []
    for rep in range(config.CV_REPEATS):
        skf = StratifiedKFold(n_splits=config.CV_FOLDS, shuffle=True,
                              random_state=SEED + rep)
        oof = np.zeros((len(y), len(config.STAGES)))
        for tr, te in skf.split(X, y):
            idx = _select_topk(X[tr], y[tr], k)
            m = clone(model).fit(X[tr][:, idx], y[tr])
            oof[te] = m.predict_proba(X[te][:, idx])
        aucs.append(roc_auc_score(y, oof, multi_class="ovr"))
        baccs.append(balanced_accuracy_score(y, oof.argmax(1)))
    return float(np.mean(aucs)), float(np.std(aucs)), float(np.mean(baccs))


def main():
    print("=" * 64)
    print("  Сравнение моделей: одинаковая проверка для всех")
    print("=" * 64)
    expr, labels = DataLoader().load()
    expr = Preprocessor().preprocess(expr)
    y = labels.map(config.STAGE_CODE).values.astype(int)
    X_all = expr.values.astype(np.float32)
    hvg = np.argsort(X_all.var(axis=0))[::-1][:config.PREFILTER_HVG]
    X = X_all[:, hvg]

    panel = joblib.load(os.path.join(config.RESULTS_FOLDER, "panel_model.pkl"))["genes"]
    import external_validation as ev
    X_ext, y_ext, _ = ev.load_external()
    A = StandardScaler().fit_transform(expr[panel].values)
    B = StandardScaler().fit_transform(X_ext[panel].values)

    rows = []
    for name, model in _models().items():
        auc, sd, bacc = _cv(model, X, y, config.PANEL_SIZE)
        P = clone(model).fit(A, y).predict_proba(B)
        ext = roc_auc_score(y_ext, P, multi_class="ovr")
        ext_bin = roc_auc_score((y_ext > 0).astype(int), 1 - P[:, 0])
        rows.append({"модель": name, "CV macro-AUC": round(auc, 3),
                     "± std": round(sd, 3), "CV bal-acc": round(bacc, 3),
                     "GSE63061 macro-AUC": round(ext, 3),
                     "GSE63061 норма vs нарушение": round(ext_bin, 3)})
        print(f"  {name:42s} CV {auc:.3f}±{sd:.3f}  bal-acc {bacc:.3f}  "
              f"| GSE63061 {ext:.3f} (норма/нарушение {ext_bin:.3f})")

    df = pd.DataFrame(rows)
    out = os.path.join(config.RESULTS_FOLDER, "model_comparison.csv")
    df.to_csv(out, index=False)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    yy = np.arange(len(df))
    ax.barh(yy + 0.2, df["CV macro-AUC"], 0.38, xerr=df["± std"],
            color="#3498DB", label="GSE63060, кросс-валидация")
    ax.barh(yy - 0.2, df["GSE63061 macro-AUC"], 0.38, color="#E67E22",
            label="GSE63061, независимая когорта")
    ax.set_yticks(yy); ax.set_yticklabels(df["модель"], fontsize=9)
    ax.invert_yaxis()
    ax.axvline(0.5, color="grey", ls=":", lw=1)
    ax.set_xlim(0.45, 0.85); ax.set_xlabel("macro ROC-AUC (0.5 — случайное угадывание)")
    ax.set_title("Сравнение моделей на панели из 15 генов", fontweight="bold")
    ax.legend(loc="lower right", fontsize=8); ax.grid(alpha=0.3, axis="x")
    plt.tight_layout()
    fig.savefig(os.path.join(config.RESULTS_FOLDER, "model_comparison.png"), dpi=150)
    plt.close(fig)
    print(f"\nСохранено: {out}, results/model_comparison.png")


if __name__ == "__main__":
    main()
