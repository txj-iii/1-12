
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电阻测量上位机 - 6通道实时波形显示
基于PyQt5 + pyqtgraph + pyserial

使用:
    python main.py

依赖安装:
    pip install pyqtgraph pyserial PyQt5 numpy
"""
import sys
import os

# 确保当前目录在sys.path中，使内部导入正常工作
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from ui.main_window import MainWindow


def main():
    # 启用高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("电阻测量上位机")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
