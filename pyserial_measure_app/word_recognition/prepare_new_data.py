"""
将新录制的单词CSV按 active segment 分割并增量追加到标注数据集。
不清空已有 data/labeled/ 文件，从已有编号续编。

用法:
  cd pyserial_measure_app
  python word_recognition/prepare_new_data.py
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prepare_data import (
    load_csv,
    normalize_data,
    find_active_segments,
    find_inactive_segments,
    save_libemg_format,
)

# 只使用 CH1-CH2 (石墨烯传感器)，CH3 量级过大且对词语区分为度低
N_CHANNELS = 2

# 12个新文件: 前4→我(单波峰), 中4→买(单波峰), 后4→苹果(双波峰)
NEW_FILES = [
    ("2026-05-24_14-15-29.csv", "我", 1),
    ("2026-05-24_14-16-42.csv", "我", 1),
    ("2026-05-24_14-18-06.csv", "我", 1),
    ("2026-05-24_14-18-51.csv", "我", 1),
    ("2026-05-24_14-19-38.csv", "买", 2),
    ("2026-05-24_14-20-17.csv", "买", 2),
    ("2026-05-24_14-21-31.csv", "买", 2),
    ("2026-05-24_14-22-28.csv", "买", 2),
    ("2026-05-24_14-23-34.csv", "苹果", 3),
    ("2026-05-24_14-24-37.csv", "苹果", 3),
    ("2026-05-24_14-25-21.csv", "苹果", 3),
    ("2026-05-24_14-26-10.csv", "苹果", 3),
]

EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "exports")
LABELED_DIR = os.path.join(os.path.dirname(__file__), "data", "labeled")


def get_next_reps(label_dir):
    """扫描已存在的 EMG 文件，按 class_id 统计最大 rep 编号"""
    max_reps = {0: 0, 1: 0, 2: 0, 3: 0}
    if not os.path.isdir(label_dir):
        return max_reps
    for f in os.listdir(label_dir):
        if not f.endswith(".csv"):
            continue
        parts = f.replace(".csv", "").split("_")
        if len(parts) >= 4 and parts[0] == "R" and parts[2] == "C":
            try:
                rep = int(parts[1])
                cls = int(parts[3])
                if cls in max_reps and rep >= max_reps[cls]:
                    max_reps[cls] = rep + 1
            except ValueError:
                continue
    return max_reps


def main():
    os.makedirs(LABELED_DIR, exist_ok=True)

    next_reps = get_next_reps(LABELED_DIR)
    print("各类别起始 rep 编号:")
    for name, cls_id in [("静息", 0), ("我", 1), ("买", 2), ("苹果", 3)]:
        print(f"  {name}(C_{cls_id}): {next_reps[cls_id]}")

    total_word = 0
    total_rest = 0

    for fname, class_name, class_id in NEW_FILES:
        filepath = os.path.join(EXPORTS_DIR, fname)
        if not os.path.exists(filepath):
            print(f"[跳过] 文件不存在: {fname}")
            continue

        print(f"\n{'='*50}")
        print(f"{class_name}: {fname}")
        raw_data = load_csv(filepath)
        print(f"  加载 {len(raw_data)} 行, 6 通道")

        # 用 CH1-3 检测活跃段 (CH3 有清晰的 speech/silence 跳变, ~26 → ~20000)
        # threshold_mult=3.0 提高门槛, 避免碎片化; min_len=30 滤除短噪声
        norm_full = normalize_data(raw_data[:, :3].copy())
        segments = find_active_segments(norm_full, threshold_mult=3.0, min_len=30, merge_gap=80)
        # 单次单词录音预期1-3个活跃段, 若过多则只保留最长的3个
        if len(segments) > 3:
            segments.sort(key=lambda se: se[1] - se[0], reverse=True)
            segments = sorted(segments[:3], key=lambda se: se[0])
        print(f"  检测到 {len(segments)} 个活跃段")

        if not segments:
            print("  ! 无活跃段，跳过")
            continue

        total_active = sum(e - s for s, e in segments)
        print(f"  有效数据: {total_active}/{len(raw_data)} = {total_active / len(raw_data) * 100:.1f}%")

        for s, e in segments:
            seg_raw = raw_data[s:e, :N_CHANNELS]  # 只保留 CH1-3
            save_libemg_format(seg_raw, next_reps[class_id], class_id, LABELED_DIR)
            print(f"    R_{next_reps[class_id]}_C_{class_id}_EMG.csv  ({e - s} 行)")
            next_reps[class_id] += 1
            total_word += 1

        # 提取静息段
        rest_segments = find_inactive_segments(raw_data, segments, min_rest_len=30)
        rest_segments = rest_segments[:3]
        if rest_segments:
            print(f"  静息段: {len(rest_segments)} 个")
            for s, e in rest_segments:
                rest_raw = raw_data[s:e, :N_CHANNELS]  # 只保留 CH1-3
                save_libemg_format(rest_raw, next_reps[0], 0, LABELED_DIR)
                print(f"    R_{next_reps[0]}_C_0_EMG.csv  ({e - s} 行)")
                next_reps[0] += 1
                total_rest += 1

    print(f"\n{'='*50}")
    print(f"完成! 新增 {total_word} 个词语段 + {total_rest} 个静息段")
    total = len(os.listdir(LABELED_DIR))
    print(f"标注目录总文件数: {total}")
    print(f"我: {next_reps[1]} | 买: {next_reps[2]} | 苹果: {next_reps[3]} | 静息: {next_reps[0]}")


if __name__ == "__main__":
    main()
