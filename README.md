# 叶读 · Leaf Reader

一个独立实现的、以本地书架和基础阅读为中心的轻量阅读器。首版交付 **iOS 16+ / Miuix UI / GitHub Actions 生成未签名 IPA**，面向已有兼容 TrollStore 环境的设备。不依赖 App Store、TestFlight 或开发者签名证书。

> 当前交付的是源码与构建流水线，不是已经在 GitHub 构建成功的 IPA。共享 UI 已在 Linux/JVM 编译验证；Apple 编译、Swift 测试和巨魔安装须由 macOS CI/真机验证。详见 [验证记录](<VALIDATION.md>)。

## 首版功能

- 本地 TXT / 基础 EPUB 导入，支持多选及重复文件识别。
- Miuix 书架：搜索书名/作者、最近阅读、阅读进度、移除书籍确认。
- 连续滚动阅读、章节目录跳转。
- 字号 14–32、两档行距；跟随系统、明亮、深色、纸色主题。
- 保存当前段落和滚动位置，返回书架/进入后台时保存，滚动时节流写入。
- 文件复制/解析到应用私有书库，不修改用户选择的原文件。
- 基于原始字节 SHA-256 去重；重复导入保留原有位置并修复派生副本。
- 原创图标与 TXT/EPUB 示例。

### 本轮有意后置

Android 宿主/APK、WebDAV、朗读、在线书源、PDF、书签笔记、正文全文搜索、原书图片、脚注交互、完整 CSS、仿真翻页、备份导出。共享模块可供后续 Android 宿主使用，但本轮没有交付 Android 安装包。

**EPUB 是基础纯文本导入**：按 OPF spine 生成章节，保留可阅读文本；不是完整 EPUB 浏览器。复杂版式、图片、SVG、数学公式、DRM 与字体混淆暂不支持。章节标题可能与首段标题重复，以优先避免删除原文。

## 不用 Mac，如何拿到 IPA？

1. 在 GitHub 新建仓库。
2. 解压本源码包，把工程内容放到仓库根目录。务必保留隐藏的 [.github 工作流目录](<.github/workflows/ios-ipa.yml>)、[Gradle wrapper](<gradle/wrapper/gradle-wrapper.jar>)和 [iOS 工程规格](<iosApp/project.yml>)，不要只上传某个子目录。
3. 打开仓库 **Actions**，如出现启用提示，启用本仓库工作流。
4. 选择 **Build iOS IPA → Run workflow**。
5. 等待共享测试、Apple 构建和 Swift importer 测试通过。
6. 在该次运行底部下载 **LeafReader-iOS16-arm64-unsigned** artifact。
7. 解压 artifact ZIP，找到 `LeafReader-0.1.0-unsigned.ipa`，传到 iPhone 并交给 TrollStore 安装。

主分支 `main` / `master` 推送和 `v*` 标签也会触发工作流。其他分支可手动运行。首次构建需要下载 Gradle、Kotlin/Native、Miuix、Apple 与 Swift 包依赖，通常明显慢于后续缓存构建。

**不需要设置开发者证书、描述文件或 GitHub Secrets。**工作流只有仓库读取权限，IPA 来自 Release / iphoneos / arm64，而不是模拟器产物。

### 巨魔兼容

按 [TrollStore 官方说明](https://github.com/opa334/TrollStore)，相关范围包含 iOS 16.0–16.6.1、iOS 16.7 RC（20H18）和 iOS 17.0；并非全部 iOS 16.x。App 最低部署版本为 iOS 16.0，但安装器兼容性是另一项条件。该项目不为普通系统安装渠道提供有效开发者签名。

## Actions 做了什么？

工作流位于 [ios-ipa.yml](<.github/workflows/ios-ipa.yml>)：

1. Ubuntu：验证源码结构和 wrapper 校验值，运行 Python 打包测试，编译共享 UI 并执行 Kotlin 测试。
2. macOS 26 / Xcode 26.4：构建静态 iOS ARM64 Shared framework。
3. XcodeGen 根据 [project.yml](<iosApp/project.yml>)生成 Xcode 工程。
4. Xcode 以关闭开发者签名的方式构建设备 App。
5. [打包脚本](<scripts/package_ipa.py>)检查 arm64 / iPhoneOS / iOS16 部署目标，保留可执行权限并封装 `Payload/LeafReader.app`。
6. 运行独立的 Swift importer XCTest（hostless simulator target）。
7. 上传 IPA、SHA-256 校验文件和测试报告。

如果失败，打开红色步骤的完整日志；本次交付没有连接你的 GitHub，因此不声称远端构建已经通过。

## Mac 本地构建

需要与锁定 Kotlin/CMP 版本兼容的现代 Xcode、JDK 17、XcodeGen。本工程的 CI 选择 macOS 26 并固定 Xcode 26.4；依据 [KMP 兼容表](https://kotlinlang.org/docs/multiplatform/multiplatform-compatibility-guide.html)和 [GitHub macOS 26 镜像清单](https://github.com/actions/runner-images/blob/main/images/macos/macos-26-Readme.md)。最低运行系统 iOS16 和构建 SDK 版本是两个概念；不要仅根据 iOS16 推断旧 Xcode 足够。

```bash
brew install xcodegen
bash scripts/build-ios.sh
bash scripts/test-ios.sh
```

产物位于 `dist/LeafReader-0.1.0-unsigned.ipa`。iOS 共享框架为静态框架，只链接、不嵌入。详见 [iOS 宿主说明](<iosApp/README.md>)。

## 本地通用验证

```bash
python3 scripts/check_project.py
python3 -m unittest discover -s scripts/tests -v
bash -n scripts/build-ios.sh scripts/test-ios.sh
bash ./gradlew :shared:desktopTest -PenableApple=false
```

`desktop` target 用于共享代码编译与测试，没有提供桌面 App 窗口。Linux 不注册 Apple targets，避免把 JVM 验证误认为 Apple 构建证明。

## 技术栈与工程结构

- Kotlin **2.4.20**、Compose Multiplatform **1.12.0**、Miuix **0.9.4**。
- Coroutines / StateFlow、kotlinx.serialization、应用私有 JSON 存储。
- SwiftUI / UIKit 文件选择器，ZIPFoundation **0.9.19**、SwiftSoup **2.7.7**。
- Gradle wrapper **9.7.1**，依赖版本已固定。

首版使用“小索引 + 每本书独立 JSON”的存储，不引入全库数据库或复杂迁移框架。索引原子替换；解析大文件放到后台；索引损坏时保留旧文件并暂停改写。

```text
shared/src/commonMain/    模型、书库状态、Miuix UI
shared/src/iosMain/       iOS 私有存储和 Compose 入口
shared/src/desktopMain/   JVM 验证用存储实现
shared/src/commonTest/    数据与阅读列表契约测试
iosApp/Sources/Host/     SwiftUI 宿主、文件选择
iosApp/Sources/Parser/   TXT/EPUB 纯文本导入
iosApp/Tests/            独立 Swift importer 测试
scripts/                 检查、构建和 IPA 封装
.github/workflows/       macOS IPA 流水线
samples/                 原创示例书籍
```

## 首版限制与数据保留

- 单个原始文件最多 **32 MiB**；正文最多 UTF-8 12 MiB / UTF-16 8 Mi units；2000 章、50000 段。
- ZIP 每个条目上限 8 MiB、总声明解压体积 64 MiB，且有条目数和压缩比限制。部分正常大图 EPUB 也可能被挡住。
- TXT 支持 UTF-8、带 BOM 的 UTF-16、GB18030；自动目录识别是启发式规则。
- EPUB 仅支持受限 ZIP32、标准 XHTML 和基础文本。字体混淆/加密清单、ZIP64、复杂或损坏标记暂不支持。完整边界见 [导入器说明](<iosApp/README.md>)。
- 字号/行距变化保留段落，旧像素偏移归零；旋转、系统字体变化可能使显示位置小幅变化。此版本还没有跨端稳定 CFI/字符锚点。
- 未实现书籍导出/备份。卸载应用会影响私有书库和阅读位置，请自行保存原始文件。正常覆盖升级需保持 Bundle ID，不要先卸载再安装。
- 首版对大文件采取上限约束，不承诺超大书籍的内存和流畅度；iOS16 低内存真机仍需测试。

## 后续建议顺序

1. 修复首轮 Actions / 真机发现的问题，建立正式 iOS16 冒烟测试。
2. 增加备份导出、书签、文本选择和正文搜索。
3. 完善 EPUB 图片和原书样式。
4. 建立版本化文本定位，再增加 WebDAV 同步。
5. 接 Android 宿主、系统 TTS / multi@TTS。

## 许可证

本项目为独立实现，未复制 Legado 代码。新增源码使用 [MIT](<LICENSE>)；依赖及 Gradle wrapper 保持各自许可，见 [第三方说明](<THIRD_PARTY_NOTICES.md>)及 [Apache 许可文本](<licenses/Apache-2.0.txt>)。
