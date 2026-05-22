"""
词语识别预测 - 图形界面版
双击运行，选CSV文件即可预测
"""
import os
import sys
import pickle
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import Counter

import numpy as np

# 项目根目录
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "pyserial_measure_app"))

from word_recognition.features import extract_features, parse_windows_from_array


def load_csv_data(filepath):
    import csv
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            rows.append([float(x) for x in row[:6]])
    return np.array(rows)


def load_model():
    model_dir = os.path.join(ROOT, "pyserial_measure_app", "word_recognition", "models")
    files = sorted(os.listdir(model_dir))
    if not files:
        return None, "未找到模型文件，请先运行 train_model.py"
    with open(os.path.join(model_dir, files[-1]), "rb") as f:
        data = pickle.load(f)
    return data, None


def predict(filepath):
    data = load_csv_data(filepath)
    model_data, err = load_model()
    if err:
        return err

    clf = model_data["model"]
    features = model_data["features"]
    window_size = model_data["window_size"]
    window_inc = model_data.get("window_increment", 25)
    class_mapping = model_data["class_mapping"]

    if len(data) < window_size:
        return f"数据太少 ({len(data)}行)，需要至少 {window_size} 行"

    windows = parse_windows_from_array(data, window_size, window_inc)
    if len(windows) < 1:
        return "分窗后无数据"

    feat = extract_features(features, windows)
    predictions = clf.predict(feat)

    vote = Counter(predictions)
    total = len(predictions)
    lines = [f"文件: {os.path.basename(filepath)}", f"窗口总数: {total}", ""]
    for cls_id in sorted(vote.keys()):
        pct = vote[cls_id] / total * 100
        name = class_mapping.get(int(cls_id), f"未知({cls_id})")
        bar = "█" * int(pct / 5)
        lines.append(f"  {name}: {pct:.1f}% ({vote[cls_id]}/{total}) {bar}")

    best = vote.most_common(1)[0]
    best_name = class_mapping.get(int(best[0]), f"未知({best[0]})")
    lines.append(f"\n→ 结论: {best_name}")
    return "\n".join(lines)


def main():
    try:
        model_data, err = load_model()
        if err:
            messagebox.showerror("错误", err)
            return

        filepath = filedialog.askopenfilename(
            title="选择CSV文件",
            filetypes=[("CSV文件", "*.csv")],
            initialdir=os.path.join(ROOT, "exports"),
        )
        if not filepath:
            return

        result = predict(filepath)
        messagebox.showinfo("预测结果", result)
    except Exception as e:
        messagebox.showerror("错误", f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    main()
