# Voice Hub Plugins

Voice Hub 的官方插件源。插件按独立目录和语义化版本维护；注册表只列出已经审核并发布的包。

## 目录

```text
registry.json                         # 插件源入口，客户端读取
plugins/<plugin-id>/README.md         # 插件长期说明
plugins/<plugin-id>/versions/<x.y.z>/ # 不可变版本源码与清单
scripts/package-plugin.py             # 生成发布 ZIP 与 SHA-256
```

插件包只包含代码、清单、文档和小型运行资源。不要提交模型、编译产物、密钥、个人路径、`.venv` 或运行数据。插件运行时需要的所有启动文件必须在 ZIP 内；Voice Hub 会安装到自己的 `data/plugins/<plugin-id>/`。

## 安装插件源

Voice Hub 已内置此源。也可以在 **插件 → 插件来源 → 添加插件源** 添加：

```text
https://raw.githubusercontent.com/RainyHorizon/voice-hub-plugins/main/registry.json
```

市场只展示注册表中的版本。安装时 Voice Hub 下载压缩包、核对 SHA-256、验证清单 ID/版本并安全解压；安装不会自动启用插件。只安装你信任的来源。

## 发布新版本

1. 在 `plugins/<plugin-id>/versions/<新版本>/` 放置完整插件包，并更新清单版本。
2. 运行 `python scripts/package-plugin.py <plugin-id> <版本>` 生成 ZIP 和摘要。
3. 在 `registry.json` 增加或更新该插件记录，填写下载 URL 和命令输出的 SHA-256。
4. 提交 Pull Request，附上测试结果、变更说明、权限/网络访问说明和依赖许可证。
5. 维护者检查协议兼容、路径/密钥安全、依赖与许可后合并，再按注册表里的 release tag 发布 ZIP。

旧版本目录和 Release 应保留，方便来源审计和回滚。已安装插件不会因刷新注册表而自动更新；更新需要用户在插件市场主动操作。

## 提交要求

- `voice-hub.plugin.json` 必须通过 Voice Hub 插件协议校验，ID 在所有版本中保持稳定。
- 提交者需拥有插件代码和其中资源的分发权；不得上传第三方模型文件、私密音频或未授权音色。
- 服务应默认仅监听环回地址，不得要求关闭 Voice Hub 的本地地址校验。
- 明确列出联网目标、数据用途、外部命令、运行平台、所需账号和费用边界。
- 新增插件目录时同步更新 `registry.json`；没有注册表条目的源码不会出现在市场。
