"""
Загрузка GSE63060 (кровь, AddNeuroMed): экспрессия генов (образцы × гены)
и метка стадии каждого образца (CTL / MCI / AD).

Разбирает series matrix (зонды × образцы + характеристики образцов) и
аннотацию платформы GPL6947 (зонд → ген), сворачивает зонды в гены
(на ген — зонд с максимальной дисперсией) и кэширует результат в CSV.
"""

import io
import gzip
import os
import numpy as np
import pandas as pd
import config


# ── классификация значения характеристики образца в стадию ──────────────
def _classify_stage(value):
    """'status: AD' / 'AD' / 'control' → 'AD' / 'CTL' / 'MCI' или None."""
    v = value.split(":", 1)[1] if ":" in value else value
    t = v.strip().upper()
    if not t:
        return None
    if "MCI" in t:
        return "MCI"
    if t == "AD" or "ALZH" in t:
        return "AD"
    if (t in ("CTL", "CN", "HC", "NL", "C")
            or "CONTROL" in t or "NORMAL" in t or "HEALTHY" in t):
        return "CTL"
    return None


def _split_tsv(line):
    return [c.strip().strip('"') for c in line.split("\t")]


def _parse_series_matrix(path):
    """→ (expr_probe_df [зонд × GSM], {GSM: стадия}, список сырых значений метки)."""
    sample_ids = None
    char_rows, extra_rows, table_lines = [], [], []
    in_table = False
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if in_table:
                if line.startswith("!series_matrix_table_end"):
                    in_table = False
                elif line:
                    table_lines.append(line)
                continue
            if line.startswith("!series_matrix_table_begin"):
                in_table = True
            elif line.startswith("!Sample_geo_accession"):
                sample_ids = _split_tsv(line)[1:]
            elif line.startswith("!Sample_characteristics_ch1"):
                char_rows.append(_split_tsv(line)[1:])
            elif (line.startswith("!Sample_title")
                  or line.startswith("!Sample_source_name_ch1")
                  or line.startswith("!Sample_description")):
                extra_rows.append(_split_tsv(line)[1:])

    if sample_ids is None or not table_lines:
        raise RuntimeError("Не удалось разобрать series matrix (нет образцов/таблицы).")

    expr = pd.read_csv(io.StringIO("\n".join(table_lines)), sep="\t", index_col=0)
    expr.columns = [str(c).strip().strip('"') for c in expr.columns]
    expr = expr.loc[:, [c for c in expr.columns if c and not c.startswith("Unnamed")]]
    expr.index = [str(i).strip().strip('"') for i in expr.index]

    # строка-метка — та, где значения раскладываются минимум в 2 разные стадии
    best_row, best_hits, raw_vals = None, -1, []
    for row in char_rows + extra_rows:
        stages = [_classify_stage(v) for v in row]
        hits = sum(s is not None for s in stages)
        if hits > best_hits and len({s for s in stages if s}) >= 2:
            best_hits, best_row, raw_vals = hits, row, row
    if best_row is None:
        raise RuntimeError("Не нашёл характеристику с метками CTL/MCI/AD.")

    gsm_to_stage = {gsm: _classify_stage(v)
                    for gsm, v in zip(sample_ids, best_row)
                    if _classify_stage(v)}
    return expr, gsm_to_stage, sorted(set(raw_vals))


def _load_probe_to_symbol(path):
    """GPL6947.annot.gz → {probe_id: gene_symbol}."""
    header, rows, in_table = None, [], False
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("!platform_table_begin"):
                in_table = True
                continue
            if line.startswith("!platform_table_end"):
                break
            if in_table:
                parts = line.split("\t")
                if header is None:
                    header = [h.strip() for h in parts]
                else:
                    rows.append(parts)
    if header is None:
        raise RuntimeError("Не удалось разобрать аннотацию GPL6947.")
    ann = pd.DataFrame(rows, columns=header)
    id_col = "ID" if "ID" in ann.columns else ann.columns[0]
    sym_col = next((c for c in ann.columns if "symbol" in c.lower()), None)
    if sym_col is None:
        raise RuntimeError(f"Нет колонки символа гена среди {list(ann.columns)}")
    ann[id_col] = ann[id_col].astype(str).str.strip()
    ann[sym_col] = ann[sym_col].astype(str).str.strip()
    return dict(zip(ann[id_col], ann[sym_col]))


class DataLoader:
    """Грузит GSE63060: экспрессия (образцы × гены) + стадия (CTL/MCI/AD)."""

    def load(self, force=False):
        if (not force and os.path.exists(config.EXPR_FILE)
                and os.path.exists(config.LABELS_FILE)):
            expr = pd.read_csv(config.EXPR_FILE, index_col=0)
            labels = pd.read_csv(config.LABELS_FILE, index_col=0)["stage"]
            self.expr, self.labels = expr, labels
            print(f"Загружено из кэша: {expr.shape[0]} образцов × {expr.shape[1]} генов")
            return expr, labels

        if not os.path.exists(config.SERIES_MATRIX_GZ):
            raise FileNotFoundError("Нет данных. Запустите: python cli.py download")

        print("Разбираю series matrix…")
        expr_probe, gsm_to_stage, raw_vals = _parse_series_matrix(config.SERIES_MATRIX_GZ)
        print(f"  зондов: {expr_probe.shape[0]}, образцов в матрице: {expr_probe.shape[1]}")
        print(f"  сырые значения метки: {raw_vals}")

        print("Аннотирую зонды → гены (GPL6947)…")
        probe2sym = _load_probe_to_symbol(config.GPL_ANNOT_GZ)

        expr_probe = expr_probe.apply(pd.to_numeric, errors="coerce").dropna(how="all")
        syms = pd.Series([probe2sym.get(p, "") for p in expr_probe.index],
                         index=expr_probe.index)
        valid = syms.ne("") & syms.notna() & (syms.str.upper() != "NAN")
        expr_probe, syms = expr_probe[valid], syms[valid]

        # для дублирующихся символов берём зонд с максимальной дисперсией
        pvar = expr_probe.var(axis=1)
        pick = (pd.DataFrame({"sym": syms.values, "var": pvar.values},
                             index=expr_probe.index)
                .sort_values("var", ascending=False)
                .groupby("sym").head(1))
        expr_genes = expr_probe.loc[pick.index]
        expr_genes.index = pick["sym"].values

        # образцы × гены, только образцы с известной стадией
        expr = expr_genes.T
        keep = [s for s in expr.index if s in gsm_to_stage]
        expr = expr.loc[keep]
        labels = pd.Series([gsm_to_stage[s] for s in keep], index=keep, name="stage")

        os.makedirs(config.DATA_DIR, exist_ok=True)
        expr.to_csv(config.EXPR_FILE)
        labels.to_frame().to_csv(config.LABELS_FILE)
        self.expr, self.labels = expr, labels
        print(f"  итог: {expr.shape[0]} образцов × {expr.shape[1]} генов")
        return expr, labels

    def print_summary(self):
        from config import STAGE_RU
        print(f"\n--- {config.GEO_ACCESSION} (кровь, AddNeuroMed) ---")
        print(f"Образцов: {len(self.labels)}, генов: {self.expr.shape[1]}")
        for s in config.STAGES:
            print(f"  {STAGE_RU.get(s, s):22s}: {int((self.labels == s).sum())}")


if __name__ == "__main__":
    dl = DataLoader()
    dl.load()
    dl.print_summary()
