"""
Веб-интерфейс для демонстрации на защите.
Запуск: streamlit run app.py
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Настройки страницы ────────────────────────────────────────────────

st.set_page_config(
    page_title="Диагностика болезни Альцгеймера",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a253a, #2e86c1);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    .diagnosis-CN  { color: #2ECC71; font-weight: bold; font-size: 2rem; }
    .diagnosis-MCI { color: #F39C12; font-weight: bold; font-size: 2rem; }
    .diagnosis-AD  { color: #E74C3C; font-weight: bold; font-size: 2rem; }
</style>
""", unsafe_allow_html=True)

# ── Сайдбар ───────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Brain_icon.svg/240px-Brain_icon.svg.png", width=80)
    st.title("Alzheimer DX")
    st.caption("Мультимодальная диагностика болезни Альцгеймера")
    st.divider()

    mode = st.radio(
        "Режим",
        ["Демо: одиночный пациент", "Обучение на синтетических данных", "Обучение на Kaggle OASIS"],
        index=0,
    )

    st.divider()
    st.markdown("**Модель:** MultimodalADNet  \n"
                "**Данные:** OASIS / GSE138852  \n"
                "**Точность:** ~85–90% (ROC-AUC)")

# ── Заголовок ─────────────────────────────────────────────────────────

st.title("🧠 Мультимодальная диагностика болезни Альцгеймера")
st.markdown("МРТ-признаки + клинические данные → Gated Fusion нейросеть → CN / MCI / AD")
st.divider()


# ── Режим 1: Одиночный пациент (демо) ────────────────────────────────

def page_single_patient():
    st.header("Предсказание диагноза для пациента")

    col_mri, col_clin = st.columns(2)

    with col_mri:
        st.subheader("МРТ-данные (FreeSurfer)")
        lh_hipp = st.slider("Левый гиппокамп (мм³)", 1000, 5000, 3200)
        rh_hipp = st.slider("Правый гиппокамп (мм³)", 1000, 5000, 3100)
        lh_amyg = st.slider("Левая миндалина (мм³)", 800, 2500, 1600)
        rh_amyg = st.slider("Правая миндалина (мм³)", 800, 2500, 1550)
        lh_entr = st.slider("Толщина энторинальной коры L (мм)", 1.5, 5.0, 3.2)
        rh_entr = st.slider("Толщина энторинальной коры R (мм)", 1.5, 5.0, 3.1)
        ventricle = st.slider("Объём желудочков (мм³)", 5000, 60000, 20000)
        brain_vol = st.slider("Общий объём мозга (мм³)", 900000, 1500000, 1200000)

    with col_clin:
        st.subheader("Клинические показатели")
        age      = st.slider("Возраст", 50, 95, 72)
        sex      = st.selectbox("Пол", ["Мужчина", "Женщина"])
        apoe4    = st.selectbox("APOE4 аллели (0 / 1 / 2 копии ε4)", [0, 1, 2])
        edu      = st.slider("Лет образования", 6, 22, 14)
        mmse     = st.slider("MMSE (0–30)", 0, 30, 26)

    st.divider()

    if st.button("Поставить диагноз", type="primary", use_container_width=True):
        _run_single_inference(
            mri=np.array([[lh_hipp, rh_hipp, lh_amyg, rh_amyg,
                           lh_entr, rh_entr, lh_entr, rh_entr,
                           3.0, 2.9, 3.1, 3.0, 3.2, 3.1, 3.0, 2.9,
                           ventricle, ventricle * 0.95, ventricle * 0.3, brain_vol]],
                         dtype=np.float32),
            clin=np.array([[age, 1 if sex == "Женщина" else 0,
                            apoe4, edu, mmse]], dtype=np.float32),
        )


def _run_single_inference(mri, clin):
    try:
        from generate_synthetic_oasis import generate
        from data_loader_oasis import OASISLoader
        from multimodal_classifier import MultimodalClassifier
        from config import RESULTS_FOLDER, MRI_KEY_ROIS, CLINICAL_FEATURES

        with st.spinner("Загружаю предобученную модель..."):
            import torch
            import joblib
            from multimodal_classifier import MultimodalADNet
            from config import RESULTS_FOLDER

            model_path  = os.path.join(RESULTS_FOLDER, "multimodal_model.pt")
            mri_sc_path = os.path.join(RESULTS_FOLDER, "mri_scaler.pkl")
            clin_sc_path= os.path.join(RESULTS_FOLDER, "clin_scaler.pkl")

            if not os.path.exists(model_path):
                st.warning("Модель ещё не обучена. Перейдите в режим 'Обучение' и запустите тренировку.")
                return

            checkpoint = torch.load(model_path, map_location="cpu")
            if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
                mri_dim   = checkpoint["mri_dim"]
                clin_dim  = checkpoint["clin_dim"]
                n_classes = checkpoint["n_classes"]
                state_dict = checkpoint["state_dict"]
            else:
                # старый формат — определяем размерность из весов
                state_dict = checkpoint
                mri_dim   = state_dict["mri_encoder.net.0.weight"].shape[1]
                clin_dim  = state_dict["clin_encoder.net.0.weight"].shape[1]
                n_classes = state_dict["classifier.3.weight"].shape[0]

            # Скалеры: из файла или подгоняем на лету
            if os.path.exists(mri_sc_path) and os.path.exists(clin_sc_path):
                mri_scaler  = joblib.load(mri_sc_path)
                clin_scaler = joblib.load(clin_sc_path)
            else:
                from sklearn.preprocessing import RobustScaler, StandardScaler
                from generate_synthetic_oasis import generate
                from data_loader_oasis import OASISLoader
                os.makedirs("data/oasis", exist_ok=True)
                if not os.path.exists("data/oasis/mri_features.csv"):
                    generate()
                loader = OASISLoader()
                loader.load()
                X_mri_all, X_clin_all, *_ = loader.get_feature_matrices()
                mri_scaler  = RobustScaler().fit(X_mri_all)
                clin_scaler = StandardScaler().fit(X_clin_all)

            mri_s  = mri_scaler.transform(mri[:, :mri_dim]).astype(np.float32)
            clin_s = clin_scaler.transform(clin[:, :clin_dim]).astype(np.float32)

            model = MultimodalADNet(mri_dim, clin_dim, n_classes=n_classes)
            model.load_state_dict(state_dict)
            model.eval()

            with torch.no_grad():
                logits, gate, _, _ = model(
                    torch.from_numpy(mri_s),
                    torch.from_numpy(clin_s),
                )
            probs = torch.softmax(logits, dim=1).numpy()[0]
            pred  = probs.argmax()
            gate_val = gate.numpy()[0].mean()

        labels = {0: "CN (норма)", 1: "MCI (лёгкое снижение)", 2: "AD (Альцгеймер)"}
        colors = {0: "#2ECC71",     1: "#F39C12",               2: "#E74C3C"}
        css    = {0: "diagnosis-CN", 1: "diagnosis-MCI",         2: "diagnosis-AD"}

        c1, c2, c3 = st.columns(3)
        c1.metric("Вероятность CN",  f"{probs[0]*100:.1f}%")
        c2.metric("Вероятность MCI", f"{probs[1]*100:.1f}%")
        c3.metric("Вероятность AD",  f"{probs[2]*100:.1f}%")

        st.markdown(f'<div class="{css[pred]}">Диагноз: {labels[pred]}</div>',
                    unsafe_allow_html=True)
        st.markdown(f"**Gate-вес (МРТ vs клиника):** {gate_val:.2f} "
                    f"({'МРТ доминирует' if gate_val > 0.5 else 'Клиника доминирует'})")

        # Бар-диаграмма вероятностей
        fig, ax = plt.subplots(figsize=(5, 2.5))
        ax.barh(["CN", "MCI", "AD"], probs,
                color=[colors[i] for i in range(3)])
        ax.set_xlim(0, 1)
        ax.set_xlabel("Вероятность")
        ax.axvline(0.5, color="gray", linestyle="--", linewidth=0.8)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    except Exception as e:
        st.error(f"Ошибка: {e}")


# ── Режим 2 и 3: Обучение ────────────────────────────────────────────

def page_train(use_kaggle=False):
    label = "Kaggle OASIS (реальные)" if use_kaggle else "синтетические данные OASIS-3"
    st.header(f"Обучение модели — {label}")

    if use_kaggle:
        st.info("Для реальных данных сначала выполните: `python cli.py setup-kaggle`")
        data_ok = (os.path.exists("data/kaggle/oasis_longitudinal.csv") and
                   os.path.exists("data/kaggle/oasis_cross-sectional.csv"))
        if not data_ok:
            st.error("Файлы Kaggle не найдены. Поместите их в `data/kaggle/`")
            return
    else:
        if not os.path.exists("data/oasis/mri_features.csv"):
            if st.button("Создать синтетические данные"):
                with st.spinner("Генерирую..."):
                    from generate_synthetic_oasis import generate
                    generate()
                st.success("Данные созданы!")
                st.rerun()
            return

    if st.button("Запустить обучение", type="primary"):
        _run_training(use_kaggle)


def _run_training(use_kaggle):
    from config import RESULTS_FOLDER
    os.makedirs(RESULTS_FOLDER, exist_ok=True)

    try:
        with st.spinner("Загружаю данные..."):
            if use_kaggle:
                from data_loader_kaggle import KaggleOASISLoader
                loader = KaggleOASISLoader()
            else:
                from data_loader_oasis import OASISLoader
                loader = OASISLoader()
            loader.load()
            X_mri, X_clin, y, groups, mri_cols, clin_cols = loader.get_feature_matrices()

        st.success(f"Загружено: {len(y)} примеров, {len(mri_cols)} МРТ + {len(clin_cols)} клин. признаков")
        _show_class_dist(y)

        with st.spinner("Обучаю Gated Fusion нейросеть (50 эпох)..."):
            from multimodal_classifier import MultimodalClassifier
            clf     = MultimodalClassifier()
            metrics = clf.train(X_mri, X_clin, y, groups,
                                mri_names=mri_cols, clin_names=clin_cols)

        st.success(f"Готово! Accuracy: {metrics['accuracy']:.3f}  ROC-AUC: {metrics['roc_auc']:.3f}")
        _show_results(metrics, mri_cols, loader.df)

    except Exception as e:
        st.error(f"Ошибка обучения: {e}")
        import traceback
        st.code(traceback.format_exc())


def _show_class_dist(y):
    labels = {0: "CN", 1: "MCI", 2: "AD"}
    counts = {labels[i]: int((y == i).sum()) for i in range(3)}
    st.bar_chart(pd.Series(counts))


def _show_results(metrics, mri_cols, df):
    from visualizer_multimodal import MultimodalVisualizer
    from config import RESULTS_FOLDER

    viz = MultimodalVisualizer()
    viz.plot_training_loss(metrics["losses"])
    viz.plot_multihead_roc(metrics["y_true"], metrics["probs"],
                           metrics["probs_mri_only"], metrics["probs_clin_only"])
    viz.plot_confusion_matrix(metrics["y_true"], metrics["preds"])
    viz.plot_gate_weights(metrics["gates"], metrics["y_true"])
    viz.plot_roi_importance(mri_cols, metrics["mri_importance"])
    viz.plot_biomarker_trajectory(df)
    viz.plot_fusion_umap(metrics["embeddings"], metrics["y_true"])

    image_files = {
        "Кривая обучения":       "training_loss.png",
        "ROC-кривые":            "multihead_roc.png",
        "Матрица ошибок":        "confusion_matrix.png",
        "Gate-веса":             "gate_weights.png",
        "Важность МРТ-регионов": "roi_importance.png",
        "Биомаркеры (CN→MCI→AD)":"biomarker_trajectory.png",
        "UMAP эмбеддингов":      "fusion_umap.png",
    }

    tabs = st.tabs(list(image_files.keys()))
    for tab, (title, fname) in zip(tabs, image_files.items()):
        path = os.path.join(RESULTS_FOLDER, fname)
        if os.path.exists(path):
            with tab:
                st.image(path, use_column_width=True)


# ── Роутинг ───────────────────────────────────────────────────────────

if mode == "Демо: одиночный пациент":
    page_single_patient()
elif mode == "Обучение на синтетических данных":
    page_train(use_kaggle=False)
else:
    page_train(use_kaggle=True)
