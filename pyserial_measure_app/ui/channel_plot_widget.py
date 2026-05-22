"""
单通道波形控件 - 使用pyqtgraph实现实时曲线显示
"""
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

from config import CHANNEL_COLORS, DISPLAY_WINDOW_SECONDS, PLOT_LINE_WIDTH


class ChannelPlotWidget(QWidget):
    """单个通道的波形显示控件"""

    def __init__(self, channel_id: int, parent=None):
        super().__init__(parent)
        self.channel_id = channel_id
        self._y_min = None
        self._y_max = None
        self._y_auto = True
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏：显示通道号和当前值
        self.title_label = QLabel(f"CH{self.channel_id + 1}: --- kΩ")
        self.title_label.setStyleSheet("""
            QLabel {
                background-color: rgb(%d, %d, %d);
                color: white;
                padding: 2px 8px;
                font-weight: bold;
                font-size: 12px;
            }
        """ % CHANNEL_COLORS[self.channel_id % len(CHANNEL_COLORS)])
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # 创建pyqtgraph绘图控件
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', '电阻', units='kΩ')
        self.plot_widget.setLabel('bottom', '时间', units='s')
        self.plot_widget.setXRange(-DISPLAY_WINDOW_SECONDS, 0)
        self.plot_widget.setMouseEnabled(x=False, y=True)
        self.plot_widget.setMenuEnabled(False)

        # 曲线
        color = CHANNEL_COLORS[self.channel_id % len(CHANNEL_COLORS)]
        pen = pg.mkPen(color=color, width=PLOT_LINE_WIDTH)
        self.curve = self.plot_widget.plot(pen=pen)

        layout.addWidget(self.plot_widget)

    def update_data(self, timestamps: list, values: list):
        """更新曲线数据"""
        if len(timestamps) < 2 or len(values) < 2:
            return

        self.curve.setData(timestamps, values)

        # 自动或手动Y轴范围
        if self._y_auto:
            self.plot_widget.enableAutoRange(axis='y')
        else:
            self.plot_widget.setYRange(self._y_min, self._y_max)

        # 更新标题显示最新值
        if values:
            latest = values[-1]
            self.title_label.setText(f"CH{self.channel_id + 1}: {latest:.3f} kΩ")

    def set_y_range(self, y_min: float, y_max: float, auto: bool = False):
        """设置Y轴范围"""
        self._y_min = y_min
        self._y_max = y_max
        self._y_auto = auto
        if not auto:
            self.plot_widget.setYRange(y_min, y_max)

    def clear_plot(self):
        """清除曲线"""
        self.curve.clear()
        self.title_label.setText(f"CH{self.channel_id + 1}: --- kΩ")
