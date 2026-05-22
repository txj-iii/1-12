"""
串口配置对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QDialogButtonBox
)

from config import BAUDRATES


class SerialConfigDialog(QDialog):
    """串口参数设置对话框"""

    def __init__(self, current_port="COM3", current_baud=115200, parent=None):
        super().__init__(parent)
        self.setWindowTitle("串口配置")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        # COM口
        com_layout = QHBoxLayout()
        com_layout.addWidget(QLabel("COM口:"))
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self._populate_ports()
        self.port_combo.setCurrentText(current_port)
        com_layout.addWidget(self.port_combo)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._populate_ports)
        com_layout.addWidget(refresh_btn)
        layout.addLayout(com_layout)

        # 波特率
        baud_layout = QHBoxLayout()
        baud_layout.addWidget(QLabel("波特率:"))
        self.baud_combo = QComboBox()
        for b in BAUDRATES:
            self.baud_combo.addItem(str(b), b)
        idx = self.baud_combo.findData(current_baud)
        if idx >= 0:
            self.baud_combo.setCurrentIndex(idx)
        baud_layout.addWidget(self.baud_combo)
        layout.addLayout(baud_layout)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_ports(self):
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            current = self.port_combo.currentText()
            self.port_combo.clear()
            for p in ports:
                self.port_combo.addItem(p.device)
            if current:
                idx = self.port_combo.findText(current)
                if idx >= 0:
                    self.port_combo.setCurrentIndex(idx)
        except Exception:
            pass

    @property
    def port(self) -> str:
        return self.port_combo.currentText().strip()

    @property
    def baudrate(self) -> int:
        return self.baud_combo.currentData()
