"""
Загрузчик данных OASIS (Kaggle) — реальный датасет без ограничений доступа.

Источник: kaggle.com — OASIS Alzheimer's Detection
Файлы:
  oasis_longitudinal.csv   — 150 пациентов, 373 визита (Group: Nondemented/Demented/Converted)
  oasis_cross-sectional.csv — 436 пациентов, 1 визит (диагноз из CDR)

МРТ-признаки (3):  eTIV, nWBV, ASF
Клин. признаки (6): возраст, пол, образование, SES, MMSE, CDR
"""

import os
import shutil
import numpy as np
import pandas as pd
from config import (
    KAGGLE_LONG_FILE, KAGGLE_CROSS_FILE,
    KAGGLE_MRI_COLS, KAGGLE_CLIN_COLS, DX_LABELS,
)


def _cdr_to_dx(cdr):
    if cdr == 0:
        return 0   # CN
    elif cdr == 0.5:
        return 1   # MCI
    else:
        return 2   # AD


def _load_longitudinal(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    group_map = {"Nondemented": 0, "Converted": 1, "Demented": 2}
    df["diagnosis"] = df["Group"].map(group_map)
    df = df.dropna(subset=["diagnosis"])

    df = df.rename(columns={
        "Subject ID": "subject_id",
        "MRI ID":     "session_id",
        "M/F":        "sex_raw",
        "Age":        "age",
        "EDUC":       "educ",
        "SES":        "ses",
        "MMSE":       "mmse",
        "CDR":        "cdr",
        "eTIV":       "etiv",
        "nWBV":       "nwbv",
        "ASF":        "asf",
    })
    df["sex"] = (df["sex_raw"] == "F").astype(int)
    return df


def _load_cross_sectional(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    df = df.rename(columns={
        "ID":    "session_id",
        "M/F":   "sex_raw",
        "Age":   "age",
        "Educ":  "educ",
        "SES":   "ses",
        "MMSE":  "mmse",
        "CDR":   "cdr",
        "eTIV":  "etiv",
        "nWBV":  "nwbv",
        "ASF":   "asf",
    })

    # CDR пустой у молодых участников (<60) — не деменция
    df = df[df["age"] >= 60].copy()
    df = df.dropna(subset=["cdr"])
    df["diagnosis"] = df["cdr"].apply(_cdr_to_dx)

    # subject_id из session_id: OAS1_0001_MR1 → OAS1_0001
    df["subject_id"] = df["session_id"].str.rsplit("_", n=1).str[0]
    df["sex"] = (df["sex_raw"] == "F").astype(int)
    return df


class KaggleOASISLoader:
    """
    Загружает и объединяет оба OASIS-файла в единый датафрейм.
    Использует donor-level grouping для правильного split.
    """

    NEEDED_COLS = ["subject_id", "session_id", "age", "sex", "educ",
                   "ses", "mmse", "cdr", "etiv", "nwbv", "asf", "diagnosis"]

    def __init__(self,
                 long_path=KAGGLE_LONG_FILE,
                 cross_path=KAGGLE_CROSS_FILE):
        self.long_path  = long_path
        self.cross_path = cross_path
        self.df = None

    def copy_from_downloads(self, src_long, src_cross):
        """Копирует файлы из Downloads в data/kaggle/."""
        os.makedirs(os.path.dirname(self.long_path), exist_ok=True)
        shutil.copy2(src_long,  self.long_path)
        shutil.copy2(src_cross, self.cross_path)
        print(f"  Скопировано: {self.long_path}")
        print(f"  Скопировано: {self.cross_path}")

    def load(self):
        for path in (self.long_path, self.cross_path):
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"\nФайл не найден: {path}\n"
                    "Запустите: python cli.py setup-kaggle"
                )

        long  = _load_longitudinal(self.long_path)
        cross = _load_cross_sectional(self.cross_path)

        # Объединяем, берём только нужные колонки
        frames = []
        for df in (long, cross):
            available = [c for c in self.NEEDED_COLS if c in df.columns]
            frames.append(df[available])
        combined = pd.concat(frames, ignore_index=True)

        # Заполняем пропуски медианой по числовым признакам
        for col in ["educ", "ses", "mmse"]:
            if col in combined.columns:
                combined[col] = combined[col].fillna(combined[col].median())

        combined = combined.dropna(subset=["etiv", "nwbv", "asf", "diagnosis"])
        combined["diagnosis"] = combined["diagnosis"].astype(int)

        self.df = combined
        print(f"Загружено: {len(self.df)} визитов, "
              f"{self.df['subject_id'].nunique()} пациентов")
        return self.df

    def get_feature_matrices(self):
        """Возвращает (X_mri, X_clin, y, groups, mri_cols, clin_cols)."""
        if self.df is None:
            self.load()

        mri_cols  = [c for c in KAGGLE_MRI_COLS  if c in self.df.columns]
        clin_cols = [c for c in KAGGLE_CLIN_COLS if c in self.df.columns]

        X_mri  = self.df[mri_cols].values.astype(np.float32)
        X_clin = self.df[clin_cols].values.astype(np.float32)
        y      = self.df["diagnosis"].values
        groups = self.df["subject_id"].values

        return X_mri, X_clin, y, groups, mri_cols, clin_cols

    def print_summary(self):
        if self.df is None:
            return
        dx_map = {0: "CN  (норма)", 1: "MCI (лёгкие нарушения)", 2: "AD  (Альцгеймер)"}
        print(f"\n--- Датасет OASIS (Kaggle) ---")
        print(f"Визитов:   {len(self.df)}")
        print(f"Пациентов: {self.df['subject_id'].nunique()}")
        print(f"\nМРТ-признаки:      {KAGGLE_MRI_COLS}")
        print(f"Клин. признаки:    {KAGGLE_CLIN_COLS}")
        print("\nРаспределение диагнозов:")
        for dx, n in self.df["diagnosis"].value_counts().sort_index().items():
            print(f"  {dx_map.get(int(dx), dx):30s}: {n}")
