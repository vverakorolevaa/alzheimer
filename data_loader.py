import os
import pandas as pd
import numpy as np
import anndata as ad
from config import DATA_FILE, META_FILE, CONDITION_COL, CELL_TYPE_COL


class DataLoader:
    """
    Загружает матрицу экспрессии генов и метаданные из CSV-файлов.

    Данные: GSE138852 (Mathys et al., Nature 2019)
    — 48 пациентов с болезнью Альцгеймера + 32 здоровых
    — Энторинальная кора головного мозга
    — 8 типов клеток
    """

    def __init__(self, data_path=DATA_FILE, meta_path=META_FILE):
        self.data_path = data_path
        self.meta_path = meta_path
        self.adata = None

    def load(self):
        """Читает CSV, создаёт объект AnnData."""
        print("Загружаю данные...")

        if not os.path.exists(self.data_path):
            raise FileNotFoundError(
                f"\nФайл не найден: {self.data_path}\n"
                "Запустите сначала: python download_data.py"
            )

        counts = pd.read_csv(self.data_path, index_col=0)
        print(f"  Матрица: {counts.shape[0]} генов × {counts.shape[1]} клеток")

        metadata = pd.read_csv(self.meta_path, index_col=0)

        # AnnData: строки = клетки, столбцы = гены
        self.adata = ad.AnnData(X=counts.T.values.astype(np.float32))
        self.adata.obs_names = counts.columns.tolist()
        self.adata.var_names = counts.index.tolist()

        # Добавляем метаданные только для тех клеток, что есть в матрице
        common = metadata.index.intersection(self.adata.obs_names)
        for col in metadata.columns:
            self.adata.obs[col] = metadata.reindex(self.adata.obs_names)[col].values

        print("  Загрузка завершена.")
        return self.adata

    def print_summary(self):
        """Выводит краткую статистику датасета."""
        if self.adata is None:
            print("Сначала вызовите .load()")
            return

        cond = self.adata.obs[CONDITION_COL]
        print(f"\n--- Датасет GSE138852 ---")
        print(f"Всего клеток: {self.adata.n_obs}")
        print(f"Всего генов:  {self.adata.n_vars}")
        print(f"С болезнью Альцгеймера: {(cond == 'AD').sum()}")
        print(f"Здоровые:               {(cond == 'ct').sum()}")
        print("\nРаспределение по типам клеток:")
        for ct, n in self.adata.obs[CELL_TYPE_COL].value_counts().items():
            print(f"  {ct:20s}: {n}")
