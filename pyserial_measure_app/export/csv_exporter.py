"""
CSV导出模块
"""
import os
import csv
import time
from typing import Optional

from config import EXPORT_DIR, CSV_HEADER


class CsvExporter:
    """数据导出为CSV文件"""

    @staticmethod
    def export(channel_data: dict, filepath: Optional[str] = None) -> str:
        """
        导出所有通道数据到CSV文件。

        Args:
            channel_data: {channel_id: ChannelData}
            filepath: 输出路径，None则自动生成

        Returns:
            文件路径
        """
        if filepath is None:
            os.makedirs(EXPORT_DIR, exist_ok=True)
            timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
            filepath = os.path.join(EXPORT_DIR, f"{timestamp}.csv")

        # 找出最长通道的数据条数
        max_len = max((d.sample_count for d in channel_data.values()), default=0)
        if max_len == 0:
            return ""

        # 收集所有通道数据
        all_data = []
        for i in range(max_len):
            row = []
            for ch in sorted(channel_data.keys()):
                d = channel_data[ch]
                if i < len(d.values):
                    row.append(f"{d.values[i]:.3f}")
                else:
                    row.append("")
            # 帧计数和时间
            ch0 = channel_data[0]
            if i < len(ch0.frame_counters) and i < len(ch0.timestamps):
                row.append(str(ch0.frame_counters[i]))
                ts = time.strftime('%H:%M:%S', time.localtime(ch0.timestamps[i]))
                row.append(ts)
            all_data.append(row)

        # 写入CSV
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 表头
            channels = sorted(channel_data.keys())
            header = [f"CH{ch + 1}" for ch in channels] + ["Frame Counter", "Timestamp"]
            writer.writerow(header)
            writer.writerows(all_data)

        return filepath
