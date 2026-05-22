@echo off
cd /d "c:\上位机\1-12通道上位机（新2026.4.13）\GPT-SoVITS-v2pro-20250604"
echo 正在启动 GPT-SoVITS TTS 服务器...
echo   使用模型: txjtxj（你训练的新模型）
echo   端口: 9880
echo.
runtime\python.exe api.py ^
    -g GPT_weights_v2/txjtxj-e6.ckpt ^
    -s SoVITS_weights_v2/txjtxj_e4_s400.pth ^
    -dr "Haogang.wav" ^
    -dt "Hello, my name is how gone is nice to meet you." ^
    -dl "zh" ^
    -p 9880 ^
    -a 0.0.0.0
pause
