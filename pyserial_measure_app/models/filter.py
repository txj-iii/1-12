"""
数据滤波模块 - 限幅滤波和滑动平均滤波
"""
from collections import deque
from typing import Optional


class DataFilter:
    """
    数据滤波器，支持两种模式：
    - 'limit': 限幅滤波，变化超过阈值百分比则丢弃
    - 'average': 滑动平均，取最近N个点的平均值
    """

    MODE_NONE = 'none'
    MODE_LIMIT = 'limit'
    MODE_AVERAGE = 'average'

    def __init__(self):
        self.mode = self.MODE_NONE
        self.limit_threshold = 10.0   # 限幅百分比
        self.average_window = 5       # 滑动窗口大小

        # 每通道状态
        self._prev_values: dict[int, float] = {}
        self._buffers: dict[int, deque] = {}

    def configure(self, mode: str, limit_threshold: float = 10.0,
                  average_window: int = 5):
        """配置滤波参数"""
        self.mode = mode
        if mode == self.MODE_LIMIT:
            self.limit_threshold = max(0.1, limit_threshold)
        elif mode == self.MODE_AVERAGE:
            self.average_window = max(2, min(100, average_window))

    def apply(self, channel_id: int, value: float) -> float:
        """对指定通道的值应用滤波，返回滤波后的值"""
        if self.mode == self.MODE_LIMIT:
            return self._apply_limit(channel_id, value)
        elif self.mode == self.MODE_AVERAGE:
            return self._apply_average(channel_id, value)
        return value

    def _apply_limit(self, channel_id: int, value: float) -> float:
        """限幅滤波：变化超过阈值则丢弃"""
        prev = self._prev_values.get(channel_id)
        if prev is None:
            self._prev_values[channel_id] = value
            return value

        if prev != 0:
            change_pct = abs(value - prev) / abs(prev) * 100
        else:
            change_pct = abs(value) * 100  # 从0跳变视为巨大变化

        if change_pct > self.limit_threshold:
            # 超出阈值，丢弃，保留上一个值
            return prev

        self._prev_values[channel_id] = value
        return value

    def _apply_average(self, channel_id: int, value: float) -> float:
        """滑动平均：返回最近N个点的平均值"""
        if channel_id not in self._buffers:
            self._buffers[channel_id] = deque(maxlen=self.average_window)

        buf = self._buffers[channel_id]
        buf.append(value)

        # 累积足够点数后才开始输出平均值
        if len(buf) < self.average_window:
            return value  # 窗口未满，直接输出原始值

        return sum(buf) / len(buf)

    def reset(self, channel_id: Optional[int] = None):
        """重置指定通道或全部通道的状态"""
        if channel_id is None:
            self._prev_values.clear()
            self._buffers.clear()
        else:
            self._prev_values.pop(channel_id, None)
            self._buffers.pop(channel_id, None)
