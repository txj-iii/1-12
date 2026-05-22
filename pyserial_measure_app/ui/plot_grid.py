"""
动态网格布局 - 管理所有通道波形控件的排列
"""
from PyQt5.QtWidgets import QWidget, QGridLayout

from ui.channel_plot_widget import ChannelPlotWidget
from config import CHANNEL_COUNT


class PlotGrid(QWidget):
    """通道波形网格布局管理器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = QGridLayout()
        self.grid.setSpacing(3)
        self.grid.setContentsMargins(2, 2, 2, 2)
        self.setLayout(self.grid)
        self.plots: dict[int, ChannelPlotWidget] = {}
        self._channel_count = CHANNEL_COUNT
        self._init_grid()

    def _init_grid(self):
        """初始化网格布局"""
        self._build_grid(self._channel_count)

    def _build_grid(self, n: int):
        """根据通道数构建网格"""
        # 清除旧的控件
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self.plots.clear()

        # 计算网格行列
        rows, cols = self._calc_grid(n)
        for ch in range(n):
            plot = ChannelPlotWidget(ch)
            self.plots[ch] = plot
            row = ch // cols
            col = ch % cols
            self.grid.addWidget(plot, row, col)

    @staticmethod
    def _calc_grid(n: int):
        """计算最优网格行列数"""
        if n <= 1:
            return 1, 1
        if n <= 2:
            return 2, 1
        if n <= 4:
            return 2, 2
        if n <= 6:
            return 3, 2
        if n <= 9:
            return 3, 3
        return 4, 3

    def set_channel_count(self, n: int):
        """动态调整通道数"""
        if n != self._channel_count:
            self._channel_count = n
            self._build_grid(n)

    def update_channel(self, channel_id: int, timestamps: list, values: list):
        """更新指定通道的波形"""
        if channel_id in self.plots:
            self.plots[channel_id].update_data(timestamps, values)

    def update_all(self, channel_data_dict: dict, window_seconds: float):
        """更新所有脏通道的波形"""
        for ch, data in channel_data_dict.items():
            if ch in self.plots and data.dirty:
                t, v = data.get_recent(window_seconds)
                if t and v:
                    self.plots[ch].update_data(t, v)
                data.dirty = False

    def set_channel_y_range(self, channel_id: int, y_min: float, y_max: float, auto: bool = False):
        """设置指定通道的Y轴范围"""
        if channel_id in self.plots:
            self.plots[channel_id].set_y_range(y_min, y_max, auto)

    def clear_all(self):
        """清除所有波形"""
        for plot in self.plots.values():
            plot.clear_plot()
