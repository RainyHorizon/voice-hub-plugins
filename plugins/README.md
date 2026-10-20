# 官方插件

每个插件使用稳定 ID 作为目录名，并在各自目录按语义化版本保存不可变源码。

```text
plugins/<plugin-id>/
├─ README.md
└─ versions/
   └─ <major.minor.patch>/
      └─ voice-hub.plugin.json
```

发布 ZIP 解压后应包含单一 `voice-hub.plugin.json`，以及运行该插件所需的全部小型文件。大模型和可单独下载的运行时不放入插件包。
