"""
Y轴范围设置对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QDoubleSpinBox,
    QCheckBox, QLabel, QDialogButtonBox
)


class RangeDialog(QDialog):
    """Y轴范围设置对话框"""

    def __init__(self, channel_id: int,
                 y_min: float = 0.0, y_max: float = 10.0,
                 auto_range: bool = True, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"CH{channel_id + 1} Y轴范围设置")
        self.setMinimumWidth(280)

        layout = QVBoxLayout(self)

        # 自动范围
        self.auto_check = QCheckBox("自动范围")
        self.auto_check.setChecked(auto_range)
        layout.addWidget(self.auto_check)

        # Y轴最小值
        min_layout = QHBoxLayout()
        min_layout.addWidget(QLabel("最小值 (kΩ):"))
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-100000, 100000)
        self.min_spin.setDecimals(3)
        self.min_spin.setValue(y_min)
        self.min_spin.setEnabled(not auto_range)
        min_layout.addWidget(self.min_spin)
        layout.addLayout(min_layout)

        # Y轴最大值
        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("最大值 (kΩ):"))
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-100000, 100000)
        self.max_spin.setDecimals(3)
        self.max_spin.setValue(y_max)
        self.max_spin.setEnabled(not auto_range)
        max_layout.addWidget(self.max_spin)
        layout.addLayout(max_layout)

        # 自动范围时禁用spinbox
        self.auto_check.toggled.connect(self.min_spin.setDisabled)
        self.auto_check.toggled.connect(self.max_spin.setDisabled)

        # 应用所有通道
        self.apply_all_check = QCheckBox("应用到所有通道")
        layout.addWidget(self.apply_all_check)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def y_min(self) -> float:
        return self.min_spin.value()

    @property
    def y_max(self) -> float:
        return self.max_spin.value()

    @property
    def auto_range(self) -> bool:
        return self.auto_check.isChecked()

    @property
    def apply_all(self) -> bool:
        return self.apply_all_check.isChecked()
