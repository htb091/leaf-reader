# 验证记录

日期：2026-11-24。工程：叶读 v0.1.0 源码首版。

## 已实际执行并通过

### 共享 UI 编译与 Kotlin 测试

在 Android 手机上的 Ubuntu / Linux aarch64、OpenJDK 17 环境执行：

```text
<本机已缓存的 Gradle 8.14.3>/bin/gradle :shared:desktopTest --no-daemon --console=plain
BUILD SUCCESSFUL in 17s
```

- Miuix 0.9.4 / CMP 1.12.0 的共享 UI 与实际 Kotlin 2.4.20 源码已编译。
- 19 项 Kotlin 测试通过：13 项书库状态/存储/失败恢复测试，6 项阅读列表与索引契约测试。
- 覆盖导入去重、阅读位置/设置重启恢复、位置夹取、打开取消、删除中打开、损坏索引保留、索引写入失败回滚、重新导入修复缺失副本和并发打开。
- 最初 Gradle DSL 有自定义 desktopMain accessor 错误，已修复并重新完整编译验证。
- 本机使用缓存 Gradle 8.14.3；仓库 wrapper 固定 9.7.1。两者不同，后者仍需 CI 验证。本机出现旧 Gradle 的弃用警告，不影响本次成功结果。

### IPA 封装和源码结构

```bash
python3 scripts/check_project.py
python3 -m unittest discover -s scripts/tests -v
bash -n scripts/build-ios.sh scripts/test-ios.sh
python3 -m compileall -q scripts
```

5 项 Python 测试通过：Payload 路径、可执行权限、拒绝模拟器包、缺失主程序、越界 symlink 与输出路径保护（其中一项组合检查）。这些使用合成 Mach-O 头 fixture，不是生成了真实可运行 iOS App。

其他静态检查：

- Gradle wrapper JAR SHA-256、分发 checksum 配置。
- Actions YAML、手动触发入口、只读权限及 job 依赖。
- XcodeGen YAML、iOS16 部署目标、Shared 静态框架只链接不嵌入。
- Info.plist 解析、Compose 帧率设置、文件类型声明。
- 原创图标 PNG 尺寸、RGB 无透明通道和 asset slots。
- 源码包本地链接与文件完整性检查。

## 尚未实际执行

- GitHub 远端工作流：当前没有连接用户仓库，也没有推送代码。
- macOS 上的 Kotlin/Native iOS framework 编译。
- Swift 编译、Xcode app 链接、15 项原生 importer XCTest。
- 真正 IPA 生成、签名/巨魔安装及 iOS16 真机运行。
- 文件提供器、后台中断、大文件内存、VoiceOver 和触摸阅读体验。
- Android 宿主、APK、WebDAV、TTS 等后续功能。

CI 选择 macOS 26 / Xcode 26.4：依据 [KMP 兼容表](https://kotlinlang.org/docs/multiplatform/multiplatform-compatibility-guide.html)及 [runner 镜像清单](https://github.com/actions/runner-images/blob/main/images/macos/macos-26-Readme.md)。这属于依据文档配置，不是该镜像已运行成功的证明。

## 首轮 Actions 验收

1. shared-tests job 通过。
2. linkReleaseFrameworkIosArm64 通过，Apple 平台源真实编译。
3. XcodeGen / Swift / 链接通过。
4. ParserTests 15 项通过。
5. artifact 内有 IPA 和 SHA-256。
6. 在兼容 TrollStore 的 iOS16 真机打开：导入示例 TXT/EPUB → 阅读 → 改字号 → 目录跳转 → 返回 → 再打开 → 后台/前台 → 重启恢复。

仅前五项通过也不代表第六项自动通过。首轮原生错误应以 CI 实际日志修复，而不是把本地 JVM 成功等同为 iOS 全部成功。
