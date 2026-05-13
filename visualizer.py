import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import scanpy as sc
from config import RESULTS_FOLDER, CONDITION_COL, CELL_TYPE_COL, TOP_GENES_COUNT


class Visualizer:
    """
    Строит все графики проекта и сохраняет их в results/.

    Графики:
      volcano_plot()  — какие гены изменились и насколько значимо
      heatmap()       — тепловая карта экспрессии топ-генов
      umap_plot()     — 2D-карта всех клеток
      deg_barplot()   — сколько DEG найдено в каждом типе клеток
    """

    def __init__(self):
        os.makedirs(RESULTS_FOLDER, exist_ok=True)
        plt.rcParams.update({'font.size': 11, 'figure.dpi': 150})

    # ── Volcano plot ──────────────────────────────────────────────────
    def volcano_plot(self, df, cell_type):
        """
        Volcano plot для одного типа клеток.
        Красные точки = гены активнее у больных (up).
        Синие точки   = гены ниже у больных (down).
        """
        df = df.copy()
        df['neg_log10'] = -np.log10(df['padj'].clip(lower=1e-300))

        color_map = {'up': '#E74C3C', 'down': '#3498DB', 'not_sig': '#CCCCCC'}
        colors = df['direction'].map(color_map)

        fig, ax = plt.subplots(figsize=(9, 6))
        ax.scatter(df['log2FoldChange'], df['neg_log10'],
                   c=colors, alpha=0.55, s=12, linewidths=0)

        # Пороговые линии
        ax.axhline(-np.log10(0.05), color='black', lw=0.8, ls='--', alpha=0.6)
        ax.axvline( 1, color='black', lw=0.8, ls='--', alpha=0.6)
        ax.axvline(-1, color='black', lw=0.8, ls='--', alpha=0.6)

        # Подписи топ-10 генов
        top = df[df['significant']].head(10)
        for _, row in top.iterrows():
            ax.annotate(row['gene'],
                        (row['log2FoldChange'], row['neg_log10']),
                        fontsize=7, alpha=0.9,
                        xytext=(3, 3), textcoords='offset points')

        n_up   = (df['direction'] == 'up').sum()
        n_down = (df['direction'] == 'down').sum()
        legend = [
            mpatches.Patch(color='#E74C3C', label=f'↑ Активнее у больных ({n_up})'),
            mpatches.Patch(color='#3498DB', label=f'↓ Ниже у больных ({n_down})'),
            mpatches.Patch(color='#CCCCCC', label='Не значимые'),
        ]
        ax.legend(handles=legend, fontsize=9)
        ax.set_xlabel('log₂ Fold Change (больные / здоровые)')
        ax.set_ylabel('−log₁₀(скорр. p-value)')
        ax.set_title(f'Volcano plot — {cell_type}', fontsize=13, fontweight='bold')

        path = os.path.join(RESULTS_FOLDER, f'volcano_{cell_type}.png')
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f'  Сохранён: {path}')
        return path

    # ── Heatmap ───────────────────────────────────────────────────────
    def heatmap(self, adata, df, cell_type):
        """
        Тепловая карта экспрессии топ-DEG генов.
        Столбцы = клетки (красные = больные, зелёные = здоровые).
        Строки = гены. Цвет = уровень экспрессии.
        """
        mask   = adata.obs[CELL_TYPE_COL] == cell_type
        subset = adata[mask]

        sig_genes = df[df['significant']]['gene'].head(TOP_GENES_COUNT).tolist()
        sig_genes = [g for g in sig_genes if g in subset.var_names]
        if len(sig_genes) < 5:
            print(f'  {cell_type}: слишком мало DEG для heatmap, пропуск.')
            return None

        g_idx  = [list(subset.var_names).index(g) for g in sig_genes]
        expr   = np.asarray(subset.X[:, g_idx]).T  # гены × клетки

        col_colors = pd.Series(
            subset.obs[CONDITION_COL].values,
            index=range(subset.n_obs)
        ).map({'AD': '#E74C3C', 'ct': '#2ECC71'})

        g = sns.clustermap(
            pd.DataFrame(expr, index=sig_genes),
            col_colors=col_colors.values,
            cmap='RdBu_r', figsize=(12, 8),
            yticklabels=True, xticklabels=False,
            dendrogram_ratio=0.1,
        )
        g.fig.suptitle(
            f'Heatmap топ-{len(sig_genes)} DEG — {cell_type}',
            y=1.01, fontsize=12, fontweight='bold'
        )
        # Легенда
        handles = [
            mpatches.Patch(color='#E74C3C', label='Болезнь Альцгеймера'),
            mpatches.Patch(color='#2ECC71', label='Здоровые'),
        ]
        g.ax_heatmap.legend(handles=handles, loc='upper right',
                            bbox_to_anchor=(1.18, 1.1), fontsize=9)

        path = os.path.join(RESULTS_FOLDER, f'heatmap_{cell_type}.png')
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        print(f'  Сохранён: {path}')
        return path

    # ── UMAP ──────────────────────────────────────────────────────────
    def umap_plot(self, adata):
        """
        UMAP — двумерная карта всех клеток.
        Каждая точка = одна клетка. Похожие клетки собираются рядом.
        """
        print('  Строю UMAP...')
        sc.pp.neighbors(adata, n_neighbors=15, n_pcs=30)
        sc.tl.umap(adata)

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        sc.pl.umap(adata, color=CONDITION_COL, ax=axes[0], show=False,
                   title='UMAP — по диагнозу')
        sc.pl.umap(adata, color=CELL_TYPE_COL,  ax=axes[1], show=False,
                   title='UMAP — по типу клеток')

        path = os.path.join(RESULTS_FOLDER, 'umap.png')
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f'  Сохранён: {path}')
        return path

    # ── Bar plot: количество DEG по типам клеток ──────────────────────
    def deg_barplot(self, summary_df):
        """
        Столбчатый график: сколько DEG найдено в каждом типе клеток.
        Показывает, какие клетки больше всего затронуты болезнью.
        """
        df = summary_df.sort_values('Всего DEG', ascending=True)

        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.barh(df['Тип клеток'], df['Всего DEG'],
                       color='steelblue', alpha=0.85)

        # Числа справа от столбцов
        for bar, val in zip(bars, df['Всего DEG']):
            ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height() / 2,
                    str(val), va='center', fontsize=10)

        ax.set_xlabel('Количество DEG')
        ax.set_title('Дифференциально экспрессированные гены по типам клеток',
                     fontweight='bold')
        ax.set_xlim(0, df['Всего DEG'].max() * 1.15)

        path = os.path.join(RESULTS_FOLDER, 'deg_by_cell_type.png')
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f'  Сохранён: {path}')
        return path
