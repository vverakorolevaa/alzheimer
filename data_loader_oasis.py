import os
import numpy as np
import pandas as pd
from config import (
    OASIS_MRI_FILE, OASIS_CLINICAL_FILE,
    MRI_KEY_ROIS, CLINICAL_FEATURES, DX_LABELS,
)


class OASISLoader:
    """
    Загружает и объединяет данные OASIS-3:
      mri_features.csv  — FreeSurfer ROI (объёмы + толщина коры)
      clinical.csv      — возраст, MMSE, CDR, APOE4, диагноз

    Каждая строка = один визит одного пациента.
    subject_id используется для donor-level split (чтобы один пациент
    не попал одновременно в train и test).
    """

    def __init__(self, mri_path=OASIS_MRI_FILE, clin_path=OASIS_CLINICAL_FILE):
        self.mri_path  = mri_path
        self.clin_path = clin_path
        self.df = None

    def load(self):
        for path in (self.mri_path, self.clin_path):
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"\nФайл не найден: {path}\n"
                    "Сначала сгенерируйте тестовые данные:\n"
                    "  python cli.py generate-synthetic\n"
                    "или поместите файлы OASIS-3 в data/oasis/"
                )

        mri  = pd.read_csv(self.mri_path)
        clin = pd.read_csv(self.clin_path)

        self.df = pd.merge(mri, clin, on=["subject_id", "session_id"], how="inner")
        self.df = self.df.dropna(subset=["diagnosis"])
        self.df["diagnosis"] = self.df["diagnosis"].astype(int)

        n_subjects = self.df["subject_id"].nunique()
        print(f"Загружено: {len(self.df)} визитов, {n_subjects} пациентов")
        return self.df

    def get_feature_matrices(self):
        """Возвращает (X_mri, X_clin, y, groups, mri_cols, clin_cols)."""
        if self.df is None:
            self.load()

        mri_cols  = [c for c in MRI_KEY_ROIS      if c in self.df.columns]
        clin_cols = [c for c in CLINICAL_FEATURES if c in self.df.columns]

        X_mri  = self.df[mri_cols].values.astype(np.float32)
        X_clin = self.df[clin_cols].values.astype(np.float32)
        y      = self.df["diagnosis"].values
        groups = self.df["subject_id"].values

        return X_mri, X_clin, y, groups, mri_cols, clin_cols

    def print_summary(self):
        if self.df is None:
            return
        dx_map = {0: "CN  (норма)", 1: "MCI (лёгкие нарушения)", 2: "AD  (Альцгеймер)"}
        print(f"\n--- Датасет OASIS-3 ---")
        print(f"Визитов: {len(self.df)}   Пациентов: {self.df['subject_id'].nunique()}")
        print("\nРаспределение диагнозов:")
        for dx, n in self.df["diagnosis"].value_counts().sort_index().items():
            print(f"  {dx_map.get(int(dx), dx):30s}: {n}")
