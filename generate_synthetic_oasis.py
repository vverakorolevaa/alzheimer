"""
Генерирует синтетические данные в формате OASIS-3 для тестирования пайплайна.
Значения основаны на реальных распределениях из публикаций по OASIS-3 / ADNI.

Запуск: python cli.py generate-synthetic
        или напрямую: python generate_synthetic_oasis.py

Создаёт:
  data/oasis/mri_features.csv   — FreeSurfer ROI (объёмы мм³, толщина мм)
  data/oasis/clinical.csv        — возраст, MMSE, CDR, APOE4, диагноз
"""

import os
import numpy as np
import pandas as pd
from config import OASIS_MRI_FILE, OASIS_CLINICAL_FILE

SEED = 42

# (CN_mean, CN_std, MCI_mean, MCI_std, AD_mean, AD_std)
ROI_PARAMS = {
    "lh_hippocampus":                  (3800, 380,  3200, 420,  2550, 480),
    "rh_hippocampus":                  (3750, 370,  3150, 410,  2500, 470),
    "lh_amygdala":                     (1650, 200,  1420, 220,  1180, 250),
    "rh_amygdala":                     (1680, 210,  1450, 225,  1200, 260),
    "lh_entorhinal_thickness":         (3.60, 0.30, 3.15, 0.35, 2.65, 0.40),
    "rh_entorhinal_thickness":         (3.50, 0.28, 3.05, 0.33, 2.55, 0.38),
    "lh_parahippocampal_thickness":    (2.80, 0.25, 2.55, 0.28, 2.25, 0.32),
    "rh_parahippocampal_thickness":    (2.75, 0.24, 2.50, 0.27, 2.20, 0.31),
    "lh_fusiform_thickness":           (2.90, 0.22, 2.70, 0.25, 2.45, 0.30),
    "rh_fusiform_thickness":           (2.85, 0.21, 2.65, 0.24, 2.40, 0.29),
    "lh_inferior_temporal_thickness":  (2.75, 0.20, 2.55, 0.23, 2.30, 0.27),
    "rh_inferior_temporal_thickness":  (2.70, 0.19, 2.50, 0.22, 2.25, 0.26),
    "lh_middle_temporal_thickness":    (2.65, 0.19, 2.48, 0.22, 2.25, 0.26),
    "rh_middle_temporal_thickness":    (2.60, 0.18, 2.43, 0.21, 2.20, 0.25),
    "lh_precuneus_thickness":          (2.55, 0.20, 2.40, 0.23, 2.20, 0.27),
    "rh_precuneus_thickness":          (2.50, 0.19, 2.35, 0.22, 2.15, 0.26),
    "left_lateral_ventricle":          (7500,  2200, 10500, 3000, 15000, 4000),
    "right_lateral_ventricle":         (7200,  2100, 10000, 2900, 14500, 3900),
    "third_ventricle":                 (800,   200,  1100,  280,  1600,  380),
    "total_brain_vol":                 (1100000, 100000, 1040000, 110000, 960000, 120000),
}


def generate(n_cn=120, n_mci=100, n_ad=80):
    rng = np.random.default_rng(SEED)
    records_mri, records_clin = [], []
    subject_id = 1

    for dx, n in [(0, n_cn), (1, n_mci), (2, n_ad)]:
        for _ in range(n):
            sid  = f"OAS3{subject_id:04d}"
            ssid = f"{sid}_ses-d0"
            subject_id += 1

            # МРТ-признаки
            mri_row = {"subject_id": sid, "session_id": ssid}
            for col, params in ROI_PARAMS.items():
                mean = params[dx * 2]
                std  = params[dx * 2 + 1]
                mri_row[col] = round(float(max(0.1, rng.normal(mean, std))), 4)
            records_mri.append(mri_row)

            # Клинические данные
            age   = float(np.clip(rng.normal(72, 8), 55, 92))
            sex   = int(rng.integers(0, 2))
            apoe4 = int(rng.random() < [0.20, 0.35, 0.50][dx])
            edu   = float(np.clip(rng.normal(14, 3), 8, 22))

            if dx == 0:
                mmse = float(np.clip(rng.normal(28.5, 1.5), 24, 30))
                cdr  = float(rng.choice([0.0, 0.5], p=[0.85, 0.15]))
            elif dx == 1:
                mmse = float(np.clip(rng.normal(24.5, 3.0), 18, 28))
                cdr  = float(rng.choice([0.5, 1.0], p=[0.75, 0.25]))
            else:
                mmse = float(np.clip(rng.normal(17.0, 5.0), 8, 24))
                cdr  = float(rng.choice([1.0, 2.0, 3.0], p=[0.50, 0.35, 0.15]))

            records_clin.append({
                "subject_id": sid, "session_id": ssid,
                "age": round(age, 1), "sex": sex, "apoe4": apoe4,
                "education_years": round(edu, 1),
                "mmse": round(mmse, 1), "cdr": cdr,
                "diagnosis": dx,
            })

    os.makedirs(os.path.dirname(OASIS_MRI_FILE), exist_ok=True)
    pd.DataFrame(records_mri).to_csv(OASIS_MRI_FILE, index=False)
    pd.DataFrame(records_clin).to_csv(OASIS_CLINICAL_FILE, index=False)

    print("Синтетические данные OASIS-3 сохранены:")
    print(f"  {OASIS_MRI_FILE}   ({n_cn + n_mci + n_ad} строк)")
    print(f"  {OASIS_CLINICAL_FILE}  ({n_cn + n_mci + n_ad} строк)")
    print(f"  Диагнозы: CN={n_cn}, MCI={n_mci}, AD={n_ad}")


if __name__ == "__main__":
    generate()
