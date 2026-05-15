import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from config import (
    CONDITION_COL, CELL_TYPE_COL,
    DISEASE_LABEL, CONTROL_LABEL,
    PVALUE_THRESHOLD, LOG2FC_THRESHOLD,
)


class GeneAnalyzer:
    """
    Ищет дифференциально экспрессированные гены (DEG) —
    гены, которые значимо изменены у больных по сравнению со здоровыми.

    Методы: критерий Манна-Уитни и FDR-коррекция
    по Бенджамини-Хохбергу (контроль доли ложных открытий).

    Анализ проводится отдельно для каждого типа клеток мозга,
    чтобы увидеть, какие именно клетки затронуты болезнью ( single-cell RNA sequencing)
    """

    def __init__(self, adata):
        self.adata   = adata
        self.results = {}   

    def analyze_cell_type(self, cell_type):
        """DEG-анализ для одного типа клеток."""
        mask   = self.adata.obs[CELL_TYPE_COL] == cell_type
        subset = self.adata[mask]

        ad_mask = subset.obs[CONDITION_COL] == DISEASE_LABEL
        ct_mask = subset.obs[CONDITION_COL] == CONTROL_LABEL

        ad_expr = subset[ad_mask].X
        ct_expr = subset[ct_mask].X

        if ad_expr.shape[0] < 5 or ct_expr.shape[0] < 5:
            return None

        n_genes  = subset.n_vars
        pvals    = np.zeros(n_genes)

        for i in range(n_genes):
            g_ad = np.asarray(ad_expr[:, i]).flatten()
            g_ct = np.asarray(ct_expr[:, i]).flatten()
            _, pvals[i] = stats.mannwhitneyu(g_ad, g_ct, alternative='two-sided')

        _, padj, _, _ = multipletests(pvals, method='fdr_bh')

        mean_ad  = np.asarray(ad_expr.mean(axis=0)).flatten()
        mean_ct  = np.asarray(ct_expr.mean(axis=0)).flatten()
        log2fc   = np.log2(mean_ad + 1) - np.log2(mean_ct + 1)

        df = pd.DataFrame({
            'gene':           subset.var_names,
            'log2FoldChange': log2fc,
            'pvalue':         pvals,
            'padj':           padj,
        })

        df['significant'] = (
            (df['padj'] < PVALUE_THRESHOLD) &
            (df['log2FoldChange'].abs() > LOG2FC_THRESHOLD)
        )
        df['direction'] = 'not_sig'
        df.loc[df['significant'] & (df['log2FoldChange'] > 0), 'direction'] = 'up'
        df.loc[df['significant'] & (df['log2FoldChange'] < 0), 'direction'] = 'down'

        return df.sort_values('padj').reset_index(drop=True)

    def run_all(self):
        """Запускает анализ для всех типов клеток."""
        cell_types = self.adata.obs[CELL_TYPE_COL].unique()
        print(f"\nАнализирую {len(cell_types)} типов клеток...")

        for ct in cell_types:
            print(f"  {ct}...", end=' ')
            res = self.analyze_cell_type(ct)
            if res is not None:
                n = res['significant'].sum()
                print(f"{n} DEG")
                self.results[ct] = res
            else:
                print("пропуск (мало клеток)")

        total = sum(r['significant'].sum() for r in self.results.values())
        print(f"\nИтого DEG по всем типам клеток: {total}")
        return self.results

    def get_top_degs(self, cell_type, n=20):
        """Топ-N значимых генов для указанного типа клеток."""
        df = self.results.get(cell_type)
        if df is None:
            return pd.DataFrame()
        return df[df['significant']].head(n)

    def summary_table(self):
        """Таблица: сколько DEG в каждом типе клеток."""
        rows = []
        for ct, df in self.results.items():
            sig = df[df['significant']]
            rows.append({
                'Тип клеток': ct,
                'Всего DEG':  len(sig),
                'Активнее у больных (up)':   (sig['direction'] == 'up').sum(),
                'Ниже у больных (down)': (sig['direction'] == 'down').sum(),
            })
        return pd.DataFrame(rows).sort_values('Всего DEG', ascending=False)
