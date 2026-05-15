# Литературный обзор

## 1. Болезнь Альцгеймера: молекулярные механизмы

Болезнь Альцгеймера (БА) — нейродегенеративное заболевание, характеризующееся
накоплением амилоид-бета бляшек и нейрофибриллярных клубков тау-белка.
На молекулярном уровне БА проявляется нарушением синаптической передачи,
митохондриальной дисфункцией и нейровоспалением.

**Ключевые работы:**
- Selkoe D.J., Hardy J. (2016). The amyloid hypothesis of Alzheimer's disease
  at 25 years. *EMBO Mol Med*, 8(6), 595–608.
- Jack C.R. et al. (2018). NIA-AA Research Framework: biomarkers of Alzheimer's
  continuum. *Alzheimers Dement*, 14(4), 535–562.

## 2. Датасет OASIS-3

LaMontagne P.J. et al. (2019). OASIS-3: Longitudinal Neuroimaging, Clinical,
and Cognitive Dataset for Normal Aging and Alzheimer's Disease.
*medRxiv*, doi: 10.1101/2019.12.13.19014902.

Датасет содержит данные 1378 участников (>55 лет) под наблюдением центра
Knight ADRC (Вашингтонский университет):
- Структурные МРТ (T1-weighted)
- FreeSurfer морфометрия (объёмы, толщина коры)
- Когнитивные тесты: CDR, MMSE
- Генотипирование APOE
- Продольные визиты: до 10+ лет наблюдения

## 3. МРТ-биомаркеры ранней стадии AD

Атрофия гиппокампа — один из самых ранних и надёжных маркеров:
- Гиппокамп теряет 3–5% объёма в год при MCI (Jack et al., 2010)
- Энторинальная кора атрофируется раньше гиппокампа (Braak stages I–II)

FreeSurfer (Fischl B., 2012) автоматически сегментирует 68 корковых регионов
и 34 подкорковых структуры, что позволяет извлекать ROI-признаки без ручной
разметки.

**Ключевые работы:**
- Jack C.R. et al. (2010). Hypothetical model of dynamic biomarkers.
  *Lancet Neurol*, 9(1), 119–128.
- Fischl B. (2012). FreeSurfer. *NeuroImage*, 62(2), 774–781.
- Dickerson B.C. et al. (2011). Entorhinal cortex atrophy as an early marker
  of AD. *Annals of Neurology*, 69(2), 283–291.

## 4. Клинические биомаркеры

**MMSE (Mini-Mental State Examination):** стандартизированный тест когниции
(0–30 баллов). Норма ≥26, MCI: 20–25, деменция: <20. Широко применяется
как первичный скрининг.

**CDR (Clinical Dementia Rating):** многомерная оценка деменции (0–3).
CDR 0 = норма, CDR 0.5 = сомнительная деменция, CDR 1 = лёгкая.

**APOE ε4:** главный генетический фактор риска AD. Носители одной копии имеют
3-кратный риск, двух копий — 8-кратный (Corder E.H. et al., 1993).

## 5. Мультимодальные методы диагностики AD

Объединение МРТ и клинических данных улучшает точность по сравнению
с однородными методами:

- Zhang D. et al. (2011). Multimodal classification of Alzheimer's disease
  combining structural MRI, PET and CSF biomarkers.
  *NeuroImage*, 55(3), 856–867. AUC = 0.93

- Liu M. et al. (2018). Multi-modality cascaded convolutional neural networks
  for Alzheimer's disease diagnosis.
  *Neuroinformatics*, 16, 295–308.

- Spasov S. et al. (2019). A parameter-efficient deep learning approach to
  predict conversion from MCI to Alzheimer's disease.
  *NeuroImage*, 189, 276–287. AUC = 0.925

## 6. Gated Fusion в мультимодальном обучении

Gated fusion позволяет модели динамически взвешивать вклад каждой модальности:

- Arevalo J. et al. (2017). Gated Multimodal Units for Information Fusion.
  *arXiv*, 1702.01992. — первая применение gate для мультимодального фьюжена

- Kiela D. et al. (2018). Dynamic Meta-Embeddings for Improved Sentence
  Representations. *EMNLP*. — gate-механизм для слияния пространств

Биологическое обоснование для AD: на ранней стадии (MCI) МРТ-изменения
могут быть ещё незначительны, тогда как клинические симптомы более выражены —
gate позволяет автоматически перераспределить доверие.

## 7. Предотвращение переобучения в биомедицинских данных

Основная проблема — малый размер выборки при высокой размерности:

- Varoquaux G. (2018). Cross-validation failure: small sample sizes lead to
  large error bars. *NeuroImage*, 180, 68–77.

- Woo C.W. et al. (2017). Cluster-extent based thresholding in fMRI analyses:
  Pitfalls and recommendations. *NeuroImage*, 91, 412–419.

**Решения применяемые в проекте:**
  - GroupShuffleSplit по subject_id (donor-level split)
  - Weighted CrossEntropyLoss (дисбаланс классов)
  - Dropout (0.3) + Weight Decay (1e-4)
  - BatchNorm в MRIEncoder (стабилизация обучения)

## 8. Исследовательский анализ (scRNA-seq GSE138852)

Mathys H. et al. (2019). Single-cell transcriptomic analysis of Alzheimer's disease.
*Nature*, 570, 332–337.

Датасет содержит scRNA-seq профили 80 пациентов (48 с БА, 32 контрольных)
из энторинальной коры. Наибольшее число DEG — в нейронах и микроглии.
