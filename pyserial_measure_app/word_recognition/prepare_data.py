"""
将原始上位机CSV转换为LibEMG标准格式的标注数据。

支持智能分割：自动检测活跃发音段，只保留真正发音的数据。
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from word_recognition.config import (
    CLASS_MAPPING,
    RAW_DATA_DIR,
    LABELED_DATA_DIR,
    DATA_FILES,
)


def normalize_data(data: np.ndarray) -> np.ndarray:
    """Z-score 归一化：每通道减去均值除以标准差，消除力度/姿势差异"""
    means = np.mean(data, axis=0)
    stds = np.std(data, axis=0)
    stds[stds < 1e-8] = 1.0  # 防止除零
    return (data - means) / stds


def load_csv(filepath: str) -> np.ndarray:
    """加载原始CSV, 只裁剪异常值不做归一化（由调用方按段独立归一化）"""
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            rows.append([float(x) for x in row[:6]])
    data = np.array(rows)
    # 裁剪异常值: 每通道超过 mean±5*std 的值拉到边界
    for ch in range(data.shape[1]):
        ch_data = data[:, ch]
        m, s = np.mean(ch_data), np.std(ch_data)
        if s > 1e-8:
            lower, upper = m - 5 * s, m + 5 * s
            data[:, ch] = np.clip(data[:, ch], lower, upper)
    return data


def find_active_segments(data, smooth_win=15, threshold_mult=1.5, merge_gap=50, min_len=20):
    """基于最强通道的滑动标准差检测活跃发音段，返回 [(start, end), ...]

    使用每个采样点各通道绝对值最大值(而非均值)，避免大量静默通道稀释信号。
    """
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


def save_libemg_format(data: np.ndarray, rep: int, class_id: int, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    filename = f"R_{rep}_C_{class_id}_EMG.csv"
    filepath = os.path.join(out_dir, filename)
    np.savetxt(filepath, data, delimiter=",", fmt="%.6f")
    return filepath


def find_inactive_segments(data, active_segments, min_rest_len=30):
    """根据活跃段反推静息段(无发音间隙), 返回 [(start, end), ...]"""
    inactive = []
    prev_end = 0
    for s, e in active_segments:
        if s - prev_end >= min_rest_len:
            inactive.append((prev_end, s))
        prev_end = e
    if len(data) - prev_end >= min_rest_len:
        inactive.append((prev_end, len(data)))
    return inactive


def split_into_reps(data: np.ndarray, num_reps: int):
    """将数据等分为 num_reps 个连续段."""
    if num_reps <= 1:
        return [data]
    total = len(data)
    seg_size = total // num_reps
    segments = []
    for i in range(num_reps):
        start = i * seg_size
        end = total if i == num_reps - 1 else (i + 1) * seg_size
        segments.append(data[start:end])
    return segments


def main():
    base_dir = os.path.dirname(__file__)
    raw_dir = os.path.join(base_dir, RAW_DATA_DIR)
    out_dir = os.path.join(base_dir, LABELED_DATA_DIR)
    os.makedirs(out_dir, exist_ok=True)

    # 清空输出目录
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))

    name_to_id = {v: k for k, v in CLASS_MAPPING.items()}

    for item in DATA_FILES:
        filename = item[0]
        class_name = item[1]

        filepath = os.path.join(raw_dir, filename)
        if not os.path.exists(filepath):
            print(f"[跳过] 文件不存在: {filename}")
            continue

        print(f"\n{'='*50}")
        print(f"{class_name}: {filename}")
        raw_data = load_csv(filepath)
        print(f"  加载 {len(raw_data)} 行, 6 通道")

        # 判断分割方式
        num_reps = item[2] if len(item) > 2 else 1
        smart = item[3] if len(item) > 3 else False

        if smart:
            # 在全文件归一化数据上检测活跃段（检测需要统一起见）
            norm_full = normalize_data(raw_data.copy())
            segments = find_active_segments(norm_full)
            print(f"  智能分割: 检测到 {len(segments)} 个活跃段")
            total_active = sum(e-s for s,e in segments)
            print(f"  有效数据: {total_active}/{len(raw_data)} = {total_active/len(raw_data)*100:.1f}%")

            # 对每个段取原始(裁剪后)数据保存 —— 不做归一化！
            class_id = name_to_id[class_name]
            for rep_i, (s, e) in enumerate(segments):
                seg_raw = raw_data[s:e]
                save_libemg_format(seg_raw, rep=rep_i, class_id=class_id, out_dir=out_dir)
                print(f"    R_{rep_i}_C_{class_id}_{class_name}.csv  ({e-s} 行)")

            # 同时提取静息段（同样原始数据不归一化）
            rest_segments = find_inactive_segments(raw_data, segments, min_rest_len=30)
            if rest_segments:
                rest_segments = rest_segments[:3] if class_name != "静息" else rest_segments
                print(f"  静息段: 检测到 {len(rest_segments)} 个(取前3)")
                rest_rep = 0
                for s, e in rest_segments:
                    rest_raw = raw_data[s:e]
                    save_libemg_format(rest_raw, rep=rest_rep, class_id=0, out_dir=out_dir)
                    print(f"    R_{rest_rep}_C_0_静息.csv  ({e-s} 行)")
                    rest_rep += 1
        else:
            # 传统等分（先整体归一化再等分）
            print(f"  传统等分: {num_reps} 段")
            data = normalize_data(raw_data)
            segments = split_into_reps(data, num_reps)
            class_id = name_to_id[class_name]
            for rep_i, seg in enumerate(segments):
                save_libemg_format(seg, rep=rep_i, class_id=class_id, out_dir=out_dir)
                print(f"    R_{rep_i}_C_{class_id}_{class_name}.csv  ({len(seg)} 行)")

    total = len(os.listdir(out_dir))
    print(f"\n{'='*50}")
    print(f"数据准备完成! 共生成 {total} 个文件")


if __name__ == "__main__":
    main()
