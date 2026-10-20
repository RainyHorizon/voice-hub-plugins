# audio.cpp 本地音频

此插件调用用户已经安装的 audio.cpp，不携带 audio.cpp 二进制、模型或权重。它通过独立适配器连接 TTS API，并在 Voice Hub 插件页面内嵌 audio.cpp 原生工作台，用于 ASR、音乐/视频生成、语音转换、增强/降噪、分离、音频分析与音色设计。

使用前需要编译支持 WebUI 的 `audiocpp_server`。安装后在插件设置中提供 audio.cpp 安装目录，启用时 Voice Hub 为适配器准备独立 Python 环境，并在需要时启动本机服务。首次安装 Python 依赖需要联网；模型由用户在 audio.cpp 中自行管理。

插件详情、平台边界、配置和故障排查见当前版本目录中的 README。
