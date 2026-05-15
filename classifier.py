import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
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
)


# ── Архитектура нейросети ─────────────────────────────────────────────
class GeneNet(nn.Module):
    """
    Многослойный перцептрон (MLP) для классификации больной/здоровый.

    Вход:  вектор экспрессии ~500 генов
    Выход: 2 класса (0 = здоровый, 1 = болезнь Альцгеймера)

    Слои: Linear → ReLU → Dropout → Linear → ReLU → Dropout → Linear
    Dropout(0.3) случайно выключает 30% нейронов при обучении —
    это защищает от переобучения (когда сеть "зубрит" тренировочные данные).
    """

    def __init__(self, input_size):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 2),
        )

    def forward(self, x):
        return self.net(x)


# ── Обёртка: обучение, оценка, сохранение ────────────────────────────
class DiseaseClassifier:
    """
    Полный цикл: подготовка данных → обучение GeneNet → метрики → сохранение.
    """

    def __init__(self):
        self.model          = None
        self.scaler         = StandardScaler()
        self.selected_genes = []

    def _prepare(self, adata, deg_results):
        """Собирает матрицу признаков из топ-DEG генов."""
        all_sig = set()
        for df in deg_results.values():
            all_sig.update(df[df['significant']]['gene'].tolist())

        available = [g for g in all_sig if g in adata.var_names]
        self.selected_genes = available[:CLASSIFIER_TOP_GENES]
        print(f'  Генов для классификатора: {len(self.selected_genes)}')

        idx = [list(adata.var_names).index(g) for g in self.selected_genes]
        X   = np.asarray(adata.X[:, idx], dtype=np.float32)
        y   = (adata.obs[CONDITION_COL] == 'AD').astype(int).values
        return X, y

    def train(self, adata, deg_results):
        """Обучает нейросеть и выводит метрики качества."""
        print('\nОбучаю классификатор (PyTorch MLP)...')
        X, y = self._prepare(adata, deg_results)

        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=CLASSIFIER_TEST_SIZE,
            random_state=42, stratify=y
        )
        X_tr = self.scaler.fit_transform(X_tr).astype(np.float32)
        X_te = self.scaler.transform(X_te).astype(np.float32)

        loader = DataLoader(
            TensorDataset(torch.from_numpy(X_tr), torch.LongTensor(y_tr)),
            batch_size=64, shuffle=True
        )

        self.model = GeneNet(X_tr.shape[1])
        optimizer  = torch.optim.Adam(self.model.parameters(), lr=1e-3)
        loss_fn    = nn.CrossEntropyLoss()

        losses = []
        for epoch in range(CLASSIFIER_EPOCHS):
            self.model.train()
            epoch_loss = 0
            for xb, yb in loader:
                optimizer.zero_grad()
                loss = loss_fn(self.model(xb), yb)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            avg = epoch_loss / len(loader)
            losses.append(avg)
            if (epoch + 1) % 10 == 0:
                print(f'  Эпоха {epoch+1:2d}/{CLASSIFIER_EPOCHS}  loss={avg:.4f}')

        # Оценка
        self.model.eval()
        with torch.no_grad():
            logits = self.model(torch.from_numpy(X_te))
            probs  = torch.softmax(logits, dim=1).numpy()
        preds   = probs.argmax(axis=1)
        acc     = accuracy_score(y_te, preds)
        auc     = roc_auc_score(y_te, probs[:, 1])

        print(f'\n  Точность (accuracy): {acc:.3f}')
        print(f'  ROC-AUC:             {auc:.3f}')
        print(classification_report(y_te, preds,
                                    target_names=['Здоровый', 'Болезнь Альцгеймера']))

        self._save_plots(losses, y_te, probs[:, 1], acc, auc)

        model_path = os.path.join(RESULTS_FOLDER, 'classifier.pt')
        torch.save(self.model.state_dict(), model_path)
        print(f'  Модель сохранена: {model_path}')

        return {'accuracy': acc, 'roc_auc': auc}

    def _save_plots(self, losses, y_true, y_prob, acc, auc):
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        ax1.plot(losses, color='steelblue', lw=2)
        ax1.set_xlabel('Эпоха')
        ax1.set_ylabel('Loss (ошибка)')
        ax1.set_title('Кривая обучения нейросети')

        ax2.plot(fpr, tpr, color='#E74C3C', lw=2,
                 label=f'ROC-AUC = {auc:.3f}')
        ax2.plot([0, 1], [0, 1], 'k--', alpha=0.4)
        ax2.set_xlabel('False Positive Rate')
        ax2.set_ylabel('True Positive Rate')
        ax2.set_title(f'ROC-кривая  (точность = {acc:.1%})')
        ax2.legend(fontsize=11)

        path = os.path.join(RESULTS_FOLDER, 'classifier_metrics.png')
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f'  График метрик: {path}')
