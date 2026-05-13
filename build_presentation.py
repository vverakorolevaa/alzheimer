"""
Генерация PowerPoint-отчёта по результатам анализа.
Запуск: python cli.py report   (или напрямую: python build_presentation.py)
"""

import os
import glob
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from config import RESULTS_FOLDER

TITLE_COLOR = RGBColor(0x2C, 0x3E, 0x50)
ACCENT      = RGBColor(0xE7, 0x4C, 0x3C)


def _blank_slide(prs):
    layout = prs.slide_layouts[6]   # пустой макет
    return prs.slides.add_slide(layout)


def _add_title(slide, text, top=Inches(0.3), size=Pt(24)):
    txb = slide.shapes.add_textbox(Inches(0.5), top, Inches(9), Inches(0.7))
    tf  = txb.text_frame
    tf.text = text
    p = tf.paragraphs[0]
    p.runs[0].font.size  = size
    p.runs[0].font.bold  = True
    p.runs[0].font.color.rgb = TITLE_COLOR


def _add_image(slide, path, left=Inches(0.5), top=Inches(1.1),
               width=Inches(9), height=Inches(5.5)):
    if os.path.exists(path):
        slide.shapes.add_picture(path, left, top, width, height)


def _add_text(slide, text, top=Inches(1.1), size=Pt(13)):
    txb = slide.shapes.add_textbox(Inches(0.5), top, Inches(9), Inches(5))
    tf  = txb.text_frame
    tf.word_wrap = True
    tf.text = text
    tf.paragraphs[0].runs[0].font.size = size


def build(output="results/report.pptx"):
    prs = Presentation()
    prs.slide_width  = Inches(10)
    prs.slide_height = Inches(7)

    # ── Титульный слайд ───────────────────────────────────────────────
    slide = _blank_slide(prs)
    _add_title(slide,
               "Анализ болезни Альцгеймера\nMультимодальный ансамблевый классификатор",
               top=Inches(2.5), size=Pt(28))
    _add_text(slide, "Данные: GSE138852 (Mathys et al., Nature 2019)\n"
                     "Метод: DEG + Gene2Vec + Ensemble (3 головы)",
              top=Inches(4.2), size=Pt(16))

    # ── DEG по типам клеток ───────────────────────────────────────────
    slide = _blank_slide(prs)
    _add_title(slide, "Дифференциально экспрессированные гены по типам клеток")
    _add_image(slide, f"{RESULTS_FOLDER}/deg_by_cell_type.png")

    # ── Volcano plots ─────────────────────────────────────────────────
    for path in sorted(glob.glob(f"{RESULTS_FOLDER}/volcano_*.png"))[:3]:
        ct = os.path.basename(path).replace("volcano_", "").replace(".png", "")
        slide = _blank_slide(prs)
        _add_title(slide, f"Volcano plot — {ct}")
        _add_image(slide, path)

    # ── Heatmaps ──────────────────────────────────────────────────────
    for path in sorted(glob.glob(f"{RESULTS_FOLDER}/heatmap_*.png"))[:2]:
        ct = os.path.basename(path).replace("heatmap_", "").replace(".png", "")
        slide = _blank_slide(prs)
        _add_title(slide, f"Тепловая карта топ-DEG — {ct}")
        _add_image(slide, path)

    # ── UMAP ──────────────────────────────────────────────────────────
    umap_path = f"{RESULTS_FOLDER}/umap.png"
    if os.path.exists(umap_path):
        slide = _blank_slide(prs)
        _add_title(slide, "UMAP — пространство клеток")
        _add_image(slide, umap_path)

    # ── Ансамблевые метрики ───────────────────────────────────────────
    ens_path = f"{RESULTS_FOLDER}/ensemble_metrics.png"
    if os.path.exists(ens_path):
        slide = _blank_slide(prs)
        _add_title(slide, "Метрики мультимодального ансамблевого классификатора")
        _add_image(slide, ens_path)

    # ── Enrichment ────────────────────────────────────────────────────
    for path in sorted(glob.glob(f"{RESULTS_FOLDER}/enrichment_*_GO.png"))[:1]:
        slide = _blank_slide(prs)
        _add_title(slide, "Анализ обогащения GO — биологические пути")
        _add_image(slide, path)

    # ── Заключение ────────────────────────────────────────────────────
    slide = _blank_slide(prs)
    _add_title(slide, "Выводы", size=Pt(26))
    _add_text(slide,
              "1. Выявлены DEG-гены в каждом типе клеток мозга (Mann-Whitney + BH FDR)\n\n"
              "2. Мультимодальный ансамбль из трёх голов:\n"
              "   • Head 1 — транскриптомные признаки (DEG)\n"
              "   • Head 2 — клеточный состав образца (вторая модальность)\n"
              "   • Head 3 — предобученные Gene2Vec эмбеддинги (Du et al., 2019)\n\n"
              "3. Ансамбль превышает качество каждой отдельной головы\n\n"
              "4. Enrichr: идентифицированы ключевые биологические пути (GO, KEGG)",
              top=Inches(1.2), size=Pt(14))

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    prs.save(output)
    print(f"Отчёт сохранён: {output}")


def main():
    print("=" * 60)
    print("  Генерация PowerPoint-отчёта")
    print("=" * 60)
    build()


if __name__ == "__main__":
    main()
