"""
用已训练的模型预测新 CSV 文件中说的是哪个词。

用法:
  cd pyserial_measure_app
  python word_recognition/predict.py <csv_path>

示例:
  python word_recognition/predict.py ../exports/我.csv
  python word_recognition/predict.py ../exports/苹果.csv
"""
import os
import pickle
import sys
import warnings
from collections import Counter

import numpy as np

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from word_recognition.features import extract_features, parse_windows_from_array


def normalize_data(data):
    """Z-score 归一化：每通道减去均值除以标准差"""
    means = np.mean(data, axis=0)
    stds = np.std(data, axis=0)
    stds[stds < 1e-8] = 1.0
    return (data - means) / stds


def find_active_segments(data, smooth_win=15, threshold_mult=1.3, merge_gap=50, min_len=10):
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


def load_csv_data(filepath: str) -> np.ndarray:
    """加载原始上位机CSV, 只裁剪不做归一化（预测时按段独立归一化）"""
    import csv
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            rows.append([float(x) for x in row[:6]])
    arr = np.array(rows)
    for ch in range(arr.shape[1]):
        ch_data = arr[:, ch]
        m, s = np.mean(ch_data), np.std(ch_data)
        if s > 1e-8:
            lower, upper = m - 5 * s, m + 5 * s
            arr[:, ch] = np.clip(arr[:, ch], lower, upper)
    return arr


def load_model(model_dir: str):
    """加载最新训练的模型."""
    files = sorted(os.listdir(model_dir))
    if not files:
        print(f"错误: {model_dir} 中没有模型文件，请先运行 train_model.py")
        sys.exit(1)
    model_path = os.path.join(model_dir, files[-1])
    with open(model_path, "rb") as f:
        data = pickle.load(f)
    return data["model"], data["features"], data["window_size"], data.get("window_increment", 25), data["class_mapping"]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"错误: 文件不存在: {csv_path}")
        sys.exit(1)

    base_dir = os.path.dirname(__file__)
    model_dir = os.path.join(base_dir, "models")

    # 加载模型
    print("加载模型中...")
    clf, features, window_size, window_inc, class_mapping = load_model(model_dir)
    inv_mapping = {v: k for k, v in class_mapping.items()}
    print(f"  模型: {clf.__class__.__name__}")
    print(f"  特征: {features}")
    print(f"  窗口: {window_size}, 步进: {window_inc}")
    print(f"  类别: {class_mapping}")

    # 加载CSV(原始未归一化)
    print(f"\n加载数据: {csv_path}")
    raw = load_csv_data(csv_path)
    print(f"  数据行数: {len(raw)}, 通道数: {raw.shape[1]}")
    print(f"  CH1 范围: {raw[:, 0].min():.3f} - {raw[:, 0].max():.3f}")

    # 用全局归一化检测活跃段，但用原始值预测（模型在原始数据上训练）
    norm_full = normalize_data(raw.copy())
    active_segments = find_active_segments(norm_full)
    print(f"  活跃段数: {len(active_segments)}")
    all_windows = []
    for s, e in active_segments:
        seg_raw = raw[s:e]  # 原始裁剪数据，不做归一化
        seg_windows = parse_windows_from_array(seg_raw, window_size, window_inc)
        if len(seg_windows) > 0:
            all_windows.append(seg_windows)
    if len(all_windows) == 0:
        print(f"未检测到活跃发音段")
        sys.exit(1)
    windows = np.concatenate(all_windows)
    print(f"  窗口数: {len(windows)}")

    # 特征提取
    feat = extract_features(features, windows)
    print(f"  特征维度: {feat.shape}")

    # 预测
    predictions = clf.predict(feat)

    # 统计结果
    vote = Counter(predictions)
    total = len(predictions)
    print(f"\n{'='*50}")
    print(f"预测结果")
    print(f"{'='*50}")
    for cls_id in sorted(vote.keys()):
        pct = vote[cls_id] / total * 100
        name = class_mapping.get(int(cls_id), f"未知({cls_id})")
        bar = "█" * int(pct / 5)
        print(f"  {name:4s} ({int(cls_id)}): {vote[cls_id]:3d}/{total} 窗口 ({pct:5.1f}%) {bar}")

    print(f"\n→ 结论: ", end="")
    best_cls = vote.most_common(1)[0][0]
    best_name = class_mapping.get(int(best_cls), f"未知({best_cls})")
    best_pct = vote.most_common(1)[0][1] / total * 100
    print(f"{best_name} ({best_pct:.0f}% 窗口支持)")


if __name__ == "__main__":
    main()
