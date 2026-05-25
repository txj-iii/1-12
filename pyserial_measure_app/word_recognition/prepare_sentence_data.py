"""
将句子录音"我买苹果"按单词分割并增量追加到标注数据集。
每个文件包含8-9次句子重复，从中提取"我"、"买"、"苹果"三个词。

只用 CH1+CH2: 基于CH2滚动标准差检测语音活动段 → 等分为3词。

用法:
  cd pyserial_measure_app
  python word_recognition/prepare_sentence_data.py
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prepare_data import load_csv, save_libemg_format

N_CHANNELS = 2

SENTENCE_FILES = [
    "2026-05-24_14-56-33.csv",
    "2026-05-24_14-57-43.csv",
    "2026-05-24_14-59-10.csv",
    "2026-05-24_14-59-45.csv",
]

EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "exports")
LABELED_DIR = os.path.join(os.path.dirname(__file__), "data", "labeled")


def get_next_reps(label_dir):
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


def ch2_energy(ch2, win=8):
    energy = np.zeros(len(ch2))
    for i in range(win, len(ch2)):
        energy[i] = np.std(ch2[i - win : i])
    return energy


def find_sentence_segments(ch2, thresh_sigma=0.2, min_dur=25, max_dur=80, merge_gap=45):
    """用CH2能量检测句子级语音段"""
    energy = ch2_energy(ch2)

    e_median = np.median(energy)
    e_std = np.std(energy)
    thresh = e_median + thresh_sigma * e_std

    active = energy > thresh
    raw = []
    start = None
    for i, a in enumerate(active):
        if a and start is None:
            start = i
        elif not a and start is not None:
            if i - start >= 8:
                raw.append((start, i))
            start = None
    if start is not None and len(energy) - start >= 8:
        raw.append((start, len(energy)))

    if not raw:
        return []

    # 合并间隔 < merge_gap 的段 (句内词间可能短暂停顿)
    merged = [raw[0]]
    for s, e in raw[1:]:
        if s - merged[-1][1] < merge_gap:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))

    # 过滤 + 切分过长段
    result = []
    for s, e in merged:
        dur = e - s
        seg_ch2 = ch2[s:e]
        # 过滤: CH2要有实际变化
        if seg_ch2.max() - seg_ch2.min() < 0.5:
            continue
        if min_dur <= dur <= max_dur:
            result.append((s, e))
        elif dur > max_dur:
            # 均分为 ~60行/段
            n_sub = max(2, round(dur / 55))
            sub_len = dur // n_sub
            for i in range(n_sub):
                sub_s = s + i * sub_len
                sub_e = s + (i + 1) * sub_len if i < n_sub - 1 else e
                if sub_e - sub_s >= min_dur:
                    result.append((sub_s, sub_e))

    return result


def split_into_words(seg_data, n_words=3):
    total = len(seg_data)
    word_len = total // n_words
    words = []
    for i in range(n_words):
        start = i * word_len
        end = total if i == n_words - 1 else (i + 1) * word_len
        words.append(seg_data[start:end])
    return words


def process_file(filepath, next_reps, label_dir):
    fname = os.path.basename(filepath)
    raw_data = load_csv(filepath)
    ch2 = raw_data[:, 1]

    print(f"\n{'='*60}")
    print(f"{fname}: {len(raw_data)} 行, CH2 [{ch2.min():.1f}, {ch2.max():.1f}]")

    sentences = find_sentence_segments(ch2)
    print(f"  检测到 {len(sentences)} 个句子段")

    total_word = 0
    total_rest = 0

    for s, e in sentences:
        seg_raw = raw_data[s:e, :N_CHANNELS]
        dur = (e - s) / 10
        words = split_into_words(seg_raw, n_words=3)
        print(f"  [{s}-{e}] {dur:.1f}s → 我({len(words[0])}) 买({len(words[1])}) 苹果({len(words[2])})")

        for wi, wdata in enumerate(words):
            cls_id = wi + 1
            if len(wdata) >= 8:
                save_libemg_format(wdata, next_reps[cls_id], cls_id, label_dir)
                next_reps[cls_id] += 1
                total_word += 1

    # 静息段: CH2能量最低的区域
    energy = ch2_energy(ch2)
    e_median = np.median(energy)
    silent = energy < e_median * 0.3
    rest_segs = []
    start = None
    for i, s in enumerate(silent):
        if s and start is None:
            start = i
        elif not s and start is not None:
            if i - start >= 30:
                rest_segs.append((start, i))
            start = None
    if start is not None and len(silent) - start >= 30:
        rest_segs.append((start, len(silent)))

    rest_segs = rest_segs[:4]
    for s, e in rest_segs:
        rest_raw = raw_data[s:e, :N_CHANNELS]
        if len(rest_raw) >= 20:
            save_libemg_format(rest_raw, next_reps[0], 0, label_dir)
            next_reps[0] += 1
            total_rest += 1
    print(f"  静息段: {len(rest_segs)}")

    return total_word, total_rest


def main():
    os.makedirs(LABELED_DIR, exist_ok=True)
    class_names = {0: "rest", 1: "我", 2: "买", 3: "苹果"}

    next_reps = get_next_reps(LABELED_DIR)
    print("各类别起始 rep:")
    for cls_id, name in class_names.items():
        print(f"  {name}: {next_reps[cls_id]}")

    total_word = 0
    total_rest = 0

    for fname in SENTENCE_FILES:
        filepath = os.path.join(EXPORTS_DIR, fname)
        if not os.path.exists(filepath):
            print(f"[跳过] 文件不存在: {fname}")
            continue
        w, r = process_file(filepath, next_reps, LABELED_DIR)
        total_word += w
        total_rest += r

    print(f"\n{'='*60}")
    print(f"新增 {total_word} 单词 + {total_rest} 静息")
    for cls_id, name in class_names.items():
        print(f"  {name}: {next_reps[cls_id]} rep")
    print(f"总文件数: {len(os.listdir(LABELED_DIR))}")


if __name__ == "__main__":
    main()
