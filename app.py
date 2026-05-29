"""
Веб-инструмент поддержки врача: определение СТАДИИ болезни Альцгеймера
(норма → MCI → деменция) по мини-панели генов крови, с объяснением решения.

Врач вводит уровни экспрессии генов панели (из qPCR/микрочипа по образцу крови),
модель выдаёт вероятности трёх стадий и ПЕРСОНАЛЬНОЕ объяснение: какие гены и
насколько повлияли на вывод (локальные SHAP-вклады линейной модели).

Запуск: streamlit run app.py
"""

import os
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import (RESULTS_FOLDER, STAGES, STAGE_RU, STAGE_RU_SHORT,
                    STAGE_COLOR, GEO_ACCESSION)

st.set_page_config(page_title="AD Blood Stage", page_icon="🩸", layout="wide")

MODEL_PATH = os.path.join(RESULTS_FOLDER, "panel_model.pkl")
PANEL_CSV  = os.path.join(RESULTS_FOLDER, "biomarker_panel.csv")

# Краткая биология генов панели (преобладают энергетический обмен и синтез белка)
GENE_INFO = {
    "MRPL51":  "митохондриальный рибосомальный белок — синтез белка в митохондриях",
    "NDUFA1":  "субъединица комплекса I дыхательной цепи (известный маркер AD)",
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

# ── Сайдбар ───────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🩸 AD Blood Stage")
    st.caption("Определение стадии болезни Альцгеймера по мини-панели генов крови")
    st.divider()
    if model:
        m = model["metrics"]
        lo, hi = m["macro_auc_ci"]
        st.metric("Генов в панели", len(model["genes"]))
        st.metric("macro ROC-AUC (честная CV)", f"{m['macro_auc']:.2f}",
                  help="Усреднённая по 3 стадиям площадь под ROC-кривой. "
                       "1.0 — идеал, 0.5 — случайность.")
        st.caption(f"95% доверительный интервал: {lo:.2f}–{hi:.2f}")
        st.caption("**AUC по стадиям:** "
                   + " · ".join(f"{STAGE_RU_SHORT[s]} {m['per_class_auc'][s]:.2f}"
                                for s in STAGES))
        st.caption(f"Данные: {GEO_ACCESSION} (AddNeuroMed), цельная кровь, "
                   f"{m['n_samples']} образцов · норма {m['n_per_class']['CTL']} / "
                   f"MCI {m['n_per_class']['MCI']} / деменция {m['n_per_class']['AD']}")
    else:
        st.error("Модель не найдена. Запустите: `python cli.py download` → `python cli.py panel`")

st.title("Стадия болезни Альцгеймера по экспрессии генов крови")
st.markdown("Инструмент **поддержки решения врача**: по уровням экспрессии генов мини-панели "
            "(анализ крови) оценивает стадию — **норма → MCI (промежуточная) → деменция** — "
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


tab_dx, tab_panel, tab_method = st.tabs(
    ["🔬 Определение стадии", "🧬 Панель и объяснение", "📊 Метод и честность"])

# ── Вкладка 1: предсказание ────────────────────────────────────────────
with tab_dx:
    st.markdown('<div class="disc">⚠️ Исследовательский/учебный прототип. '
                'НЕ медицинское изделие и не заменяет врача — это вспомогательный '
                'инструмент. Промежуточная стадия (MCI) распознаётся труднее всего '
                '(см. вкладку «Метод и честность»).</div>', unsafe_allow_html=True)
    st.write("")
    st.subheader("Уровни экспрессии генов панели (log2)")
    st.caption("Заполните вручную или подставьте типичный профиль:")
    c1, c2, c3 = st.columns(3)
    if c1.button("Пример: норма", width="stretch"):
        apply_preset("CTL")
    if c2.button("Пример: MCI", width="stretch"):
        apply_preset("MCI")
    if c3.button("Пример: деменция", width="stretch"):
        apply_preset("AD")

    cols = st.columns(3)
    values = []
    for i, g in enumerate(genes):
        r = ref[g]
        with cols[i % 3]:
            v = st.number_input(
                f"{g}  [норма≈{r['mean']['CTL']:.1f} · деменц≈{r['mean']['AD']:.1f}]",
                min_value=float(r["min"]) - 1, max_value=float(r["max"]) + 1,
                step=0.05, format="%.3f", key=f"g_{g}")
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
        if pred_stage == "MCI":
            st.info("MCI — промежуточная стадия и терапевтическое окно: именно здесь "
                    "раннее вмешательство наиболее осмысленно. При этом MCI — самый "
                    "трудный для распознавания класс, трактуйте результат осторожно.")

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
                "ген": genes, "введено": np.round(values, 2),
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
    st.subheader(f"Мини-панель из {len(genes)} генов крови")
    st.markdown(
        f"Панель отобрана из **{model['metrics']['n_genes_total']} генов** транскриптома "
        "крови по силе различия стадий (ANOVA F-критерий, отбор строго внутри фолдов "
        "кросс-валидации). Биологически панель отражает **снижение энергетического "
        "обмена и синтеза белка** (митохондриальные и рибосомальные гены) по мере "
        "прогрессирования болезни.")
    for img, cap in [("biomarker_panel.png", "Качество vs размер панели и важность генов"),
                     ("shap_summary.png", "Глобальная важность генов по SHAP")]:
        p = os.path.join(RESULTS_FOLDER, img)
        if os.path.exists(p):
            st.image(p, caption=cap, width="stretch")
    if os.path.exists(PANEL_CSV):
        df = pd.read_csv(PANEL_CSV)
        df["биология"] = df["gene"].map(GENE_INFO).fillna("—")
        st.dataframe(df, width="stretch", hide_index=True)

# ── Вкладка 3: метод и честность ───────────────────────────────────────
with tab_method:
    m = model["metrics"]
    st.subheader("Как оценено качество (честно)")
    st.markdown(f"""
- **Данные:** {GEO_ACCESSION} (когорта AddNeuroMed), цельная кровь, {m['n_samples']} образцов:
  норма {m['n_per_class']['CTL']} · MCI {m['n_per_class']['MCI']} · деменция {m['n_per_class']['AD']}.
- **Модель:** мультиномиальная логистическая регрессия по мини-панели генов.
- **Валидация:** стратифицированная кросс-валидация; отбор генов и масштабирование —
  **строго внутри обучающих фолдов** (без утечки). Контроль: «наивный» отбор на всех
  данных даёт macro-AUC {m['macro_auc_naive']:.2f} ≈ честные {m['macro_auc']:.2f} →
  **утечки/переобучения нет**.
- **Качество (честный macro-AUC):** **{m['macro_auc']:.2f}** (95% ДИ
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
    st.markdown("""
**Честные ограничения (важно для интерпретации):**
- **MCI распознаётся хуже всего** — это объективно трудная промежуточная стадия
  (в литературе AUC ~0.55–0.80); модель часто путает MCI с соседними стадиями.
- Сильнее всего модель отделяет **норму от болезни** — это и есть её скрининговая
  ценность: «кровь выглядит ненормально → направить на дообследование».
- Данные — одна когорта; для клиники нужна независимая внешняя валидация
  (например, GSE63061) и проспективное исследование.
- Это **прототип для поддержки решения**, а не сертифицированный диагностический тест.
""")
