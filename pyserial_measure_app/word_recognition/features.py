"""
特征提取模块 - 与 LibEMG HTD 组一致
"""
import numpy as np


def extract_mav(windows: np.ndarray) -> np.ndarray:
    """Mean Absolute Value: 每个窗口每通道的绝对值均值."""
    return np.mean(np.abs(windows), axis=2)


def extract_zc(windows: np.ndarray) -> np.ndarray:
    """Zero Crossings: 过零率."""
    n_windows, n_channels, n_samples = windows.shape
    zc = np.zeros((n_windows, n_channels))
    for i in range(n_windows):
        for j in range(n_channels):
            sign_changes = np.diff(np.sign(windows[i, j])) != 0
            zc[i, j] = np.sum(sign_changes)
    return zc


def extract_ssc(windows: np.ndarray) -> np.ndarray:
    """Slope Sign Changes: 斜率符号变化次数."""
    n_windows, n_channels, n_samples = windows.shape
    ssc = np.zeros((n_windows, n_channels))
    for i in range(n_windows):
        for j in range(n_channels):
            diff = np.diff(windows[i, j])
            slope_sign_changes = np.diff(np.sign(diff)) != 0
            ssc[i, j] = np.sum(slope_sign_changes)
    return ssc


def extract_wl(windows: np.ndarray) -> np.ndarray:
    """Waveform Length: 波形长度."""
    diffs = np.diff(windows, axis=2)
    return np.sum(np.abs(diffs), axis=2)


FEATURE_FUNCS = {
    'MAV': extract_mav,
    'ZC': extract_zc,
    'SSC': extract_ssc,
    'WL': extract_wl,
}


def center_windows(windows: np.ndarray) -> np.ndarray:
    """每窗口每通道减均值（去直流），消除传感器基线偏移"""
    centered = windows.copy()
    means = np.mean(centered, axis=1, keepdims=True)
    return centered - means


def extract_features(feature_list, windows, center=False):
    """提取多个特征并拼接为一个二维数组 (n_windows, n_features * n_channels).

    center=True: 先对每个窗口去直流（减均值），使特征不受基线电压偏移影响。
    """
    if center and windows.shape[1] > 0:
        windows = center_windows(windows)
    feat_vectors = []
    for fname in feature_list:
        func = FEATURE_FUNCS.get(fname)
        if func is None:
            raise ValueError(f"未知特征: {fname}")
        feat = func(windows)
        feat_vectors.append(feat)
    return np.concatenate(feat_vectors, axis=1)


def parse_windows_from_array(data: np.ndarray, window_size: int, window_increment: int):
    """对单个数据数组分窗."""
    windows = []
    n_samples = data.shape[0]
    if n_samples < window_size:
        return np.array([])
    for start in range(0, n_samples - window_size + 1, window_increment):
        windows.append(data[start:start + window_size])
    return np.array(windows)
