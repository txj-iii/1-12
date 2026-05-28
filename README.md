# DermaSpectra — 基于喉部石墨烯电阻传感器的无声语音交互系统

> 6 通道电阻实时采集 → 词语分类识别 → LLM 组句对话 → TTS 语音合成

## 项目概览

本系统通过贴在喉部的石墨烯电阻传感器采集发声时的电阻变化信号（~10 Hz 采样），利用 Random Forest 分类器识别中文词语（静息 / 我 / 买 / 苹果），再经 LLM 组句和 TTS 语音合成，实现从"无声默念"到"有声回复"的完整闭环。

**当前对话逻辑更新：**
- 第一次先识别一段 CSV 震动，并由 LLM 完成扩句。
- 随后进入输入框阶段，等待对方输入回复。
- 第二次改为再次识别一段新的 CSV 震动，再由 LLM 扩句。
- 再次收到对方输入后，后续轮次不再重新识别震动，直接基于输入内容继续走 LLM 扩句。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│  硬件层                                                              │
│  石墨烯传感器 (CH1参考+CH2信号) → STM32 → 串口/USB → PC               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ 6通道电阻值（~10 Hz）
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  数据采集层 — pyserial_measure_app/                                   │
│  ▶ main.py                 PyQt5 上位机，6通道实时波形显示+CSV导出     │
│  ▶ workers/serial_worker.py  串口读取线程                            │
│  ▶ ui/main_window.py         主窗口（控制面板+绘图网格）              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ CSV 文件（exports/）
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ML 推理层 — pyserial_measure_app/word_recognition/                   │
│  ▶ train_model.py          训练 RF 分类模型 → 输出 .pkl               │
│  ▶ predict.py              单文件词语预测                             │
│  ▶ server.py (Flask)       Web API 在线预测 + LLM + TTS 调度          │
│  ▶ 预测.bat                 独立预测快捷入口                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST API (:5001)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  后端服务层 — server.py (Flask)                                       │
│  /api/predict       → RF 模型预测词序列                               │
│  /api/compose       → LLM 组句                                      │
│  /api/chat          → LLM 对话                                      │
│  /api/generate_replies → 生成 3 个回复选项                           │
│  /api/tts_gen       → TTS 语音合成                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP API
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  前端应用层 — uniii/ (uni-app)                                        │
│  移动端交互界面，调用后端 API                                          │
└─────────────────────────────────────────────────────────────────────┘
```

## 目录结构

```
根目录文件
├── server.py                      # Flask 后端入口（API + LLM + TTS），端口 5001
├── CLAUDE.md                      # 后端架构说明文档
├── README.md                      # 本文件
├── .gitignore                     # Git 忽略规则
├── Haogang.wav                    # TTS 参考音频（GPT-SoVITS 语音克隆用）
│
核心目录
├── pyserial_measure_app/          # 数据采集上位机 + ML 词语识别训练/预测
│   ├── main.py                    # PyQt5 上位机入口（6 通道实时波形+CSV 导出）
│   ├── config.py                  # 全局配置
│   ├── ui/                        # GUI 组件
│   │   ├── main_window.py         # 主窗口
│   │   ├── control_panel.py       # 控制面板
│   │   ├── plot_grid.py           # 6 通道波形网格
│   │   ├── channel_plot_widget.py # 单通道波形组件
│   │   ├── serial_config_dialog.py# 串口配置对话框
│   │   └── range_dialog.py        # 量程设置对话框
│   ├── models/                    # 数据模型
│   │   ├── channel_data.py        # 通道数据管理
│   │   ├── packet.py              # 通信协议包
│   │   └── filter.py              # 数字滤波
│   ├── workers/
│   │   └── serial_worker.py       # 串口后台读取线程
│   ├── export/
│   │   └── csv_exporter.py        # CSV 导出
│   ├── word_recognition/          # ML 词语识别
│   │   ├── CLAUDE.md              # 训练流水线说明
│   │   ├── config.py              # 训练参数配置
│   │   ├── features.py            # 特征提取 (MAV/ZC/SSC/WL)
│   │   ├── train_model.py         # 训练脚本
│   │   ├── predict.py             # 预测脚本
│   │   ├── compare_models.py      # 模型对比工具
│   │   ├── prepare_new_data.py    # 新数据标注
│   │   ├── prepare_sentence_data.py# 句子级数据标注
│   │   ├── split_continuous_csv.py# 连续录音切分
│   │   ├── 预测.bat                # 预测快捷入口
│   │   ├── data/labeled/          # 标注训练数据
│   │   └── models/                # 训练好的 .pkl 模型
│   └── exports/                   # 采集导出的 CSV 文件
│
├── GPT-SoVITS-v2pro-20250604/     # TTS 语音合成引擎（第三方），端口 9880
├── libemg-main/                   # LibEMG 肌电信号处理库（参考，未直接使用）
├── uniii/                         # uni-app 移动端前端（已排除版本控制）
│
辅助目录
├── RES_SENSOR/                    # 电阻传感器相关资源/资料
├── Volume/                        # 第三方大文件依赖（被 .gitignore 排除）
├── exports/                       # 数据采集导出的 CSV 文件
├── tts_cache/                     # TTS 语音合成音频缓存
├── fonts/                         # 字体文件
└── __pycache__/                   # Python 字节码缓存（自动生成）
```

## 各模块详解

### 1. 数据采集上位机 — [pyserial_measure_app/main.py](pyserial_measure_app/main.py)

**功能：** 通过串口接收 STM32 传来的 6 通道电阻值，实时波形显示，支持 CSV 导出。

**启动方式：**
```bash
cd pyserial_measure_app
python main.py
```

**关键步骤：**
1. 启动后弹出串口配置 → 选择 STM32 对应 COM 口和波特率
2. 主界面显示 6 通道实时波形（CH1-CH6），10 秒时间窗口滚动
3. 点击"开始采集"记录数据 → 点击"结束采集"自动导出 CSV 到 `exports/`
4. 可拖拽 CSV 到 `预测.bat` 进行词语识别

**依赖安装：**
```bash
pip install pyqtgraph pyserial PyQt5 numpy
```

### 2. ML 词语识别训练 — [word_recognition/train_model.py](pyserial_measure_app/word_recognition/train_model.py)

**功能：** 用标注的喉部电阻 CSV 数据训练 Random Forest 分类器，识别 4 类词语。

**训练流程：**
| 步骤 | 做什么 | 关键参数 |
|------|--------|----------|
| ① 加载 | 读取 `data/labeled/R_*_C_*_EMG.csv`，解析文件名得类别ID和重复编号 | [train_model.py:80](pyserial_measure_app/word_recognition/train_model.py#L80) |
| ② 分窗 | 窗口大小 20 × 步进 10，词类每文件最多 5 窗口 | [train_model.py:88](pyserial_measure_app/word_recognition/train_model.py#L88) |
| ③ 划分 | 80% 训练 / 20% 测试，分层抽样 | [train_model.py:115](pyserial_measure_app/word_recognition/train_model.py#L115) |
| ④ 特征 | 每窗口提取 MAV+ZC+SSC+WL，2 通道 × 4 = 8 维 | [train_model.py:130](pyserial_measure_app/word_recognition/train_model.py#L130) |
| ⑤ 平衡 | rest 类下采样至 ≤ 词类窗口数 × 3 | [train_model.py:136](pyserial_measure_app/word_recognition/train_model.py#L136) |
| ⑥ 训练 | RandomForest(200 trees, max_depth=10), 保存 .pkl | [train_model.py:155](pyserial_measure_app/word_recognition/train_model.py#L155) |

**启动方式：**
```bash
cd pyserial_measure_app
python word_recognition/train_model.py
```

**数据格式：** 采用 LibEMG 命名规范 `R_{rep}_C_{class}_EMG.csv`
- `rep`: 重复编号
- `class`: 0=静息, 1=我, 2=买, 3=苹果

### 3. 独立预测 — [word_recognition/预测.bat](pyserial_measure_app/word_recognition/预测.bat)

**功能：** 拖入 CSV 文件快速预测，输出词序列和置信度，不依赖 server.py。

**使用方式：**
- 直接双击 `预测.bat` → 输入 CSV 文件名
- 或拖拽 CSV 文件到 `预测.bat` 图标上

**示例输出：**
```
Enter CSV file name: 2026-05-24_16-06-18.csv

加载模型中...
  模型: RandomForestClassifier
  特征: ['MAV', 'ZC', 'SSC', 'WL']
  窗口: 20, 步进: 5

加载数据: ..\exports\2026-05-24_16-06-18.csv
  数据行数: 2085, 通道数: 6
  活跃段数: 8, 窗口数: 169

→ 结论: 我 (100% 窗口支持)
```

### 4. Flask 后端 — [server.py](server.py)

**功能：** 统一的 Web API 服务，串联 RF 预测 → LLM 组句 → TTS 语音输出。

**启动方式：**
```bash
python server.py
```

**API 路由：**
| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/ping` | GET | 健康检查 |
| `/api/predict` | POST/GET | 读取最新 CSV，预测词序列 |
| `/api/compose` | POST | 词序列 → LLM 组句 |
| `/api/chat` | POST | 多轮对话 |
| `/api/generate_replies` | POST | 生成 3 个回复候选（非首次回复阶段） |
| `/api/tts_gen` | GET | 文本 → TTS 语音 |
| `/api/tts_config` | POST | 动态更新 TTS 服务地址 |

**对话时序说明：**
1. 先通过 `/api/predict` 读取最新 CSV，完成当前一次震动识别。
2. 再通过 `/api/compose` 把识别结果扩成自然语言表达。
3. 然后进入输入框等待对方输入回复。
4. 第二轮重新采集新的 CSV，并再次通过 `/api/predict` + `/api/compose` 完成“识别 + 扩句”。
5. 第二轮之后，再次等待对方输入。
6. 从第三轮开始，不再重新采集震动，后续统一直接基于输入内容继续走 LLM 扩句。

**三类模型协同：**
| 模型 | 部署位置 | 功能 |
|------|----------|------|
| RF 词语分类 | 本地 `.pkl` 文件 | 电阻信号 → 词序列 (静息/我/买/苹果) |
| LLM 组句/对话 | 远程 API (Deepseek/阿里云) | 词序列 → 自然语言句子 |
| TTS 语音合成 | 本地 GPT-SoVITS (端口 9880) | 文本 → 语音音频 |

**端口说明：**
- Flask 后端: `5001`（`host=0.0.0.0`，Flask 会自动打印两个 URL）
- TTS 引擎: `9880`（修改地址通过 `POST /api/tts_config`）

**关闭服务：**
- 正常情况下，直接关闭对应的终端窗口，或点击终端右上角关闭按钮，即可终止该服务
- 如果服务没有正常退出，再使用根目录下的关闭脚本：
  - `关闭Flask服务.bat`
  - `关闭TTS服务.bat`
- 如果关闭脚本提示无权限，请右键对应 `bat`，选择“以管理员身份运行”

### 5. TTS 语音合成 — GPT-SoVITS-v2pro-20250604/

**功能：** 第三方语音合成引擎，启动 TTS API 服务供 server.py 调用。

**启动方式：**
```bash
cd GPT-SoVITS-v2pro-20250604
python api_v2.py
```
默认监听端口 9880。

## 为什么选择 RF 而不是直接用 LibEMG

LibEMG 是完整的肌电信号处理框架（49 个特征、8 种模型、在线推理），但本项目选择了手写最小实现：

- **信号类型不同** — LibEMG 为 kHz 级肌电信号（20-450 Hz）设计，本项目是 ~10 Hz 喉部电阻信号，大量频域特征和滤波器无效
- **数据量小** — 4 分类、数百个文件，RF 足够且不易过拟合
- **通道量级差异** — CH3 原始值 ~20000，CH1/CH2 ~1-4，LibEMG 的逐通道归一化实测有害
- **部署简单** — 单文件 .pkl，无需引入 scipy/librosa/PyWavelets 等重量依赖

核心思路：**借鉴 LibEMG 的概念（HTD 特征组、窗口参数、文件命名），手写最小实现。**

| LibEMG 概念 | 本项目实现 | 文件位置 |
|-------------|-----------|----------|
| 窗口参数 (window_size/increment) | WINDOW_SIZE=20, WINDOW_INCREMENT=5 | [config.py:18](pyserial_measure_app/word_recognition/config.py#L18) |
| HTD 特征组 (MAV+ZC+SSC+WL) | FEATURES = ['MAV', 'ZC', 'SSC', 'WL'] | [config.py:25](pyserial_measure_app/word_recognition/config.py#L25) |
| 特征提取函数 | extract_mav/zc/ssc/wl() | [features.py:19](pyserial_measure_app/word_recognition/features.py#L19) |
| 文件命名格式 | R_{rep}_C_{class}_EMG.csv | [train_model.py:43](pyserial_measure_app/word_recognition/train_model.py#L43) |

## 当前推荐推理参数

用于当前线上识别与历史 CSV 参数扫描的推荐组合：

- `window_size=20`
- `window_increment=5`
- `smooth_win=9`
- `threshold_mult=1.4`
- `merge_gap=20`
- `min_len=10`

## 快速开始

### 根目录脚本入口（推荐）

优先直接使用根目录下的脚本：

- [启动TTS服务.bat](启动TTS服务.bat)
- [启动Flask服务.bat](启动Flask服务.bat)
- [启动上位机.bat](启动上位机.bat)
- [关闭TTS服务.bat](关闭TTS服务.bat)
- [关闭Flask服务.bat](关闭Flask服务.bat)
- [显示当前IP.bat](显示当前IP.bat)

### 上位机快速打开

推荐直接双击：

- [启动上位机.bat](启动上位机.bat)

代码入口位置：

- [main.py](pyserial_measure_app/main.py)

### 完整流程

```bash
# 1. 推荐先双击根目录脚本
#    启动TTS服务.bat
#    启动Flask服务.bat
#    启动上位机.bat
#
# 2. 如需手动命令行启动 TTS 引擎（另一个终端）
cd GPT-SoVITS-v2pro-20250604
python api_v2.py                          # → TTS API :9880

# 3. 手动启动 Flask 后端
python server.py                          # → Web API :5001

# 关闭方式
# 正常情况下直接关闭对应终端窗口即可
# 如果关闭失败，再右键“关闭Flask服务.bat”或“关闭TTS服务.bat”，选择“以管理员身份运行”

# 4. 上位机主入口推荐使用 启动上位机.bat
#    如需查看代码入口，可打开 pyserial_measure_app/main.py

# 5. 训练新模型（有新标注数据时）
cd pyserial_measure_app
python word_recognition/train_model.py    # → 输出 models/word_classifier_RF.pkl

# 6. 对比模型性能
python word_recognition/compare_models.py
```

### 环境要求
- **Python**: Anaconda Python 推荐（`server.py` 会自动检测并切换）
- **GPU**: TTS 引擎推荐 NVIDIA GPU
- **依赖**: `pip install numpy scikit-learn pyqtgraph pyserial PyQt5 flask`
- **完整 TTS 依赖**: 见 `GPT-SoVITS-v2pro-20250604/` 内文档

## 相关文档

- [CLAUDE.md](CLAUDE.md) — 后端 server.py 架构详解
- [word_recognition/CLAUDE.md](pyserial_measure_app/word_recognition/CLAUDE.md) — ML 训练流水线详解
