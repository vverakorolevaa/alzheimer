"""
Мультимодальный ансамблевый классификатор AD vs. здоровый.

Три параллельных головы:
  Head 1 — Expression MLP    : топ-DEG транскриптомные признаки
  Head 2 — Composition MLP   : клеточный состав образца (вторая модальность)
  Head 3 — Gene2Vec MLP      : предобученные эмбеддинги генов (Gene2Vec, Du 2019)

Финальное решение: среднее softmax-вероятностей трёх голов.
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve, classification_report

from config import (
    CONDITION_COL, CLASSIFIER_TEST_SIZE,
    CLASSIFIER_TOP_GENES, CLASSIFIER_EPOCHS, RESULTS_FOLDER,
    GENE2VEC_DIM,
)
from gene_embeddings import load_gene2vec, compute_cell_embeddings, compute_composition_features


# ── Архитектуры голов ─────────────────────────────────────────────────

class ExpressionHead(nn.Module):
    """Head 1: транскриптомные признаки (топ-DEG гены)."""

    def __init__(self, input_size):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 64),         nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, 2),
        )

    def forward(self, x):
        return self.net(x)


class CompositionHead(nn.Module):
    """Head 2: клеточный состав образца (вторая модальность)."""

    def __init__(self, input_size):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 32), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32, 16),         nn.ReLU(),
            nn.Linear(16, 2),
        )

    def forward(self, x):
        return self.net(x)


class EmbeddingHead(nn.Module):
    """Head 3: предобученные Gene2Vec эмбеддинги."""

    def __init__(self, input_size=GENE2VEC_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64),         nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 2),
        )

    def forward(self, x):
        return self.net(x)


# ── Основной класс ────────────────────────────────────────────────────

class EnsembleClassifier:
    """
    Полный цикл: подготовка данных → обучение трёх голов → ансамбль → метрики.
    """

    def __init__(self):
        self.head1 = None          # ExpressionHead
        self.head2 = None          # CompositionHead
        self.head3 = None          # EmbeddingHead
        self.scaler1  = StandardScaler()
        self.scaler2  = StandardScaler()
        self.scaler3  = StandardScaler()
        self.selected_genes = []
        self.gene2vec = {}

    # ── Подготовка данных ──────────────────────────────────────────────

    def _prepare_expression(self, adata, deg_results):
        all_sig = set()
        for df in deg_results.values():
            all_sig.update(df[df["significant"]]["gene"].tolist())
        available = [g for g in all_sig if g in adata.var_names]
        self.selected_genes = available[:CLASSIFIER_TOP_GENES]
        idx = [list(adata.var_names).index(g) for g in self.selected_genes]
        X = np.asarray(adata.X[:, idx], dtype=np.float32)
        print(f"  Head 1 (Expression): {len(self.selected_genes)} генов")
        return X

    def _prepare_composition(self, adata):
        X, ct_names = compute_composition_features(adata)
        print(f"  Head 2 (Composition): {X.shape[1]} типов клеток")
        return X

    def _prepare_embeddings(self, adata, deg_results):
        self.gene2vec = load_gene2vec()
        X = compute_cell_embeddings(adata, deg_results, self.gene2vec)
        print(f"  Head 3 (Gene2Vec): {X.shape[1]}-мерные эмбеддинги")
        return X

    # ── Обучение одной головы ──────────────────────────────────────────

    def _train_head(self, model, X_tr, y_tr, tag):
        loader = DataLoader(
            TensorDataset(torch.from_numpy(X_tr), torch.LongTensor(y_tr)),
            batch_size=64, shuffle=True,
        )
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
        loss_fn   = nn.CrossEntropyLoss()

        losses = []
        model.train()
        for epoch in range(CLASSIFIER_EPOCHS):
            ep_loss = 0.0
            for xb, yb in loader:
                optimizer.zero_grad()
                loss = loss_fn(model(xb), yb)
                loss.backward()
                optimizer.step()
                ep_loss += loss.item()
            avg = ep_loss / len(loader)
            losses.append(avg)
            if (epoch + 1) % 10 == 0:
                print(f"    [{tag}] эпоха {epoch+1:2d}/{CLASSIFIER_EPOCHS}  loss={avg:.4f}")
        return losses

    # ── Инференс одной головы ──────────────────────────────────────────

    @staticmethod
    def _predict_proba(model, X_te):
        model.eval()
        with torch.no_grad():
            logits = model(torch.from_numpy(X_te))
            return torch.softmax(logits, dim=1).numpy()

    # ── Главный метод ──────────────────────────────────────────────────

    def train(self, adata, deg_results):
        """Обучает три головы и выводит метрики ансамбля и каждой головы."""
        print("\nПодготовка признаков для трёх голов...")
        X1 = self._prepare_expression(adata, deg_results)
        X2 = self._prepare_composition(adata)
        X3 = self._prepare_embeddings(adata, deg_results)

        y = (adata.obs[CONDITION_COL] == "AD").astype(int).values

        # Стратифицированное разбиение (единый для всех голов)
        idx_all = np.arange(len(y))
        idx_tr, idx_te = train_test_split(
            idx_all, test_size=CLASSIFIER_TEST_SIZE, random_state=42, stratify=y
        )
        y_tr, y_te = y[idx_tr], y[idx_te]

        def split_scale(X, scaler):
            X_tr = scaler.fit_transform(X[idx_tr]).astype(np.float32)
            X_te = scaler.transform(X[idx_te]).astype(np.float32)
            return X_tr, X_te

        X1_tr, X1_te = split_scale(X1, self.scaler1)
        X2_tr, X2_te = split_scale(X2, self.scaler2)
        X3_tr, X3_te = split_scale(X3, self.scaler3)

        # ── Обучение голов ─────────────────────────────────────────────
        print("\n[Head 1] Expression MLP")
        self.head1 = ExpressionHead(X1_tr.shape[1])
        losses1 = self._train_head(self.head1, X1_tr, y_tr, "Expr")

        print("\n[Head 2] Composition MLP (вторая модальность)")
        self.head2 = CompositionHead(X2_tr.shape[1])
        losses2 = self._train_head(self.head2, X2_tr, y_tr, "Comp")

        print("\n[Head 3] Gene2Vec Embedding MLP (предобученная модель)")
        self.head3 = EmbeddingHead(X3_tr.shape[1])
        losses3 = self._train_head(self.head3, X3_tr, y_tr, "Emb")

        # ── Оценка каждой головы и ансамбля ───────────────────────────
        p1 = self._predict_proba(self.head1, X1_te)
        p2 = self._predict_proba(self.head2, X2_te)
        p3 = self._predict_proba(self.head3, X3_te)
        p_ens = (p1 + p2 + p3) / 3.0

        def metrics(probs, name):
            preds = probs.argmax(axis=1)
            acc = accuracy_score(y_te, preds)
            auc = roc_auc_score(y_te, probs[:, 1])
            print(f"\n  {name}: accuracy={acc:.3f}  ROC-AUC={auc:.3f}")
            return acc, auc

        print("\n=== Метрики классификации ===")
        acc1, auc1 = metrics(p1,    "Head 1 — Expression")
        acc2, auc2 = metrics(p2,    "Head 2 — Composition")
        acc3, auc3 = metrics(p3,    "Head 3 — Gene2Vec")
        acc_e, auc_e = metrics(p_ens, "ENSEMBLE (avg)")
        print(classification_report(y_te, p_ens.argmax(axis=1),
                                    target_names=["Здоровый", "Болезнь Альцгеймера"]))

        # ── Сохранение графиков и моделей ─────────────────────────────
        self._save_plots(losses1, losses2, losses3, y_te, p_ens[:, 1], acc_e, auc_e,
                         p1[:, 1], p2[:, 1], p3[:, 1])
        self._save_models()

        return {
            "head1": {"accuracy": acc1, "roc_auc": auc1},
            "head2": {"accuracy": acc2, "roc_auc": auc2},
            "head3": {"accuracy": acc3, "roc_auc": auc3},
            "ensemble": {"accuracy": acc_e, "roc_auc": auc_e},
        }

    def _save_plots(self, l1, l2, l3, y_true, ens_prob, acc, auc,
                    p1, p2, p3):
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Кривые обучения
        ax = axes[0, 0]
        ax.plot(l1, label="Head 1 Expression", color="#E74C3C")
        ax.plot(l2, label="Head 2 Composition", color="#3498DB")
        ax.plot(l3, label="Head 3 Gene2Vec",    color="#2ECC71")
        ax.set_xlabel("Эпоха"); ax.set_ylabel("Loss")
        ax.set_title("Кривые обучения трёх голов"); ax.legend(fontsize=9)

        # ROC ансамбля
        ax = axes[0, 1]
        fpr_e, tpr_e, _ = roc_curve(y_true, ens_prob)
        ax.plot(fpr_e, tpr_e, color="#8E44AD", lw=2, label=f"Ensemble AUC={auc:.3f}")
        for probs, label, col in [(p1, "Head1", "#E74C3C"),
                                   (p2, "Head2", "#3498DB"),
                                   (p3, "Head3", "#2ECC71")]:
            fpr, tpr, _ = roc_curve(y_true, probs)
            ax.plot(fpr, tpr, lw=1, ls="--", color=col, alpha=0.7,
                    label=f"{label} AUC={roc_auc_score(y_true, probs):.3f}")
        ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
        ax.set_xlabel("FPR"); ax.set_ylabel("TPR")
        ax.set_title(f"ROC-кривые  (Ensemble acc={acc:.1%})")
        ax.legend(fontsize=8)

        # Точность по головам
        ax = axes[1, 0]
        names  = ["Head1\nExpression", "Head2\nComposition", "Head3\nGene2Vec", "Ensemble"]
        accs   = [accuracy_score(y_true, p1.round()),
                  accuracy_score(y_true, p2.round()),
                  accuracy_score(y_true, p3.round()), acc]
        colors = ["#E74C3C", "#3498DB", "#2ECC71", "#8E44AD"]
        bars = ax.bar(names, accs, color=colors, alpha=0.85)
        for bar, v in zip(bars, accs):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.005,
                    f"{v:.3f}", ha="center", fontsize=10)
        ax.set_ylim(0, 1.1); ax.set_ylabel("Accuracy")
        ax.set_title("Точность по головам и ансамблю")

        # AUC по головам
        ax = axes[1, 1]
        aucs = [roc_auc_score(y_true, p1),
                roc_auc_score(y_true, p2),
                roc_auc_score(y_true, p3), auc]
        bars = ax.bar(names, aucs, color=colors, alpha=0.85)
        for bar, v in zip(bars, aucs):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.005,
                    f"{v:.3f}", ha="center", fontsize=10)
        ax.set_ylim(0, 1.1); ax.set_ylabel("ROC-AUC")
        ax.set_title("ROC-AUC по головам и ансамблю")

        path = os.path.join(RESULTS_FOLDER, "ensemble_metrics.png")
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"  График метрик: {path}")

    def _save_models(self):
        for name, model in [("head1_expression", self.head1),
                             ("head2_composition", self.head2),
                             ("head3_gene2vec", self.head3)]:
            path = os.path.join(RESULTS_FOLDER, f"{name}.pt")
            torch.save(model.state_dict(), path)
        print(f"  Модели сохранены: {RESULTS_FOLDER}/head*.pt")
