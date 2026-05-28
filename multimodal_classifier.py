"""
Мультимодальный классификатор болезни Альцгеймера: MRI + клинические данные.

Архитектура:
  МРТ (FreeSurfer ROI) ──► MRIEncoder      ──► e_mri  ──┐
                                                           ├──► GatedFusion ──► FC ──► CN/MCI/AD
  Клиника (CDR, MMSE)  ──► ClinicalEncoder ──► e_clin ──┘

Gate = sigmoid(W·[e_mri; e_clin])
Fused = gate·e_mri + (1−gate)·e_clin

Если gate→1 — модель доверяет МРТ.
Если gate→0 — модель доверяет клиническим данным.
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import (
    accuracy_score, roc_auc_score,
    classification_report, confusion_matrix,
)
from config import (
    RESULTS_FOLDER, MULTIMODAL_EMBED_DIM, MULTIMODAL_EPOCHS,
    MULTIMODAL_TEST_SIZE, MULTIMODAL_BATCH, DX_LABELS,
)


# ── Энкодеры ──────────────────────────────────────────────────────────

class MRIEncoder(nn.Module):
    """Кодирует FreeSurfer ROI-признаки в 128-мерный вектор."""

    def __init__(self, input_dim, embed_dim=MULTIMODAL_EMBED_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, embed_dim),
        )

    def forward(self, x):
        return self.net(x)


class ClinicalEncoder(nn.Module):
    """Кодирует клинические признаки (возраст, MMSE, CDR, APOE4...)."""

    def __init__(self, input_dim, embed_dim=MULTIMODAL_EMBED_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, embed_dim),
        )

    def forward(self, x):
        return self.net(x)


# ── Gated Fusion ──────────────────────────────────────────────────────

class GatedFusion(nn.Module):
    def __init__(self, embed_dim=MULTIMODAL_EMBED_DIM):
        super().__init__()
        self.gate_fc = nn.Linear(embed_dim * 2, embed_dim)

    def forward(self, e_mri, e_clin):
        gate  = torch.sigmoid(self.gate_fc(torch.cat([e_mri, e_clin], dim=-1)))
        fused = gate * e_mri + (1 - gate) * e_clin
        return fused, gate


# ── Полная сеть ───────────────────────────────────────────────────────

class MultimodalADNet(nn.Module):
    def __init__(self, mri_dim, clin_dim, n_classes=3):
        super().__init__()
        self.mri_encoder  = MRIEncoder(mri_dim)
        self.clin_encoder = ClinicalEncoder(clin_dim)
        self.fusion       = GatedFusion()
        self.classifier   = nn.Sequential(
            nn.Linear(MULTIMODAL_EMBED_DIM, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, n_classes),
        )

    def forward(self, x_mri, x_clin):
        e_mri  = self.mri_encoder(x_mri)
        e_clin = self.clin_encoder(x_clin)
        fused, gate = self.fusion(e_mri, e_clin)
        logits = self.classifier(fused)
        return logits, gate, e_mri, e_clin


# ── Однородные базовые модели для сравнения ───────────────────────────

class _BaselineNet(nn.Module):
    def __init__(self, input_dim, n_classes):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64),        nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, n_classes),
        )

    def forward(self, x):
        return self.net(x)


def _train_baseline(model, X_tr, y_tr, weights, epochs, batch):
    loader = DataLoader(
        TensorDataset(torch.from_numpy(X_tr), torch.LongTensor(y_tr)),
        batch_size=batch, shuffle=True,
    )
    opt     = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss(weight=weights)
    model.train()
    for _ in range(epochs):
        for xb, yb in loader:
            opt.zero_grad()
            loss_fn(model(xb), yb).backward()
            opt.step()


def _predict_proba(model, X):
    model.eval()
    with torch.no_grad():
        return torch.softmax(model(torch.from_numpy(X)), dim=1).numpy()


# ── Тренировочная обёртка ─────────────────────────────────────────────

class MultimodalClassifier:
    """Полный цикл: donor-level split → обучение → метрики → сохранение."""

    def __init__(self):
        self.model          = None
        self.mri_scaler     = RobustScaler()
        self.clin_scaler    = StandardScaler()
        self.mri_feature_names  = []
        self.clin_feature_names = []

    def train(self, X_mri, X_clin, y, groups,
              mri_names=None, clin_names=None):
        self.mri_feature_names  = mri_names  or [f"mri_{i}"  for i in range(X_mri.shape[1])]
        self.clin_feature_names = clin_names or [f"clin_{i}" for i in range(X_clin.shape[1])]

        n_classes = len(np.unique(y))
        print(f"\nМультимодальный классификатор (MRI + Clinical):")
        print(f"  МРТ-признаков:         {X_mri.shape[1]}")
        print(f"  Клинических признаков: {X_clin.shape[1]}")
        print(f"  Пациентов:             {len(np.unique(groups))}")
        for i, name in DX_LABELS.items():
            print(f"  {name}: {(y == i).sum()}")

        # ── Donor-level split ──────────────────────────────────────────
        gss = GroupShuffleSplit(n_splits=1,
                                test_size=MULTIMODAL_TEST_SIZE, random_state=42)
        tr_idx, te_idx = next(gss.split(X_mri, y, groups))

        X_mri_tr  = self.mri_scaler.fit_transform(X_mri[tr_idx]).astype(np.float32)
        X_mri_te  = self.mri_scaler.transform(X_mri[te_idx]).astype(np.float32)
        X_clin_tr = self.clin_scaler.fit_transform(X_clin[tr_idx]).astype(np.float32)
        X_clin_te = self.clin_scaler.transform(X_clin[te_idx]).astype(np.float32)
        y_tr, y_te = y[tr_idx], y[te_idx]

        counts  = np.bincount(y_tr)
        weights = torch.tensor(1.0 / counts, dtype=torch.float32)

        # ── Базовые однородные модели ──────────────────────────────────
        print("\n  Обучаю базовые модели (MRI-only, Clinical-only)...")
        mri_only  = _BaselineNet(X_mri_tr.shape[1], n_classes)
        clin_only = _BaselineNet(X_clin_tr.shape[1], n_classes)
        _train_baseline(mri_only,  X_mri_tr,  y_tr, weights, MULTIMODAL_EPOCHS, MULTIMODAL_BATCH)
        _train_baseline(clin_only, X_clin_tr, y_tr, weights, MULTIMODAL_EPOCHS, MULTIMODAL_BATCH)
        probs_mri_only  = _predict_proba(mri_only,  X_mri_te)
        probs_clin_only = _predict_proba(clin_only, X_clin_te)

        # ── Обучение мультимодальной сети ──────────────────────────────
        print("  Обучаю мультимодальную сеть (Gated Fusion)...")
        loader = DataLoader(
            TensorDataset(
                torch.from_numpy(X_mri_tr),
                torch.from_numpy(X_clin_tr),
                torch.LongTensor(y_tr),
            ),
            batch_size=MULTIMODAL_BATCH, shuffle=True,
        )

        self.model = MultimodalADNet(X_mri.shape[1], X_clin.shape[1], n_classes)
        optimizer  = torch.optim.Adam(self.model.parameters(),
                                      lr=1e-3, weight_decay=1e-4)
        loss_fn    = nn.CrossEntropyLoss(weight=weights)

        losses = []
        for epoch in range(MULTIMODAL_EPOCHS):
            self.model.train()
            ep_loss = 0.0
            for xm, xc, yb in loader:
                optimizer.zero_grad()
                logits, _, _, _ = self.model(xm, xc)
                loss = loss_fn(logits, yb)
                loss.backward()
                optimizer.step()
                ep_loss += loss.item()
            avg = ep_loss / len(loader)
            losses.append(avg)
            if (epoch + 1) % 10 == 0:
                print(f"  Эпоха {epoch+1:3d}/{MULTIMODAL_EPOCHS}  loss={avg:.4f}")

        # ── Инференс мультимодальной сети ──────────────────────────────
        self.model.eval()
        with torch.no_grad():
            logits, gates, e_mri, e_clin = self.model(
                torch.from_numpy(X_mri_te),
                torch.from_numpy(X_clin_te),
            )
        probs  = torch.softmax(logits, dim=1).numpy()
        gates  = gates.numpy()
        preds  = probs.argmax(axis=1)

        # ── Метрики ────────────────────────────────────────────────────
        acc = accuracy_score(y_te, preds)
        auc = roc_auc_score(y_te, probs, multi_class="ovr", average="macro")
        dx_names = [DX_LABELS[i] for i in sorted(DX_LABELS)]

        def _auc(p):
            return roc_auc_score(y_te, p, multi_class="ovr", average="macro")

        print(f"\n  MRI-only      AUC: {_auc(probs_mri_only):.3f}")
        print(f"  Clinical-only AUC: {_auc(probs_clin_only):.3f}")
        print(f"  Fusion        AUC: {auc:.3f}   Accuracy: {acc:.3f}")
        print(classification_report(y_te, preds, target_names=dx_names))

        import joblib
        os.makedirs(RESULTS_FOLDER, exist_ok=True)
        torch.save({
            "state_dict": self.model.state_dict(),
            "mri_dim":    X_mri.shape[1],
            "clin_dim":   X_clin.shape[1],
            "n_classes":  n_classes,
        }, os.path.join(RESULTS_FOLDER, "multimodal_model.pt"))
        joblib.dump(self.mri_scaler,  os.path.join(RESULTS_FOLDER, "mri_scaler.pkl"))
        joblib.dump(self.clin_scaler, os.path.join(RESULTS_FOLDER, "clin_scaler.pkl"))
        print(f"  Модель: {RESULTS_FOLDER}/multimodal_model.pt")

        # Важность МРТ-признаков: |W_first_layer| × std(X_test)
        W = self.model.mri_encoder.net[0].weight.detach().numpy()  # (256, n_mri)
        mri_importance = np.abs(W).sum(axis=0) * X_mri_te.std(axis=0)
        mri_importance = mri_importance / (mri_importance.sum() + 1e-8)

        return {
            "accuracy": acc, "roc_auc": auc,
            "y_true": y_te, "probs": probs, "preds": preds,
            "probs_mri_only": probs_mri_only,
            "probs_clin_only": probs_clin_only,
            "gates": gates, "losses": losses,
            "embeddings": np.concatenate([e_mri.numpy(), e_clin.numpy()], axis=1),
            "mri_importance": mri_importance,
        }
