# audio.cpp · Voice Hub 插件

在 Voice Hub 中使用本机 audio.cpp。安装并启用后，**插件页面 → audio.cpp 本地音频**内嵌 audio.cpp 原生界面，完整保留以下八类入口及其模型专用参数、文件上传、结果预览和下载：

| 能力 | 使用位置 |
| --- | --- |
| 文本转语音 | audio.cpp 插件页面；已注册的离线 TTS 也可在 Voice Hub 合成页、网关、CLI、MCP 使用 |
| ASR / 转录 | audio.cpp 插件页面 |
| 音乐 / 视频生成 | audio.cpp 插件页面 |
| 语音转换 | audio.cpp 插件页面 |
| 增强 / 降噪 | audio.cpp 插件页面 |
| 音源分离 | audio.cpp 插件页面 |
| 音频分析 | audio.cpp 插件页面 |
| 音色设计 | audio.cpp 插件页面 |

模型下载、加载、卸载及硬件后端继续由 audio.cpp 管理。类别存在不代表每个模型已下载或在当前设备可运行；插件不会自动下载模型。除 TTS 外，其他能力通过原生工作台调用 audio.cpp 自身 API，暂未接入 Voice Hub 的 `/v1`、CLI、MCP 或任务历史。

插件入口由已安装清单动态生成；未安装、停用或卸载后不显示，也不会加载 audio.cpp 界面。Voice Hub 只保留通用插件导航和延迟加载的页面容器，不内置 audio.cpp 的模型、原生 WebUI 或推理依赖。高级参数在此独立页面中调整，齿轮弹窗用于连接配置。

## 安装和第一次使用

需要已编译、支持原生 WebUI 的 `audiocpp_server` 和当前源码版 Voice Hub。自动管理需要源码版使用的 Python 支持创建 venv；首次安装适配依赖需要联网。插件不下载或编译 audio.cpp，也不下载模型。

1. 在 Voice Hub **插件 → 插件市场**安装 **audio.cpp 本地音频**。
2. 打开插件齿轮：默认自动寻找 Voice Hub 同级的 `audio.cpp` 文件夹；其他位置填写 **audio.cpp 安装目录**。保留“自动启动服务”开启并保存。
3. 点击**启用**。插件自动准备独立环境、启动适配服务，并在 audio.cpp 未运行时启动原生服务，无需每次运行 `start.ps1`。首次准备可能需要几分钟；后续复用环境。

默认适配服务地址为 `http://127.0.0.1:8791`，原生工作台为 `http://127.0.0.1:8080`，两个服务须使用不同端口。“检查连接”只检查已经运行的服务；首次使用先保存配置、启用，再检查。更改安装目录、后端或地址前，先停用插件。

支持寻找 `build/windows-cuda-release/bin`、`build/windows-cpu-release/bin`、`build/bin/Release`、`build/bin`、`bin` 或安装目录下的 `audiocpp_server`。自动后端根据选中构建的 CUDA 标志/运行库判断，否则使用 CPU；可在齿轮中指定 `cpu`、`cuda`、`vulkan`、`metal`，以当前 audio.cpp 构建支持为准。

展开侧边栏 **插件页面 → audio.cpp 本地音频**（也可点击插件卡片的“打开插件页面”），即可使用原生界面的八类功能。在模型库安装或选择已安装模型，再用短文本或测试音频实际执行一次。

## 启停与手动管理

Voice Hub 重启时恢复已启用插件；停用、卸载或正常退出 Voice Hub 时，只停止本次由插件启动的服务。已有的手动服务会复用，不会被插件关闭。后端异常退出时，适配进程通过父进程管道关闭信号清理自己启动的 audio.cpp。若自动恢复失败，插件卡片显示错误，启动日志位于 `data/logs/plugin-audio-cpp.log`。启动失败不覆盖原来的启用状态、配置或目录缓存。

未安装或未启用时不启动进程；卸载保留运行环境和服务文件，便于恢复，模型文件不受影响。首次自动启动原生服务时，会把安装目录下已有的 `models` 设为该实例的模型库；复用现有原生服务时不修改模型库设置。

如需自行管理服务，先停用插件，在齿轮关闭**自动启动服务**，再自行运行 audio.cpp 和下面的适配脚本：

```powershell
.\start.ps1
```

手动脚本支持 `-AudioCppUrl http://127.0.0.1:新端口` 与 `-Port 新端口`，对应齿轮中的原生工作台地址、适配服务地址。首次手动注册可加 `-Register`，它不覆盖已有清单。手动模式需要自己保持两个服务运行。

macOS / Linux 可在本目录创建独立虚拟环境、安装 `requirements.txt`，复制清单到该 Voice Hub 实例的 `data/plugins/audio-cpp/`，再运行：

```bash
AUDIOCPP_URL=http://127.0.0.1:8080 .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8791
```

## 接入原有语音合成页

audio.cpp `/v1/models` 中配置为 `task=tts` 或 `clon`、`mode=offline` 的模型可进入 Voice Hub 合成页。运行时新增模型后，在插件页点击**同步模型与音色**。

- `服务默认音色`会省略上游 `voice`，由模型的默认预设处理。需要参考音频的模型必须先在 audio.cpp 配置默认预设，或选取兼容的音色库条目。
- 其他音色来自 `/v1/audio/voices?model=...`。audio.cpp 可能共享参考音色库；某条参考音色不一定适用于每个模型，需用短句验证。GGUF 内置但上游未枚举的说话人仍可在原生工作台选择。
- 公开模型 ID 为 `plugin-audio-cpp/<模型ID>`，音色 ID 为 `plugin-audio-cpp:<模型ID>:<音色ID>`。不满足核心 ID 格式的上游名字会映射为稳定 ID，显示名称保留。
- 适配器只接受有效的 16-bit PCM WAV，输出最多 50 MB，合成上游超时 150 秒。不强行给模型传入不支持的语速参数；非 1 倍语速通过 FFmpeg 的 `atempo` 调整，需已安装 FFmpeg 并加入 PATH。
- 尚未加载 TTS 时仍可启用插件页面；合成页没有 audio.cpp 模型属于正常状态。原生流式模式、克隆或设计的专用控制保留在原生工作台。

## 连接和数据边界

这是本机插件。浏览器须能访问 `workbench_url`，Voice Hub 后端须能访问 `endpoint`，适配服务须能访问 `AUDIOCPP_URL`。Docker、远程浏览器或 HTTPS 站点的环回地址不一定指同一机器；不要用公网监听绕过这一限制。

工作台使用独立来源的沙箱 iframe；不在 Voice Hub 页面直接注入插件脚本。只启用自己信任的本地服务。浏览器可能要求授予本地网络、麦克风或剪贴板权限；嵌入页不支持某项浏览器权限时，可用**新窗口打开**。离开工作台会移除嵌入页以停止页面播放；已经提交的 audio.cpp 推理不保证取消。

原生工作台的数据、下载与历史由 audio.cpp 处理；Voice Hub 原有合成页产生的音频仍进入 Voice Hub 历史。手动结束服务后，可停用并重新启用插件恢复自动管理。不要在推理或下载过程中停用插件：插件启动的 audio.cpp 会随之结束。自动管理当前针对包含本目录源码的本机运行方式；便携包、容器和其他操作系统构建未验证。
