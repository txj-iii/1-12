"""
将连续"我买苹果"录音按 active segment 分割为单个词标注数据，
使用与 prepare_data.py 相同的 EMG 命名格式，确保 train_model.py 能加载。

用法:
  cd pyserial_measure_app
  python word_recognition/split_continuous_csv.py

依赖: 先运行 prepare_data.py 准备好旧数据的标注目录结构
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prepare_data import find_active_segments, normalize_data, save_libemg_format, find_inactive_segments

# 类别映射
CLASS_NAMES = ["我", "买", "苹果"]
CLASS_IDS = {"我": 1, "买": 2, "苹果": 3}

# 3个新CSV文件（连续"我买苹果"重复录音）
NEW_FILES = [
    "2026-05-18_14-05-32.csv",
    "2026-05-18_14-06-15.csv",
    "2026-05-18_14-06-56.csv",
]

# 配置
EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "exports")
LABELED_DIR = os.path.join(os.path.dirname(__file__), "data", "labeled")

# 分词参数 (与 prepare_data 默认值一致，三个文件均得到3的倍数段)
MERGE_GAP = 50
MIN_LEN = 20
THRESHOLD_MULT = 1.5


def load_csv(filepath):
    """加载 CSV 文件的6个通道数据"""
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            rows.append([float(x) for x in row[:6]])
    return np.array(rows)


def get_next_reps(label_dir):
    """扫描已存在的 EMG 文件，按 class_id 统计最大 rep 编号（不受中文名影响）"""
    max_reps = {0: 0, 1: 0, 2: 0, 3: 0}
    if not os.path.isdir(label_dir):
        return max_reps
    for f in os.listdir(label_dir):
        if not f.endswith(".csv"):
            continue
        # 格式: R_{rep}_C_{class_id}_EMG.csv
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

    # 按 class_id 扫描现有文件，不受中文名编码影响
    next_reps = get_next_reps(LABELED_DIR)
    print("各类别起始 rep 编号:")
    for name, cls_id in sorted(CLASS_IDS.items(), key=lambda x: x[1]):
        print(f"  {name}(C_{cls_id}): {next_reps[cls_id]}")
    print(f"  静息(C_0): {next_reps[0]}")

    total_word_segments = 0

    for fname in NEW_FILES:
        filepath = os.path.join(EXPORTS_DIR, fname)
        if not os.path.exists(filepath):
            print(f"[跳过] {fname} 不存在")
            continue

        print(f"\n{'='*50}")
        print(f"处理: {fname}")
        raw = load_csv(filepath)
        print(f"  总行数: {len(raw)}")

        # 用归一化数据检测活跃段
        norm_full = normalize_data(raw.copy())
        segments = find_active_segments(
            norm_full,
            smooth_win=15,
            threshold_mult=THRESHOLD_MULT,
            merge_gap=MERGE_GAP,
            min_len=MIN_LEN,
        )
        print(f"  活跃段数: {len(segments)} (merge_gap={MERGE_GAP})")
        for i, (s, e) in enumerate(segments):
            print(f"    段{i}: {s}-{e} ({e-s}行)")

        if len(segments) == 0:
            print("  ! 无活跃段，跳过")
            continue

        # 按"我→买→苹果"循环分配标签
        word_idx = 0
        for s, e in segments:
            cls_name = CLASS_NAMES[word_idx % 3]
            cls_id = CLASS_IDS[cls_name]
            seg_data = raw[s:e]  # 原始数据，不归一化

            save_libemg_format(seg_data, next_reps[cls_id], cls_id, LABELED_DIR)
            print(f"    R_{next_reps[cls_id]}_C_{cls_id}_EMG.csv ({e-s}行)")
            next_reps[cls_id] += 1
            total_word_segments += 1
            word_idx += 1

        # 提取静息段（反推活跃段间隙）
        rest_segments = find_inactive_segments(raw, segments, min_rest_len=30)
        rest_segments = rest_segments[:3]  # 最多取3个
        print(f"  静息段: {len(rest_segments)} 个")
        for s, e in rest_segments:
            rest_data = raw[s:e]
            save_libemg_format(rest_data, next_reps[0], 0, LABELED_DIR)
            print(f"    R_{next_reps[0]}_C_0_EMG.csv ({e-s}行)")
            next_reps[0] += 1

    print(f"\n{'='*50}")
    print(f"完成! 新增 {total_word_segments} 个词语段 + 静息段")
    total = len(os.listdir(LABELED_DIR))
    print(f"  标注目录总文件数: {total}")
    print(f"  我: {next_reps[1]} | 买: {next_reps[2]} | 苹果: {next_reps[3]} | 静息: {next_reps[0]}")


if __name__ == "__main__":
    main()
