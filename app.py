"""
Веб-инструмент поддержки врача: определение СТАДИИ болезни Альцгеймера
(норма → MCI → деменция) по панели генов крови, с объяснением решения.

Вводятся уровни экспрессии генов панели в шкале микрочипа Illumina HumanHT-12
(нормализованные log2-значения, как в GSE63060); модель выдаёт вероятности трёх стадий и ПЕРСОНАЛЬНОЕ объяснение: какие гены и
насколько повлияли на вывод (локальные SHAP-вклады линейной модели).

Запуск: streamlit run app.py
"""

import os
import json
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import (RESULTS_FOLDER, STAGES, STAGE_RU, STAGE_RU_SHORT,
                    STAGE_COLOR, GEO_ACCESSION)

st.set_page_config(page_title="AD Blood Stage", page_icon="🧬", layout="wide")

MODEL_PATH = os.path.join(RESULTS_FOLDER, "panel_model.pkl")
PANEL_CSV  = os.path.join(RESULTS_FOLDER, "biomarker_panel.csv")
EXT_JSON   = os.path.join(RESULTS_FOLDER, "external_metrics.json")
EXT_CSV    = os.path.join(RESULTS_FOLDER, "external_patients.csv")
CMP_CSV    = os.path.join(RESULTS_FOLDER, "model_comparison.csv")

# Краткая биология генов панели (преобладают энергетический обмен и синтез белка)
GENE_INFO = {
    "MRPL51":  "митохондриальный рибосомальный белок — синтез белка в митохондриях",
    "NDUFA1":  "субъединица комплекса I дыхательной цепи (описан как маркер AD в крови)",
    "NDUFS5":  "субъединица комплекса I дыхательной цепи митохондрий",
    "UQCRB":   "субъединица комплекса III дыхательной цепи митохондрий",
    "ATP5I":   "субъединица АТФ-синтазы (комплекс V) — производство АТФ",
    "COX17":   "сборка цитохром-c-оксидазы (комплекс IV)",
    "HSPE1":   "митохондриальный шаперон Hsp10 — сворачивание белков",
    "RPS25":   "рибосомальный белок малой субъединицы — синтез белка",
    "SHFM1":   "субъединица протеасомы (SEM1) — деградация белков",
    "ING3":    "регулятор транскрипции и апоптоза",
    "RPA3":    "репликация и репарация ДНК",
    "ENY2":    "транскрипция и экспорт мРНК из ядра",
    "CALML4":  "кальмодулин-подобный белок — кальциевая сигнализация",
    "TBCA":    "кофактор сборки тубулина (цитоскелет)",
    "CETN2":   "центрин — функция центросомы",
}

st.markdown("""
<style>
 .dx { font-weight:800; font-size:2rem; padding:.3rem 0; }
 .disc { background:#FEF9E7; border-left:5px solid #F1C40F; padding:.6rem .9rem;
         border-radius:4px; font-size:.9rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_model():
    import joblib
    return joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None


@st.cache_data
def load_external():
    ext = None
    if os.path.exists(EXT_JSON):
        with open(EXT_JSON, encoding="utf-8") as f:
            ext = json.load(f)
    patients = pd.read_csv(EXT_CSV) if os.path.exists(EXT_CSV) else None
    return ext, patients


def prob_bar(proba):
    fig, ax = plt.subplots(figsize=(9, 0.9))
    left = 0.0
    for ci, s in enumerate(STAGES):
        ax.barh(0, proba[ci], left=left, color=STAGE_COLOR[s], edgecolor="white")
        if proba[ci] > 0.06:
            ax.text(left + proba[ci] / 2, 0, f"{STAGE_RU_SHORT[s]}\n{proba[ci]*100:.0f}%",
                    ha="center", va="center", color="white", fontweight="bold", fontsize=10)
        left += proba[ci]
    ax.set_xlim(0, 1); ax.set_ylim(-0.5, 0.5); ax.axis("off")
    return fig


def contrib_bar(genes, contrib, pred_stage):
    order = np.argsort(np.abs(contrib))[::-1][:12][::-1]
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = [STAGE_COLOR[pred_stage] if contrib[i] > 0 else "#95A5A6" for i in order]
    ax.barh(range(len(order)), contrib[order], color=colors)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([genes[i] for i in order], fontsize=9)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Вклад в стадию (лог-шансы)")
    ax.set_title(f"Почему «{STAGE_RU_SHORT[pred_stage]}»: вклад генов\n"
                 f"цвет — за стадию, серый — против", fontsize=10, fontweight="bold")
    ax.grid(alpha=0.3, axis="x")
    plt.tight_layout()
    return fig


model = load_model()
ext, ext_patients = load_external()

# ── Сайдбар ───────────────────────────────────────────────────────────
with st.sidebar:
    st.title("AD Blood Stage")
    st.caption("Определение стадии болезни Альцгеймера по экспрессии генов крови")
    st.divider()
    if model:
        m = model["metrics"]
        lo, hi = m["macro_auc_ci"]
        st.metric("Генов в панели", len(model["genes"]))
        st.metric("macro ROC-AUC (кросс-валидация)", f"{m['macro_auc']:.2f}",
                  help="Усреднённая по 3 стадиям площадь под ROC-кривой. "
                       "1.0 — идеал, 0.5 — случайность.")
        st.caption(f"95% доверительный интервал: {lo:.2f}–{hi:.2f}")
        st.caption("**AUC по стадиям:** "
                   + " · ".join(f"{STAGE_RU_SHORT[s]} {m['per_class_auc'][s]:.2f}"
                                for s in STAGES))
        if ext:
            e = ext["per_dataset_zscore"]
            st.metric("macro ROC-AUC (независимая когорта)", f"{e['macro_auc']:.2f}",
                      help=f"Проверка на {ext['dataset']}: другие люди и другой чип. "
                           "Ниже, чем на кросс-валидации, — так и должно быть.")
            st.caption(f"95% ДИ: {e['macro_auc_ci'][0]:.2f}–{e['macro_auc_ci'][1]:.2f} · "
                       f"норма против нарушения {e['ctl_vs_impaired_auc']:.2f}")
        st.caption(f"Данные: {GEO_ACCESSION} (AddNeuroMed), цельная кровь, "
                   f"{m['n_samples']} образцов · норма {m['n_per_class']['CTL']} / "
                   f"MCI {m['n_per_class']['MCI']} / деменция {m['n_per_class']['AD']}")
    else:
        st.error("Модель не найдена. Запустите: `python cli.py download` → `python cli.py panel`")

st.title("Стадия болезни Альцгеймера по экспрессии генов крови")
st.markdown("Инструмент **поддержки решения врача**: по уровням экспрессии генов в крови "
            "оценивает стадию — **норма → MCI (промежуточная) → деменция** — "
            "и поясняет, на какие гены опиралась модель.")

if not model:
    st.stop()

genes, ref, scaler, clf = model["genes"], model["ref_ranges"], model["scaler"], model["clf"]

# инициализация значений полей профилем нормы
for g in genes:
    st.session_state.setdefault(f"g_{g}", float(ref[g]["mean"]["CTL"]))


def apply_preset(stage):
    for g in genes:
        st.session_state[f"g_{g}"] = float(ref[g]["mean"][stage])
    st.session_state["true_stage"] = None


def apply_random_patient():
    row = ext_patients.sample(1).iloc[0]
    for g in genes:
        st.session_state[f"g_{g}"] = float(row[g])
    st.session_state["true_stage"] = row["true_stage"]
    st.session_state["true_sample"] = row["sample"]


tab_dx, tab_panel, tab_method = st.tabs(
    ["🔬 Определение стадии", "🧬 Панель и объяснение", "📊 Метод и оценка"])

# ── Вкладка 1: предсказание ────────────────────────────────────────────
with tab_dx:
    st.markdown('<div class="disc">⚠️ НЕ медицинское изделие и не заменяет врача.</div>',
                unsafe_allow_html=True)
    st.write("")
    st.markdown('<div class="disc">📏 <b>Шкала ввода.</b> Модель понимает только значения '
                'в шкале микрочипа Illumina HumanHT-12 v3 после нормализации (log2, как в '
                f'{GEO_ACCESSION}). Результаты qPCR или другого чипа без пересчёта шкалы '
                'дадут неверный ответ: при проверке на другом чипе без пересчёта модель '
                'почти всем ставила «MCI».</div>', unsafe_allow_html=True)
    st.write("")
    st.subheader("Уровни экспрессии генов панели (log2)")
    st.caption("Заполните вручную или подставьте типичный профиль:")

    with st.expander("🧬 Какие гены измеряются и за что они отвечают"):
        st.dataframe(pd.DataFrame({
            "ген": list(genes),
            "за что отвечает": [GENE_INFO.get(g, "—") for g in genes],
            "норма ≈": [f"{ref[g]['mean']['CTL']:.1f}" for g in genes],
            "деменция ≈": [f"{ref[g]['mean']['AD']:.1f}" for g in genes],
        }), width="stretch", hide_index=True)
        st.caption("Большинство генов панели связаны с энергетическим обменом митохондрий и "
                   "синтезом белка. У всех 15 генов экспрессия при MCI и деменции в среднем "
                   "ниже, чем в норме; MCI и деменция между собой различаются слабо.")

    st.session_state.setdefault("true_stage", None)
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Средний профиль: норма", width="stretch"):
        apply_preset("CTL")
    if c2.button("Средний профиль: MCI", width="stretch"):
        apply_preset("MCI")
    if c3.button("Средний профиль: деменция", width="stretch"):
        apply_preset("AD")
    if ext_patients is not None and c4.button("Случайный реальный пациент", width="stretch",
                                              help="Человек из независимой когорты GSE63061, "
                                                   "которую модель не видела. Значения "
                                                   "пересчитаны в шкалу GSE63060."):
        apply_random_patient()
    if st.session_state["true_stage"]:
        st.caption(f"Загружен пациент {st.session_state['true_sample']} из GSE63061. "
                   "Настоящий диагноз покажем после определения стадии.")

    cols = st.columns(3)
    values = []
    for i, g in enumerate(genes):
        r = ref[g]
        with cols[i % 3]:
            v = st.number_input(
                f"{g}  [норма≈{r['mean']['CTL']:.1f} · деменц≈{r['mean']['AD']:.1f}]",
                min_value=float(r["min"]) - 1, max_value=float(r["max"]) + 1,
                step=0.05, format="%.3f", key=f"g_{g}")
            if g in GENE_INFO:
                st.caption(GENE_INFO[g])
            values.append(v)

    st.divider()
    if st.button("Определить стадию", type="primary", width="stretch"):
        x_scaled = scaler.transform(np.array([values], dtype=np.float64))
        proba = clf.predict_proba(x_scaled)[0]
        pred_i = int(np.argmax(proba))
        pred_stage = STAGES[pred_i]

        st.subheader("Результат")
        cc = st.columns(3)
        for ci, s in enumerate(STAGES):
            cc[ci].metric(STAGE_RU[s], f"{proba[ci]*100:.1f}%")
        st.pyplot(prob_bar(proba)); plt.close("all")

        st.markdown(f'<div class="dx" style="color:{STAGE_COLOR[pred_stage]}">'
                    f'Наиболее вероятная стадия: {STAGE_RU[pred_stage]} '
                    f'({proba[pred_i]*100:.0f}%)</div>', unsafe_allow_html=True)

        # уверенность
        top2 = np.sort(proba)[::-1]
        if top2[0] - top2[1] < 0.15:
            st.warning("⚠️ Пограничный результат: две стадии близки по вероятности — "
                       "нужно дообследование.")
        if st.session_state.get("true_stage"):
            ts = st.session_state["true_stage"]
            ok = "совпадает" if ts == pred_stage else "не совпадает"
            st.info(f"Настоящий диагноз этого пациента: **{STAGE_RU[ts]}** — "
                    f"предсказание {ok}. На независимой когорте модель угадывает стадию "
                    f"примерно в половине случаев (при случайном выборе — в трети).")
        if pred_stage == "MCI":
            st.info("MCI — промежуточная стадия и терапевтическое окно: именно здесь "
                    "раннее вмешательство наиболее осмысленно. Строго говоря, MCI — не "
                    "подтверждённая стадия болезни Альцгеймера, а синдром с подозрением "
                    "на её раннее начало. При этом MCI — самый трудный для распознавания "
                    "класс, трактуйте результат осторожно.")

        # персональное объяснение: вклад генов (локальный SHAP линейной модели)
        st.subheader("Объяснение: вклад генов в это решение")
        st.caption("Для линейной модели вклад гена = коэффициент × стандартизованное "
                   "значение (это и есть его локальное SHAP-значение). Цвет — ген "
                   "повышает оценку выбранной стадии; серый — понижает.")
        contrib = clf.coef_[pred_i] * x_scaled[0]
        ce, ct = st.columns([3, 2])
        with ce:
            st.pyplot(contrib_bar(genes, contrib, pred_stage)); plt.close("all")
        with ct:
            df = pd.DataFrame({
                "ген": genes,
                "за что отвечает": [GENE_INFO.get(g, "—") for g in genes],
                "введено": np.round(values, 2),
                "норма≈": [ref[g]["mean"]["CTL"] for g in genes],
                "деменц≈": [ref[g]["mean"]["AD"] for g in genes],
                "вклад": np.round(contrib, 3),
            }).sort_values("вклад", key=np.abs, ascending=False)
            st.dataframe(df, width="stretch", hide_index=True, height=430)

        st.markdown('<div class="disc">Окончательный диагноз ставит врач по результатам '
                    'комплексного обследования. Модель лишь подсказывает и объясняет '
                    'свою оценку.</div>', unsafe_allow_html=True)

# ── Вкладка 2: панель и объяснение ─────────────────────────────────────
with tab_panel:
    st.subheader(f"Панель из {len(genes)} генов крови")
    st.markdown(
        "**Панель** — это небольшой фиксированный набор генов, экспрессию которых "
        "измеряют вместе как один анализ (как биохимическая панель крови). "
        f"Здесь — всего **{len(genes)} генов** из **{model['metrics']['n_genes_total']}**, "
        "отобранных по силе различия стадий (ANOVA F-критерий, строго внутри фолдов "
        "кросс-валидации), чтобы тест можно было сделать дёшево. Биологически панель "
        "отражает **снижение энергетического обмена и синтеза белка** (митохондриальные "
        "и рибосомальные гены) по мере прогрессирования болезни.")
    for img, cap in [("biomarker_panel.png", "Качество vs размер панели и важность генов"),
                     ("shap_summary.png", "Глобальная важность генов по SHAP")]:
        p = os.path.join(RESULTS_FOLDER, img)
        if os.path.exists(p):
            st.image(p, caption=cap, width="stretch")
    if os.path.exists(PANEL_CSV):
        df = pd.read_csv(PANEL_CSV)
        df["биология"] = df["gene"].map(GENE_INFO).fillna("—")
        st.dataframe(df, width="stretch", hide_index=True)

# ── Вкладка 3: метод и оценка ──────────────────────────────────────────
with tab_method:
    m = model["metrics"]
    st.subheader("Как оценено качество")
    st.markdown(f"""
- **Данные:** {GEO_ACCESSION} (когорта AddNeuroMed), цельная кровь, {m['n_samples']} образцов:
  норма {m['n_per_class']['CTL']} · MCI {m['n_per_class']['MCI']} · деменция {m['n_per_class']['AD']}.
- **Модель:** мультиномиальная логистическая регрессия по панели генов.
- **Валидация:** стратифицированная кросс-валидация 5×5; отбор генов и масштабирование —
  **строго внутри обучающих фолдов** (без утечки). Контроль: «наивный» отбор на всех
  данных даёт macro-AUC {m['macro_auc_naive']:.2f} ≈ {m['macro_auc']:.2f} →
  утечка при отборе генов мала. Проверить, что модель работает на **других людях**,
  можно только на независимой когорте — см. ниже.
- **Качество (macro-AUC):** **{m['macro_auc']:.2f}** (95% ДИ
  {m['macro_auc_ci'][0]:.2f}–{m['macro_auc_ci'][1]:.2f}).
""")
    st.markdown("**AUC по каждой стадии (one-vs-rest):**")
    st.dataframe(pd.DataFrame({
        "стадия": [STAGE_RU[s] for s in STAGES],
        "AUC": [f"{m['per_class_auc'][s]:.2f}" for s in STAGES],
        "95% ДИ": [f"{m['per_class_auc_ci'][s][0]:.2f}–{m['per_class_auc_ci'][s][1]:.2f}"
                   for s in STAGES],
    }), width="stretch", hide_index=True)
    p = os.path.join(RESULTS_FOLDER, "metrics.png")
    if os.path.exists(p):
        st.image(p, caption="Матрица ошибок и ROC по стадиям", width="stretch")

    if ext:
        e, r = ext["per_dataset_zscore"], ext["no_rescaling"]
        n = ext["n_per_class"]
        st.subheader(f"Проверка на независимой когорте {ext['dataset']}")
        st.markdown(f"""
Вторая партия AddNeuroMed: **другие люди** (норма {n['CTL']} · MCI {n['MCI']} ·
деменция {n['AD']}) и **другой чип** (Illumina HumanHT-12 v4). Модель обучена на всём
{GEO_ACCESSION} и ни разу не видела этих людей. Шкалы чипов разные, поэтому каждый
датасет стандартизован отдельно.
""")
        st.dataframe(pd.DataFrame({
            "метрика": ["macro ROC-AUC", "AUC норма", "AUC MCI", "AUC деменция",
                        "норма против нарушения", "MCI против деменции",
                        "balanced accuracy (случайно — 0.33)"],
            f"{GEO_ACCESSION}, кросс-валидация": [
                f"{m['macro_auc']:.2f}", *[f"{m['per_class_auc'][s]:.2f}" for s in STAGES],
                "—", "—", f"{m['bal_acc'][0]:.2f}"],
            f"{ext['dataset']}, независимая": [
                f"{e['macro_auc']:.2f} ({e['macro_auc_ci'][0]:.2f}–{e['macro_auc_ci'][1]:.2f})",
                *[f"{e['per_class_auc'][s]:.2f}" for s in STAGES],
                f"{e['ctl_vs_impaired_auc']:.2f}", f"{e['mci_vs_ad_auc']:.2f}",
                f"{e['bal_acc']:.2f}"],
        }), width="stretch", hide_index=True)
        st.caption(f"Без пересчёта шкалы под новый чип balanced accuracy падает до "
                   f"{r['bal_acc']:.2f}: модель почти всем ставит «MCI». Поэтому для "
                   "реального применения нужна калибровка под платформу лаборатории.")

    if os.path.exists(CMP_CSV):
        st.subheader("Почему логистическая регрессия")
        st.markdown("Все модели проверены одинаково: та же кросс-валидация без утечки и та же "
                    "независимая когорта. Сложные модели не дают заметного выигрыша, а "
                    "логистическая регрессия проще, устойчивее и объясняет каждое решение.")
        st.dataframe(pd.read_csv(CMP_CSV), width="stretch", hide_index=True)
        p = os.path.join(RESULTS_FOLDER, "model_comparison.png")
        if os.path.exists(p):
            st.image(p, width="stretch")
    st.markdown("""
**Ограничения (важно для интерпретации):**
- **MCI распознаётся хуже всего** — это трудно распознаваемая промежуточная стадия
  (в литературе AUC ~0.55–0.80); модель часто путает MCI с соседними стадиями.
- Сильнее всего модель отделяет **норму от болезни** — в случае плохого анализа крови
  направляет на дообследование.
- Гены панели сильно связаны между собой (медианная корреляция ≈0.85): по сути
  панель измеряет один общий показатель. Поэтому вклад отдельного гена в объяснении
  нужно читать как вклад всей группы похожих генов.
- Данные — одна когорта AddNeuroMed (две партии); диагнозы клинические, без
  биомаркеров амилоида и тау. Для клиники нужны проверка в других популяциях,
  калибровка под лабораторную платформу и проспективное исследование.
- Это **прототип для поддержки решения**, а не сертифицированный диагностический тест.
""")
