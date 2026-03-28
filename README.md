# CleanMyCodeMac

macOS 垃圾清理工具，扫描并清理系统中的无用文件，快速释放磁盘空间。

## 功能

- **系统缓存** — 清理 macOS 系统应用产生的临时缓存
- **应用缓存** — 清理 Chrome、VSCode、JetBrains 等第三方 App 缓存
- **日志文件** — 清理 7 天以上的崩溃报告与运行日志
- **下载文件** — 分析下载文件夹中的旧文件，按类型分组展示
- **大文件扫描** — 搜索 500MB 以上的大文件，支持深入分析（含 Docker 空间分析）
- **废纸篓** — 一键清空废纸篓

## 特性

- 本地原生窗口（pywebview + WKWebView），非浏览器打开
- 分层分组展示扫描结果，支持按分类/应用逐级展开
- 安全标签提示（建议清理 / 谨慎清理）
- 文件移入废纸篓，可恢复
- 支持 Finder 快速定位文件
- 可选扫描范围，按需扫描

## 截图

（待补充）

## 快速开始

### 环境要求

- macOS 12.0+
- Python 3.10+

### 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 运行

```bash
# 方式一：命令行启动
cd cleanmycodemac
../venv/bin/python3 main.py

# 方式二：双击 run.command
```

### 打包为 .app

```bash
pip install -r requirements-build.txt
python3 -m PyInstaller --noconfirm CleanMyCodeMac.spec
# 产物在 dist/CleanMyCodeMac.app
```

详细打包说明见 [BUILD.md](BUILD.md)。

## 项目结构

```
cleanmycodemac/
├── main.py                 # 入口
├── web_app.py              # HTTP 服务 + pywebview 窗口 + 前端页面
├── core/
│   ├── scanner.py          # 扫描调度器（多线程并行）
│   ├── analyzer.py         # 大文件深入分析（含 Docker）
│   ├── disk_info.py        # 磁盘用量
│   ├── permissions.py      # 完全磁盘访问权限检测
│   ├── app_detector.py     # 已安装应用检测
│   └── cleaners/           # 各类清理器
│       ├── base_cleaner.py
│       ├── system_cache.py
│       ├── app_cache.py
│       ├── logs_cleaner.py
│       ├── downloads.py
│       ├── large_files.py
│       └── trash.py
├── models/                 # 数据模型
│   ├── scan_item.py
│   ├── scan_result.py
│   └── clean_report.py
└── utils/
    ├── config.py           # 用户配置
    └── subprocess_utils.py # macOS 命令封装
```

## 配置

首次运行后会在 `~/.cleanmycodemac_config.json` 生成配置文件：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `large_file_threshold_mb` | 500 | 大文件阈值（MB） |
| `old_download_days` | 30 | 下载文件过期天数 |
| `old_log_days` | 7 | 日志过期天数 |

## 许可证

MIT
