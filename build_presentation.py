"""
Генерация PowerPoint-отчёта по результатам мультимодального анализа.
Запуск: python cli.py report   (или напрямую: python build_presentation.py)
"""

import os
import glob
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from config import RESULTS_FOLDER

TITLE_COLOR  = RGBColor(0x2C, 0x3E, 0x50)
ACCENT       = RGBColor(0xE7, 0x4C, 0x3C)
SUBTITLE_CLR = RGBColor(0x7F, 0x8C, 0x8D)
GREEN        = RGBColor(0x27, 0xAE, 0x60)
ORANGE       = RGBColor(0xF3, 0x9C, 0x12)


def _slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _title(slide, text, top=Inches(0.3), size=Pt(22), color=TITLE_COLOR, bold=True):
    txb = slide.shapes.add_textbox(Inches(0.5), top, Inches(9), Inches(0.8))
    tf  = txb.text_frame
    tf.text = text
    run = tf.paragraphs[0].runs[0]
    run.font.size  = size
    run.font.bold  = bold
    run.font.color.rgb = color


def _text(slide, text, top=Inches(1.2), size=Pt(13), color=TITLE_COLOR):
    txb = slide.shapes.add_textbox(Inches(0.5), top, Inches(9), Inches(5.2))
    tf  = txb.text_frame
    tf.word_wrap = True
    tf.text = text
    run = tf.paragraphs[0].runs[0]
    run.font.size = size
    run.font.color.rgb = color


def _image(slide, path, left=Inches(0.5), top=Inches(1.1),
           width=Inches(9), height=Inches(5.5)):
    if os.path.exists(path):
        slide.shapes.add_picture(path, left, top, width, height)


def _two_images(slide, path1, path2):
    for path, left in [(path1, Inches(0.3)), (path2, Inches(5.1))]:
        if os.path.exists(path):
            slide.shapes.add_picture(path, left, Inches(1.1),
                                     Inches(4.5), Inches(5.2))


def build(output="results/report.pptx"):
    prs = Presentation()
    prs.slide_width  = Inches(10)
    prs.slide_height = Inches(7)

    # ── 1. Титульный слайд ────────────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "Alzheimer", top=Inches(1.8), size=Pt(36))
    _title(sl, "Мультимодальная ранняя диагностика\nболезни Альцгеймера",
           top=Inches(2.7), size=Pt(24), bold=False)
    _text(sl,
          "Данные: OASIS-3 (МРТ + клинические биомаркеры)\n"
          "Архитектура: двуголовая нейросеть с Gated Fusion\n"
          "Задача: CN / MCI / AD — три класса",
          top=Inches(4.5), size=Pt(14), color=SUBTITLE_CLR)

    # ── 2. Проблема ───────────────────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "Почему важна ранняя диагностика?")
    _text(sl,
          "Болезнь Альцгеймера — нейродегенеративное заболевание, поражающее\n"
          "более 55 млн людей по всему миру (ВОЗ, 2023).\n\n"
          "Ключевая проблема:\n"
          "  • Симптомы появляются спустя 10–20 лет после начала патологии\n"
          "  • На стадии AD нейроны уже необратимо повреждены\n"
          "  • Стадия MCI — «окно возможностей»: вмешательство ещё эффективно\n\n"
          "Цель проекта:\n"
          "  Отличить CN (норма) от MCI и AD на основе неинвазивных данных:\n"
          "  МРТ мозга + стандартные клинические тесты (MMSE, CDR, возраст, APOE4)",
          top=Inches(1.2), size=Pt(13))

    # ── 3. Подход ─────────────────────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "Мультимодальный подход: две головы")
    _text(sl,
          "Модальность 1 — МРТ (FreeSurfer ROI):\n"
          "  • 20 регионов мозга: гиппокамп, энторинальная кора,\n"
          "    миндалина, боковые желудочки...\n"
          "  • Гиппокамп уменьшается на 3–5% в год при MCI\n\n"
          "Модальность 2 — Клинические данные:\n"
          "  • Возраст, пол, образование, ген APOE4\n"
          "  • MMSE (память, ориентация, внимание: 0–30 баллов)\n"
          "  • CDR (Clinical Dementia Rating: 0–3)\n\n"
          "Fusion: Gated Fusion\n"
          "  gate = σ(W·[e_МРТ; e_клиника])\n"
          "  fused = gate·e_МРТ + (1−gate)·e_клиника\n"
          "  → Сеть сама решает, какой модальности доверять",
          top=Inches(1.2), size=Pt(12))

    # ── 4. Данные OASIS-3 ─────────────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "Датасет OASIS-3")
    _text(sl,
          "Open Access Series of Imaging Studies (OASIS-3)\n"
          "  — Knight Alzheimer Disease Research Center, Вашингтонский университет\n\n"
          "  • 1378 участников (>55 лет), продольное наблюдение\n"
          "  • МРТ T1 + FreeSurfer морфометрия\n"
          "  • Когнитивные тесты: MMSE, CDR\n"
          "  • Генотипирование APOE\n\n"
          "Диагнозы:\n"
          "  CN  — когнитивно нормальные\n"
          "  MCI — лёгкие когнитивные нарушения (предстадия AD)\n"
          "  AD  — болезнь Альцгеймера\n\n"
          "Ключевое: МРТ и клиника взяты от ОДНОГО человека на ОДНОМ визите\n"
          "  → нет ошибки несовпадения модальностей",
          top=Inches(1.2), size=Pt(12))

    # ── 5. Биомаркеры CN → MCI → AD ───────────────────────────────────
    sl = _slide(prs)
    _title(sl, "Биомаркеры: нарастание патологии CN → MCI → AD")
    _image(sl, f"{RESULTS_FOLDER}/biomarker_trajectory.png")

    # ── 6. Важность МРТ-регионов ──────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "Какие области мозга наиболее информативны?")
    _image(sl, f"{RESULTS_FOLDER}/roi_importance.png")

    # ── 7. Кривая обучения ────────────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "Обучение нейросети")
    _image(sl, f"{RESULTS_FOLDER}/training_loss.png",
           top=Inches(1.1), height=Inches(4.5))

    # ── 8. ROC-кривые ─────────────────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "ROC-кривые: Fusion превосходит каждую модальность отдельно")
    _image(sl, f"{RESULTS_FOLDER}/multihead_roc.png")

    # ── 9. Матрица ошибок ─────────────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "Матрица ошибок: CN / MCI / AD")
    _image(sl, f"{RESULTS_FOLDER}/confusion_matrix.png",
           left=Inches(1.5), width=Inches(7), height=Inches(5.5))

    # ── 10. Gate-веса ─────────────────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "Gated Fusion: какой модальности доверяет модель?")
    _image(sl, f"{RESULTS_FOLDER}/gate_weights.png",
           left=Inches(1.0), width=Inches(8), height=Inches(5.2))

    # ── 11. UMAP ──────────────────────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "UMAP фьюженных эмбеддингов")
    _image(sl, f"{RESULTS_FOLDER}/fusion_umap.png",
           left=Inches(1.0), width=Inches(8), height=Inches(5.5))

    # ── 12. Выводы ────────────────────────────────────────────────────
    sl = _slide(prs)
    _title(sl, "Выводы", size=Pt(26))
    _text(sl,
          "1. Мультимодальная модель (МРТ + клиника) точнее однородных:\n"
          "   Fusion AUC > MRI-only AUC и Clinical-only AUC\n\n"
          "2. Gated Fusion интерпретируем:\n"
          "   gate-веса показывают, когда модель опирается на МРТ, а когда на клинику\n\n"
          "3. Ранние маркеры AD — гиппокамп и энторинальная кора:\n"
          "   уменьшение объёма видно уже на стадии MCI\n\n"
          "4. Правильный split по пациентам (donor-level) предотвращает\n"
          "   завышение метрик и обеспечивает честную оценку\n\n"
          "5. Следующий шаг: загрузить реальные данные OASIS-3 (oasis-brains.org)\n"
          "   и обучить на ~1378 пациентах вместо синтетических данных",
          top=Inches(1.2), size=Pt(13))

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
