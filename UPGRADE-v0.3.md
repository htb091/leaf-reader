# 叶读 v0.3：Miuix 视觉与动效补齐

v0.3 不是功能版本，只针对 v0.2 的界面反馈逐条落地。阅读/分页/分章存储引擎保持原样。

## 九条反馈的落点

| 反馈 | 实现 |
|---|---|
| 书架设置做成悬浮底栏 | `Scaffold(floatingToolbar = … , BottomCenter)` + Miuix `FloatingToolbar`，里面是「书架 / 设置」两枚胶囊 `DockTab`，底栏不占布局高度，列表底部留 104dp 避免遮挡 |
| 顶栏不要一刀切 | 去掉 `TopAppBar` 实心条与分割线，改为 `GradientHeaderScrim`（surface→透明四段渐变），内容在其下滚动溶入 |
| 打开/关闭动画 | 阅读页入口 `Animatable` 0→1：scale 0.94→1 + alpha，360ms `cubic-bezier(0.22,1,0.36,1)`；返回时先 280ms 反向再真正关闭，期间吞掉点击 |
| 返回按钮悬浮圆形 | 顶栏内 `MiuixCircleButton(Glyph.BACK)`，40dp 圆形、Miuix 容器色 |
| 控件间距 | `PageMargin=20dp`、`ControlGap=12dp`，dock 内 16dp/8dp，设置分组 24dp，触控目标 44dp |
| 目录仿截图 | `OverlayBottomSheet(cornerRadius=28dp)`：自带拖拽条、书封+书名+当前章+进度胶囊、`TabRowWithContour` 四段（信息/目录/书签/笔记）、搜索行 + 4 个方形小按钮、当前章高亮卡 + 蓝色字数胶囊、列表行左标题右字数（数据来自 manifest.characterCount） |
| 导入按钮变小圆形加号 | `MiuixCircleButton(Glyph.ADD, size=40dp)`，与搜索按钮同尺寸并排 |
| 上滑标题缩放 | 由 `LazyGridState` 滚动量驱动：大标题 scale 1→0.68 + 淡出，紧凑标题反向淡入，140ms 补间，仅头部重组 |
| 搜索改按钮+放大镜 | 顶栏右侧 40dp 圆形放大镜按钮，点开在下方展开 Miuix `InputField` 搜索行（带清空/收起圆钮） |

另：阅读顶/底栏默认不显示，点屏幕中央唤出，分别从顶部/底部 `slideInVertically` 滑入、滑出；底栏右侧为「设置」（排版设置），中间显示「章 / 总章 · 百分比」。

## 有意保留的取舍

- 渐变遮罩是**渐变色**而非真实 background blur（Compose 无跨平台 backdrop-blur，miuix-blur 的 LayerBackdrop 属于实验路径）。iOS 16 上表现一致、无掉帧风险。
- 目录面板的「信息 / 书签 / 笔记」为占位空态，不伪造数据；书签/笔记功能后续版本再加。
- 点当前章不重置阅读位置（只收起面板），避免丢锚点。
- 打开动画是整页 scale+fade，不是真正的 shared-element（书封飞到顶部）；后者需要 `LookaheadScope` + 共享 bounds，风险较高，留作后续。

## 验证

- 本机 `gradle :shared:desktopTest` 编译通过，47 项 Kotlin 测试全部通过（分页/锚点/存储回归未受影响）。
- 未在 iOS 真机跑过；Miuix 组件 API 均对照 0.9.4 tag 源码核对。
- 16:9/刘海：使用 `WindowInsets.safeDrawing` 与 `BoxWithConstraints` 分档，面板高度上限 72% 屏高，未写死像素。

## 升级方式

沿用同一套离线安装器：`LeafReader-v0.3-upgrade.py` 会写入 30 个源码文件并把 `iosApp/project.yml` 的版本号改为 0.3.0 / 3，其余构建配置（Bundle ID、静态框架路径、镜像设置）保持不变。备份和变更清单写在 `.leaf-upgrade-backup/<UTC>/`。
