"""
Лёгкая предобработка табличной экспрессии микрочипа (GSE63060):
  1. при необходимости log2 (если данные в линейном масштабе);
  2. заполнение пропусков средним по гену;
  3. удаление генов с нулевой дисперсией.
Масштабирование (StandardScaler) делается ПОЗЖЕ и строго внутри фолдов
кросс-валидации — чтобы не было утечки информации из теста в трейн.
"""

import numpy as np
import pandas as pd


class Preprocessor:
    def preprocess(self, expr):
        print("Предобработка…")
        expr = expr.apply(pd.to_numeric, errors="coerce")

        finite_max = np.nanmax(expr.values)
        if finite_max > 100:
            print(f"  значения линейные (max={finite_max:.0f}) → log2(x+1)")
            expr = np.log2(expr.clip(lower=0) + 1)
        else:
            print(f"  данные уже в лог-масштабе (max={finite_max:.2f})")

        if expr.isna().any().any():
            expr = expr.fillna(expr.mean(axis=0))

        nz = expr.var(axis=0) > 0
        expr = expr.loc[:, nz]
        print(f"  итог: {expr.shape[0]} образцов × {expr.shape[1]} генов")
        return expr
