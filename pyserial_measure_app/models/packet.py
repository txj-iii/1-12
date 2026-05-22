"""
协议解析器 - 解析10字节单通道和30字节6通道协议
"""
import struct
from typing import Optional

from config import (
    FRAME_HEADER, FRAME_FOOTER,
    PACKET_SIZE_1CH, PACKET_SIZE_6CH,
    VALUES_OFFSET_1CH, VALUES_OFFSET_6CH,
    VALUES_COUNT_1CH, VALUES_COUNT_6CH,
    COUNTER_OFFSET_1CH, COUNTER_OFFSET_6CH,
    VALUE_SIZE,
)


class ParsedPacket:
    """解析后的数据包"""
    __slots__ = ('values', 'frame_counter', 'is_valid', 'packet_size')

    def __init__(self, values: list[float], frame_counter: int,
                 is_valid: bool = True, packet_size: int = 0):
        self.values = values
        self.frame_counter = frame_counter
        self.is_valid = is_valid
        self.packet_size = packet_size

    def __repr__(self):
        return (f"ParsedPacket(values={self.values}, "
                f"counter={self.frame_counter}, valid={self.is_valid})")


class PacketParser:
    """
    串口数据包解析器。
    支持10字节单通道和30字节6通道两种协议格式。
    """

    @staticmethod
    def parse_packet(data: bytes) -> Optional[ParsedPacket]:
        """解析完整的数据包"""
        if len(data) < len(FRAME_HEADER) + len(FRAME_FOOTER):
            return None

        # 校验帧头
        if data[:len(FRAME_HEADER)] != FRAME_HEADER:
            return None

        # 判断包类型 (30字节6通道 or 10字节单通道)
        if len(data) == PACKET_SIZE_6CH:
            return PacketParser._parse_6ch(data)
        elif len(data) == PACKET_SIZE_1CH:
            return PacketParser._parse_1ch(data)
        else:
            return None

    @staticmethod
    def _parse_1ch(data: bytes) -> Optional[ParsedPacket]:
        """解析10字节单通道数据包"""
        if len(data) != PACKET_SIZE_1CH:
            return None

        # 校验帧尾
        if data[PACKET_SIZE_1CH - 2:] != FRAME_FOOTER:
            return None

        # 提取电阻值 (float32 LE)
        value = struct.unpack('<f', data[VALUES_OFFSET_1CH:VALUES_OFFSET_1CH + VALUE_SIZE])[0]

        # 提取帧计数 (uint16 LE)
        counter = struct.unpack('<H', data[COUNTER_OFFSET_1CH:COUNTER_OFFSET_1CH + 2])[0]

        return ParsedPacket(
            values=[value],
            frame_counter=counter,
            is_valid=True,
            packet_size=PACKET_SIZE_1CH
        )

    @staticmethod
    def _parse_6ch(data: bytes) -> Optional[ParsedPacket]:
        """解析30字节6通道数据包"""
        if len(data) != PACKET_SIZE_6CH:
            return None

        # 校验帧尾
        if data[PACKET_SIZE_6CH - 2:] != FRAME_FOOTER:
            return None

        # 提取6通道电阻值 (6 x float32 LE)
        values = []
        for i in range(VALUES_COUNT_6CH):
            offset = VALUES_OFFSET_6CH + i * VALUE_SIZE
            val = struct.unpack('<f', data[offset:offset + VALUE_SIZE])[0]
            values.append(val)

        # 提取帧计数 (uint16 LE)
        counter = struct.unpack('<H', data[COUNTER_OFFSET_6CH:COUNTER_OFFSET_6CH + 2])[0]

        return ParsedPacket(
            values=values,
            frame_counter=counter,
            is_valid=True,
            packet_size=PACKET_SIZE_6CH
        )

    @staticmethod
    def find_packet(buffer: bytearray) -> Optional[tuple[ParsedPacket, int]]:
        """
        从字节流缓冲区中搜索完整数据包。

        返回: (ParsedPacket, bytes_consumed) 或 None
        bytes_consumed: 已消耗的字节数（包括跳过的无效字节和完整包）
        """
        if len(buffer) < 4:  # 最少需要 帧头2 + 帧尾2
            return None

        # 扫描帧头
        for i in range(len(buffer) - 3):
            if buffer[i] == FRAME_HEADER[0] and buffer[i + 1] == FRAME_HEADER[1]:
                # 找到候选帧头，尝试匹配6通道或单通道
                remaining = len(buffer) - i

                # 尝试30字节6通道
                if remaining >= PACKET_SIZE_6CH:
                    candidate = bytes(buffer[i:i + PACKET_SIZE_6CH])
                    packet = PacketParser.parse_packet(candidate)
                    if packet and packet.is_valid:
                        consumed = i + PACKET_SIZE_6CH
                        return (packet, consumed)

                # 尝试10字节单通道
                if remaining >= PACKET_SIZE_1CH:
                    candidate = bytes(buffer[i:i + PACKET_SIZE_1CH])
                    packet = PacketParser.parse_packet(candidate)
                    if packet and packet.is_valid:
                        consumed = i + PACKET_SIZE_1CH
                        return (packet, consumed)

                # 帧头匹配但帧尾校验失败，继续扫描
                # 跳过当前帧头位置继续搜索（不直接return）

        # 没有找到有效包，但缓冲区可能包含部分数据
        # 如果缓冲区超过最大包大小，丢弃前面的字节防内存泄漏
        max_packet = max(PACKET_SIZE_6CH, PACKET_SIZE_1CH)
        if len(buffer) > max_packet * 2:
            # 丢弃前一半数据重新扫描
            discard = len(buffer) - max_packet
            return None, discard

        return None

    @staticmethod
    def find_packet_v2(buffer: bytearray) -> Optional[tuple[Optional[ParsedPacket], int]]:
        """
        改进版：始终返回 (packet_or_None, bytes_to_discard)
        保证每次调用都有进展，不会无限循环。
        """
        if len(buffer) < 4:
            return (None, 0)

        for i in range(len(buffer) - 1):
            if buffer[i] != FRAME_HEADER[0] or buffer[i + 1] != FRAME_HEADER[1]:
                continue

            remaining = len(buffer) - i

            # 尝试6通道
            if remaining >= PACKET_SIZE_6CH:
                p = PacketParser.parse_packet(bytes(buffer[i:i + PACKET_SIZE_6CH]))
                if p and p.is_valid:
                    return (p, i + PACKET_SIZE_6CH)

            # 尝试单通道
            if remaining >= PACKET_SIZE_1CH:
                p = PacketParser.parse_packet(bytes(buffer[i:i + PACKET_SIZE_1CH]))
                if p and p.is_valid:
                    return (p, i + PACKET_SIZE_1CH)

            # 剩余数据不够完成任何包，等待更多数据
            needed = max(PACKET_SIZE_6CH, PACKET_SIZE_1CH)
            if remaining < needed:
                # 丢弃头部无效字节到当前帧头位置
                return (None, i)

        # 整个缓冲区都没有帧头
        return (None, max(0, len(buffer) - max(PACKET_SIZE_6CH, PACKET_SIZE_1CH)))
