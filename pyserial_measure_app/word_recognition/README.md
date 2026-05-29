# word_recognition

本目录包含喉部石墨烯电阻信号的词语识别训练、预测和数据准备脚本。

当前词表为：

- `I`
- `buy`
- `apple`
- `nine`
- `pound`
- `one`

类别映射约定：

- `0 = rest`
- `1 = I`
- `2 = buy`
- `3 = apple`
- `4 = nine`
- `5 = pound`
- `6 = one`

## 目录说明

- [train_model.py](train_model.py)：训练 Random Forest 词语分类器
- [predict.py](predict.py)：对单个 CSV 做离线预测
- [features.py](features.py)：窗口特征提取
- [prepare_new_data.py](prepare_new_data.py)：新数据准备
- [compare_models.py](compare_models.py)：模型对比
- [data/labeled](data/labeled)：标注数据
- [models](models)：训练输出模型

## 训练流程

1. 读取 `data/labeled/R_*_C_*_EMG.csv`
2. 对连续信号分窗
3. 提取 MAV / ZC / SSC / WL 等特征
4. 对 `rest` 类做下采样平衡
5. 训练 Random Forest
6. 保存 `.pkl` 模型供在线识别复用

## 为什么选择 RF，而不是直接用 LibEMG

本项目借鉴了 LibEMG 的一些概念，但没有直接把整套框架接入在线识别流程，主要原因如下：

- 信号类型不同：LibEMG 面向 kHz 级肌电信号，本项目是约 10 Hz 的喉部电阻信号，很多高频滤波和频域处理并不适配。
- 数据规模更小：当前任务是小样本、多词分类，Random Forest 更容易快速迭代和稳定部署。
- 通道角色不同：当前识别以 `CH1` 为主导，`CH2`、`CH3` 为辅助；项目更关注针对这类信号做轻量特征和窗口策略，而不是直接套用通用肌电管线。
- 部署更简单：RF 训练和推理都可以直接复用单个 `.pkl` 文件，便于和现有 Flask 接口、上位机导出 CSV 流程衔接。

因此，本项目采用的是“借鉴 LibEMG 思路，保留轻量实现”的路线：

- 保留窗口化处理思路
- 保留简洁的手工特征
- 保留 LibEMG 风格的标注文件命名
- 不直接依赖整套 LibEMG 在线推理框架

## 相关入口

- 首页说明见 [../../README.md](../../README.md)
- 流水线细节见 [CLAUDE.md](CLAUDE.md)
