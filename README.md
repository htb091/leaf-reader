# 叶读 · Leaf Reader v0.5.1

面向 iOS16+ 的本地小说阅读器，Kotlin Multiplatform / Compose Multiplatform / Miuix 0.9.4。使用 GitHub Actions 构建未签名 ARM64 IPA，交给兼容设备上的 TrollStore 安装。

## v0.5.1 体验优化

- 书架圆按钮扩大触控区域，生成封面提高白字对比及小字可读性。
- iOS 跟随系统减少动态效果，主要自定义过场与点击翻页滚动支持即时切换；第三方控件内部动画与 iOS 真机效果待验证。
- 核查并保留现有 Compose 手势检测器，增加点击与拖动取消回归。

## v0.5 界面修复

- 修正模糊背景透明采样造成的文字色块，材质延伸到状态栏区域。
- 书架/设置页滑动切换，悬浮栏高亮平滑移动，设置采用 Miuix 弹出列表。
- 修复阅读设置缺少弹窗宿主；精简阅读底栏与目录行，适配短屏。

## v0.4 视觉与动效

- 书架与设置改为 Miuix 悬浮底栏（`Scaffold.floatingToolbar` + `FloatingToolbar`），不再占用布局高度。
- 顶栏使用 Miuix 渐进背景模糊及渐变遮罩，内容滚动时溶入；上滑时「书架」大标题缩放淡出、紧凑标题淡入。
- 搜索与导入为两个等大 40dp 圆形按钮（放大镜 / 加号）并排；搜索在下方展开 Miuix 搜索行。
- 书籍打开/关闭使用 360ms/280ms 弹性缩放淡入淡出；返回按钮为悬浮圆形按钮。
- 阅读页顶/底栏默认隐藏，点屏幕中央从顶部/底部滑出；底栏右侧为「设置」，中间显示章节进度。
- 目录改为参考模板的 Miuix 页面：书封、书名、进度、搜索、排序、当前章高亮与每章字数；短屏使用紧凑布局。
- 控件间距：页面边距 20dp、控件间距 12dp、触控目标 ≥44dp。

## 与 v0.1 的区别

- 真正 Miuix 折叠大标题、搜索、分组设置、分段选项、Switch 和 Slider。
- 网格 / 列表 / 紧凑三种书架。
- 横向滑动分页 / 瞬翻 / 纵向滚动，单栏 / 双栏 / 自动分栏。
- 阅读顶底栏可点击收起、可自动隐藏；叠层不挤压分页尺寸。
- 字体、字号、行距、段距、字距、边距、首行缩进、粗体、主题。
- 实际字体行测量和文字锚点；不是固定字数分页或整章一页。
- 大书文件流导入、正文按章存储、按章读取。TXT 输入上限512MiB，EPUB输入上限1GiB；这些数值是校验上限，不是真机跑满的承诺。
- 兼容旧索引/正文的渐进迁移；保留已修好的 POSIX 存储和 lipo -archs 构建链。

详细范围与限制见 [v0.5.1 说明](<UPGRADE-v0.5.1.md>)、[v0.5 说明](<UPGRADE-v0.5.md>)、[v0.4 说明](<UPGRADE-v0.4.md>)、[v0.3 说明](<UPGRADE-v0.3.md>)、[v0.2 说明](<UPGRADE-v0.2.md>)、[验证记录](<VALIDATION.md>)。

## GitHub Actions

已有工程：把下载的 `LeafReader-v0.5.1-upgrade.py` 放到仓库根目录，把 `upgrade-v051.yml` 放到 `.github/workflows/`，手动运行 **Build LeafReader v0.5.1**。升级器明文可审阅、标准库、自包含；备份被覆盖的源码，不读取凭据，不自动提交或推送。

工作流会应用升级、运行共享测试、构建静态 Shared.framework / iOS App、上传 IPA 和完整升级源码，再跑原生导入测试。升级后的源码 artifact 可作为以后直接维护的仓库内容，不需要永久依赖补丁升级器。

已有完整 v0.2 源码时，原有构建工作流继续可用：

```bash
bash ./gradlew :shared:desktopTest -PenableApple=false
bash scripts/build-ios.sh
bash scripts/test-ios.sh
```

macOS 构建仍需兼容 Kotlin2.4.20 的 Xcode，CI 优先 Xcode26.4；最低运行版本 iOS16 与构建SDK分别管理。

## 数据

覆盖升级请保持已有 Bundle ID，不要先卸载。书库位于应用私有 Application Support/LeafReader。旧 v1 索引备份为 library.v1-backup.json；旧整书 JSON 首次打开分章迁移并保留原副本。原始导入文件不修改。备份/导出仍未提供，请自行保存原书。

v0.2 进度为章节、局部段落、UTF-16 文字位置，按本地字体尺寸定位；不承诺与任意第三方引擎 CFI 兼容。WebDAV、朗读、书源、PDF、仿真翻页、完整 EPUB CSS/图片仍后置。

## 验证状态

本机可运行桌面 JVM 的共享代码编译与测试；Apple 侧编译、Swift 测试与真机安装仍需 GitHub Actions 与 iOS 设备验证。桌面测试通过不等于 iOS 渲染与性能通过。

## 许可

本项目为独立实现，未复制 Legado 代码。源码使用 [MIT](<LICENSE>)，依赖保持各自许可，见 [第三方说明](<THIRD_PARTY_NOTICES.md>)。
