"""
主窗口 - 组装所有UI组件，协调数据流
"""
import json
import os
import time

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStatusBar,
    QMessageBox
)
from PyQt5.QtCore import QTimer

from config import (
    APP_TITLE, CHANNEL_COUNT, DISPLAY_WINDOW_SECONDS,
    REFRESH_INTERVAL_MS, BUFFER_MAXLEN, CONFIG_FILE,
    DEFAULT_PORT, DEFAULT_BAUDRATE,
    FILTER_DEFAULT_MODE, FILTER_DEFAULT_LIMIT, FILTER_DEFAULT_WINDOW,
)
from models.channel_data import ChannelData
from models.filter import DataFilter
from workers.serial_worker import SerialWorker
from ui.control_panel import ControlPanel
from ui.plot_grid import PlotGrid
from export.csv_exporter import CsvExporter


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(1200, 800)

        # 加载配置
        self.config = self._load_config()

        # 通道数据缓冲区
        self.channel_count = self.config.get("channel_count", CHANNEL_COUNT)
        self.channel_data: dict[int, ChannelData] = {}
        self._init_channel_data()

        # 串口工作线程
        self.serial_worker = SerialWorker()
        self.serial_worker.packet_received.connect(self._on_packet_received)
        self.serial_worker.connection_status.connect(self._on_connection_status)
        self.serial_worker.error_occurred.connect(self._on_error)
        self.serial_worker.finished.connect(self._on_thread_finished)

        # 数据滤波器
        self.data_filter = DataFilter()
        filter_cfg = self.config.get("filter", {})
        self.data_filter.configure(
            mode=filter_cfg.get("mode", FILTER_DEFAULT_MODE),
            limit_threshold=filter_cfg.get("limit_threshold", FILTER_DEFAULT_LIMIT),
            average_window=filter_cfg.get("average_window", FILTER_DEFAULT_WINDOW),
        )

        # 统计
        self._packet_count = 0
        self._start_time = 0.0

        # 初始化UI
        self._setup_ui()
        self._connect_signals()

        # 加载保存的滤波配置到UI控件
        filter_cfg = self.config.get("filter", {})
        if filter_cfg:
            self.control_panel.set_filter_config(filter_cfg)

        # 刷新定时器
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_displays)
        self.refresh_timer.start(REFRESH_INTERVAL_MS)

    def _setup_ui(self):
        """构建UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 控制栏
        self.control_panel = ControlPanel()
        layout.addWidget(self.control_panel)

        # 波形网格
        self.plot_grid = PlotGrid()
        layout.addWidget(self.plot_grid, 1)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _connect_signals(self):
        """连接信号"""
        self.control_panel.start_requested.connect(self._on_start_requested)
        self.control_panel.stop_requested.connect(self._on_stop_requested)
        self.control_panel.export_requested.connect(self._on_export_requested)
        self.control_panel.filter_changed.connect(self._on_filter_changed)

    def _init_channel_data(self):
        """初始化通道数据缓冲区"""
        self.channel_data.clear()
        for i in range(self.channel_count):
            self.channel_data[i] = ChannelData(i, maxlen=BUFFER_MAXLEN)

    def _on_start_requested(self, port: str, baudrate: int, channels: int):
        """用户点击启动"""
        if self.serial_worker.isRunning():
            return

        self.channel_count = channels
        self._init_channel_data()
        self.plot_grid.set_channel_count(channels)
        self.plot_grid.clear_all()

        self.serial_worker.configure(port, baudrate, channels)
        self.serial_worker.start()

    def _on_stop_requested(self):
        """用户点击停止"""
        if self.serial_worker.isRunning():
            self.serial_worker.requestInterruption()
            # 串口读取会因此停止
            self.serial_worker.wait(3000)
        self.control_panel.set_acquiring(False)
        self.status_bar.showMessage("已停止采集")

    def _on_thread_finished(self):
        """线程结束"""
        self.control_panel.set_acquiring(False)

    def _on_packet_received(self, values: list, frame_counter: int):
        """收到解析后的数据包"""
        now = time.time()

        if self._packet_count == 0:
            self._start_time = now
        self._packet_count += 1

        # 存入各通道（先滤波）
        for i, val in enumerate(values):
            if i in self.channel_data:
                filtered = self.data_filter.apply(i, val)
                self.channel_data[i].append(filtered, now, frame_counter)

    def _on_connection_status(self, connected: bool, message: str):
        """连接状态变化"""
        self.control_panel.set_acquiring(connected)
        self.status_bar.showMessage(message)
        if connected:
            self._packet_count = 0
            self._start_time = 0.0

    def _on_filter_changed(self, mode: str, limit_threshold: float, average_window: int):
        """滤波参数变更"""
        self.data_filter.configure(mode, limit_threshold, average_window)
        self.data_filter.reset()
        # 在状态栏显示当前滤波状态
        status_map = {'none': '无滤波', 'limit': f'限幅滤波 (阈值{limit_threshold}%)',
                      'average': f'滑动平均 (窗口{average_window})'}
        msg = status_map.get(mode, '无滤波')
        self.status_bar.showMessage(f"滤波: {msg}", 3000)

    def _on_error(self, message: str):
        """错误处理"""
        self.status_bar.showMessage(f"错误: {message}")
        if "连接失败" in message:
            QMessageBox.warning(self, "连接错误", message)

    def _refresh_displays(self):
        """定时刷新所有波形"""
        self.plot_grid.update_all(self.channel_data, DISPLAY_WINDOW_SECONDS)

        # 更新状态栏信息
        if self.serial_worker.isRunning():
            elapsed = time.time() - self._start_time if self._start_time else 0
            rate = self._packet_count / elapsed if elapsed > 0 else 0
            self.status_bar.showMessage(
                f"采集中 | 总包数: {self._packet_count} | "
                f"采样率: {rate:.1f} 包/秒"
            )

    def _on_export_requested(self):
        """导出CSV"""
        filepath = CsvExporter.export(self.channel_data)
        if filepath:
            self.status_bar.showMessage(f"已导出: {filepath}")
            QMessageBox.information(self, "导出成功", f"数据已保存到:\n{filepath}")
        else:
            self.status_bar.showMessage("导出失败: 无数据")
            QMessageBox.warning(self, "导出失败", "没有可导出的数据")

    def _load_config(self) -> dict:
        """加载配置文件"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"channel_count": CHANNEL_COUNT,
                "port": DEFAULT_PORT,
                "baudrate": DEFAULT_BAUDRATE}

    def _save_config(self):
        """保存配置到文件"""
        config = {
            "channel_count": self.channel_count,
            "port": self.control_panel.com_port_combo.currentText(),
            "baudrate": self.control_panel.baudrate_combo.currentData(),
            "filter": self.control_panel.get_filter_config(),
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def closeEvent(self, event):
        """窗口关闭事件"""
        self._save_config()
        self.refresh_timer.stop()
        if self.serial_worker.isRunning():
            self.serial_worker.requestInterruption()
            self.serial_worker.wait(3000)
        event.accept()
