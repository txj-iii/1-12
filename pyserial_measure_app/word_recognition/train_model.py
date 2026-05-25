"""
基于 LibEMG 的喉部震动词语识别训练与评估流程。

用法:
  cd pyserial_measure_app
  python word_recognition/prepare_data.py   # 先准备数据
  python word_recognition/train_model.py    # 训练+评估
"""
import os
import pickle
import sys
import warnings
from glob import glob

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from word_recognition.config import (
    CLASS_MAPPING,
    CLASS_NAMES,
    WINDOW_SIZE,
    WINDOW_INCREMENT,
    FEATURES,
    CLASSIFIER,
    LABELED_DATA_DIR,
    N_CHANNELS,
)
from word_recognition.features import extract_features, parse_windows_from_array


def load_labeled_data(data_dir: str):
    """加载 LibEMG 格式的标注数据。

    文件名格式: R_{rep}_C_{class}_EMG.csv
    """
    files = sorted(glob(os.path.join(data_dir, "R_*_C_*_EMG.csv")))
    if not files:
        raise FileNotFoundError(f"在 {data_dir} 中没有找到标注数据文件")

    all_data = []
    all_classes = []
    all_reps = []

    for filepath in files:
        basename = os.path.basename(filepath)
        parts = basename.replace(".csv", "").split("_")
        rep = int(parts[1])
        cls = int(parts[3])

        data = np.loadtxt(filepath, delimiter=",")
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        # 只取前 N_CHANNELS 通道 (CH1-CH3 石墨烯传感器, CH4-6 无传感器)
        if data.shape[1] > N_CHANNELS:
            data = data[:, :N_CHANNELS]

        all_data.append(data)
        all_classes.append(cls)
        all_reps.append(rep)

    return all_data, np.array(all_classes), np.array(all_reps)


def main():
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, LABELED_DATA_DIR)

    print("=" * 50)
    print("LibEMG 喉部震动词语识别 - 训练")
    print("=" * 50)

    # 1. 加载数据
    print(f"\n[1/5] 加载数据: {data_dir}")
    data_list, class_list, rep_list = load_labeled_data(data_dir)
    print(f"  文件数: {len(data_list)}")
    for i, (d, c, r) in enumerate(zip(data_list, class_list, rep_list)):
        name = CLASS_MAPPING.get(c, f"未知({c})")
        print(f"    R_{r}_C_{c}_{name}.csv  ({len(d)} 行)")

    # 2. 分窗 (按文件独立分窗, 保留 rep 标签)
    print(f"\n[2/5] 分窗: 窗口大小={WINDOW_SIZE}, 步进={WINDOW_INCREMENT}")
    all_windows = []
    all_classes = []
    all_reps = []

    for data, cls, rep in zip(data_list, class_list, rep_list):
        windows = parse_windows_from_array(data, WINDOW_SIZE, WINDOW_INCREMENT)
        # 限制每个词类文件最多5个窗口，避免长录音主导训练
        if cls != 0 and len(windows) > 5:
            idx = np.random.RandomState(42).choice(len(windows), size=5, replace=False)
            windows = windows[idx]
        if len(windows) > 0:
            all_windows.append(windows)
            all_classes.append(np.full(len(windows), cls))
            all_reps.append(np.full(len(windows), rep))

    windows = np.concatenate(all_windows)
    classes = np.concatenate(all_classes)
    reps = np.concatenate(all_reps)
    print(f"  总窗口数: {windows.shape[0]}")
    print(f"  窗口维度: {windows.shape}")

    unique_cls, counts = np.unique(classes, return_counts=True)
    for cls_id, cnt in zip(unique_cls, counts):
        name = CLASS_MAPPING.get(int(cls_id), f"未知({cls_id})")
        print(f"    类别 {int(cls_id)} ({name}): {cnt} 窗口")

    # 3. 划分: 80/20 随机分层
    print(f"\n[3/6] 划分数据: 80/20 分层随机")
    train_idx, test_idx = train_test_split(
        np.arange(len(windows)), test_size=0.2,
        stratify=classes, random_state=42
    )
    train_windows = windows[train_idx]
    train_labels = classes[train_idx]
    test_windows = windows[test_idx]
    test_labels = classes[test_idx]

    print(f"  训练集: {len(train_windows)} 窗口")
    print(f"  测试集: {len(test_windows)} 窗口")

    # 4. 特征提取
    print(f"\n[4/6] 特征提取: {FEATURES}")
    train_features = extract_features(FEATURES, train_windows)
    test_features = extract_features(FEATURES, test_windows)
    print(f"  训练特征维度: {train_features.shape}")
    print(f"  测试特征维度: {test_features.shape}")

    # 5. 平衡训练集: 下采样 rest 类避免类别失衡
    print(f"\n[5/6] 平衡训练集: 下采样 rest 类")
    rest_mask = train_labels == 0
    word_mask = ~rest_mask
    n_word = word_mask.sum()
    # rest 窗口数限制为 word 的 3 倍
    max_rest = n_word * 3
    if rest_mask.sum() > max_rest:
        rest_idx = np.where(rest_mask)[0]
        keep_rest = np.random.RandomState(42).choice(rest_idx, size=max_rest, replace=False)
        keep_mask = np.zeros(len(train_labels), dtype=bool)
        keep_mask[keep_rest] = True
        keep_mask[word_mask] = True
        train_features = train_features[keep_mask]
        train_labels = train_labels[keep_mask]
        print(f"  rest: {rest_mask.sum()} → {max_rest}, word: {n_word}")
    else:
        print(f"  rest: {rest_mask.sum()}, word: {n_word} (无需下采样)")

    # 6. 训练
    print(f"\n[6/6] 训练分类器: {CLASSIFIER}")
    if CLASSIFIER == 'RF':
        clf = RandomForestClassifier(n_estimators=200, max_depth=10,
                                     class_weight='balanced', random_state=42)
    else:
        clf = LinearDiscriminantAnalysis()
    clf.fit(train_features, train_labels)
    predictions = clf.predict(test_features)

    acc = accuracy_score(test_labels, predictions)
    print(f"\n  准确率: {acc:.1%}")

    cm = confusion_matrix(test_labels, predictions)
    print(f"\n  混淆矩阵 (行=真实, 列=预测):\n{cm}")

    print(f"\n  分类报告:")
    present_labels = sorted(np.unique(np.concatenate([test_labels, predictions])))
    present_names = [CLASS_MAPPING.get(int(l), f"未知({l})") for l in present_labels]
    print(classification_report(
        test_labels, predictions,
        labels=present_labels,
        target_names=present_names,
        zero_division=0,
    ))

    # 保存模型
    model_dir = os.path.join(base_dir, "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, f"word_classifier_{CLASSIFIER}.pkl")
    with open(model_path, "wb") as f:
        pickle.dump({
            "model": clf,
            "features": FEATURES,
            "window_size": WINDOW_SIZE,
            "window_increment": WINDOW_INCREMENT,
            "class_mapping": CLASS_MAPPING,
        }, f)
    print(f"\n模型已保存: {model_path}")


if __name__ == "__main__":
    main()
