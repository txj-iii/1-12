# DermaSpectra Backend - server.py 架构

## 启动流程

### 第 1 步：Python 环境自检 — server.py:8-17
当前 Python 缺少 numpy 时自动搜索 Anaconda Python 路径，通过 `os.execv()` 重启自身。

### 第 2 步：加载配置变量 — server.py:33-57
- `FLASK_PORT = 5001` — 服务端口（环境变量可覆盖）
- `DEVICE_IP = "10.0.0.78"` — 成像设备 IP（已定义但未接入路由）
- `EXPORTS_DIRS` — CSV 数据文件搜索路径
- `MODEL_DIR` — 训练好的模型目录
- `LLM_CONFIG` — Deepseek + 阿里云 LLM 的 API key
- `TTS_API_URL` — TTS 语音合成地址（默认值，可通过 `/api/tts_config` 动态更新）
- `TTS_CACHE_DIR` — TTS 音频缓存目录

### 第 3 步：创建 Flask app — server.py:59
### 第 4 步：注册 CORS 中间件 — server.py:63-68
每个响应自动加 `Access-Control-Allow-Origin: *`。

### 第 5 步：注册路由 — server.py:327-510

| 路由 | 行号 | 功能 |
|------|------|------|
| GET `/api/ping` | 327 | 前端检测后端是否在线 |
| POST/GET `/api/predict` | 333 | 读取最新 CSV，预测词语分类 |
| POST `/api/compose` | 361 | 接收词序列，LLM 组句 |
| POST `/api/chat` | 374 | 对话回复 |
| POST `/api/generate_replies` | 411 | 生成 3 个回复选项 |
| POST `/api/tts_config` | 457 | 动态更新 TTS 服务器地址 |
| GET `/api/tts/<filename>` | 482 | 返回缓存的 TTS 音频文件 |
| GET `/api/tts_gen` | 492 | 按需生成指定文本的 TTS 音频 |
| GET `/` | 513 | 根路径，返回服务信息 |

### 第 6 步：启动 Flask — server.py:522-530
`app.run(host="0.0.0.0", port=5001, debug=False)`

`host="0.0.0.0"` 绑定所有网卡，Flask 自动打印两条 URL：
- `http://127.0.0.1:5001` — 本机回环
- `http://192.168.x.x:5001` — 局域网地址

两条指向同一个服务，端口只有一个 5001。

### 第 7 步：模型加载 — server.py:137-147
`load_model()` 按修改时间取最新的 `.pkl` 文件，排除带 `_old`、`_6ch`、`_192files`、`_261files` 标签的备份文件。

### 第 8 步：预测流水线 — server.py:149-220
`run_prediction()`: 加载 CSV → 取前 2 通道 → 裁剪异常值(5σ) → 找活跃段 → 分窗 → 提取特征 → 分类 → 平滑 → 输出词序列

## 三类模型

| 模型 | 位置 | 说明 |
|------|------|------|
| RF 词语分类 | 本地 `.pkl` | 喉部电阻传感器 → 词序列 |
| LLM 组句/对话 | 远程 API (Deepseek/阿里云) | 词序列 → 自然语言 |
| TTS 语音合成 | 本地 GPT-SoVITS (端口 9880) | 文本 → 语音 |
