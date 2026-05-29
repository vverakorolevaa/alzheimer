"""
Веб-интерфейс: диагностика болезни Альцгеймера по мини-панели генов.

Врач/исследователь вводит уровни экспрессии 12 генов панели (из qPCR/NanoString),
модель выдаёт вероятность болезни Альцгеймера и биологическую интерпретацию.

Запуск: streamlit run app.py
"""

import os
import numpy as np
import pandas as pd
import streamlit as st

from config import RESULTS_FOLDER

st.set_page_config(page_title="AD Gene Panel", page_icon="🧬", layout="wide")

st.markdown("""
<style>
    .dx-AD { color:#E74C3C; font-weight:bold; font-size:2rem; }
    .dx-CT { color:#2ECC71; font-weight:bold; font-size:2rem; }
</style>
""", unsafe_allow_html=True)

MODEL_PATH = os.path.join(RESULTS_FOLDER, "panel_model.pkl")
PANEL_CSV  = os.path.join(RESULTS_FOLDER, "biomarker_panel.csv")

# Краткая биологическая справка по генам панели
GENE_INFO = {
    "LINGO1":    "негативный регулятор миелинизации, терапевтическая мишень AD",
    "NRXN1":     "нейрексин — синаптическая адгезия; снижение = дисфункция синапсов",
    "NEAT1":     "длинная некодирующая РНК, стабильно повышена при AD",
    "RORA":      "циркадный транскрипционный фактор, ассоциирован с AD",
    "SPP1":      "остеопонтин — маркер активации микроглии при нейровоспалении",
    "HSPA1A":    "белок теплового шока — протеостаз при нейродегенерации",
    "LSAMP":     "молекула адгезии нейронов лимбической системы",
    "CTNNA2":    "катенин α2 — стабильность синаптических контактов",
    "GPM6A":     "мембранный гликопротеин нейронов, рост отростков",
    "NKAIN3":    "взаимодействует с Na/K-АТФазой в нейронах",
    "LINC00486": "длинная некодирующая РНК",
    "FAM155A":   "субъединица ионного канала NALCN в нейронах",
}


@st.cache_resource
def load_model():
    import joblib
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)


# ── Сайдбар ───────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧬 AD Gene Panel")
    st.caption("Ранняя диагностика болезни Альцгеймера по мини-панели генов")
    st.divider()
    model = load_model()
    if model:
        st.metric("Генов в панели", len(model["genes"]))
        st.metric("ROC-AUC (площадь под кривой, 0→1)",
                  f"{model['cv_auc']:.2f} ± {model['cv_auc_std']:.2f}")
        st.caption("ROC-AUC = вероятность того, что больной получит более высокий "
                   "балл, чем здоровый. 1.0 = идеал, 0.5 = случайность.")
        st.caption("Данные: GSE138852 (Grubman et al., 2019), "
                   "энторинальная кора, scRNA-seq")
    else:
        st.error("Модель не найдена. Запустите: `python cli.py panel`")

st.title("Диагностика болезни Альцгеймера по экспрессии генов")
st.markdown("Введите уровни экспрессии генов панели (log-нормализованные, как из scRNA-seq/qPCR) "
            "→ модель оценит вероятность болезни Альцгеймера.")
st.divider()

if not model:
    st.warning("Сначала обучите панель: `python cli.py download` затем `python cli.py panel`")
    st.stop()

genes      = model["genes"]
ref        = model["ref_ranges"]
scaler     = model["scaler"]
clf        = model["clf"]

tab_dx, tab_panel = st.tabs(["Предсказание", "О панели"])

# ── Вкладка: предсказание ─────────────────────────────────────────────
with tab_dx:
    st.subheader("Уровни экспрессии генов")

    # Кнопки автозаполнения типичными профилями
    c1, c2, _ = st.columns([1, 1, 3])
    preset = None
    if c1.button("Пример: здоровый"):
        preset = "ct"
    if c2.button("Пример: больной AD"):
        preset = "ad"

    cols = st.columns(3)
    values = []
    for i, g in enumerate(genes):
        r = ref[g]
        default = r["mean_ad"] if preset == "ad" else (
                  r["mean_ct"] if preset == "ct" else (r["mean_ct"] + r["mean_ad"]) / 2)
        with cols[i % 3]:
            v = st.number_input(
                f"{g}  [норма≈{r['mean_ct']}, AD≈{r['mean_ad']}]",
                min_value=float(r["min"]), max_value=float(r["max"]),
                value=float(round(default, 3)), step=0.01, format="%.3f",
                key=f"gene_{g}",
            )
            values.append(v)

    st.divider()
    if st.button("Поставить диагноз", type="primary", use_container_width=True):
        X = scaler.transform(np.array([values], dtype=np.float64))
        proba = clf.predict_proba(X)[0]
        p_ad = float(proba[1])
        pred_ad = p_ad >= 0.5

        c1, c2 = st.columns(2)
        c1.metric("Вероятность: здоров", f"{(1 - p_ad) * 100:.1f}%")
        c2.metric("Вероятность: болезнь Альцгеймера", f"{p_ad * 100:.1f}%")

        cls = "dx-AD" if pred_ad else "dx-CT"
        label = "Болезнь Альцгеймера (AD)" if pred_ad else "Норма (контроль)"
        st.markdown(f'<div class="{cls}">Заключение: {label}</div>',
                    unsafe_allow_html=True)

        # Какие гены тянут к AD
        st.subheader("Вклад генов в решение")
        st.caption("Сравнение введённых значений с типичными уровнями нормы и AD:")
        contrib = []
        for g, v in zip(genes, values):
            r = ref[g]
            # ближе к среднему AD или контроля?
            d_ad = abs(v - r["mean_ad"])
            d_ct = abs(v - r["mean_ct"])
            toward = "→ AD" if d_ad < d_ct else "→ норма"
            contrib.append({
                "ген": g, "введено": round(v, 3),
                "норма≈": r["mean_ct"], "AD≈": r["mean_ad"],
                "указывает": toward,
            })
        st.dataframe(pd.DataFrame(contrib), use_container_width=True, hide_index=True)

        if 0.4 < p_ad < 0.6:
            st.warning("⚠️ Пограничный результат — требуется дообследование.")
        st.info("Результат носит вспомогательный характер. Окончательный диагноз "
                "ставит врач на основании комплексного обследования.")

# ── Вкладка: о панели ─────────────────────────────────────────────────
with tab_panel:
    st.subheader("Состав панели и валидация")
    st.markdown(
        f"Панель из **{len(genes)} генов** отобрана из ~10 850 генов транскриптома. "
        f"Честная валидация на уровне доноров даёт ROC-AUC "
        f"**{model['cv_auc']:.2f} ± {model['cv_auc_std']:.2f}** — это оценка работы "
        "на новом, ранее не виденном пациенте."
    )

    img = os.path.join(RESULTS_FOLDER, "biomarker_panel.png")
    if os.path.exists(img):
        st.image(img, use_column_width=True)

    if os.path.exists(PANEL_CSV):
        df = pd.read_csv(PANEL_CSV)
        df["биология"] = df["gene"].map(GENE_INFO).fillna("—")
        st.dataframe(df, use_container_width=True, hide_index=True)
