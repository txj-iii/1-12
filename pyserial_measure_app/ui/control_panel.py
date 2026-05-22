"""
控制栏 - 串口配置、滤波、启停、导出按钮
"""
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QPushButton,
    QSpinBox, QDoubleSpinBox, QLabel
)
from PyQt5.QtCore import pyqtSignal

from config import (
    BAUDRATES, CHANNEL_COUNT, MIN_CHANNELS, MAX_CHANNELS,
    FILTER_DEFAULT_LIMIT, FILTER_DEFAULT_WINDOW,
)


class ControlPanel(QWidget):
    """顶部控制栏"""

    start_requested = pyqtSignal(str, int, int)  # port, baudrate, channels
    stop_requested = pyqtSignal()
    export_requested = pyqtSignal()
    filter_changed = pyqtSignal(str, float, int)  # mode, limit_threshold, avg_window

    def __init__(self, parent=None):
        super().__init__(parent)
        self._acquiring = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # COM口选择
        layout.addWidget(QLabel("COM口:"))
        self.com_port_combo = QComboBox()
        self.com_port_combo.setMinimumWidth(80)
        self.com_port_combo.setEditable(True)
        self._populate_com_ports()
        layout.addWidget(self.com_port_combo)

        # 刷新COM口按钮
        self.refresh_com_btn = QPushButton("刷新")
        self.refresh_com_btn.setFixedWidth(40)
        self.refresh_com_btn.clicked.connect(self._populate_com_ports)
        layout.addWidget(self.refresh_com_btn)

        # 波特率选择
        layout.addWidget(QLabel("波特率:"))
        self.baudrate_combo = QComboBox()
        for b in BAUDRATES:
            self.baudrate_combo.addItem(str(b), b)
        self.baudrate_combo.setCurrentText("115200")
        layout.addWidget(self.baudrate_combo)

        # 通道数
        layout.addWidget(QLabel("通道:"))
        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(MIN_CHANNELS, MAX_CHANNELS)
        self.channel_spin.setValue(CHANNEL_COUNT)
        self.channel_spin.setFixedWidth(50)
        layout.addWidget(self.channel_spin)

        layout.addSpacing(10)

        # 滤波模式
        layout.addWidget(QLabel("滤波:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("无", 'none')
        self.filter_combo.addItem("限幅", 'limit')
        self.filter_combo.addItem("平滑", 'average')
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.filter_combo)

        # 限幅阈值 (%)
        self.limit_label = QLabel("阈值%:")
        self.limit_spin = QDoubleSpinBox()
        self.limit_spin.setRange(0.1, 100.0)
        self.limit_spin.setDecimals(1)
        self.limit_spin.setSingleStep(1.0)
        self.limit_spin.setValue(FILTER_DEFAULT_LIMIT)
        self.limit_spin.setFixedWidth(55)
        self.limit_spin.valueChanged.connect(self._on_filter_changed)
        layout.addWidget(self.limit_label)
        layout.addWidget(self.limit_spin)

        # 滑动窗口
        self.window_label = QLabel("窗口:")
        self.window_spin = QSpinBox()
        self.window_spin.setRange(2, 100)
        self.window_spin.setValue(FILTER_DEFAULT_WINDOW)
        self.window_spin.setFixedWidth(45)
        self.window_spin.valueChanged.connect(self._on_filter_changed)
        layout.addWidget(self.window_label)
        layout.addWidget(self.window_spin)

        self._update_filter_visibility()

        layout.addSpacing(15)

        # 启动按钮
        self.start_btn = QPushButton("启动")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white;
                font-weight: bold; padding: 5px 20px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.start_btn.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.start_btn)

        # 停止按钮
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336; color: white;
                font-weight: bold; padding: 5px 20px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #da190b; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.stop_btn)

        layout.addSpacing(15)

        # 导出按钮
        self.export_btn = QPushButton("导出CSV")
        self.export_btn.clicked.connect(self.export_requested.emit)
        layout.addWidget(self.export_btn)

        layout.addStretch()

    def _populate_com_ports(self):
        """扫描可用COM口"""
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            current = self.com_port_combo.currentText()
            self.com_port_combo.clear()
            for p in ports:
                self.com_port_combo.addItem(p.device)
            if current:
                idx = self.com_port_combo.findText(current)
                if idx >= 0:
                    self.com_port_combo.setCurrentIndex(idx)
        except Exception:
            self.com_port_combo.clear()
            self.com_port_combo.addItem("COM3")

    def _on_start_clicked(self):
        port = self.com_port_combo.currentText().strip()
        baudrate = self.baudrate_combo.currentData()
        channels = self.channel_spin.value()
        self.start_requested.emit(port, baudrate, channels)

    def _on_stop_clicked(self):
        self.stop_requested.emit()

    def set_acquiring(self, acquiring: bool):
        """切换采集状态UI"""
        self._acquiring = acquiring
        self.start_btn.setEnabled(not acquiring)
        self.stop_btn.setEnabled(acquiring)
        self.com_port_combo.setEnabled(not acquiring)
        self.baudrate_combo.setEnabled(not acquiring)
        self.channel_spin.setEnabled(not acquiring)
        self.refresh_com_btn.setEnabled(not acquiring)

    def _update_filter_visibility(self):
        """根据滤波模式显示/隐藏对应参数"""
        mode = self.filter_combo.currentData()
        show_limit = (mode == 'limit')
        show_avg = (mode == 'average')

        self.limit_label.setVisible(show_limit)
        self.limit_spin.setVisible(show_limit)
        self.window_label.setVisible(show_avg)
        self.window_spin.setVisible(show_avg)

    def _on_filter_changed(self):
        """滤波参数变更"""
        mode = self.filter_combo.currentData()
        self._update_filter_visibility()
        self.filter_changed.emit(
            mode,
            self.limit_spin.value(),
            self.window_spin.value()
        )

    def get_filter_config(self) -> dict:
        """获取当前滤波配置"""
        return {
            "mode": self.filter_combo.currentData(),
            "limit_threshold": self.limit_spin.value(),
            "average_window": self.window_spin.value(),
        }

    def set_filter_config(self, config: dict):
        """设置滤波配置（从config.json加载）"""
        mode = config.get("mode", 'none')
        idx = self.filter_combo.findData(mode)
        if idx >= 0:
            self.filter_combo.setCurrentIndex(idx)
        self.limit_spin.setValue(config.get("limit_threshold", 10.0))
        self.window_spin.setValue(config.get("average_window", 5))
        self._update_filter_visibility()
