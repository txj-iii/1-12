"""
对比旧模型（81文件训练）和新模型（192文件训练）在相同测试集上的性能。

用法:
  cd pyserial_measure_app
  python word_recognition/compare_models.py
"""
import os
import pickle
import sys
import warnings
from glob import glob

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from word_recognition.config import (
    CLASS_MAPPING, CLASS_NAMES, WINDOW_SIZE, WINDOW_INCREMENT,
    FEATURES, CLASSIFIER, LABELED_DATA_DIR, N_CHANNELS,
)
from word_recognition.features import extract_features, parse_windows_from_array
from word_recognition.train_model import load_labeled_data
from sklearn.model_selection import train_test_split


def main():
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, LABELED_DATA_DIR)
    models_dir = os.path.join(base_dir, "models")

    # 加载所有标注数据
    print("加载标注数据...")
    data_list, class_list, rep_list = load_labeled_data(data_dir)
    print(f"  共 {len(data_list)} 个文件")

    # 分窗
    print(f"分窗: size={WINDOW_SIZE}, step={WINDOW_INCREMENT}")
    all_windows = []
    all_classes = []
    for data, cls in zip(data_list, class_list):
        windows = parse_windows_from_array(data, WINDOW_SIZE, WINDOW_INCREMENT)
        if len(windows) > 0:
            all_windows.append(windows)
            all_classes.append(np.full(len(windows), cls))
    windows = np.concatenate(all_windows)
    classes = np.concatenate(all_classes)
    print(f"  总窗口: {len(windows)}")

    # 80/20 分层划分
    train_idx, test_idx = train_test_split(
        np.arange(len(windows)), test_size=0.2,
        stratify=classes, random_state=42
    )
    test_windows = windows[test_idx]
    test_labels = classes[test_idx]
    print(f"  测试集: {len(test_windows)} 窗口")

    # 提取测试特征
    test_features = extract_features(FEATURES, test_windows)
    print(f"  测试特征: {test_features.shape}")

    # 加载并评估两个模型
    for label, pkl_file in [
        ("旧模型 (81文件)", "word_classifier_RF_old.pkl"),
        ("新模型 (192文件)", "word_classifier_RF.pkl"),
    ]:
        path = os.path.join(models_dir, pkl_file)
        if not os.path.exists(path):
            print(f"\n[跳过] {pkl_file} 不存在")
            continue

        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")

        with open(path, "rb") as f:
            bundle = pickle.load(f)

        clf = bundle["model"]
        pred = clf.predict(test_features)

        acc = accuracy_score(test_labels, pred)
        print(f"\n  准确率: {acc:.1%}")

        cm = confusion_matrix(test_labels, pred)
        print(f"\n  混淆矩阵 (行=真实, 列=预测):")
        print(f"          rest   I  buy apple")
        for i, row_name in enumerate(["rest", "I   ", "buy ", "apple"]):
            print(f"    {row_name}  " + "  ".join(f"{v:>3}" for v in cm[i]))

        print(f"\n  分类报告:")
        present = sorted(np.unique(np.concatenate([test_labels, pred])))
        names = [CLASS_MAPPING.get(int(l), f"?{l}") for l in present]
        print(classification_report(
            test_labels, pred,
            labels=present, target_names=names, zero_division=0,
        ))

    print(f"\n{'='*60}")
    print("  对比完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
