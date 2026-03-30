# CleanMyCodeMac 打包说明

该项目可在 macOS 上通过 `PyInstaller` 打包为 `.app`，再通过 `hdiutil` 打包为 `.dmg`。

## 前置条件

- macOS
- 可用的 Python 3 环境
- 已创建虚拟环境，或通过环境变量覆盖 `PYTHON_BIN` / `PIP_BIN`

## 一键构建

在项目根目录执行：

```bash
chmod +x build_dmg.sh
./build_dmg.sh
```

默认会按当前机器架构生成一套产物，例如：

- `dist/x86_64/CleanMyCodeMac.app`
- `dist/CleanMyCodeMac-x86_64.dmg`

也可以显式指定架构：

```bash
./build_dmg.sh x86_64
./build_dmg.sh arm64
./build_dmg.sh all
```

生成双架构产物时会输出：

- `dist/x86_64/CleanMyCodeMac.app`
- `dist/CleanMyCodeMac-x86_64.dmg`
- `dist/arm64/CleanMyCodeMac.app`
- `dist/CleanMyCodeMac-arm64.dmg`

## 应用图标

如果你准备了 `resources/app_icon.png`，可以先生成 `.icns`：

```bash
chmod +x build_icon.sh
./build_icon.sh
```

生成后，`CleanMyCodeMac.spec` 会自动使用 `resources/app.icns`。

## 可选环境变量

如果你的 Python 或 pip 不在默认虚拟环境里，可以这样执行：

```bash
PYTHON_BIN=/path/to/python3 PIP_BIN=/path/to/pip3 ./build_dmg.sh
```

## 说明

- 构建脚本会在检测到缺少 `PyInstaller` 时自动安装 `requirements-build.txt` 中的依赖。
- `dmg` 内会包含 `CleanMyCodeMac.app` 和指向 `/Applications` 的快捷方式，便于用户拖拽安装。
- 生成 `arm64` / `x86_64` 时，当前 Python 与 PyInstaller 环境需要支持目标架构，否则 PyInstaller 会报错。

## 签名与公证

如果你有 Apple Developer 证书，可以在打包完成后执行：

```bash
DEVELOPER_ID_APP="Developer ID Application: Your Name (TEAMID)" \
APPLE_ID="your-apple-id@example.com" \
TEAM_ID="TEAMID" \
APP_PASSWORD="xxxx-xxxx-xxxx-xxxx" \
./sign_and_notarize.sh
```

如果只提供 `DEVELOPER_ID_APP`，脚本会完成签名并跳过 notarization。

## GitHub Release 自动发布

这个仓库可以通过 GitHub Actions 自动把 DMG 发布到 Release。

- 推送 tag，例如 `v1.0.0`
- `release.yml` 会分别构建 `arm64` 和 `x86_64` 的 DMG
- 如果配置了签名相关 secrets，就会自动签名，并在配置完整时继续做 notarization
- 最终生成的 DMG 会自动上传到对应的 GitHub Release

建议在 GitHub 仓库里配置这些 secrets：

- `DEVELOPER_ID_APP`
- `APPLE_CERTIFICATE_P12`（base64 编码后的 `.p12` 证书）
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_ID`
- `TEAM_ID`
- `APP_PASSWORD`

如果这些 secrets 没有配置，workflow 仍然会发布未签名的 DMG。
