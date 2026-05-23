 ---
  # Мультимодальная ранняя диагностика болезни Альцгеймера                                                               
                                                                                                                       
  Курсовой проект по биоинформатике. ML-приложение для классификации пациентов                                           
  по трём стадиям болезни Альцгеймера: CN (норма) → MCI (ранняя) → AD (деменция).                                        
                                                                                                                         
  ## Как работает                                                                                                        
                                                                                                                       
  Модель **MultimodalADNet** объединяет два источника данных:                                                            
                                                                                                                         
  - **МРТ-признаки** (FreeSurfer): объём мозга (nWBV), объём черепа (eTIV), масштаб (ASF)
  - **Клинические данные**: возраст, пол, образование, SES, MMSE, CDR                                                    
                                                                                                                       
  Ключевой элемент — **Gated Fusion**: для каждого пациента модель индивидуально                                         
  решает, каким данным доверять больше (МРТ или клинике).                                                                
                                                                                                                         
  gate = sigmoid(W · [e_MRI; e_clin])                                                                                    
  fused = gate · e_MRI + (1 − gate) · e_clin                                                                             
                                                                                                                         
  ## Данные                                                                                                              
                                                                                                                       
  Открытый датасет **OASIS** (Kaggle, без ограничений доступа):                                                          
  - `oasis_longitudinal.csv` — 150 пациентов, повторные визиты
  - `oasis_cross-sectional.csv` — 436 пациентов                                                                          
                                                                                                                         
  ## Установка и запуск                                                                                                  
                                                                                                                         
  ```bash                                                                                                              
  git clone https://github.com/vverakorolevaa/altchgamer
  cd altchgamer                                                                                                          
  pip install -r requirements.txt
                                                                                                                         
  # Скопировать данные OASIS из ~/Downloads:                                                                             
  python cli.py setup-kaggle
                                                                                                                         
  # Обучить модель и получить визуализации:                                                                              
  python cli.py classify-kaggle
                                                                                                                         
  # Сгенерировать PowerPoint-презентацию (12 слайдов):                                                                   
  python cli.py report
                                                                                                                         
  Архитектура                                                                                                            
   
  MRIEncoder (3→128)  ──┐                                                                                                
                         ├── GatedFusion ── Classifier → CN / MCI / AD                                                   
  ClinicalEncoder (6→128)┘                                                                                               
                                                                                                                         
  Каждый энкодер: Linear → BatchNorm → ReLU → Dropout(0.3)                                                               
                                                                                                                       
  Дополнительно: scRNA-seq анализ                                                                                        
                                                                                                                       
  Параллельный исследовательский анализ одноклеточного РНК-секвенирования:                                               
                                                                                                                       
  python cli.py download   # GSE138852 (80 пациентов, 80 000+ клеток)                                                    
  python cli.py analyze    # DEG: Mann-Whitney U + BH FDR-коррекция                                                      
                                                                                                                         
  Стек                                                                                                                   
                                                                                                                         
  Python · PyTorch · scikit-learn · scanpy · anndata · matplotlib · python-pptx                                          
                                                                                                                       
  Результаты                                                                                                             
                                                                                                                       
  - Fusion AUC > MRI-only AUC и > Clinical-only AUC                                                                      
  - Gate-веса биологически валидны: выше при AD (атрофия), ниже при MCI
  - nWBV — самый важный признак (согласуется с Fox et al., 1999)                                                         
                                                                                                                         
  ---                                  
