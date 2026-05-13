import scanpy as sc


class Preprocessor:
    """
    Предобработка данных РНК-секвенирования.

    Шаги:
    1. Фильтрация "плохих" клеток (слишком мало генов — брак)
    2. Нормализация: все клетки приводятся к одному масштабу
    3. Логарифмирование: log(x+1) — убирает перекос распределения
    """

    def __init__(self, min_genes=200, min_cells=3):
        self.min_genes  = min_genes
        self.min_cells  = min_cells

    def preprocess(self, adata):
        print("Предобработка данных...")
        print(f"  До: {adata.n_obs} клеток, {adata.n_vars} генов")

        sc.pp.filter_cells(adata, min_genes=self.min_genes)
        sc.pp.filter_genes(adata, min_cells=self.min_cells)
        print(f"  После фильтрации: {adata.n_obs} клеток, {adata.n_vars} генов")

        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)
        print("  Нормализация и log1p — выполнено.")

        return adata
