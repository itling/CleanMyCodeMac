# CleanMyCodeMac 打包说明

该项目通过 Swift Package Manager 构建原生 macOS `.app`，再通过 `hdiutil` 打包为 `.dmg`。

## 前置条件

- macOS 13.0+
- Xcode 16.4+ 或兼容的 Swift 6.1 工具链
- macOS 自带的 `hdiutil`、`codesign`、`xcrun`

## 一键构建

在项目根目录执行：

```bash
chmod +x build_dmg.sh
./build_dmg.sh
```

默认会按当前机器架构生成一套产物，例如：

- `dist/arm64/CleanMyCodeMac.app`
- `dist/CleanMyCodeMac-arm64.dmg`

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

如果你希望界面和 app bundle 元数据展示指定版本号，可以通过环境变量传入：

```bash
APP_VERSION=1.2.3 ./build_dmg.sh
```

如果没有显式传 `APP_VERSION`，构建脚本也会回退读取项目根目录下的 `.env`：

```bash
APP_VERSION=1.2.3
```

## 应用图标

如果你更新了 `resources/app_icon.png`，可以先重新生成 `.icns`：

```bash
chmod +x build_icon.sh
./build_icon.sh
```

生成后会写入 `resources/app.icns`。Release workflow 会优先使用仓库中已提交的 `app.icns`，缺失时才回退到 `./build_icon.sh`。

## 说明

- 构建脚本会通过 `swift build --configuration release` 生成 Swift 可执行文件。
- `resources/ui/index.html` 会被复制进 app bundle，发布产物不依赖仓库相对路径。
- `dmg` 内会包含 `CleanMyCodeMac.app` 和指向 `/Applications` 的快捷方式，便于用户拖拽安装。
- 生成 `arm64` / `x86_64` 时，本机 Swift 工具链需要支持对应架构。

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

本地开发时，`sign_and_notarize.sh` 也会回退读取项目根目录 `.env` 中的这些变量：

- `DEVELOPER_ID_APP`
- `APPLE_ID`
- `TEAM_ID`
- `APP_PASSWORD`

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
