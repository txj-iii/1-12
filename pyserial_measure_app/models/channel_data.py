"""
每通道环形缓冲区 - 存储和管理单个通道的时间序列数据
"""
from collections import deque
from typing import Optional
import time


class ChannelData:
    """单通道数据缓冲区"""

    def __init__(self, channel_id: int, maxlen: int = 10000):
        self.channel_id = channel_id
        self.maxlen = maxlen
        self.timestamps: deque[float] = deque(maxlen=maxlen)
        self.values: deque[float] = deque(maxlen=maxlen)
        self.frame_counters: deque[int] = deque(maxlen=maxlen)
        self._dirty = False
        self._last_value: Optional[float] = None

    @property
    def dirty(self) -> bool:
        return self._dirty

    @dirty.setter
    def dirty(self, value: bool):
        self._dirty = value

    @property
    def last_value(self) -> Optional[float]:
        return self._last_value

    @property
    def sample_count(self) -> int:
        return len(self.values)

    def append(self, value: float, timestamp: float, frame_counter: int):
        """添加一个数据点"""
        self.timestamps.append(timestamp)
        self.values.append(value)
        self.frame_counters.append(frame_counter)
        self._last_value = value
        self._dirty = True

    def clear(self):
        """清空所有数据"""
        self.timestamps.clear()
        self.values.clear()
        self.frame_counters.clear()
        self._last_value = None
        self._dirty = False

    def get_recent(self, window_seconds: float = 30.0):
        """
        获取最近 window_seconds 秒内的数据。
        返回 (timestamps, values)，时间戳为相对于最新的偏移（最新为0）。
        """
        n = len(self.timestamps)
        if n < 2:
            return [], []

        now = self.timestamps[-1]
        cutoff = now - window_seconds

        # 找到起始索引
        start = 0
        for i in range(n):
            if self.timestamps[i] >= cutoff:
                start = i
                break

        t = [ts - now for ts in list(self.timestamps)[start:]]
        v = list(self.values)[start:]
        return t, v

    def to_csv_rows(self):
        """
        导出所有数据为CSV行。
        返回 [(value, frame_counter, timestamp_str), ...]
        """
        rows = []
        for i in range(len(self.values)):
            ts = time.strftime('%H:%M:%S', time.localtime(self.timestamps[i]))
            rows.append((self.values[i], self.frame_counters[i], ts))
        return rows
