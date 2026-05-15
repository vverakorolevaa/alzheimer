import os
import requests
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from config import RESULTS_FOLDER


class EnrichmentAnalyzer:
    """
    Анализ обогащения биологических путей через Enrichr API.

    После того как нашли DEG-гены, непонятно — что они делают?
    Enrichr сопоставляет список генов с базами знаний (GO, KEGG)
    и находит биологические процессы, в которых эти гены участвуют
    чаще, чем ожидалось бы случайно.

    API: https://maayanlab.cloud/Enrichr
    """

    BASE_URL = 'https://maayanlab.cloud/Enrichr'

    def __init__(self):
        os.makedirs(RESULTS_FOLDER, exist_ok=True)

    def _upload(self, genes):
        """POST: загружаем список генов, получаем user_list_id."""
        resp = requests.post(
            f'{self.BASE_URL}/addList',
            files={'list': (None, '\n'.join(genes)),
                   'description': (None, 'AD_DEGs')},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()['userListId']

    def _query(self, user_list_id, library):
        """GET: запрашиваем результаты для одной библиотеки."""
        resp = requests.get(
            f'{self.BASE_URL}/enrich',
            params={'userListId': user_list_id, 'backgroundType': library},
            timeout=30,
        )
        if resp.status_code != 200:
            return pd.DataFrame()
        raw = resp.json().get(library, [])
        rows = [{'term': r[1], 'pvalue': r[2], 'odds_ratio': r[3]} for r in raw[:20]]
        return pd.DataFrame(rows)

    def run(self, gene_list, cell_type='all'):
        """
        Основной метод.
        Запускает обогащение по GO (биологические процессы) и KEGG (пути).
        """
        if len(gene_list) < 5:
            print(f'  Слишком мало генов ({len(gene_list)}), пропуск.')
            return {}

        print(f'  Отправляю {len(gene_list)} генов в Enrichr...')
        try:
            uid = self._upload(gene_list)
        except Exception as e:
            print(f'  Ошибка связи с Enrichr: {e}')
            return {}

        libraries = {
            'GO_Biological_Process_2023': 'GO — биологические процессы',
            'KEGG_2021_Human':            'KEGG — метаболические пути',
        }

        results = {}
        for lib, label in libraries.items():
            print(f'  Запрашиваю {label}...')
            try:
                df = self._query(uid, lib)
            except Exception:
                continue
            if df.empty:
                continue
            results[lib] = df
            csv_path = os.path.join(RESULTS_FOLDER, f'enrichment_{cell_type}_{lib}.csv')
            df.to_csv(csv_path, index=False)

        if 'GO_Biological_Process_2023' in results:
            self._barplot(
                results['GO_Biological_Process_2023'],
                title=f'Топ биологических процессов — {cell_type}',
                filename=f'enrichment_{cell_type}_GO.png',
            )

        return results

    def _barplot(self, df, title, filename):
        df = df.head(15).copy()
        df['-log10p'] = -np.log10(df['pvalue'].clip(lower=1e-300))
        df = df.sort_values('-log10p')
        df['term_short'] = df['term'].str[:55]

        fig, ax = plt.subplots(figsize=(10, 7))
        ax.barh(df['term_short'], df['-log10p'], color='steelblue', alpha=0.85)
        ax.axvline(-np.log10(0.05), color='red', ls='--', lw=1, label='p=0.05')
        ax.set_xlabel('−log₁₀(p-value)')
        ax.set_title(title, fontweight='bold')
        ax.legend(fontsize=9)

        path = os.path.join(RESULTS_FOLDER, filename)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f'  Сохранён: {path}')
