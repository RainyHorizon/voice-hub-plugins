param(
    [ValidateRange(1, 65535)][int]$Port = 8791,
    [string]$AudioCppUrl = "http://127.0.0.1:8080",
    [switch]$Register,
    [string]$VoiceHubRoot = (Join-Path $PSScriptRoot "../../..")
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:AUDIOCPP_URL = $AudioCppUrl
$python = Join-Path $PSScriptRoot ".venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "创建插件环境失败" }
}
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "安装插件依赖失败" }
& $python -c 'from server import UPSTREAM; print("audio.cpp: " + UPSTREAM)'
if ($LASTEXITCODE -ne 0) { throw "audio.cpp 地址无效" }
if ($Register) {
    $directory = Join-Path $VoiceHubRoot "data/plugins/audio-cpp"
    $target = Join-Path $directory "voice-hub.plugin.json"
    if (Test-Path -LiteralPath $target) { throw "插件清单已存在，请保留现有配置；启动时移除 -Register" }
    $manifest = Get-Content -LiteralPath "voice-hub.plugin.json" -Raw | ConvertFrom-Json
    $manifest.endpoint = "http://127.0.0.1:$Port"
    $manifest.workbench_url = $AudioCppUrl.TrimEnd('/')
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $json = $manifest | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText($target, $json, [Text.UTF8Encoding]::new($false))
    Write-Host "清单已注册。在 Voice Hub 的插件页启用 audio.cpp。"
}
& $python -m uvicorn server:app --host 127.0.0.1 --port $Port
if ($LASTEXITCODE -ne 0) { throw "插件服务退出，请检查端口是否占用" }
