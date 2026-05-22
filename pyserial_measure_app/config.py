"""
配置模块 - 所有常量和默认配置集中管理
"""
import os

# ============ 协议常量 ============
# 帧头/帧尾
FRAME_HEADER = bytes([0x03, 0xFC])
FRAME_FOOTER = bytes([0xFC, 0x03])

# 单通道协议 (10字节)
PACKET_SIZE_1CH = 10
VALUES_OFFSET_1CH = 2
VALUES_COUNT_1CH = 1
COUNTER_OFFSET_1CH = 6
VALUE_SIZE = 4  # float32

# 6通道协议 (30字节)
PACKET_SIZE_6CH = 30
VALUES_OFFSET_6CH = 2
VALUES_COUNT_6CH = 6
COUNTER_OFFSET_6CH = 26

# ============ 串口默认配置 ============
DEFAULT_PORT = "COM3"
DEFAULT_BAUDRATE = 115200
BAUDRATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800]

# ============ 通道配置 ============
CHANNEL_COUNT = 6
MIN_CHANNELS = 1
MAX_CHANNELS = 12

# ============ 显示配置 ============
DISPLAY_WINDOW_SECONDS = 30  # X轴时间窗口
BUFFER_MAXLEN = 10000        # 环形缓冲区容量
REFRESH_INTERVAL_MS = 50     # 刷新间隔 (20fps)
PLOT_LINE_WIDTH = 1.5

# ============ 通道颜色 (12色) ============
CHANNEL_COLORS = [
    (255, 0, 0),      # 红
    (0, 170, 0),      # 绿
    (0, 0, 255),      # 蓝
    (255, 170, 0),    # 橙
    (170, 0, 255),    # 紫
    (0, 200, 200),    # 青
    (255, 100, 100),  # 粉红
    (100, 100, 100),  # 灰
    (150, 80, 0),     # 棕
    (0, 100, 0),      # 深绿
    (100, 150, 255),  # 浅蓝
    (200, 150, 100),  # 米色
]

# ============ 窗口标题 ============
APP_TITLE = "电阻测量上位机 - 6通道"

# ============ CSV导出 ============
# 统一保存到项目根目录的 exports/
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")
CSV_HEADER = "CH1,CH2,CH3,CH4,CH5,CH6,Frame Counter,Timestamp"

# ============ 滤波配置 ============
FILTER_MODE_NONE = 'none'
FILTER_MODE_LIMIT = 'limit'
FILTER_MODE_AVERAGE = 'average'
FILTER_DEFAULT_MODE = FILTER_MODE_NONE
FILTER_DEFAULT_LIMIT = 10.0      # 限幅百分比
FILTER_DEFAULT_WINDOW = 5        # 滑动窗口大小

# ============ 配置文件路径 ============
CONFIG_FILE = "config.json"
