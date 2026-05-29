"""
Генерация PowerPoint-презентации по курсовому проекту:
дифференциальная экспрессия генов при болезни Альцгеймера.

Структура: титул + 8 разделов по критериям защиты.
Запуск: python build_presentation.py   (или: python cli.py report — если добавлено)
Файл сохраняется на Рабочий стол: ~/Desktop/report_genes.pptx
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from config import RESULTS_FOLDER

DARK  = RGBColor(0x1A, 0x25, 0x3A)
BLUE  = RGBColor(0x2E, 0x86, 0xC1)
GRAY  = RGBColor(0x5D, 0x6D, 0x7E)
GREEN = RGBColor(0x1E, 0x8B, 0x4C)
RED   = RGBColor(0xCB, 0x4A, 0x35)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LBLUE = RGBColor(0xAE, 0xD6, 0xF1)
PURPLE= RGBColor(0x8E, 0x44, 0xAD)

DESKTOP = os.path.expanduser("~/Desktop")


def _slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

def _rect(slide, l, t, w, h, fill):
    s = slide.shapes.add_shape(1, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill
    s.line.fill.background()
    return s

def _box(slide, text, l, t, w, h, size=Pt(13), color=DARK, bold=False, font="Calibri"):
    tb = slide.shapes.add_textbox(l, t, w, h); tf = tb.text_frame
    tf.word_wrap = True; tf.text = text
    for p in tf.paragraphs:
        for r in p.runs:
            r.font.size = size; r.font.bold = bold
            r.font.color.rgb = color; r.font.name = font

def _title(slide, text):
    _rect(slide, Inches(0), Inches(0), Inches(10), Inches(1.1), DARK)
    _box(slide, text, Inches(0.4), Inches(0.18), Inches(9.2), Inches(0.8),
         size=Pt(22), color=WHITE, bold=True)

def _body(slide, text, top=Inches(1.35), height=Inches(5.4), size=Pt(13)):
    _box(slide, text, Inches(0.5), top, Inches(9.0), height, size=size, color=DARK)

def _code(slide, text, top=Inches(1.3), height=Inches(5.5)):
    _rect(slide, Inches(0.3), top, Inches(9.4), height, RGBColor(0xF4, 0xF6, 0xF7))
    _box(slide, text, Inches(0.5), top + Pt(6), Inches(9.0), height - Pt(12),
         size=Pt(11), color=DARK, font="Courier New")

def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def build(output=None):
    if output is None:
        output = os.path.join(DESKTOP, "report_genes.pptx")
    prs = Presentation()
    prs.slide_width = Inches(10); prs.slide_height = Inches(7)

    # ── 0. Титул ───────────────────────────────────────────────────────
    sl = _slide(prs)
    _rect(sl, Inches(0), Inches(0), Inches(10), Inches(2.4), DARK)
    _box(sl, "ДИФФЕРЕНЦИАЛЬНАЯ ЭКСПРЕССИЯ ГЕНОВ\nПРИ БОЛЕЗНИ АЛЬЦГЕЙМЕРА",
         Inches(0.5), Inches(0.35), Inches(9), Inches(1.3),
         size=Pt(24), color=WHITE, bold=True)
    _box(sl, "Мини-панель генов-биомаркеров для ранней диагностики",
         Inches(0.5), Inches(1.7), Inches(9), Inches(0.5), size=Pt(15), color=LBLUE)
    _box(sl,
         "Курсовой проект по биоинформатике\n"
         "Данные: GSE138852 — scRNA-seq энторинальной коры (Grubman et al., 2019)\n"
         "13 214 клеток · 3 пациента AD + 3 контроля · 8 типов клеток",
         Inches(0.5), Inches(2.7), Inches(9), Inches(1.5), size=Pt(13))
    _box(sl, "Вера Королёва · 2026", Inches(0.5), Inches(6.0), Inches(9), Inches(0.4),
         size=Pt(11), color=GRAY)
    _notes(sl, "Здравствуйте. Тема проекта — анализ дифференциальной экспрессии генов "
               "при болезни Альцгеймера на данных одноклеточного РНК-секвенирования. "
               "Главный результат — компактная панель из 12 генов для ранней диагностики.")

    # ── 1. Литобзор ────────────────────────────────────────────────────
    sl = _slide(prs); _title(sl, "1. Литературный обзор")
    _body(sl,
        "Болезнь Альцгеймера (AD)\n\n"
        "•  55+ млн больных в мире (ВОЗ, 2023); деменция №1\n"
        "•  Патология стартует за 10–20 лет до симптомов; к диагнозу утрачено\n"
        "   30–40% нейронов гиппокампа (Jack et al., 2018)\n"
        "•  Одобренные препараты (Lecanemab, Donanemab) эффективны только РАНО\n\n"
        "Молекулярный уровень\n\n"
        "•  Первой страдает энторинальная кора — «ворота» памяти\n"
        "•  scRNA-seq позволяет увидеть изменения экспрессии в каждой клетке\n"
        "•  Grubman et al. (2019, Nat Neurosci) — атлас энторинальной коры при AD (GSE138852)\n"
        "•  Mathys et al. (2019, Nature) — клеточно-специфичная дисрегуляция при AD\n\n"
        "Методы поиска маркеров\n\n"
        "•  DEG-анализ: Mann-Whitney U + поправка FDR (Benjamini-Hochberg, 1995)\n"
        "•  Известные гены AD: APOE, APP, MAPT, TREM2, CLU, LINGO1, NEAT1 и др.")
    _notes(sl, "Болезнь поражает десятки миллионов, начинается задолго до симптомов, "
               "а лечение эффективно только на ранней стадии — отсюда нужда в ранних маркерах. "
               "scRNA-seq даёт экспрессию на уровне отдельных клеток. Базовый датасет — Grubman 2019.")

    # ── 2. Обоснование + новизна ───────────────────────────────────────
    sl = _slide(prs); _title(sl, "2. Обоснование разработки и новизна")
    _body(sl,
        "Проблема\n\n"
        "•  Ранняя диагностика AD — ключ к лечению, но scRNA-seq всего транскриптома\n"
        "   (~14 000 генов) дорог и неприменим в рутинной клинике\n"
        "•  Наивные ML-модели на single-cell данных страдают утечкой: клетки одного\n"
        "   пациента попадают и в обучение, и в тест → завышенная точность\n\n"
        "Новизна проекта\n\n"
        "  ✓  Отбор МИНИ-ПАНЕЛИ из 12 генов вместо всего транскриптома —\n"
        "     такую панель реально измерить дешёвым qPCR / NanoString\n"
        "  ✓  ЧЕСТНАЯ донор-уровневая валидация: целые пациенты уходят в тест,\n"
        "     моделью не виданы — оценка для НОВОГО больного\n"
        "  ✓  Биологическая валидация: 6 из 12 генов независимо подтверждены\n"
        "     литературой по AD (LINGO1, NRXN1, NEAT1, RORA, SPP1, HSPA1A)\n\n"
        "Практический смысл: панель = прототип дешёвого теста ранней диагностики.")
    _notes(sl, "Главная идея: из тысяч генов выделить маленький набор, пригодный для дешёвого "
               "клинического теста. И сделать это ЧЕСТНО — валидировать на пациентах, которых "
               "модель не видела. Это и есть новизна, плюс биологическое подтверждение генов.")

    # ── 3. Реферат ─────────────────────────────────────────────────────
    sl = _slide(prs); _title(sl, "3. Реферат")
    _body(sl,
        "Что реализовано\n\n"
        "•  CLI-приложение (Python): download → analyze → panel\n"
        "•  Загрузка и предобработка scRNA-seq GSE138852 (scanpy)\n"
        "•  DEG-анализ по каждому типу клеток: Mann-Whitney U + FDR\n"
        "•  Pathway enrichment через Enrichr API (GO/KEGG)\n"
        "•  Отбор мини-панели биомаркеров + донор-уровневая валидация\n"
        "•  Веб-интерфейс (Streamlit): ввод экспрессии генов → вероятность AD\n\n"
        "Ожидаемые / полученные результаты\n\n"
        "•  Панель из 12 генов: ROC-AUC 0.79 ± 0.12 (честная, донор-уровень)\n"
        "•  Полная модель (2000 генов): AUC 0.96 — панель в 160 раз меньше,\n"
        "   сохраняет основную часть сигнала\n"
        "•  6/12 генов панели подтверждены литературой по AD")
    _notes(sl, "Реализован полный путь: от скачивания данных до веб-интерфейса. "
               "Ключевой результат — панель из 12 генов с честным AUC 0.79. "
               "Полная модель даёт 0.96, но требует все 2000 генов; панель практичнее.")

    # ── 4. Функциональная схема ────────────────────────────────────────
    sl = _slide(prs); _title(sl, "4. Функциональная схема")
    _code(sl,
        "   GSE138852  (counts 14k генов × 13 214 клеток  +  covariates)\n"
        "        │\n"
        "        ▼\n"
        "   download_data.py        — загрузка с NCBI GEO\n"
        "        │\n"
        "        ▼\n"
        "   data_loader.py          — counts + метаданные → AnnData\n"
        "        │\n"
        "        ▼\n"
        "   preprocessor.py (scanpy) — фильтрация, нормализация, log1p\n"
        "        │\n"
        "        ├──────────────────────────┐\n"
        "        ▼                           ▼\n"
        "   gene_analyzer.py          biomarker_panel.py   ◀── НОВИЗНА\n"
        "   DEG: Mann-Whitney+FDR     предфильтр HVG (2000)\n"
        "   по типам клеток           ранжирование (ANOVA F)\n"
        "        │                    отбор 12 генов\n"
        "        ▼                    донор-уровневый CV (3 фолда)\n"
        "   enrichment_analysis.py           │\n"
        "   Enrichr: GO/KEGG                 ▼\n"
        "        │                    panel_model.pkl → app.py (веб)\n"
        "        ▼                           │\n"
        "   visualizer.py            ВЫХОД: вероятность AD + панель генов",
        top=Inches(1.25), height=Inches(5.6))
    _notes(sl, "Данные качаются с GEO, превращаются в объект AnnData, проходят предобработку scanpy. "
               "Дальше две ветки: классический DEG-анализ с enrichment, и — главная — отбор мини-панели "
               "с честной валидацией. Обученная панель сохраняется и используется в веб-интерфейсе.")

    # ── 5. Инструменты ─────────────────────────────────────────────────
    sl = _slide(prs); _title(sl, "5. Технологии и инструменты")
    _body(sl,
        "Инструмент          Применение                      Почему\n"
        "──────────────────────────────────────────────────────────────────\n"
        "scanpy + anndata    хранение и предобработка        отраслевой стандарт\n"
        "                    scRNA-seq (фильтр, норм., log)   биоинформатики\n\n"
        "GEOparse            загрузка GSE138852 с GEO         нативный формат GEO\n\n"
        "scipy.stats         Mann-Whitney U-критерий          непараметрический,\n"
        "                    (DEG, без нормальности)          подходит для экспрессии\n\n"
        "statsmodels         FDR Бенджамини-Хохберга          контроль ложных\n"
        "                    (поправка на 14k тестов)         открытий\n\n"
        "scikit-learn        LogisticRegression, ANOVA F,     прозрачная модель;\n"
        "                    донор-уровневый CV               интерпретируемость\n\n"
        "matplotlib          volcano, heatmap, UMAP, панель   полный контроль\n"
        "streamlit           веб-интерфейс диагностики        быстрый ML-фронтенд\n"
        "python-pptx         автогенерация этого отчёта       воспроизводимость")
    _notes(sl, "scanpy/anndata — стандарт для single-cell. Mann-Whitney выбран потому, что экспрессия "
               "не нормальна. Бенджамини-Хохберг обязателен при тысячах тестов. Для панели — "
               "логистическая регрессия: она прозрачна, видно вклад каждого гена. Streamlit — веб.")

    # ── 6. Структура проекта ───────────────────────────────────────────
    sl = _slide(prs); _title(sl, "6. Структура проекта")
    _code(sl,
        "  alzheimer/\n"
        "  ├── cli.py                  — точка входа: download / analyze / panel\n"
        "  ├── config.py               — параметры и пути\n"
        "  │\n"
        "  ├── ЗАГРУЗКА И ПОДГОТОВКА\n"
        "  │   ├── download_data.py    — скачивание GSE138852 с NCBI GEO\n"
        "  │   ├── data_loader.py      — counts + covariates → AnnData\n"
        "  │   └── preprocessor.py     — scanpy: фильтр, нормализация, log1p\n"
        "  │\n"
        "  ├── АНАЛИЗ ЭКСПРЕССИИ\n"
        "  │   ├── gene_analyzer.py    — DEG: Mann-Whitney U + BH FDR по клеткам\n"
        "  │   ├── enrichment_analysis.py — Enrichr: GO / KEGG пути\n"
        "  │   └── visualizer.py       — volcano, heatmap, UMAP, barplot\n"
        "  │\n"
        "  ├── ★ biomarker_panel.py    — отбор мини-панели (новизна)\n"
        "  ├── app.py                  — веб-интерфейс (Streamlit)\n"
        "  └── results/                — DEG-таблицы, графики, panel_model.pkl",
        top=Inches(1.25), height=Inches(5.6))
    _notes(sl, "Структура по функциям: загрузка/подготовка, анализ экспрессии, и отдельно — "
               "модуль новизны biomarker_panel.py и веб-интерфейс. config.py хранит все параметры.")

    # ── 7. Интерфейс / демонстрация ────────────────────────────────────
    sl = _slide(prs); _title(sl, "7. Веб-интерфейс и результаты")
    panel_img = os.path.join(RESULTS_FOLDER, "biomarker_panel.png")
    if os.path.exists(panel_img):
        sl.shapes.add_picture(panel_img, Inches(0.3), Inches(1.3), width=Inches(9.4))
        _box(sl, "Слева: качество vs размер панели (12 генов ≈ полная модель). "
                 "Справа: гены панели; * — подтверждены литературой по AD.",
             Inches(0.3), Inches(5.5), Inches(9.4), Inches(0.5), size=Pt(11), color=GRAY)
    else:
        _body(sl, "[biomarker_panel.png — запустите python cli.py panel]")
    _box(sl, "Веб-интерфейс (streamlit run app.py): врач вводит экспрессию 12 генов → "
             "вероятность AD + интерпретация по каждому гену.",
         Inches(0.3), Inches(6.05), Inches(9.4), Inches(0.7), size=Pt(12), color=DARK, bold=True)
    _notes(sl, "Это ключевой график. Левая панель: с ростом числа генов AUC растёт, но уже на 12 "
               "генах близко к насыщению — обоснование размера панели. Правая: состав панели, "
               "звёздочкой отмечены гены, известные в литературе. В демо я ввожу профиль пациента — "
               "здорового и больного — и показываю, как меняется вероятность.")

    # ── 8. Заключение ──────────────────────────────────────────────────
    sl = _slide(prs); _title(sl, "8. Заключение и результаты")
    _body(sl,
        "Достигнуто\n\n"
        "  ✓  Полный биоинформатический пайплайн на РЕАЛЬНЫХ данных (GSE138852)\n"
        "  ✓  Мини-панель из 12 генов, ROC-AUC 0.79 ± 0.12 (честная валидация)\n"
        "  ✓  Донор-уровневый CV — нет утечки, оценка для нового пациента\n"
        "  ✓  6/12 генов подтверждены литературой → метод находит реальную биологию\n"
        "  ✓  Рабочий веб-интерфейс для демонстрации\n\n"
        "Честные ограничения\n\n"
        "  •  Всего 6 доноров → высокая дисперсия AUC между фолдами (0.65–0.93)\n"
        "  •  Строгий порог DEG даёт мало значимых генов (малая выборка) —\n"
        "     поэтому панель строится на непрерывном ранжировании\n"
        "  •  Нужна валидация на независимой когорте (ROSMAP, Mathys 2019)\n\n"
        "Развитие\n\n"
        "  →  Кросс-датасетная валидация панели  →  ранние стадии (Braak)  →  qPCR-прототип")
    _notes(sl, "Итог: честный пайплайн на реальных данных, панель из 12 генов с AUC 0.79, "
               "большинство генов биологически осмысленны. Ограничения честно проговариваю: "
               "доноров мало, дисперсия высокая, нужна внешняя валидация. "
               "Это сильнее, чем красивый, но завышенный результат. Спасибо, готова к вопросам.")

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    prs.save(output)
    print(f"  Презентация сохранена: {output}")


def main():
    print("=" * 60)
    print("  Генерация презентации (гены, 9 слайдов)")
    print("=" * 60)
    build()


if __name__ == "__main__":
    main()
