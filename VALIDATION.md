# 验证状态

## v0.5.1（2026-11-26）

- Linux aarch64 / JDK 17 实际运行 `:shared:desktopTest`：90 项，0 失败、0 错误、0 跳过；其中 8 项使用模拟 PointerInput 事件测试 Compose 检测器，并非真实设备手势或图形测试。
- `scripts/check_project.py`、44 项 Python 脚本测试、`bash -n` 和 `git diff --check` 均通过。
- 生成书封的对比值是按代码色彩组合计算，不是设备截图测量。
- iOS Kotlin/Native 编译、UIKit 减少动态通知、Miuix 内部动画、16:9、VoiceOver 与 IPA 安装尚未实机验证。新增的 iOS 通知测试须在支持模拟器的 Apple CI 上运行。

## v0.5（2026-11-26）

- Linux aarch64 / JDK 17 执行 `:shared:desktopTest`：70 项、0 失败、0 错误、0 跳过。其中 4 项是源码结构检查，不是触屏或渲染测试。
- `scripts/check_project.py` 通过；34 项 Python 打包和升级脚本测试通过。执行 `bash -n` 与 `git diff --check` 通过。
- 截图灰块与 Miuix 官方文档中透明文字图层模糊产生色块的情形吻合，采样层已补不透明底色；最终因果与视觉修复仍待该设备复测。
- 没有执行 iOS 编译、真机点击、状态栏、16:9 材质渲染/帧率、VoiceOver 或 IPA 安装。Miuix iOS shader capability 为真并不保证所有 GPU 路径经过验证。

## v0.4（2026-11-26）

- 本机执行 `bash ./gradlew :shared:desktopTest -PenableApple=false --stacktrace`，构建成功；测试结果 XML 统计 **58 项、0 失败、0 错误、0 跳过**，包含新增目录和阅读控制逻辑测试。
- `python3 scripts/check_project.py` 通过；23 项 Python 脚本测试通过（其中升级器 18 项、原 IPA 打包器 5 项）。
- 用原始 v0.1 源码 ZIP 在临时目录执行 v0.4 升级两次，并检查 Bundle ID、blur 依赖和源码归档；在另一份升级后的 v0.1 临时工程上重新运行 `:shared:desktopTest`，构建及测试通过。
- 这些是 Linux/JVM 检验，不是渲染截图或设备性能测试。iOS Kotlin/Native、Swift、IPA、实际 16:9 布局和渐进模糊均待 GitHub macOS 构建与真机验证。

## v0.3 验证状态

日期：2026-11-25。

## 本轮实际执行（本机，真实运行）

```text
gradle :shared:desktopTest   → BUILD SUCCESSFUL, 47 tests, 0 failures
```

环境：Linux aarch64 / OpenJDK 17 / 缓存 Gradle 8.14.3。覆盖 Miuix 0.9.4 + CMP 1.12.0 的全部共享 UI 源码，包括本版新增的 `MiuixAtoms.kt`、`MiuixGlyphs.kt`、`TocSheet.kt` 与重写的书架/阅读/设置页。分页、文字锚点、分章存储的回归测试全部通过。

升级器同样在本机做了端到端演练：对临时模拟仓库执行 `LeafReader-v0.3-upgrade.py --project … --archive …`，31 个源文件写入、`project.yml` 版本改为 0.3.0/3、备份目录与 change-manifest 生成、归档包含 TocSheet/UPGRADE-v0.3/工作流，二次运行全部 unchanged（幂等）。

## 本轮未执行

- macOS 上的 Kotlin/Native iOS framework 编译、Swift 编译、Xcode 链接、IPA 打包。
- iOS16 真机运行与巨魔安装；手势、动画帧率、刘海/16:9 实际观感。
- 真实文件提供器导入与后台中断。

## v0.2 及更早记录

## 本轮实际完成

- 读取用户附带的编译复盘，以及现有 POSIX 文件写入、lipo -archs、Xcode 选择和产物上传顺序修复；未恢复已失效的 NSString.writeToFile 或 lipo -verify_arch。
- 阅读器、书架、分章存储、Swift 流式导入的源码实现与逐文件静态复核。
- Miuix 0.9.4 使用的组件 API 对照对应 tag 的真实源码核实。
- 新增/更新回归测试源码：Kotlin 书库/manifest 33 例、分页/章节 14 例；原生流式导入新增13例，原15例导入测试保留。
- 静态审查发现并修复总段数 Int 求和溢出、取消旧库迁移后索引偏移、索引写入失败后重启定位、未挂载滚动 state 等待首帧等问题，保留回归用例。

## 本轮未执行

执行器首次调用返回 `spawn bash ENOENT`；glob/ripgrep 子进程也失败。read/edit/write 可用。本轮没有重复尝试损坏的执行器，没有运行 Gradle、Swift/XCTest、打包或真机安装。测试用例数量不是通过数量。

v0.1 的成功构建和19项本地通过记录只适用于旧版本，不作为 v0.2 成功证明。v0.2 未产出现成 IPA。

## Actions 必须验证

1. 标准库升级器可解析、路径预检、源码备份和全量源码 ZIP 生成。
2. JVM 共享 UI 编译和全部 Kotlin 回归测试。
3. Apple iOS 源集/静态框架编译、Swift 编译、App 链接与 IPA 封装。
4. 28 项原生导入测试（原15+新增13，实际数量以 XCTest 报告为准）。
5. IPA 产物在原生测试之前上传；测试失败仍应保留已成功构建的 IPA，但工作流会标记失败。

## iOS16 真机验收

- 覆盖安装、保留 Bundle ID，不先卸载；旧书库进度与分章迁移保持原文位置。
- Miuix书架折叠大标题、搜索、网格/列表/紧凑布局、设置切换保存。
- 横滑/瞬翻/滚动、单栏/双栏/旋转、目录和前后章连续性。
- 中央点击显示/收起工具栏，5秒自动隐藏可关闭，叠层不改分页。
- 字体/字号/行距改变后的文字锚点恢复，辅助字号、emoji、空章、极长段落。
- 大于32MiB TXT实测内存与导入时间；512MiB/1GiB是校验上限，不等于已通过该体积压力测试。
- 来回切换应用、导入过程中停止/空间不足、损坏中间章节、重启后状态恢复。

## 已知边界

EPUB仍是纯文本导入，不保留完整CSS/图片；ZIP64、DRM、过大单个XHTML和不规范HTML有明确兼容限制。过程终止或索引提交失败可能留下未被当前索引引用的章节修订副本；有效草稿保留便于重试，尚无完整磁盘垃圾回收界面。Canvas辅助朗读、字体fallback与真机触控待验收。
