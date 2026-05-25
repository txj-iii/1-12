"""DermaSpectra 统一后端服务"""
import os
import sys

# ── 引导：确保使用有 numpy 的 Python ──
if "DermaSpectra_BOOTSTRAPPED" not in os.environ:
    try:
        import numpy as _numpy_check
    except ImportError:
        for _py in [
            r"C:\Software\anaconda3\python.exe",
            r"C:\Users\Embark\anaconda3\python.exe",
        ]:
            if os.path.exists(_py):
                os.environ["DermaSpectra_BOOTSTRAPPED"] = "1"
                os.execv(_py, [_py, __file__] + sys.argv[1:])
        sys.exit("Error: numpy not found. Please install numpy or set up Anaconda Python.")
import csv
import pickle
import glob
import warnings
from collections import Counter
from functools import reduce
from io import BytesIO
import json
import time
import hashlib
import re

import numpy as np
from flask import Flask, jsonify, request, Response, send_file
import requests as http_req

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "pyserial_measure_app"))

from word_recognition.features import extract_features, parse_windows_from_array

# ─── 配置 ─────────────────────────────────────────────
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5001))
DEVICE_IP = os.environ.get("DEVICE_IP", "10.0.0.78")
DEVICE_PORT = int(os.environ.get("DEVICE_PORT", 5000))
EXPORTS_DIRS = [
    os.path.join(ROOT, "exports"),
    os.path.join(ROOT, "pyserial_measure_app", "exports"),
]
MODEL_DIR = os.path.join(ROOT, "pyserial_measure_app", "word_recognition", "models")

# LLM 组句配置
LLM_CONFIG = {
    "primary": {
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "api_key": "sk-8c4e9da4760749c88dbace0a0c90e729",
        "model": "deepseek-chat",
    },
    "fallback": {
        "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "api_key": "sk-e6dc062be8a04a37a077d2327c5233ac",
        "model": "qwen-max",
    }
}
TTS_API_URL = os.environ.get("TTS_API_URL", "http://127.0.0.1:9880/tts")
TTS_REF_AUDIO = os.environ.get("TTS_REF_AUDIO", "Haogang.wav")
TTS_CACHE_DIR = os.path.join(ROOT, "tts_cache")

app = Flask(__name__)


# ─── CORS (允许跨域) ───────────────────────────────────
@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    return resp


# ─── 预测逻辑 ──────────────────────────────────────────
def normalize_data(data):
    """Z-score 归一化：每通道减去均值除以标准差"""
    means = np.mean(data, axis=0)
    stds = np.std(data, axis=0)
    stds[stds < 1e-8] = 1.0
    return (data - means) / stds


def find_active_segments(data, smooth_win=15, threshold_mult=1.3, merge_gap=60, min_len=10):
    """与 prepare_data.py 一致的智能分割，返回活跃段 [(start, end), ...]"""
    max_ch = np.max(np.abs(data), axis=1)
    stds = np.array([np.std(max_ch[max(0,i-smooth_win//2):i+smooth_win//2]) for i in range(len(max_ch))])
    pos_stds = stds[stds > 1e-8]
    if len(pos_stds) == 0:
        return [(0, len(data))]
    threshold = np.median(pos_stds) * threshold_mult
    active = stds > threshold
    segments = []
    start = None
    for i, a in enumerate(active):
        if a and start is None:
            start = i
        elif not a and start is not None:
            if i - start >= min_len:
                if segments and start - segments[-1][1] < merge_gap:
                    segments[-1] = (segments[-1][0], i)
                else:
                    segments.append((start, i))
            start = None
    if start is not None and len(data) - start >= min_len:
        if segments and start - segments[-1][1] < merge_gap:
            segments[-1] = (segments[-1][0], len(data))
        else:
            segments.append((start, len(data)))
    return segments


def load_csv_data(filepath):
    """加载原始CSV, 只裁剪异常值（归一化交给run_prediction按段处理）"""
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            rows.append([float(x) for x in row[:2]])  # CH1-2 石墨烯传感器 (CH3不稳定，训练未使用)
    arr = np.array(rows)
    # 裁剪异常值
    for ch in range(arr.shape[1]):
        ch_data = arr[:, ch]
        m, s = np.mean(ch_data), np.std(ch_data)
        if s > 1e-8:
            lower, upper = m - 5 * s, m + 5 * s
            arr[:, ch] = np.clip(arr[:, ch], lower, upper)
    return arr


def find_latest_csv():
    all_files = []
    for d in EXPORTS_DIRS:
        all_files.extend(glob.glob(os.path.join(d, "*.csv")))
    if not all_files:
        return None
    return max(all_files, key=os.path.getmtime)


def load_model():
    # 加载最新训练的模型 (按修改时间, 排除备份文件)
    model_files = [f for f in os.listdir(MODEL_DIR)
                   if f.endswith('.pkl') and not any(tag in f for tag in ['_old', '_6ch', '_192files', '_261files'])]
    if not model_files:
        return None, "Model file not found, please run train_model.py first"
    latest = max(model_files, key=lambda f: os.path.getmtime(os.path.join(MODEL_DIR, f)))
    with open(os.path.join(MODEL_DIR, latest), "rb") as f:
        data = pickle.load(f)
    return data, None


def run_prediction(filepath):
    """对 CSV 文件执行预测，返回结构化结果"""
    data = load_csv_data(filepath)
    model_data, err = load_model()
    if err:
        return {"success": False, "error": err}

    clf = model_data["model"]
    features = model_data["features"]
    window_size = model_data["window_size"]
    window_inc = model_data.get("window_increment", 25)
    class_mapping = model_data["class_mapping"]

    raw = data  # 原始(未归一化)数据
    if len(raw) < window_size:
        return {"success": False, "error": f"Too few data rows ({len(raw)}), need at least {window_size}"}

    # 用全局归一化数据检测活跃段，但用原始值预测（模型在原始数据上训练）
    norm_full = normalize_data(raw.copy())
    active_segments = find_active_segments(norm_full)
    all_windows = []
    for s, e in active_segments:
        seg_raw = raw[s:e]
        seg_windows = parse_windows_from_array(seg_raw, window_size, window_inc)
        if len(seg_windows) > 0:
            all_windows.append(seg_windows)

    if len(all_windows) == 0:
        return {"success": False, "error": "No active speech segment detected"}
    windows = np.concatenate(all_windows)
    if len(windows) < 1:
        return {"success": False, "error": "No data after windowing"}

    feat = extract_features(features, windows)
    predictions = clf.predict(feat)

    # 用滑动窗口众数平滑预测，然后构建时序词序列
    def smooth_labels(labels, window=3):
        half = window // 2
        smoothed = []
        for i in range(len(labels)):
            seg = labels[max(0, i-half):min(len(labels), i+half+1)]
            smoothed.append(Counter(seg).most_common(1)[0][0])
        return smoothed

    smoothed = smooth_labels(predictions, window=3)
    word_sequence = []
    if len(smoothed) > 0:
        current_cls = smoothed[0]
        current_cnt = 1
        for pred in smoothed[1:]:
            if pred == current_cls:
                current_cnt += 1
            else:
                if current_cnt >= 2:  # 过滤孤立单窗口
                    word_sequence.append({
                        "word": class_mapping.get(int(current_cls), f"unknown({current_cls})"),
                        "windows": current_cnt,
                    })
                current_cls = pred
                current_cnt = 1
        if current_cnt >= 2:  # 最后一段
            word_sequence.append({
                "word": class_mapping.get(int(current_cls), f"unknown({current_cls})"),
                "windows": current_cnt,
            })

    vote = Counter(predictions)
    total = len(predictions)
    results = []
    for cls_id in sorted(vote.keys()):
        pct = vote[cls_id] / total * 100
        name = class_mapping.get(int(cls_id), f"unknown({cls_id})")
        results.append({
            "class": name,
            "percentage": round(pct, 1),
            "count": vote[cls_id],
        })

    best = vote.most_common(1)[0]
    best_name = class_mapping.get(int(best[0]), f"未知({best[0]})")
    best_pct = round(best[1] / total * 100, 1)

    return {
        "success": True,
        "file": os.path.basename(filepath),
        "total_windows": total,
        "results": results,
        "conclusion": best_name,
        "conclusion_pct": best_pct,
        "word_sequence": word_sequence,
    }


# ─── LLM 组句 ──────────────────────────────────────────

def call_llm(messages, temperature=0.7, max_tokens=1024):
    """调用LLM，优先Deepseek，回退DashScope，返回文本响应"""
    for provider, cfg in [("primary", LLM_CONFIG["primary"]), ("fallback", LLM_CONFIG["fallback"])]:
        try:
            resp = http_req.post(
                cfg["api_url"],
                json={"model": cfg["model"], "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens},
                headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            print(f"  LLM {provider} 返回 {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"  LLM {provider} 异常: {e}")
    return None


def compose_sentences(word_sequence):
    """将词序列通过LLM组句，返回句子列表"""
    words = [w["word"] for w in word_sequence if w["word"] != "rest"]
    if not words:
        return []

    prompt = (
        f"The following word sequence was detected from a throat vibration sensor: {json.dumps(words, ensure_ascii=False)}\n"
        f"Based on these keywords, generate 3 different English sentences for a customer talking to a fruit shop owner.\n"
        f"Make the sentences natural and varied, like real conversation — don't just repeat the keywords.\n"
        f"Try different angles: asking about price, stating quantity, expressing preference, making a request, etc.\n"
        f"Return as a JSON array directly, e.g. [\"sentence1\",\"sentence2\",\"sentence3\"]"
    )
    messages = [
        {"role": "system", "content": "You are a fruit shop conversation assistant. Generate natural, varied customer sentences based on the given keywords."},
        {"role": "user", "content": prompt},
    ]

    response = call_llm(messages)
    if not response:
        return []

    # 尝试提取JSON数组
    try:
        json_match = re.search(r'\[.*?\]', response, re.DOTALL)
        if json_match:
            sentences = json.loads(json_match.group())
            if isinstance(sentences, list):
                return [s for s in sentences if isinstance(s, str) and len(s) > 2][:5]
    except Exception as e:
        print(f"  解析LLM响应失败: {e}")

    return []


# ─── TTS ───────────────────────────────────────────────

def tts_generate(text):
    """调用GPT-SoVITS合成语音，返回WAV文件路径（缓存）"""
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    text_hash = hashlib.md5(text.encode()).hexdigest()
    cache_path = os.path.join(TTS_CACHE_DIR, f"{text_hash}.wav")
    if os.path.exists(cache_path):
        return cache_path

    try:
        resp = http_req.post(
            TTS_API_URL,
            json={"text": text, "text_lang": "zh", "ref_audio_path": TTS_REF_AUDIO, "prompt_lang": "zh"},
            timeout=60,
        )
        if resp.status_code == 200:
            with open(cache_path, "wb") as f:
                f.write(resp.content)
            return cache_path
        print(f"  TTS 返回 {resp.status_code}")
    except Exception as e:
        print(f"  TTS 异常: {e}")
    return None


# ─── API 端点 ──────────────────────────────────────────

@app.route("/api/ping", methods=["GET"])
def ping():
    """轻量连接测试"""
    return jsonify({"success": True})


@app.route("/api/predict", methods=["POST", "GET"])
def predict():
    """预测词汇分类：读取最新 CSV 返回结果。
    支持 compose=true 参数，额外返回 LLM 组句和 TTS 音频。
    """
    csv_path = find_latest_csv()
    if csv_path is None:
        return jsonify({"success": False, "error": "No CSV file in exports/ directory"}), 404

    result = run_prediction(csv_path)
    if not result["success"]:
        return jsonify(result), 400

    # LLM 组句
    compose_mode = request.args.get("compose", "").lower() == "true"
    if compose_mode:
        word_seq = result.get("word_sequence", [])
        sentences = compose_sentences(word_seq)
        result["sentences"] = sentences
        # 预生成第一个句子的 TTS
        if sentences:
            wav_path = tts_generate(sentences[0])
            if wav_path:
                result["audio_url"] = f"/api/tts/{os.path.basename(wav_path)}"

    return jsonify(result)


@app.route("/api/compose", methods=["POST"])
def compose():
    """接收词序列，返回LLM组句结果。
    POST JSON: {"word_sequence": [{"word": "我", "confidence": 85.0, "windows": 8}, ...]}
    """
    data = request.get_json(silent=True)
    if not data or "word_sequence" not in data:
        return jsonify({"success": False, "error": "word_sequence parameter required"}), 400

    sentences = compose_sentences(data["word_sequence"])
    return jsonify({"success": True, "sentences": sentences})


@app.route("/api/chat", methods=["POST"])
def chat():
    """对话回复：接收消息和历史，返回 AI 自然回复"""
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"success": False, "error": "message parameter required"}), 400

    message = data["message"]
    history = data.get("history", [])

    # Build conversation history
    history_text = ""
    for h in history:
        role = "User" if h["role"] == "user" else "Assistant"
        history_text += f"{role}: {h['content']}\n"

    system_prompt = (
        "You are a fruit shop AI assistant, communicating in text with a customer who cannot speak.\n"
        "The customer uses a throat vibration sensor to detect keywords and compose sentences.\n"
        "Reply with short, natural responses about the \"buying apples\" scenario — e.g. ask about quantity, "
        "confirm the variety, or give a general response.\n"
        "Reply in no more than 40 words, directly with the reply content, no quotation marks."
    )
    user_prompt = f"Conversation history:\n{history_text}User's latest message: {message}\n\nPlease reply:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    reply = call_llm(messages, temperature=0.7, max_tokens=256)
    if not reply:
        return jsonify({"success": False, "error": "LLM returned empty"}), 500

    return jsonify({"success": True, "reply": reply.strip()})


@app.route("/api/generate_replies", methods=["POST"])
def generate_replies():
    """根据对话历史和对方（真人）最新回复，为顾客生成3个回应选项"""
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"success": False, "error": "message parameter required"}), 400

    other_message = data["message"]
    history = data.get("history", [])

    history_text = ""
    for h in history:
        role = "Customer" if h["role"] == "user" else "Shopkeeper"
        history_text += f"{role}: {h['content']}\n"

    prompt = (
        f"Conversation history:\n{history_text}"
        f"Shopkeeper's latest reply: {other_message}\n\n"
        f"Generate 3 different English reply options for the customer to continue the conversation with the fruit shop owner.\n"
        f"Make the sentences natural and diverse, like real conversation — cover different angles (e.g. answering, asking further, expressing preference, etc.).\n"
        f"Each sentence should be no more than 20 words.\n"
        f"Return as a JSON array directly, e.g. [\"sentence1\",\"sentence2\",\"sentence3\"]"
    )
    messages = [
        {"role": "system", "content": "You are a fruit shop conversation assistant. Generate natural customer reply options based on the conversation context."},
        {"role": "user", "content": prompt},
    ]

    response = call_llm(messages, temperature=0.8)
    if not response:
        return jsonify({"success": False, "error": "LLM returned empty"}), 500

    try:
        json_match = re.search(r'\[.*?\]', response, re.DOTALL)
        if json_match:
            sentences = json.loads(json_match.group())
            if isinstance(sentences, list):
                sentences = [s for s in sentences if isinstance(s, str) and len(s) > 1][:5]
                if sentences:
                    return jsonify({"success": True, "sentences": sentences})
    except Exception as e:
        print(f"  Failed to parse LLM response: {e}")

    return jsonify({"success": False, "error": "Failed to parse response"}), 500


@app.route("/api/tts_config", methods=["POST"])
def tts_config():
    """接收 APP 传来的 TTS 服务器地址，动态更新 TTS_API_URL 并测试连接"""
    data = request.get_json(silent=True)
    if not data or "port" not in data:
        return jsonify({"success": False, "error": "port parameter required"}), 400
    host = data.get("host", "127.0.0.1")
    port = int(data["port"])
    new_url = f"http://{host}:{port}/tts"
    try:
        resp = http_req.post(new_url, json={
            "text": "test",
            "text_lang": "zh",
            "ref_audio_path": TTS_REF_AUDIO,
            "prompt_lang": "zh",
        }, timeout=10)
        if resp.status_code == 200:
            global TTS_API_URL
            TTS_API_URL = new_url
            print(f"  TTS 服务器已更新: {new_url}")
            return jsonify({"success": True, "message": f"TTS server connected: {new_url}"})
        return jsonify({"success": False, "error": f"TTS returned status code {resp.status_code}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Cannot connect to TTS server: {new_url} ({e})"}), 400


@app.route("/api/tts/<filename>")
def tts_serve(filename):
    """返回缓存的 TTS 音频文件"""
    wav_path = os.path.join(TTS_CACHE_DIR, filename)
    if not os.path.exists(wav_path):
        return jsonify({"success": False, "error": "Audio file not found"}), 404
    return send_file(wav_path, mimetype="audio/wav")


@app.route("/api/tts_gen")
def tts_gen():
    """生成并返回指定文本的TTS音频（按需生成）"""
    text = request.args.get("text", "")
    if not text:
        return jsonify({"success": False, "error": "text parameter required"}), 400
    wav_path = tts_generate(text)
    if not wav_path:
        return jsonify({"success": False, "error": "TTS generation failed"}), 500
    return send_file(wav_path, mimetype="audio/wav")


@app.route("/")
def index():
    return jsonify({
        "service": "DermaSpectra Backend",
        "endpoints": {
            "/api/predict": "POST/GET - Word classification prediction",
        },
    })


if __name__ == "__main__":
    print(f"DermaSpectra Backend starting...")
    print(f"  Port: {FLASK_PORT}")
    print(f"  Imaging device: {DEVICE_IP}:{DEVICE_PORT}")
    print(f"  Model directory: {MODEL_DIR}")
    for d in EXPORTS_DIRS:
        print(f"  Export directory: {d}")
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=False)
