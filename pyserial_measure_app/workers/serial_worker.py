"""
串口工作线程 - 后台读取串口数据并解析
"""
from typing import Optional
import time

import serial
from PyQt5.QtCore import QThread, pyqtSignal

from models.packet import PacketParser
from config import CHANNEL_COUNT, PACKET_SIZE_1CH


class SerialWorker(QThread):
    """串口读取线程"""

    packet_received = pyqtSignal(list, int)  # ([ch1..ch6], frame_counter)
    connection_status = pyqtSignal(bool, str)  # (connected, message)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._port = "COM3"
        self._baudrate = 115200
        self._channel_count = CHANNEL_COUNT
        self._serial: Optional[serial.Serial] = None
        self._buffer = bytearray()
        self._packet_count = 0
        self._last_packet_time = 0.0

    def configure(self, port: str, baudrate: int, channel_count: int = CHANNEL_COUNT):
        """配置串口参数（启动前调用）"""
        self._port = port
        self._baudrate = baudrate
        self._channel_count = channel_count

    @property
    def packet_count(self) -> int:
        return self._packet_count

    def run(self):
        """QThread 运行入口"""
        self._buffer.clear()
        self._packet_count = 0
        self._last_packet_time = 0.0

        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1
            )
            self.connection_status.emit(
                True, f"已连接到 {self._port} @ {self._baudrate} bps"
            )
        except Exception as e:
            self.error_occurred.emit(f"串口连接失败: {e}")
            self.connection_status.emit(False, f"连接失败: {e}")
            return

        self._last_packet_time = time.time()

        while not self.isInterruptionRequested():
            try:
                if self._serial.is_open and self._serial.in_waiting > 0:
                    chunk = self._serial.read(self._serial.in_waiting)
                    self._buffer.extend(chunk)
                    self._process_buffer()
                else:
                    QThread.msleep(2)
            except serial.SerialException as e:
                self.error_occurred.emit(f"串口读取错误: {e}")
                break
            except Exception as e:
                self.error_occurred.emit(f"解析错误: {e}")
                # 不中断，继续下一轮读取

        # 清理
        self._serial_close()

    def _serial_close(self):
        """安全关闭串口"""
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self.connection_status.emit(False, "已断开")

    def _process_buffer(self):
        """处理缓冲区中的原始数据，提取并分发数据包"""
        MAX_BUFFER = 4096
        if len(self._buffer) > MAX_BUFFER:
            self._buffer = self._buffer[-MAX_BUFFER:]

        while True:
            result = PacketParser.find_packet_v2(self._buffer)
            if result is None:
                break

            packet, consumed = result
            if packet and packet.is_valid:
                self._packet_count += 1
                self._last_packet_time = time.time()

                values = list(packet.values)
                while len(values) < self._channel_count:
                    values.append(0.0)
                values = values[:self._channel_count]

                self.packet_received.emit(values, packet.frame_counter)

            if consumed > 0:
                self._buffer = self._buffer[consumed:]
            else:
                break
