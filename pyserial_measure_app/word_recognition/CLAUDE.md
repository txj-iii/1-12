# 词语识别模型训练流水线

## 数据命名规范
采用 LibEMG 格式：`R_{rep}_C_{class}_EMG.csv`
- `rep`: 重复编号
- `class`: 类别 ID（0=rest, 1=I, 2=buy, 3=apple）

数据目录：`data/labeled/`，由 `prepare_new_data.py` 管理。

## 训练流程（6 步）— train_model.py

| 步骤 | 做什么 | 代码位置 |
|------|--------|----------|
| ① 加载 | 读取 data/labeled/ 下所有 CSV，解析文件名得到类别ID和重复编号 | :80-86 |
| ② 分窗 | 每个文件切成多个窗口，词类文件每文件最多取 5 个窗口 | :88-102 |
| ③ 划分 | 80%训练 / 20%测试，分层抽样保证各类比例一致 | :115-127 |
| ④ 特征 | 每个窗口提取 MAV+ZC+SSC+WL，2通道×4特征=8维向量 | :130-134 |
| ⑤ 平衡 | rest 类窗口限制为词类窗口的 3 倍，避免类别失衡 | :136-153 |
| ⑥ 训练 | RandomForest(200棵树, max_depth=10, class_weight='balanced')，保存为 .pkl | :155-193 |

## 为什么选择 RF 而不是直接用 LibEMG

LibEMG 是完整的肌电信号处理框架（49 个特征、8 种模型、在线推理、硬件流），但本项目的场景存在根本差异：

- **信号类型不同** — LibEMG 为 kHz 级肌电信号（20-450Hz）设计，本项目是 ~10Hz 喉部电阻信号，大量频域特征（MDF、MNF）和滤波器在此采样率下无效
- **数据量小** — 4 分类、几百个文件，RF 足够且不易过拟合；LibEMG 的 DL 模型（CNN+GRU）需要大量数据
- **通道量级差异** — CH3 原始值 ~20000，CH1/CH2 ~1-4，LibEMG 的逐通道归一化对此场景有害（实测降低准确率）
- **部署简单** — 单文件 .pkl，server.py 直接加载，无需引入 scipy/librosa/PyWavelets 等重量依赖

核心思路是**借鉴 LibEMG 的概念，手写最小实现**，避免引入整个框架。

## LibEMG 概念 vs 本项目实现

| LibEMG 概念 | 本项目实现 | 位置 |
|-------------|-----------|------|
| 窗口参数 (window_size/increment) | WINDOW_SIZE=20, WINDOW_INCREMENT=10 | [config.py:18-19](pyserial_measure_app/word_recognition/config.py#L18-L19) |
| 特征组 HTD (MAV+ZC+SSC+WL) | FEATURES = ['MAV', 'ZC', 'SSC', 'WL'] | [config.py:25](pyserial_measure_app/word_recognition/config.py#L25) |
| 特征提取 | extract_mav/zc/ssc/wl() | [features.py:19-50](pyserial_measure_app/word_recognition/features.py#L19-L50) |
| 文件命名 R_{rep}_C_{class}_EMG.csv | 相同的命名格式 | [train_model.py:43](pyserial_measure_app/word_recognition/train_model.py#L43) |

## 关键参数 — config.py

| 参数 | 值 | 行号 |
|------|----|------|
| WINDOW_SIZE | 20 | :18-19 |
| WINDOW_INCREMENT | 10 | :18-19 |
| N_CHANNELS | 2 | :22 |
| FEATURES | ['MAV', 'ZC', 'SSC', 'WL'] (HTD 特征组) | :25 |
| CLASSIFIER | 'RF' | :28 |
| CLASS_MAPPING | {0:'rest', 1:'I', 2:'buy', 3:'apple'} | :31-37 |

## 特征说明 — features.py

| 特征 | 函数 | 含义 |
|------|------|------|
| MAV | extract_mav() | 平均绝对值，衡量信号强度 |
| ZC | extract_zc() | 过零率，衡量信号频率 |
| SSC | extract_ssc() | 斜率符号变化，衡量信号复杂度 |
| WL | extract_wl() | 波形长度，衡量信号变化幅度 |

## 模型评估 — compare_models.py
在同一测试集上对比两个模型的准确率和混淆矩阵。用法：
```
cd pyserial_measure_app
python word_recognition/compare_models.py
```

## 独立预测 — 预测.bat → predict.py

拖入 CSV 文件或手动输入文件名即可预测，不依赖 server.py。示例运行：

```
Enter CSV file name: 2026-05-24_16-06-18.csv
Running prediction for:
..\exports\2026-05-24_16-06-18.csv

加载模型中...
  模型: RandomForestClassifier
  特征: ['MAV', 'ZC', 'SSC', 'WL']
  窗口: 20, 步进: 5
  类别: {0: '静息', 1: '我', 2: '买', 3: '苹果'}

加载数据: ..\exports\2026-05-24_16-06-18.csv
  数据行数: 2085, 通道数: 6
  CH1 范围: 1.634 - 1.734
  活跃段数: 8
  窗口数: 169
  特征维度: (169, 80)

==================================================
预测结果
==================================================
  我    (1): 169/169 窗口 (100.0%) ████████████████████

→ 结论: 我 (100% 窗口支持)
```
