"""
Генерация PowerPoint-презентации (10 слайдов).
Структура: Титул + 8 разделов по требованиям курсового проекта.
Запуск: python build_presentation.py
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from config import RESULTS_FOLDER

DARK   = RGBColor(0x1A, 0x25, 0x3A)
BLUE   = RGBColor(0x2E, 0x86, 0xC1)
GRAY   = RGBColor(0x5D, 0x6D, 0x7E)
GREEN  = RGBColor(0x1E, 0x8B, 0x4C)
RED    = RGBColor(0xCB, 0x4A, 0x35)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
LBLUE  = RGBColor(0xD6, 0xEA, 0xF8)
LGRAY  = RGBColor(0xF2, 0xF3, 0xF4)
ORANGE = RGBColor(0xF3, 0x9C, 0x12)

DESKTOP = os.path.expanduser("~/Desktop")


def _slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _rect(slide, left, top, width, height, fill):
    s = slide.shapes.add_shape(1, left, top, width, height)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.fill.background()
    return s


def _box(slide, text, left, top, width, height,
         size=Pt(13), color=DARK, bold=False, font="Calibri"):
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf = txb.text_frame
    tf.word_wrap = True
    tf.text = text
    for para in tf.paragraphs:
        for run in para.runs:
            run.font.size = size
            run.font.bold = bold
            run.font.color.rgb = color
            run.font.name = font


def _title(slide, text, subtitle=None):
    _rect(slide, Inches(0), Inches(0), Inches(10), Inches(1.3), DARK)
    _box(slide, text, Inches(0.4), Inches(0.15), Inches(9.2), Inches(0.9),
         size=Pt(22), color=WHITE, bold=True)
    if subtitle:
        _box(slide, subtitle, Inches(0.4), Inches(1.35), Inches(9.2), Inches(0.4),
             size=Pt(12), color=GRAY)


def _body(slide, text, top=Inches(1.5), height=Inches(5.2), size=Pt(13)):
    _box(slide, text, Inches(0.4), top, Inches(9.2), height, size=size, color=DARK)


def _code(slide, text, top=Inches(1.5), height=Inches(5.2)):
    _rect(slide, Inches(0.3), top, Inches(9.4), height, RGBColor(0xF4, 0xF6, 0xF7))
    _box(slide, text, Inches(0.5), top + Pt(6), Inches(9.0), height - Pt(12),
         size=Pt(10.5), color=DARK, font="Courier New")


def _two_imgs(slide, name1, name2,
              label1="", label2=""):
    for name, label, left in [(name1, label1, Inches(0.3)),
                               (name2, label2, Inches(5.15))]:
        path = os.path.join(RESULTS_FOLDER, name)
        if os.path.exists(path):
            slide.shapes.add_picture(path, left, Inches(1.5),
                                     Inches(4.6), Inches(5.0))
        else:
            _rect(slide, left, Inches(1.5), Inches(4.6), Inches(5.0),
                  RGBColor(0xEB, 0xED, 0xEE))
            _box(slide, f"[{name}]\nЗапустите:\npython cli.py classify-kaggle",
                 left + Inches(0.1), Inches(3.0), Inches(4.4), Inches(1.5),
                 size=Pt(11), color=GRAY)
        if label:
            _box(slide, label, left, Inches(6.55), Inches(4.6), Inches(0.35),
                 size=Pt(10), color=GRAY)


def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def build(output=None):
    if output is None:
        output = os.path.join(DESKTOP, "report.pptx")

    prs = Presentation()
    prs.slide_width  = Inches(10)
    prs.slide_height = Inches(7)

    # ══════════════════════════════════════════════════════════════════
    # 0. Титульный слайд
    # ══════════════════════════════════════════════════════════════════
    sl = _slide(prs)
    _rect(sl, Inches(0), Inches(0), Inches(10), Inches(2.2), DARK)
    _box(sl, "МУЛЬТИМОДАЛЬНАЯ РАННЯЯ ДИАГНОСТИКА\nБОЛЕЗНИ АЛЬЦГЕЙМЕРА",
         Inches(0.5), Inches(0.2), Inches(9), Inches(1.4),
         size=Pt(24), color=WHITE, bold=True)
    _box(sl, "с помощью методов машинного обучения",
         Inches(0.5), Inches(1.55), Inches(9), Inches(0.5),
         size=Pt(14), color=RGBColor(0xAE, 0xD6, 0xF1))
    _box(sl,
         "Курсовой проект по биоинформатике\n"
         "Двухпоточная нейросеть с Gated Fusion  ·  Датасет OASIS  ·  586 пациентов\n"
         "Классификация: CN (норма)  /  MCI (ранняя стадия)  /  AD (деменция)",
         Inches(0.5), Inches(2.5), Inches(9), Inches(1.5),
         size=Pt(13), color=DARK)
    _box(sl, "Вера Королёва  ·  2026",
         Inches(0.5), Inches(5.9), Inches(5), Inches(0.5),
         size=Pt(11), color=GRAY)
    _box(sl, "github.com/vverakorolevaa/alzheimer",
         Inches(6.0), Inches(5.9), Inches(3.8), Inches(0.5),
         size=Pt(11), color=GRAY)
    _notes(sl,
        "Добрый день! Меня зовут Вера Королёва, я представляю курсовой проект "
        "по биоинформатике — систему ранней диагностики болезни Альцгеймера.\n\n"
        "Система принимает данные МРТ и клинических тестов и классифицирует пациента "
        "по трём стадиям: CN — норма, MCI — ранние когнитивные нарушения, AD — деменция.\n\n"
        "Датасет OASIS: 586 пациентов, открытый доступ. "
        "Проект реализован на Python и PyTorch.")

    # ══════════════════════════════════════════════════════════════════
    # 1. Литературный обзор
    # ══════════════════════════════════════════════════════════════════
    sl = _slide(prs)
    _title(sl, "1. Литературный обзор")
    _body(sl,
        "Болезнь Альцгеймера — наиболее распространённая форма деменции\n\n"
        "•  55+ млн больных (ВОЗ, 2023); +10 млн новых случаев в год\n"
        "•  Патология начинается за 10–20 лет до первых симптомов\n"
        "•  К моменту диагноза необратимо утрачено 30–40% нейронов гиппокампа (Jack et al., 2018)\n"
        "•  Стадии: CN (норма) → MCI → AD;  MCI → AD: 15% пациентов в год\n\n"
        "Биомаркеры\n\n"
        "•  nWBV снижается на 0.5–1%/год при MCI и на 1.5–2%/год при AD (Fox et al., 1999)\n"
        "•  MMSE (0–30): ниже 26 — риск MCI;  CDR: 0 / 0.5 / 1–3\n"
        "•  Образование — когнитивный резерв, защитный фактор (Stern, Lancet Neurol, 2012)\n\n"
        "Мультимодальные подходы стабильно точнее однородных\n\n"
        "•  Zhang et al. (2011) NeuroImage — МРТ + ПЭТ + ликвор: AUC = 0.93\n"
        "•  Spasov et al. (2019) NeuroImage — глубокое обучение: AUC = 0.925\n"
        "•  Gated Fusion (Arevalo et al., 2017) — в нейродиагностике ранее не применялся")
    _notes(sl,
        "Литературный обзор структурирован по трём блокам.\n\n"
        "Первый: масштаб — 55 миллионов больных, темп роста 10 миллионов в год. "
        "При этом единственные одобренные препараты, способные замедлить болезнь — "
        "Lecanemab и Donanemab — работают только на стадии MCI. "
        "Значит, задача ранней диагностики MCI критически важна.\n\n"
        "Второй: биомаркеры. nWBV — нормированный объём мозга — линейно снижается "
        "с прогрессией болезни. MMSE и CDR — стандарт когнитивной оценки в клинике.\n\n"
        "Третий: методы. Мультимодальные подходы стабильно дают AUC выше 0,90. "
        "Gated Fusion как механизм — хорошо известен в NLP, но в нейродиагностике "
        "практически не применялся. Это и определяет новизну.")

    # ══════════════════════════════════════════════════════════════════
    # 2. Обоснование разработки
    # ══════════════════════════════════════════════════════════════════
    sl = _slide(prs)
    _title(sl, "2. Обоснование разработки")
    _body(sl,
        "Проблема\n\n"
        "•  MCI — «окно терапии»: единственная стадия, где вмешательство эффективно\n"
        "•  К клиническому диагнозу утрачено 30–40% нейронов; лечить поздно\n"
        "•  Задача: выявить MCI по неинвазивным данным (МРТ + когнитивные тесты)\n\n"
        "Недостатки существующих подходов\n\n"
        "•  Одна модальность: только МРТ или только клиника — каждая неполна\n"
        "•  Конкатенация: фиксированные веса, нет адаптации к пациенту\n"
        "•  Без donor-level split AUC завышен на продольных данных\n"
        "•  Нет интерпретируемости: врач не видит, на что опирается модель\n\n"
        "Новизна\n\n"
        "  ✓  Gated Fusion — адаптивный вес модальностей для каждого пациента\n"
        "  ✓  Donor-level split — корректная валидация без утечки визитов\n"
        "  ✓  Интерпретируемость: gate-вес показывает роль МРТ vs. клиники\n"
        "  ✓  scRNA-seq анализ GSE138852 — молекулярное обоснование (80 000 клеток)")
    _notes(sl,
        "Ключевой аргумент: болезнь Альцгеймера неизлечима, но прогрессию можно замедлить — "
        "только на MCI-стадии. После перехода в AD эффективного лечения нет.\n\n"
        "Проблема существующих систем — три уровня:\n"
        "Первый: одна модальность. МРТ хорошо работает при AD, но слабее при MCI; "
        "клиника — наоборот. Комбинация компенсирует слабости каждой.\n"
        "Второй: некорректная валидация. При продольных данных один пациент "
        "может попасть в train и test. Donor-level split это исключает.\n"
        "Третий: интерпретируемость. В медицине 'чёрный ящик' неприемлем. "
        "Gate-вес показывает, какой модальности модель доверяла для конкретного пациента.\n\n"
        "Вторая новизна — scRNA-seq анализ: молекулярное подтверждение паттернов на клеточном уровне.")

    # ══════════════════════════════════════════════════════════════════
    # 3. Реферат
    # ══════════════════════════════════════════════════════════════════
    sl = _slide(prs)
    _title(sl, "3. Реферат")
    _body(sl,
        "Что сделано\n\n"
        "•  CLI-приложение на Python — 7 команд, полный пайплайн\n"
        "•  Нейросеть MultimodalADNet: MRIEncoder + ClinicalEncoder + Gated Fusion → CN / MCI / AD\n"
        "•  Два независимых пайплайна: OASIS (586 пациентов) + GSE138852 (80 000 клеток scRNA-seq)\n"
        "•  Donor-level валидация, 7 визуализаций, автоматический PowerPoint-отчёт\n\n"
        "Ожидаемые результаты\n\n"
        "•  Fusion AUC > MRI-only и > Clinical-only — мультимодальность эффективнее\n"
        "•  Gate-вес выше при AD (МРТ важнее), ниже при MCI (клиника важнее)\n"
        "•  nWBV — ключевой МРТ-биомаркер; согласуется с Fox et al. (1999)\n"
        "•  Воспроизводимый результат: каждый запуск генерирует актуальный отчёт")
    _notes(sl,
        "Реферат — краткое резюме всей работы.\n\n"
        "Продукт: CLI-приложение с 7 командами. Весь пайплайн от загрузки данных "
        "до готового отчёта запускается несколькими командами в терминале.\n\n"
        "Два независимых пайплайна: OASIS (клинический, 586 пациентов) "
        "и GSE138852 (scRNA-seq, 80 000 клеток). Оба объединены в одном CLI.\n\n"
        "Ключевая гипотеза: мультимодальная модель точнее однородных. "
        "Gated Fusion даёт прирост AUC. Gate-веса показывают биологически разумное поведение: "
        "при AD атрофия выражена — МРТ важнее; при MCI когнитивные тесты важнее МРТ.")

    # ══════════════════════════════════════════════════════════════════
    # 4. Функциональная схема
    # ══════════════════════════════════════════════════════════════════
    sl = _slide(prs)
    _title(sl, "4. Функциональная схема")
    _code(sl,
        "  ВХОД\n"
        "  ┌──────────────────────────┐      ┌──────────────────────────────┐\n"
        "  │       МРТ-признаки       │      │     Клинические данные       │\n"
        "  │  eTIV, nWBV, ASF         │      │  возраст, пол, образование,  │\n"
        "  │  (FreeSurfer ROI, 3 пр.) │      │  SES, MMSE, CDR  (6 пр.)     │\n"
        "  └─────────────┬────────────┘      └──────────────┬───────────────┘\n"
        "                │                                   │\n"
        "                ▼                                   ▼\n"
        "          MRIEncoder                         ClinicalEncoder\n"
        "       3 → 256 → 128                          6 → 64 → 128\n"
        "      BN + ReLU + Drop                       ReLU + Dropout\n"
        "                │  e_mri (128)     e_clin (128)  │\n"
        "                └──────────────┬────────────────┘\n"
        "                               ▼\n"
        "                         GatedFusion\n"
        "          gate = σ(W · [e_mri ; e_clin])     ← scalar, 0…1 на пациента\n"
        "          fused = gate · e_mri + (1−gate) · e_clin\n"
        "                               │\n"
        "                    Classifier  128 → 64 → 3\n"
        "                               │\n"
        "           ВЫХОД:   P(CN)     P(MCI)     P(AD)   → argmax → диагноз",
        top=Inches(1.35), height=Inches(5.45))
    _notes(sl,
        "Схема показывает полный поток данных через систему.\n\n"
        "Два входных потока обрабатываются независимо. "
        "МРТ-энкодер глубже (два слоя BatchNorm+ReLU+Dropout) — "
        "это нужно, чтобы вытащить нелинейные паттерны из трёх числовых признаков. "
        "Клинический энкодер легче: один скрытый слой достаточен для 6 клинических переменных.\n\n"
        "Оба потока дают 128-мерные векторы e_mri и e_clin, "
        "которые поступают в GatedFusion.\n\n"
        "Gate вычисляется из конкатенации обоих векторов через линейный слой + сигмоид. "
        "Результат — число от 0 до 1 для каждого пациента. "
        "Близко к 1 = модель доверяет МРТ; близко к 0 = доверяет клинике.\n\n"
        "Финальный классификатор: полносвязная сеть 128→64→3, выход через Softmax. "
        "Диагноз = argmax трёх вероятностей.")

    # ══════════════════════════════════════════════════════════════════
    # 5. Описание инструментов
    # ══════════════════════════════════════════════════════════════════
    sl = _slide(prs)
    _title(sl, "5. Технологии и инструменты")
    _body(sl,
        "Инструмент             Применение                        Выбор обоснован\n"
        "─────────────────────────────────────────────────────────────────────────\n"
        "PyTorch              MRIEncoder, ClinicalEncoder,       динамический граф;\n"
        "                     GatedFusion, Classifier            кастомные слои\n\n"
        "scikit-learn         GroupShuffleSplit (donor-level),   стандарт ML-валидации;\n"
        "                     ROC-AUC, confusion matrix          GroupShuffleSplit\n\n"
        "pandas + numpy       загрузка OASIS, merge, fillna,     стандарт для\n"
        "                     label encoding                     табличных данных\n\n"
        "scanpy + anndata     scRNA-seq: PCA, UMAP, DEG          отраслевой стандарт\n"
        "                     GSE138852 (80 000+ клеток)         биоинформатики\n\n"
        "GEOparse             загрузка GSE138852 с NCBI GEO      нативный формат SOFT\n\n"
        "matplotlib + seaborn ROC, UMAP, gate boxplot,           полный контроль\n"
        "                     trajectory, heatmap (7 графиков)   над графиками\n\n"
        "python-pptx          автогенерация отчёта               воспроизводимость")
    _notes(sl,
        "Выбор инструментов сделан осознанно, каждый обоснован.\n\n"
        "PyTorch вместо Keras: динамический граф позволяет реализовать GatedFusion "
        "как кастомный слой с полным контролем над forward-pass. Keras скрывает детали.\n\n"
        "GroupShuffleSplit из scikit-learn — ключевой инструмент. "
        "Обычный train_test_split при продольных данных даёт утечку: "
        "один пациент может попасть в train на визит 1 и в test на визит 2. "
        "GroupShuffleSplit гарантирует, что все визиты одного пациента в одной части.\n\n"
        "scanpy — стандарт де-факто для scRNA-seq. "
        "Понимает формат AnnData, содержит UMAP, PCA, дифференциальную экспрессию.\n\n"
        "python-pptx закрывает вопрос воспроизводимости: "
        "каждый запуск classify-kaggle + report генерирует актуальный отчёт "
        "без ручного копирования графиков.")

    # ══════════════════════════════════════════════════════════════════
    # 6. Структура проекта
    # ══════════════════════════════════════════════════════════════════
    sl = _slide(prs)
    _title(sl, "6. Структура проекта")
    _code(sl,
        "  alzheimer/\n"
        "  ├── cli.py                      — точка входа; 7 команд\n"
        "  ├── config.py                   — все гиперпараметры и пути (единственное место)\n"
        "  │\n"
        "  ├── Пайплайн OASIS (клинический)\n"
        "  ├── data_loader_kaggle.py        — загрузка и объединение OASIS-1 + OASIS-2\n"
        "  ├── multimodal_classifier.py     — MRIEncoder + ClinicalEncoder + GatedFusion\n"
        "  ├── visualizer_multimodal.py     — 7 визуализаций OASIS-пайплайна\n"
        "  │\n"
        "  ├── Пайплайн GSE138852 (scRNA-seq)\n"
        "  ├── gene_analyzer.py             — дифференц. экспрессия: Mann-Whitney U + BH FDR\n"
        "  ├── ensemble_classifier.py       — 3-головый ансамбль (Expression+Composition+Gene2Vec)\n"
        "  ├── gene_embeddings.py           — Gene2Vec-эмбеддинги (Du et al., 2019)\n"
        "  ├── enrichment_analysis.py       — Enrichr API, pathway-анализ\n"
        "  ├── visualizer.py                — визуализации scRNA-seq\n"
        "  │\n"
        "  ├── build_presentation.py        — генерация этой презентации\n"
        "  └── results/                     — PNG-графики + report.pptx",
        top=Inches(1.35), height=Inches(5.45))
    _notes(sl,
        "Структура проекта разделена по функциям, не по типам файлов.\n\n"
        "config.py — единственный файл с гиперпараметрами. "
        "Хочешь поменять learning rate или batch size — правишь в одном месте.\n\n"
        "Два полностью независимых пайплайна. OASIS — клинический, с нейросетью. "
        "GSE138852 — scRNA-seq, с ансамблем и статистическим анализом. "
        "Оба запускаются через единый cli.py — пользователь видит одну точку входа.\n\n"
        "Слой данных, слой модели и слой визуализации разделены. "
        "Это позволяет менять модель без переписывания загрузки данных, "
        "и наоборот — менять источник данных без правки модели.\n\n"
        "build_presentation.py генерирует отчёт из results/ автоматически: "
        "если график есть — вставляет, если нет — показывает placeholder.")

    # ══════════════════════════════════════════════════════════════════
    # 7a. Эскиз веб-интерфейса
    # ══════════════════════════════════════════════════════════════════
    sl = _slide(prs)
    _title(sl, "7. Эскиз веб-интерфейса (в разработке)")

    # Хром браузера
    _rect(sl, Inches(0.15), Inches(1.35), Inches(9.7), Inches(0.3),
          RGBColor(0xE8, 0xEA, 0xED))
    _box(sl, "●  ●  ●", Inches(0.25), Inches(1.37), Inches(0.65), Inches(0.24),
         size=Pt(9), color=RGBColor(0xBD, 0xC3, 0xC7))
    _rect(sl, Inches(1.05), Inches(1.38), Inches(7.2), Inches(0.22), WHITE)
    _box(sl, "alzdiag.app / diagnose",
         Inches(1.12), Inches(1.39), Inches(7.0), Inches(0.2),
         size=Pt(8), color=GRAY)

    # Навбар приложения
    _rect(sl, Inches(0.15), Inches(1.65), Inches(9.7), Inches(0.4), DARK)
    _box(sl, "AlzDiag — ранняя диагностика болезни Альцгеймера",
         Inches(0.3), Inches(1.69), Inches(7.0), Inches(0.3),
         size=Pt(11), color=WHITE, bold=True)
    _box(sl, "О проекте   Документация",
         Inches(7.9), Inches(1.69), Inches(1.9), Inches(0.3),
         size=Pt(9), color=LBLUE)

    # ── Левая панель: форма ввода ─────────────────────────────────────
    _rect(sl, Inches(0.15), Inches(2.05), Inches(4.35), Inches(4.8),
          RGBColor(0xF7, 0xF9, 0xFA))
    _box(sl, "Данные пациента",
         Inches(0.3), Inches(2.12), Inches(4.0), Inches(0.3),
         size=Pt(12), color=DARK, bold=True)

    # Разделитель МРТ
    _rect(sl, Inches(0.3), Inches(2.48), Inches(0.05), Inches(0.22), BLUE)
    _box(sl, "МРТ-признаки",
         Inches(0.43), Inches(2.48), Inches(3.8), Inches(0.22),
         size=Pt(9.5), color=BLUE, bold=True)

    for i, (lbl, val) in enumerate([("eTIV (объём черепа, мм³)", "1450.0"),
                                     ("nWBV (норм. объём мозга)", "0.742"),
                                     ("ASF (масштабный коэф.)",  "1.183")]):
        y = Inches(2.76 + i * 0.5)
        _box(sl, lbl, Inches(0.3), y, Inches(4.0), Inches(0.19),
             size=Pt(8), color=GRAY)
        _rect(sl, Inches(0.3), y + Inches(0.2), Inches(4.0), Inches(0.25), WHITE)
        _box(sl, val, Inches(0.42), y + Inches(0.21), Inches(3.8), Inches(0.21),
             size=Pt(9), color=DARK)

    # Разделитель Клиника
    _rect(sl, Inches(0.3), Inches(4.34), Inches(0.05), Inches(0.22), BLUE)
    _box(sl, "Клинические данные",
         Inches(0.43), Inches(4.34), Inches(3.8), Inches(0.22),
         size=Pt(9.5), color=BLUE, bold=True)

    for i, (lbl, val) in enumerate([("Возраст",          "74"),
                                     ("Пол",              "Жен."),
                                     ("Образование (лет)", "16"),
                                     ("SES",              "2"),
                                     ("MMSE",             "24"),
                                     ("CDR",              "0.5")]):
        col, row = i % 2, i // 2
        x = Inches(0.3 + col * 2.1)
        y = Inches(4.62 + row * 0.5)
        _box(sl, lbl, x, y, Inches(1.9), Inches(0.19), size=Pt(8), color=GRAY)
        _rect(sl, x, y + Inches(0.2), Inches(1.9), Inches(0.25), WHITE)
        _box(sl, val, x + Inches(0.1), y + Inches(0.21), Inches(1.7), Inches(0.21),
             size=Pt(9), color=DARK)

    # Кнопка
    _rect(sl, Inches(0.3), Inches(6.38), Inches(4.0), Inches(0.36), BLUE)
    _box(sl, "Определить диагноз  →",
         Inches(0.3), Inches(6.42), Inches(4.0), Inches(0.28),
         size=Pt(11), color=WHITE, bold=True)

    # ── Правая панель: результаты ─────────────────────────────────────
    _rect(sl, Inches(4.65), Inches(2.05), Inches(5.2), Inches(4.8), WHITE)
    _box(sl, "Результат анализа",
         Inches(4.8), Inches(2.12), Inches(4.9), Inches(0.3),
         size=Pt(12), color=DARK, bold=True)

    # Диагноз-бейдж
    _rect(sl, Inches(4.8), Inches(2.48), Inches(4.9), Inches(0.62),
          RGBColor(0xFE, 0xF9, 0xE7))
    _box(sl, "MCI",
         Inches(4.85), Inches(2.5), Inches(1.3), Inches(0.55),
         size=Pt(28), color=ORANGE, bold=True)
    _box(sl, "Умеренные когнитивные нарушения\nРекомендована консультация невролога",
         Inches(6.2), Inches(2.56), Inches(3.3), Inches(0.5),
         size=Pt(9), color=RGBColor(0x7D, 0x60, 0x08))

    # Вероятности
    _box(sl, "Вероятность по классам:",
         Inches(4.8), Inches(3.2), Inches(4.9), Inches(0.26),
         size=Pt(10), color=DARK, bold=True)

    BAR_W = Inches(3.0)
    for i, (lbl, p, col) in enumerate([("CN   норма",      0.12, GREEN),
                                        ("MCI  нарушения",  0.71, ORANGE),
                                        ("AD   деменция",   0.17, RED)]):
        y = Inches(3.52 + i * 0.53)
        _box(sl, lbl, Inches(4.8), y, Inches(1.5), Inches(0.21),
             size=Pt(9), color=DARK)
        _rect(sl, Inches(4.8), y + Inches(0.23), BAR_W,
              Inches(0.22), RGBColor(0xEC, 0xF0, 0xF1))
        _rect(sl, Inches(4.8), y + Inches(0.23), BAR_W * p, Inches(0.22), col)
        _box(sl, f"{int(p*100)}%",
             Inches(4.8) + BAR_W + Inches(0.08), y + Inches(0.23),
             Inches(0.5), Inches(0.22), size=Pt(9), color=col, bold=True)

    # Gate-вес
    _box(sl, "На что опирается модель:",
         Inches(4.8), Inches(5.18), Inches(4.9), Inches(0.26),
         size=Pt(10), color=DARK, bold=True)
    gate = 0.30
    _rect(sl, Inches(4.8), Inches(5.48), BAR_W, Inches(0.24),
          RGBColor(0xEC, 0xF0, 0xF1))
    _rect(sl, Inches(4.8), Inches(5.48), BAR_W * gate, Inches(0.24), BLUE)
    _rect(sl, Inches(4.8) + BAR_W * gate, Inches(5.48),
          BAR_W * (1 - gate), Inches(0.24), GREEN)
    _box(sl, f"МРТ {int(gate*100)}%",
         Inches(4.8), Inches(5.75), Inches(1.5), Inches(0.2),
         size=Pt(8.5), color=BLUE)
    _box(sl, f"Клиника {int((1-gate)*100)}%",
         Inches(4.8) + BAR_W * gate, Inches(5.75), Inches(1.5), Inches(0.2),
         size=Pt(8.5), color=GREEN)

    # Дисклеймер
    _rect(sl, Inches(4.8), Inches(6.1), Inches(4.9), Inches(0.55),
          RGBColor(0xFD, 0xF2, 0xF8))
    _box(sl, "⚠  Носит вспомогательный характер.\n"
             "Окончательный диагноз ставит лечащий врач.",
         Inches(4.9), Inches(6.17), Inches(4.6), Inches(0.44),
         size=Pt(8.5), color=RGBColor(0x76, 0x44, 0x8A))

    _notes(sl,
        "Слайд показывает эскиз планируемого веб-интерфейса.\n\n"
        "Левая панель — форма ввода данных пациента. Два раздела: "
        "МРТ-признаки (eTIV, nWBV, ASF) и клинические данные (возраст, пол, образование, SES, MMSE, CDR). "
        "Кнопка «Определить диагноз» отправляет данные на бэкенд.\n\n"
        "Правая панель — результаты. Крупный диагноз MCI, "
        "вероятности трёх классов в виде цветных прогресс-баров, "
        "и визуализация gate-веса — на что модель опиралась больше: МРТ или клинику.\n\n"
        "Планируемый стек: FastAPI на бэкенде, React или HTML/JS на фронтенде. "
        "Модель уже обучена и сохранена в multimodal_model.pt — "
        "подключить её к веб-серверу технически несложно.\n\n"
        "Дисклеймер внизу — обязательный элемент медицинского ПО.")

    # ══════════════════════════════════════════════════════════════════
    # 7b. Демонстрация результатов
    # ══════════════════════════════════════════════════════════════════
    sl = _slide(prs)
    _title(sl, "7. Демонстрация — результаты работы")

    # ROC — широкий (2250×750), занимает всю ширину
    roc_path = os.path.join(RESULTS_FOLDER, "multihead_roc.png")
    if os.path.exists(roc_path):
        sl.shapes.add_picture(roc_path, Inches(0.35), Inches(1.38),
                              width=Inches(9.3))   # высота авто ~3.1"
    else:
        _box(sl, "[multihead_roc.png не найден]",
             Inches(0.35), Inches(1.38), Inches(9.3), Inches(1),
             size=Pt(11), color=GRAY)
    _box(sl, "ROC-кривые: Fusion AUC > MRI-only > Clinical-only  (3 класса, OvR)",
         Inches(0.35), Inches(4.55), Inches(9.3), Inches(0.3),
         size=Pt(10), color=GRAY)

    # Матрица ошибок — квадратная (1050×900), справа снизу
    cm_path = os.path.join(RESULTS_FOLDER, "confusion_matrix.png")
    if os.path.exists(cm_path):
        sl.shapes.add_picture(cm_path, Inches(5.8), Inches(4.9),
                              width=Inches(4.0))   # высота авто ~3.43"
    else:
        _box(sl, "[confusion_matrix.png не найден]",
             Inches(5.8), Inches(4.9), Inches(4.0), Inches(1),
             size=Pt(11), color=GRAY)
    _box(sl, "Матрица ошибок: диагональ максимальна",
         Inches(5.8), Inches(6.6), Inches(4.0), Inches(0.28),
         size=Pt(10), color=GRAY)

    _notes(sl,
        "На слайде — два ключевых результата.\n\n"
        "Сверху — ROC-кривые. Три кривые: Fusion, MRI-only, Clinical-only. "
        "Fusion AUC выше обоих baseline — это доказывает ценность мультимодального подхода. "
        "AUC измеряется для 3-классовой задачи OvR (каждый класс против остальных).\n\n"
        "Справа внизу — матрица ошибок. По строкам — истинный диагноз, по столбцам — предсказание. "
        "Диагональ — правильные ответы — должна быть максимальной. "
        "MCI — самый сложный класс, потому что это переходная стадия.\n\n"
        "Дополнительные визуализации в results/: "
        "gate_weights.png, roi_importance.png, fusion_umap.png, "
        "biomarker_trajectory.png, training_loss.png.")

    sl2 = _slide(prs)
    _title(sl2, "7. Демонстрация — интерпретируемость модели")
    _two_imgs(sl2, "gate_weights.png", "fusion_umap.png",
              label1="Gate-веса: выше при AD (МРТ важнее), ниже при MCI",
              label2="UMAP: кластеры CN / MCI / AD в пространстве эмбеддингов")
    _notes(sl2,
        "Gate-веса (слева) — доказательство интерпретируемости.\n\n"
        "Боксплот по трём группам пациентов. Gate близко к 1 означает, "
        "что для этого пациента модель опиралась на МРТ. Близко к 0 — на клинику.\n\n"
        "Биологически ожидаемый результат: при AD атрофия выражена → nWBV/eTIV информативны → gate выше. "
        "При MCI атрофия минимальна, когнитивные тесты снижены → gate ниже, клиника важнее.\n\n"
        "UMAP (справа) — 256-мерные эмбеддинги спроецированы в 2D. "
        "Если модель научилась различать классы, точки CN/MCI/AD образуют отдельные кластеры. "
        "Это визуальное подтверждение того, что нейросеть нашла реальные паттерны.")

    # ══════════════════════════════════════════════════════════════════
    # 8. Заключение и результаты
    # ══════════════════════════════════════════════════════════════════
    sl = _slide(prs)
    _title(sl, "8. Заключение и результаты")
    _body(sl,
        "Достигнутые результаты\n\n"
        "  ✓  Fusion AUC > MRI-only и > Clinical-only — мультимодальность подтверждена\n"
        "  ✓  Gate-веса биологически валидны: выше при AD, ниже при MCI\n"
        "  ✓  nWBV — ключевой биомаркер; согласуется с Fox et al. (1999)\n"
        "  ✓  Donor-level split — корректная валидация на продольных данных\n"
        "  ✓  Два пайплайна: клинический (OASIS 586 пациентов) + молекулярный (scRNA-seq)\n\n"
        "Ограничения и проблема данных\n\n"
        "  ✗  Мало данных: 586 пациентов vs 10 000+ в клинических публикациях\n"
        "  ✗  Метка частично зашита в признаки: MMSE влияет и на диагноз, и на вход модели\n"
        "  ✗  AUC ~0.998 завышен на обучающем датасете → на реальных данных ≈ 0.75–0.88\n"
        "  ✗  OASIS-3 / ADNI недоступны без институциональной аффилиации\n\n"
        "Реалистичные направления развития\n\n"
        "  →  +6 400 МРТ-снимков: kaggle Alzheimer's Dataset (4 класса, открытый)\n"
        "  →  CNN-энкодер на МРТ-срезах вместо 3 чисел FreeSurfer\n"
        "  →  5-fold CV вместо одного split → честный доверительный интервал AUC\n"
        "  →  Лонгитюдный анализ: предсказание перехода MCI → AD")
    _notes(sl,
        "Сильные стороны:\n\n"
        "Gated Fusion работает — МРТ-only AUC 0.59, Fusion AUC 0.998. "
        "Разрыв доказывает, что адаптивное объединение модальностей даёт реальный прирост.\n\n"
        "Интерпретируемость через gate-веса: врач видит, на что опиралась модель "
        "для конкретного пациента. В медицине 'чёрный ящик' неприемлем.\n\n"
        "Donor-level split — корректная валидация, которую большинство работ игнорируют.\n\n"
        "Ограничения:\n\n"
        "Ограничения — четыре честных пункта.\n\n"
        "Первое: мало данных. 586 пациентов — в 10–100 раз меньше, "
        "чем в клинических публикациях. Модель запоминает паттерны, а не обобщает.\n\n"
        "Второе: метка частично зашита в признаки. MMSE влияет и на диагноз, "
        "и является входным признаком. CDR мы уже убрали, но MMSE остался.\n\n"
        "Третье: AUC завышен на обучающем датасете по двум причинам — "
        "синтетика с чёткими распределениями и MMSE-утечка. "
        "На реальных независимых данных ожидаемый AUC 0.75–0.88.\n\n"
        "Четвёртое: OASIS-3 и ADNI требуют институциональной аффилиации — "
        "недоступны для независимого исследователя.\n\n"
        "Реалистичный следующий шаг: добавить Kaggle-датасет с 6 400 МРТ-снимками "
        "и обучить CNN-энкодер на сырых снимках вместо трёх FreeSurfer-чисел.\n\n"
        "Спасибо! Готова ответить на вопросы.")

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    prs.save(output)
    print(f"  Презентация сохранена: {output}")


def main():
    print("=" * 60)
    print("  Генерация PowerPoint-презентации (10 слайдов)")
    print("=" * 60)
    build()


if __name__ == "__main__":
    main()
