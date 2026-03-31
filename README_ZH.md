# CleanMyCodeMac

专为程序员打造的 macOS 磁盘清理工具，深度清理开发环境产生的缓存与冗余文件，快速释放磁盘空间。

## 功能

- **系统缓存** — 清理 macOS 系统应用产生的临时缓存
- **应用缓存** — 清理 Chrome、VSCode、JetBrains、Slack、Telegram 等第三方 App 缓存
- **编程缓存** — 清理 Node.js、Python、Ruby、Rust、Go、Java、AI 模型工具等开发工具链产生的缓存
- **文本文件** — 扫描 PDF、Word、Excel、Markdown、iWork 等文档文件
- **媒体文件** — 扫描图片、音频、视频等媒体文件，包含 Downloads 中的媒体文件
- **日志文件** — 清理崩溃报告与运行日志
- **下载文件** — 分析下载文件夹中的文件，按类型分组展示
- **大文件扫描** — 搜索 500MB 以上的大文件，并提供快速分析
- **废纸篓** — 查看废纸篓占用并按需清空

## 特性

- 基于 Swift、AppKit、WKWebView 的原生 macOS 应用
- 数据和清理流程都在本机完成，不依赖云服务
- 分层分组展示扫描结果，支持按分类/应用逐级展开
- 安全标签提示（建议清理 / 谨慎清理）
- 非安全文件尽量移入废纸篓；安全项可直接释放空间
- 支持 Finder 快速定位文件
- 可选扫描范围，按需扫描

## 截图

![CleanMyCodeMac 主界面](/Users/killy/AweSun/cleanMyCodeMac/resources/screenshots/home-readme.png)

## 快速开始

### 环境要求

- macOS 13.0+
- Xcode 16.4+ 或兼容的 Swift 6.1 工具链

### 运行

```bash
swift run

# 或双击 run.command
```

### 打包为 .app / .dmg

```bash
./build_dmg.sh
# 产物：
# - dist/<arch>/CleanMyCodeMac.app
# - dist/CleanMyCodeMac-<arch>.dmg
```

详细打包说明见 [BUILD_ZH.md](BUILD_ZH.md)。

## 隐私与权限

- 所有扫描和清理逻辑都在你的 Mac 本地执行。
- 正常使用不依赖任何云服务。
- 部分扫描目标需要“完全磁盘访问权限”后才能完整显示。
- 清理操作会尽量将文件移入废纸篓，方便恢复。

## 项目结构

```text
Package.swift
source/
├── AppMain.swift           # AppKit 窗口 + WKWebView 启动入口
├── AppSupport.swift        # bridge 注入、磁盘/权限/语言辅助
├── NativeBridge.swift      # JS bridge 方法分发
└── NativeScanEngine.swift  # 原生扫描、勾选、清理、分析
resources/
├── ui/
│   └── index.html              # 当前单页前端 UI
├── screenshots/
│   └── home-readme.png
├── app_icon.png
└── app.icns
build_dmg.sh                    # 通过 SwiftPM 构建 .app + .dmg
build_icon.sh                   # 从 app_icon.png 生成 app.icns
sign_and_notarize.sh            # 签名 / 公证脚本
```

## 许可证

[MIT](LICENSE)

## 参与贡献

贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。
