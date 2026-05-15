"""
Визуализации для мультимодального классификатора MRI + Clinical.

1. plot_training_loss()        — кривая обучения
2. plot_multihead_roc()        — ROC: Fusion / MRI-only / Clinical-only
3. plot_confusion_matrix()     — матрица ошибок 3 класса
4. plot_gate_weights()         — gate-веса по классам (МРТ vs клиника)
5. plot_roi_importance()       — важность МРТ-регионов
6. plot_biomarker_trajectory() — CN → MCI → AD по ключевым биомаркерам
7. plot_fusion_umap()          — UMAP/t-SNE фьюженных эмбеддингов
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.metrics import roc_curve, auc as sk_auc, confusion_matrix
from config import RESULTS_FOLDER, DX_LABELS, DX_COLORS

PALETTE = [DX_COLORS[0], DX_COLORS[1], DX_COLORS[2]]


class MultimodalVisualizer:

    def __init__(self):
        os.makedirs(RESULTS_FOLDER, exist_ok=True)
        plt.rcParams.update({"font.size": 11, "figure.dpi": 150})

    # ── 1. Кривая обучения ────────────────────────────────────────────
    def plot_training_loss(self, losses):
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(losses, color="#3498DB", lw=2)
        ax.set_xlabel("Эпоха")
        ax.set_ylabel("Loss (ошибка)")
        ax.set_title("Кривая обучения мультимодальной нейросети", fontweight="bold")
        path = os.path.join(RESULTS_FOLDER, "training_loss.png")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f"  Сохранён: {path}")
        return path

    # ── 2. Multi-head ROC ─────────────────────────────────────────────
    def plot_multihead_roc(self, y_true, probs_fused,
                           probs_mri=None, probs_clin=None):
        """ROC для каждого класса (One-vs-Rest) + сравнение голов."""
        n_classes = probs_fused.shape[1]
        fig, axes = plt.subplots(1, n_classes, figsize=(5 * n_classes, 5))

        for i, ax in enumerate(axes):
            y_bin = (y_true == i).astype(int)
            curves = [
                (probs_fused, "Fusion (МРТ + клиника)", "#8E44AD", "-",  2.5),
                (probs_mri,   "МРТ alone",              "#3498DB", "--", 1.5),
                (probs_clin,  "Клиника alone",          "#E67E22", ":",  1.5),
            ]
            for probs, label, col, ls, lw in curves:
                if probs is None:
                    continue
                fpr, tpr, _ = roc_curve(y_bin, probs[:, i])
                roc_val = sk_auc(fpr, tpr)
                ax.plot(fpr, tpr, color=col, ls=ls, lw=lw,
                        label=f"{label} (AUC={roc_val:.3f})")
            ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
            ax.set_title(f"ROC — {DX_LABELS[i]} vs остальные", fontweight="bold")
            ax.set_xlabel("FPR (ложная тревога)")
            ax.set_ylabel("TPR (чувствительность)")
            ax.legend(fontsize=8)

        fig.suptitle("ROC-кривые: сравнение голов", fontsize=13, fontweight="bold")
        path = os.path.join(RESULTS_FOLDER, "multihead_roc.png")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f"  Сохранён: {path}")
        return path

    # ── 3. Confusion matrix ───────────────────────────────────────────
    def plot_confusion_matrix(self, y_true, y_pred):
        labels = [DX_LABELS[i] for i in range(3)]
        cm = confusion_matrix(y_true, y_pred, normalize="true")

        fig, ax = plt.subplots(figsize=(7, 6))
        sns.heatmap(cm, annot=True, fmt=".2f", cmap="Blues",
                    xticklabels=labels, yticklabels=labels,
                    linewidths=0.5, ax=ax, vmin=0, vmax=1)
        ax.set_xlabel("Предсказанный диагноз", fontsize=12)
        ax.set_ylabel("Истинный диагноз", fontsize=12)
        ax.set_title("Матрица ошибок (нормированная)", fontweight="bold")
        path = os.path.join(RESULTS_FOLDER, "confusion_matrix.png")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f"  Сохранён: {path}")
        return path

    # ── 4. Gate weights ───────────────────────────────────────────────
    def plot_gate_weights(self, gates, y_true):
        """
        Боксплот средних gate-значений по классам.
        gate ≈ 1 → МРТ важнее, gate ≈ 0 → клиника важнее.
        """
        df = pd.DataFrame({
            "gate": gates.mean(axis=1),
            "diagnosis": [DX_LABELS[int(i)] for i in y_true],
        })
        order = [DX_LABELS[0], DX_LABELS[1], DX_LABELS[2]]

        fig, ax = plt.subplots(figsize=(7, 5))
        sns.boxplot(data=df, x="diagnosis", y="gate", order=order,
                    palette=PALETTE, ax=ax, width=0.5)
        ax.axhline(0.5, color="black", ls="--", lw=1.2, alpha=0.6,
                   label="Равный вес (0.5)")
        ax.set_ylim(0, 1)
        ax.set_xlabel("Диагноз")
        ax.set_ylabel("Gate-вес")
        ax.set_title("Gated Fusion: какой модальности доверяет модель?",
                     fontweight="bold")
        ax.text(2.6, 0.85, "МРТ важнее", fontsize=9, color="#3498DB", alpha=0.8)
        ax.text(2.6, 0.15, "Клиника важнее", fontsize=9, color="#E67E22", alpha=0.8)
        ax.legend(fontsize=9)
        path = os.path.join(RESULTS_FOLDER, "gate_weights.png")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f"  Сохранён: {path}")
        return path

    # ── 5. ROI importance ─────────────────────────────────────────────
    def plot_roi_importance(self, feature_names, importances):
        """Барплот важности МРТ-регионов (по std активаций энкодера)."""
        order = np.argsort(importances)[::-1]
        names = [
            feature_names[i]
            .replace("_", " ").replace("lh ", "Л. ").replace("rh ", "П. ")
            .replace(" thickness", " (толщина)")
            for i in order
        ]
        vals = importances[order]
        n    = min(15, len(names))

        fig, ax = plt.subplots(figsize=(9, 6))
        colors = ["#E74C3C" if "hippocampus" in names[i] or "entorhinal" in names[i]
                  else "#3498DB" for i in range(n)]
        ax.barh(names[:n][::-1], vals[:n][::-1], color=colors[::-1], alpha=0.85)
        ax.set_xlabel("Относительная важность")
        ax.set_title("Топ МРТ-регионов для диагностики AD\n"
                     "(красные = первыми поражаются при AD)", fontweight="bold")

        handles = [
            mpatches.Patch(color="#E74C3C", label="Ранние маркеры AD"),
            mpatches.Patch(color="#3498DB", label="Другие регионы"),
        ]
        ax.legend(handles=handles, fontsize=9)
        path = os.path.join(RESULTS_FOLDER, "roi_importance.png")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f"  Сохранён: {path}")
        return path

    # ── 6. Biomarker trajectory ───────────────────────────────────────
    def plot_biomarker_trajectory(self, df):
        """Средние значения биомаркеров по CN / MCI / AD."""
        wanted = {
            "lh_hippocampus":          "Гиппокамп Л (мм³)",
            "rh_hippocampus":          "Гиппокамп П (мм³)",
            "mmse":                    "MMSE (0–30)",
            "cdr":                     "CDR (0–3)",
            "lh_entorhinal_thickness": "Энторинальная кора Л (мм)",
        }
        available = {k: v for k, v in wanted.items() if k in df.columns}
        n = len(available)
        if n == 0:
            return

        df_plot = df.copy()
        df_plot["dx_label"] = df_plot["diagnosis"].map(DX_LABELS)
        order = [DX_LABELS[0], DX_LABELS[1], DX_LABELS[2]]

        fig, axes = plt.subplots(1, n, figsize=(4.5 * n, 5))
        if n == 1:
            axes = [axes]

        for ax, (col, title) in zip(axes, available.items()):
            means = df_plot.groupby("dx_label")[col].mean().reindex(order)
            sems  = df_plot.groupby("dx_label")[col].sem().reindex(order)
            ax.bar(order, means.values, yerr=sems.values,
                   color=PALETTE, alpha=0.85, capsize=6, edgecolor="white")
            # Соединяем точки линией для наглядности тренда
            ax.plot(range(3), means.values, "k-o", lw=1.5, ms=5, alpha=0.6)
            ax.set_title(title, fontweight="bold")
            ax.set_ylabel("Среднее ± SE")

        fig.suptitle("Биомаркеры: CN → MCI → AD (нарастание патологии)",
                     fontsize=13, fontweight="bold")
        path = os.path.join(RESULTS_FOLDER, "biomarker_trajectory.png")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f"  Сохранён: {path}")
        return path

    # ── 7. UMAP / t-SNE эмбеддингов ──────────────────────────────────
    def plot_fusion_umap(self, embeddings, y_true):
        try:
            from umap import UMAP
            coords = UMAP(n_components=2, random_state=42).fit_transform(embeddings)
            title  = "UMAP фьюженных эмбеддингов (МРТ + клиника)"
        except ImportError:
            from sklearn.manifold import TSNE
            coords = TSNE(n_components=2, random_state=42,
                          perplexity=min(30, len(y_true) // 4)).fit_transform(embeddings)
            title  = "t-SNE фьюженных эмбеддингов (МРТ + клиника)"

        fig, ax = plt.subplots(figsize=(8, 7))
        for i, label in DX_LABELS.items():
            mask = y_true == i
            ax.scatter(coords[mask, 0], coords[mask, 1],
                       c=DX_COLORS[i], label=label, alpha=0.65, s=25)
        ax.set_title(title, fontweight="bold")
        ax.legend(fontsize=11, markerscale=2)
        ax.set_xticks([])
        ax.set_yticks([])
        path = os.path.join(RESULTS_FOLDER, "fusion_umap.png")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f"  Сохранён: {path}")
        return path
