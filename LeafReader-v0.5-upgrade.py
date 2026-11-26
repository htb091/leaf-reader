#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LeafReader v0.5 offline source upgrade (Python 3.8+, standard library only).

Usage: python3 LeafReader-v0.5-upgrade.py --project PATH [--archive PATH]
Plain FILES payloads are reviewable. No network, installs, subprocess or Git.
Embeds 50 complete source files; preserves the user's Gradle configuration and
Bundle ID by patching only approved material dependencies and Xcode version scalars.
All target, Python AST, plist, anchor and payload checks precede source writes.
Backups, change manifest and payload SHA map live in .leaf-upgrade-backup/.
Kotlin/Swift compilation and tests remain CI/device verification tasks.
"""
INSTALLER_VERSION = '0.5'
VERSION_PATCHES = {'MARKETING_VERSION': '0.5.0', 'CURRENT_PROJECT_VERSION': '5'}
REQUIRED_MATERIAL_DEPENDENCIES = ('top.yukonga.miuix.kmp:miuix-blur:0.9.4',)
FILES = {
    '.github/workflows/upgrade-v02.yml': r'''name: Build LeafReader v0.2

on:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: leaf-v02-${{ github.ref }}
  cancel-in-progress: true

jobs:
  upgrade-and-build:
    runs-on: macos-26
    timeout-minutes: 90
    env:
      PREFERRED_XCODE: /Applications/Xcode_26.4.app/Contents/Developer
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - name: Apply readable source upgrade and archive sources
        run: |
          python3 -m py_compile LeafReader-v0.2-upgrade.py
          python3 LeafReader-v0.2-upgrade.py --project . --archive dist/LeafReader-v0.2-source.zip
          python3 scripts/check_project.py
          python3 -m unittest discover -s scripts/tests -v
          bash -n scripts/build-ios.sh scripts/test-ios.sh
      - name: Upload complete upgraded source
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.2-complete-source
          path: dist/LeafReader-v0.2-source.zip
          if-no-files-found: error
      - name: Compile shared UI and run regression tests
        run: bash ./gradlew :shared:desktopTest -PenableApple=false --stacktrace
      - name: Select Xcode
        run: |
          set -euo pipefail
          if [ -d "$PREFERRED_XCODE" ]; then
            echo "DEVELOPER_DIR=$PREFERRED_XCODE" >> "$GITHUB_ENV"
          else
            python3 - <<'PY'
          import os, pathlib, re
          apps = list(pathlib.Path('/Applications').glob('Xcode*.app'))
          if not apps:
              raise SystemExit('No Xcode application found')
          apps.sort(key=lambda p: tuple(int(n) for n in re.findall(r'\d+', p.name)))
          with open(os.environ['GITHUB_ENV'], 'a') as out:
              out.write('DEVELOPER_DIR=' + str(apps[-1] / 'Contents/Developer') + '\n')
          PY
          fi
      - name: Inspect Apple tools and install XcodeGen
        run: |
          xcodebuild -version
          xcrun --sdk iphoneos --show-sdk-version
          brew list xcodegen >/dev/null 2>&1 || brew install xcodegen
          xcodegen --version
      - name: Build and package device IPA
        run: bash scripts/build-ios.sh
      - name: Upload IPA before optional native test execution
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.2-iOS16-arm64-unsigned
          path: |
            dist/*.ipa
            dist/*.ipa.sha256
          if-no-files-found: error
          retention-days: 14
      - name: Run native streaming importer tests
        run: bash scripts/test-ios.sh
      - name: Upload all test reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.2-test-reports
          path: |
            shared/build/reports/tests/
            build/ParserTests.xcresult
          if-no-files-found: ignore
      - name: Summary
        if: always()
        run: |
          echo '### LeafReader v0.2' >> "$GITHUB_STEP_SUMMARY"
          echo 'Full upgraded source is published separately. IPA is available only if the build step succeeded.' >> "$GITHUB_STEP_SUMMARY"
          echo 'Keep the existing Bundle ID and install over the prior version to retain the local library. Verify migration and pagination on your iOS16 device.' >> "$GITHUB_STEP_SUMMARY"
''',
    '.github/workflows/upgrade-v03.yml': r'''name: Build LeafReader v0.3

on:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: leaf-v03-${{ github.ref }}
  cancel-in-progress: true

jobs:
  upgrade-and-build:
    runs-on: macos-26
    timeout-minutes: 90
    env:
      PREFERRED_XCODE: /Applications/Xcode_26.4.app/Contents/Developer
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - name: Apply readable source upgrade and archive sources
        run: |
          python3 -m py_compile LeafReader-v0.3-upgrade.py
          python3 LeafReader-v0.3-upgrade.py --project . --archive dist/LeafReader-v0.3-source.zip
          python3 scripts/check_project.py
          python3 -m unittest discover -s scripts/tests -v
          bash -n scripts/build-ios.sh scripts/test-ios.sh
      - name: Upload complete upgraded source
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.3-complete-source
          path: dist/LeafReader-v0.3-source.zip
          if-no-files-found: error
      - name: Compile shared UI and run regression tests
        run: bash ./gradlew :shared:desktopTest -PenableApple=false --stacktrace
      - name: Select Xcode
        run: |
          set -euo pipefail
          if [ -d "$PREFERRED_XCODE" ]; then
            echo "DEVELOPER_DIR=$PREFERRED_XCODE" >> "$GITHUB_ENV"
          else
            python3 - <<'PY'
          import os, pathlib, re
          apps = list(pathlib.Path('/Applications').glob('Xcode*.app'))
          if not apps:
              raise SystemExit('No Xcode application found')
          apps.sort(key=lambda p: tuple(int(n) for n in re.findall(r'\d+', p.name)))
          with open(os.environ['GITHUB_ENV'], 'a') as out:
              out.write('DEVELOPER_DIR=' + str(apps[-1] / 'Contents/Developer') + '\n')
          PY
          fi
      - name: Inspect Apple tools and install XcodeGen
        run: |
          xcodebuild -version
          xcrun --sdk iphoneos --show-sdk-version
          brew list xcodegen >/dev/null 2>&1 || brew install xcodegen
          xcodegen --version
      - name: Build and package device IPA
        run: bash scripts/build-ios.sh
      - name: Upload IPA before optional native test execution
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.3-iOS16-arm64-unsigned
          path: |
            dist/*.ipa
            dist/*.ipa.sha256
          if-no-files-found: error
          retention-days: 14
      - name: Run native streaming importer tests
        run: bash scripts/test-ios.sh
      - name: Upload all test reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.3-test-reports
          path: |
            shared/build/reports/tests/
            build/ParserTests.xcresult
          if-no-files-found: ignore
      - name: Summary
        if: always()
        run: |
          echo '### LeafReader v0.3' >> "$GITHUB_STEP_SUMMARY"
          echo 'Full upgraded source is published separately. IPA is available only if the build step succeeded.' >> "$GITHUB_STEP_SUMMARY"
          echo 'Keep the existing Bundle ID and install over the prior version to retain the local library. Verify migration and pagination on your iOS16 device.' >> "$GITHUB_STEP_SUMMARY"
''',
    '.github/workflows/upgrade-v04.yml': r'''name: Build LeafReader v0.4

on:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: leaf-v04-${{ github.ref }}
  cancel-in-progress: true

jobs:
  upgrade-and-build:
    runs-on: macos-26
    timeout-minutes: 90
    env:
      PREFERRED_XCODE: /Applications/Xcode_26.4.app/Contents/Developer
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - name: Apply readable source upgrade and archive sources
        run: |
          python3 -m py_compile LeafReader-v0.4-upgrade.py
          python3 LeafReader-v0.4-upgrade.py --project . --archive dist/LeafReader-v0.4-source.zip
      - name: Upload complete upgraded source before tests
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.4-complete-source
          path: |
            dist/LeafReader-v0.4-source.zip
            .leaf-upgrade-backup/**/payload-sha256.json
            .leaf-upgrade-backup/**/change-manifest.json
          include-hidden-files: true
          if-no-files-found: error
      - name: Verify project scripts and installer regression tests
        run: |
          python3 scripts/check_project.py
          python3 -m unittest discover -s scripts/tests -v
          bash -n scripts/build-ios.sh scripts/test-ios.sh
      - name: Compile shared UI and run regression tests
        run: bash ./gradlew :shared:desktopTest -PenableApple=false --stacktrace
      - name: Select Xcode
        run: |
          set -euo pipefail
          if [ -d "$PREFERRED_XCODE" ]; then
            echo "DEVELOPER_DIR=$PREFERRED_XCODE" >> "$GITHUB_ENV"
          else
            python3 - <<'PY'
          import os, pathlib, re
          apps = list(pathlib.Path('/Applications').glob('Xcode*.app'))
          if not apps:
              raise SystemExit('No Xcode application found')
          apps.sort(key=lambda p: tuple(int(n) for n in re.findall(r'\d+', p.name)))
          with open(os.environ['GITHUB_ENV'], 'a') as out:
              out.write('DEVELOPER_DIR=' + str(apps[-1] / 'Contents/Developer') + '\n')
          PY
          fi
      - name: Inspect Apple tools and install XcodeGen
        run: |
          xcodebuild -version
          xcrun --sdk iphoneos --show-sdk-version
          brew list xcodegen >/dev/null 2>&1 || brew install xcodegen
          xcodegen --version
      - name: Build and package device IPA
        run: bash scripts/build-ios.sh
      - name: Upload IPA before native test execution
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.4-iOS16-arm64-unsigned
          path: |
            dist/*.ipa
            dist/*.ipa.sha256
          if-no-files-found: error
          retention-days: 14
      - name: Run native streaming importer tests
        run: bash scripts/test-ios.sh
      - name: Upload all test reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.4-test-reports
          path: |
            shared/build/reports/tests/
            build/ParserTests.xcresult
          if-no-files-found: ignore
      - name: Summary
        if: always()
        run: |
          echo '### LeafReader v0.4' >> "$GITHUB_STEP_SUMMARY"
          echo 'Upgraded source and payload hashes are published before tests. IPA is available only if the build step succeeded.' >> "$GITHUB_STEP_SUMMARY"
          echo 'Keep the existing Bundle ID and install over the prior version to retain the local library. Verify the reading chrome, contents navigation and blur on your iOS16 device.' >> "$GITHUB_STEP_SUMMARY"
''',
    '.github/workflows/upgrade-v05.yml': r'''name: Build LeafReader v0.5

on:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: leaf-v05-${{ github.ref }}
  cancel-in-progress: true

jobs:
  upgrade-and-build:
    runs-on: macos-26
    timeout-minutes: 90
    env:
      PREFERRED_XCODE: /Applications/Xcode_26.4.app/Contents/Developer
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - name: Apply readable source upgrade and archive sources
        run: |
          python3 -m py_compile LeafReader-v0.5-upgrade.py
          python3 LeafReader-v0.5-upgrade.py --project . --archive dist/LeafReader-v0.5-source.zip
      - name: Upload complete upgraded source before tests
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.5-complete-source
          path: |
            dist/LeafReader-v0.5-source.zip
            .leaf-upgrade-backup/**/payload-sha256.json
            .leaf-upgrade-backup/**/change-manifest.json
          include-hidden-files: true
          if-no-files-found: error
      - name: Verify project scripts and installer regression tests
        run: |
          python3 scripts/check_project.py
          python3 -m unittest discover -s scripts/tests -v
          bash -n scripts/build-ios.sh scripts/test-ios.sh
      - name: Compile shared UI and run regression tests
        run: bash ./gradlew :shared:desktopTest -PenableApple=false --stacktrace
      - name: Select Xcode
        run: |
          set -euo pipefail
          if [ -d "$PREFERRED_XCODE" ]; then
            echo "DEVELOPER_DIR=$PREFERRED_XCODE" >> "$GITHUB_ENV"
          else
            python3 - <<'PY'
          import os, pathlib, re
          apps = list(pathlib.Path('/Applications').glob('Xcode*.app'))
          if not apps:
              raise SystemExit('No Xcode application found')
          apps.sort(key=lambda p: tuple(int(n) for n in re.findall(r'\d+', p.name)))
          with open(os.environ['GITHUB_ENV'], 'a') as out:
              out.write('DEVELOPER_DIR=' + str(apps[-1] / 'Contents/Developer') + '\n')
          PY
          fi
      - name: Inspect Apple tools and install XcodeGen
        run: |
          xcodebuild -version
          xcrun --sdk iphoneos --show-sdk-version
          brew list xcodegen >/dev/null 2>&1 || brew install xcodegen
          xcodegen --version
      - name: Build and package device IPA
        run: bash scripts/build-ios.sh
      - name: Upload IPA before native test execution
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.5-iOS16-arm64-unsigned
          path: |
            dist/*.ipa
            dist/*.ipa.sha256
          if-no-files-found: error
          retention-days: 14
      - name: Run native streaming importer tests
        run: bash scripts/test-ios.sh
      - name: Upload all test reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.5-test-reports
          path: |
            shared/build/reports/tests/
            build/ParserTests.xcresult
          if-no-files-found: ignore
      - name: Summary
        if: always()
        run: |
          echo '### LeafReader v0.5' >> "$GITHUB_STEP_SUMMARY"
          echo 'Upgraded source and payload hashes are published before tests. IPA is available only if the build step succeeded.' >> "$GITHUB_STEP_SUMMARY"
          echo 'Keep the existing Bundle ID and install over the prior version to retain the local library. Verify UI, material rendering and reading state on your iOS16 device.' >> "$GITHUB_STEP_SUMMARY"
''',
    'README.md': r'''# 叶读 · Leaf Reader v0.5

面向 iOS16+ 的本地小说阅读器，Kotlin Multiplatform / Compose Multiplatform / Miuix 0.9.4。使用 GitHub Actions 构建未签名 ARM64 IPA，交给兼容设备上的 TrollStore 安装。

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

详细范围与限制见 [v0.5 说明](<UPGRADE-v0.5.md>)、[v0.4 说明](<UPGRADE-v0.4.md>)、[v0.3 说明](<UPGRADE-v0.3.md>)、[v0.2 说明](<UPGRADE-v0.2.md>)、[验证记录](<VALIDATION.md>)。

## GitHub Actions

已有工程：把下载的 `LeafReader-v0.5-upgrade.py` 放到仓库根目录，把 `upgrade-v05.yml` 放到 `.github/workflows/`，手动运行 **Build LeafReader v0.5**。升级器明文可审阅、标准库、自包含；备份被覆盖的源码，不读取凭据，不自动提交或推送。

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
''',
    'UPGRADE-v0.2.md': r'''# 叶读 v0.2：从打开小说到实际阅读

## 这次针对的具体问题

上一版只做了纵向段落列表，Miuix 组件使用零散、阅读顶底栏常驻、整本书经 JSON 传递、32MiB 文件限制偏低。v0.2 不是只改配色和数字上限，而是更换阅读布局与存储/导入主链。

### 界面

- 采用实际 Miuix 大标题折叠 TopAppBar、SearchBar/InputField、TabRowWithContour、BasicComponent、Switch/Slider 和分组设置。
- 书架有网格、详细列表、紧凑列表；布局选择持久化。
- 最近阅读入口、书名/作者搜索与排序。

### 阅读

- 横向滑动分页、无动画瞬翻、纵向滚动三种模式。
- 单栏、双栏、宽屏自动双栏；当前自动阈值为 840dp。
- 字体、字号、行距、字距、段距、左右边距、首行缩进、粗体、主题。
- 中央点击显示/收起顶底工具栏，左右区域翻页；可选5秒自动收起。
- 工具栏是覆盖层，不参与正文分页尺寸，显示/隐藏不强制重排。
- 按实际字体测量的行分页，不把整章伪装成一页，也不按固定字符数切页。
- 仅排版当前章节；位置保存为章节、段落、UTF-16 文字偏移，而不是设备页码。

### 大书

- 文件流入口：TXT 上限 512MiB，EPUB 上限 1GiB。此为输入校验上限，不是上述体积的真机性能承诺。
- TXT 64KiB 字节块读取，流式哈希和有 carry 的 UTF-8/UTF-16/GB18030 解码。
- EPUB 使用文件 URL 归档，中央目录/本地头有界读取，单个 XHTML 解析仍有8MiB边界。
- 正文分章写入；目标每个持久章节不超过256Ki UTF-16 / 512KiB文本，核心允许512Ki UTF-16的兼容上限。
- Swift/Kotlin 之间只传较小目录元数据，不再传整本正文 JSON。
- 打开、翻章只读取当前章节，有限缓存，不把全书正文 flatten 为 UI 列表。
- 正常书籍也可能遇到 ZIP64、加密、极大单 XHTML、复杂原书排版等兼容边界。完整图片/CSS 渲染不在本轮。

## 旧书库

- 保留 Bundle ID 与 AppSupport/LeafReader 路径，建议覆盖安装，不先卸载。
- v1 索引首次加载时保存 library.v1-backup.json。
- 旧单文件正文首次打开迁移为按章文件；旧原始 JSON 保留。
- 旧全局段落索引转换到章节/局部段落；长章拆分记录来源位置。
- 新索引发布使用同目录 POSIX 临时文件+fsync+rename，保留此前已修好的新 SDK 兼容。
- 该迁移与覆盖升级尚需 iOS16 真机验证；请保留原始书籍。

## 构建

本机执行工具当前返回 `spawn bash ENOENT`，glob/ripgrep 子进程也失败。文件编辑仍可用。本轮只完成源码与静态复核，未执行新版本编译或测试，不沿用 v0.1 的通过数作为 v0.2 证据。

交付两个文件：

1. LeafReader-v0.2-upgrade.py：明文、标准库、自包含源码升级器，应用前备份被覆盖文件；可生成完整升级源码 ZIP。
2. upgrade-v02.yml：放进现有仓库的 .github/workflows/，手动运行；它应用升级、执行共享测试、构建 IPA、运行原生导入测试，并上传源码与 IPA。

升级器不会提交或推送 Git，不读取账号/密钥，不改 Bundle ID，不重置 wrapper/镜像配置。工作流沿用已验证方向：POSIX 文件存储、lipo -archs，以及产物上传先于原生测试。

## 尚未声称完成

- 本轮未实际构建或安装 v0.2 IPA。
- 未声称视觉与 Legado 全量功能/动画等价；没有仿真翻页、EPUB 原书 CSS/图片兼容。
- 大文件上限、分页手势、旋转重排、Canvas 无障碍和迁移必须由 CI 与真机验收。
''',
    'UPGRADE-v0.3.md': r'''# 叶读 v0.3：Miuix 视觉与动效补齐

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
''',
    'UPGRADE-v0.4.md': r'''# 叶读 v0.4：书架与阅读界面优化

本版参照用户的三个 HTML 模板调整布局，使用 Miuix 0.9.4 和 Compose 实现，而非嵌入网页或加载模板外部资源。

- 书架和设置入口使用 Miuix 悬浮工具栏；内容为工具栏留白，滚动时大标题缩放过渡。搜索和导入是并排的等尺寸圆形按钮；搜索支持书名、作者、格式。
- 顶部使用 Miuix `miuix-blur` 的 `progressiveTextureBlur` 采样正文/书架并渐变模糊；仅采样内容层，避免递归；无 shader 的平台使用半透明渐变。iOS 上的运行效果与性能仍需真机验证。
- 书籍转场保持书架挂载，读取点击位置，360ms 展开阅读页、280ms 收回。阅读期间暂存书架书籍次序以免打开时重排序导致收回跳位；窗口尺寸变化或未获取源坐标时回退居中缩放。它是整页变换，不是封面共享元素动画。
- 阅读控制默认隐藏，点击中央唤出；顶栏从上方、底栏从下方滑入和滑出；返回、目录与设置采用浮动控件。
- 目录包含书籍信息、章节列表与当前章节标记；支持搜索、正倒序和定位当前章，章节列表懒加载。未实现的书签与笔记显示空态。短窗口/大字号采用紧凑布局，确保列表空间。
- 新增目录筛选、定位与紧凑布局测试；页面缩放、模糊与 16:9 显示效果仍以实际设备为准。

## 安装和测试

将 `LeafReader-v0.4-upgrade.py` 放在现有仓库根目录，`upgrade-v04.yml` 放入 `.github/workflows/`，在 Actions 手动运行 **Build LeafReader v0.4**。脚本仅在共享 Gradle 构建文件的 Miuix 依赖旁插入 blur 依赖，并备份覆盖文件；保留 Bundle ID。升级器和 CI 不自动提交、推送。

```sh
bash ./gradlew :shared:desktopTest -PenableApple=false
bash scripts/build-ios.sh
bash scripts/test-ios.sh
```

构建 iOS 需要 macOS、Xcode 和 iOS SDK；IPA 是未签名 arm64 产物，需在兼容设备用 TrollStore 安装。覆盖安装时不要先卸载；请保留原始书籍，旧书库迁移仍应先在设备上验证。

## 边界

本机的桌面 JVM 测试结果仅证明共享代码和逻辑回归；不代表 iOS 原生编译、iOS16 渲染、手势、安全区、16:9 设备、转场帧率或真实阅读体验已通过。阅读模式和大文件架构沿用前版。EPUB 排版仍为纯文本，WebDAV、朗读、书签和笔记未在本次实现。
''',
    'UPGRADE-v0.5.md': r'''# 叶读 v0.5：材质、阅读设置与界面动效

## 本版调整

- 修正背景模糊的采样：先在采样图层中绘制不透明的当前主题底色，再绘制文字和内容。Miuix 官方文档提示，对透明文字图层直接模糊会产生颜色扩散；该遗漏与用户截图中的块状文字相符，修复效果仍需 iOS 真机验证。
- 顶栏材质延伸至状态栏区域；系统状态栏文字保持清晰。阅读正文依旧在安全区域内分页，工具栏显隐不改变正文尺寸。
- 继续使用 Miuix 0.9.4 的渐进模糊和普通材质模糊；浮动底栏在可用时采样底层内容，shader 不可用时回退不透明材质。iOS 的 Miuix 高光/传感器支持不等于 iOS 26 Liquid Glass，本版不宣称支持后者。
- 书架和设置间滑动切换；底栏的选中高亮随切换移动，外层胶囊收紧。多选一设置使用 Miuix 原生列表弹层。
- 阅读页增加 Miuix 弹窗宿主，修正设置按钮点击后弹窗不显示的调用链。阅读顶栏移除重复目录入口，目录和设置位于底栏；底栏缩矮，保留足够触控区域。
- 目录章节行和圆形控件缩小；考虑短屏、系统安全区域及大字号，不通过固定裁剪文字控制高度。

## 构建和验证

将 `LeafReader-v0.5-upgrade.py` 放进现有仓库根目录，将 `upgrade-v05.yml` 放到 `.github/workflows/`，手动运行 **Build LeafReader v0.5**。构建产物为 iOS 16+ arm64 未签名 IPA；保留已有 Bundle ID 并覆盖安装，原始书籍另行保留。

共享 Kotlin 的桌面编译测试、升级器脚本测试与安装器演练以最终构建记录为准。iOS 的材质渲染、状态栏、弹窗触摸、16:9、实际机型性能和 Xcode 构建均须通过 CI 及设备验证；本源码不等同于已安装成功的 IPA。
''',
    'VALIDATION.md': r'''# 验证状态

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
''',
    'iosApp/README.md': r'''# LeafReader iOS host

> v0.2 UPDATE: user-selected files now use the file-backed streaming importer and chapter manifest bridge. See [the current importer contract](<Sources/Parser/STREAMING_IMPORT.md>) and [upgrade notes](<../UPGRADE-v0.2.md>). The small in-memory limits/API descriptions below are retained as v0.1 fixture history, not the user-facing v0.2 file limits. Apple compilation and v0.2 tests are pending CI.

Original Swift host and generated test fixtures for the project contract. No Legado code or book content is copied.

## Build requirements

- macOS with the Xcode version supported by the pinned Kotlin/Native toolchain (the root workflow selects macOS 26 / Xcode 26.4; project language mode is Swift 5), selected via DEVELOPER_DIR or xcode-select, accepted Xcode license, iOS SDK, and an installed simulator runtime for tests. The iOS16 deployment target does not imply that an old Xcode can compile the shared framework.
- XcodeGen **2.38.0+** (`brew install xcodegen`). No Gradle script/build phase is generated in the Xcode project.
- Shared must already be built as the **static iOS ARM64 release framework**, at `../shared/build/bin/iosArm64/releaseFramework/Shared.framework` relative to this folder. Lead/CI owns generating it, e.g. `./gradlew :shared:linkReleaseFrameworkIosArm64` from project root.
- App target/scheme **LeafReader**, bundle identifier `dev.leaf.reader`, iOS deployment target **16.0**, iPhone/iPad, device-only. The framework is linked with `embed: false`; never add it to Embed Frameworks.
- First SPM resolution requires network access. Both package versions are exact, released, non-prerelease pins, verified from upstream release APIs and tagged manifests:
  - [ZIPFoundation 0.9.19 release](https://github.com/weichsel/ZIPFoundation/releases/tag/0.9.19), [tagged Package.swift](https://github.com/weichsel/ZIPFoundation/blob/0.9.19/Package.swift).
  - [SwiftSoup 2.7.7 release](https://github.com/scinfu/SwiftSoup/releases/tag/2.7.7), [tagged Package.swift](https://github.com/scinfu/SwiftSoup/blob/2.7.7/Package.swift).

Run from `iosApp` after building Shared externally:

```sh
xcodegen generate --spec project.yml
xcodebuild -resolvePackageDependencies \
  -project LeafReader.xcodeproj -scheme LeafReader
xcodebuild -project LeafReader.xcodeproj -scheme LeafReader \
  -configuration Release -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath build \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO build
```

The unsigned app is `build/Build/Products/Release-iphoneos/LeafReader.app`. IPA assembly/signing/install and TrollStore device/OS compatibility are Lead responsibilities; this host does not claim a tested IPA. No commit or push is performed.

## Parser tests without a Shared simulator framework

`ParserTests` is a **hostless XCTest bundle** that compiles `Sources/Parser` directly. It does not link Shared, depend on LeafReader, or require an app test host. Its separate scheme is suitable for simulator CI even while the app framework is device-only. Do not substitute scheme LeafReader for simulator testing.

```sh
xcodegen generate --spec project.yml
xcrun simctl list devices available
# Choose an available iOS simulator UDID; CI can select one dynamically.
xcodebuild -project LeafReader.xcodeproj -scheme ParserTests \
  -destination 'platform=iOS Simulator,id=SIMULATOR_UDID' \
  -derivedDataPath build-tests \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO test
```

Fixtures are generated in memory by the test code; no filesystem extraction or downloaded books. Cases cover byte SHA-256/JSON shape, UTF-8/UTF-16 BOM/GB18030, consecutive TXT headings, oversized and pathological single-line/grapheme text, EPUB metadata/spine/nonlinear selection, deflate and signed ZIP32 data descriptors, active-content removal, nested block text, CRC/truncation, encryption/DRM, traversal/remote references, duplicates/symlinks, declared entry/total/ratio/count limits, fixed layout, entities and XML nesting.

## Host and import behavior

- SwiftUI embeds `MainViewControllerKt.MainViewController(onImportRequested:)` through `UIViewControllerRepresentable`. The Kotlin import action opens a `UIDocumentPickerViewController` with TXT/EPUB, **asCopy: true**, multi-select. Files/Open-In uses the same importer.
- A serial user-initiated background queue reads/parses/hashes/encodes one book at a time. Security-scoped access starts in the picker callback and ends after parsing. Up to 16 pending books; autorelease pools bound per-file temporary objects.
- Only on the main queue, call `ReaderRuntime.shared.importBook(json:)` or `ReaderRuntime.shared.reportError(message:)`. Flush on inactive/background. Neither book text nor raw OS/archive errors are logged.
- SHA-256 is computed over the exact original bytes (including BOM/ZIP representation), before decoding.
- TXT: strict BOM-aware UTF-8/UTF-16 LE/BE, then UTF-8, then GB18030. UTF-32/NUL-bearing input is rejected. Chinese/English chapter headings are recognized; consecutive headings survive as empty chapters. Nonempty paragraphs are split at 2,000 UTF-16 units, including pathological single grapheme clusters.
- EPUB: validate ZIP central/local headers, then read only `mimetype`, container XML, OPF, and text spine documents through ZIPFoundation's chunk consumer. Resolve container/OPF references within the archive; never extract paths to disk. OPF title/first creator and primary linear spine order are used; if every spine entry is nonlinear, use that declared order. Duplicate spine references are rejected.
- Text-only XHTML is validated before offline SwiftSoup parsing. Scripts, styles, embedded assets/media/SVG/math are discarded; nothing executes or fetches resources. Block text is traversed once, so nested blocks are not duplicated or dropped. Headings remain in body text to avoid silent content removal (a chapter heading may consequently appear both as its title and first paragraph).

## Limits and deliberate compatibility tradeoffs

| Item | Limit |
| --- | --- |
| Original file | 32 MiB |
| ZIP entry (every entry, including unused assets) | 8 MiB uncompressed |
| All ZIP entries / actual consumed decompression | 64 MiB |
| Archive entries / compression ratio | 4,096 / 200:1 |
| Container / OPF XML | 1 MiB each |
| Readable body UTF-8 | 12 MiB |
| Total imported UTF-16, including metadata/headings | 8 × 1,024 × 1,024 units (Shared contract) |
| Chapters / paragraphs / one paragraph | 2,000 / 50,000 / 2,000 UTF-16 units |
| XML nesting / elements; parsed body nodes | 128 / 100,000; 100,000 |

- **Images and CSS are unsupported**; fixed layout, DRM, any `encryption.xml` (including font obfuscation), rights/license entries, ZIP encryption flags/AES extras, symlinks and unsafe/duplicate archive paths are rejected.
- Narrow ZIP32 support: stored/deflate, UTF-8 names (non-ASCII requires ZIP UTF-8 flag), optional **signed** ZIP32 data descriptors. ZIP64, multi-volume, unsigned/ambiguous data descriptors and excessive compression ratios are intentionally rejected, even for otherwise benign books.
- Content is required to be well-formed UTF-8 or BOM-tagged UTF-16 XHTML. Container/OPF DTDs and all custom entity declarations are rejected. XHTML external doctypes are never resolved. Standard HTML names such as `&nbsp;` are converted, only for XML validation, into numeric references using SwiftSoup's built-in finite table (at most 100,000 references, at most 16 MiB validation output). Original markup is used for text parsing, preserving escaped angle brackets as text. Unknown/custom names and malformed HTML are rejected. No CSS-hidden-text semantics, image alt rendering, cover extraction, NCX/nav TOC, font styling, ruby/MathML/SVG layout, or encoding guessing beyond the stated codecs.
- A book is bounded, but import still holds original bytes, decompressed chapter, DOM, text and JSON temporarily. Older iOS devices may experience memory pressure near limits. JSON persistence on the Kotlin main thread can briefly affect responsiveness; queueing prevents simultaneous large imports.
- File-provider scope, background interruption, real device presentation, Kotlin export header linkage, actual XcodeGen output, Apple compilation and XCTest execution require Apple CI/device verification.

## Original app icon

`Assets.xcassets/AppIcon.appiconset` contains 13 opaque RGB PNGs for all 18 standard iPhone/iPad/marketing slots, including 1024 px marketing art. The open-book/leaf design is generated from original vector geometry; no external artwork or image library. `ASSETCATALOG_COMPILER_APPICON_NAME` is `AppIcon`. To reproduce the assets, run `python3 Tools/generate_app_icon.py` from this folder (Python standard library only).

## Validation performed in the implementation environment

The delegated Linux/Android environment has no Swift compiler, XcodeGen, Apple SDK, or xcodebuild. `Info.plist` was parsed with Python plistlib and `project.yml` with PyYAML; target/package pins/static-link structure were asserted. Dependencies' release status and APIs were checked online. Swift/XCTest has **not been executed here**; no successful Apple build is implied.
''',
    'iosApp/Sources/Host/DocumentPicker.swift': r'''import SwiftUI
import UIKit
import UniformTypeIdentifiers
import Shared

@MainActor
struct DocumentPicker: UIViewControllerRepresentable {
    let onSelection: ([URL]) -> Void
    let onCancel: () -> Void

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }
    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let epub = UTType(filenameExtension: "epub") ?? UTType(importedAs: "org.idpf.epub-container")
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: [.plainText, epub], asCopy: true)
        picker.allowsMultipleSelection = true
        picker.delegate = context.coordinator
        return picker
    }
    func updateUIViewController(_ controller: UIDocumentPickerViewController, context: Context) {}

    final class Coordinator: NSObject, UIDocumentPickerDelegate {
        let parent: DocumentPicker
        init(parent: DocumentPicker) { self.parent = parent }
        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            parent.onSelection(urls)
        }
        func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) { parent.onCancel() }
    }
}

@MainActor
final class ImportCoordinator: ObservableObject {
    @Published var pickerPresented = false
    @Published private(set) var pending = 0
    private let queue = DispatchQueue(label: "dev.leaf.reader.import", qos: .userInitiated)
    private let batchLimit = 16

    func presentPicker() {
        guard pending == 0 else { return }
        pickerPresented = true
    }

    func importFiles(_ urls: [URL]) {
        pickerPresented = false
        guard !urls.isEmpty else { return }
        guard pending + urls.count <= batchLimit else {
            ReaderRuntime.shared.reportError(message: "每批最多导入 16 本，请等待当前任务结束。")
            return
        }
        pending += urls.count
        for url in urls {
            // Obtain the scope while the document-picker callback is active.
            // asCopy URLs inside our container commonly return false, which is fine.
            let scoped = url.startAccessingSecurityScopedResource()
            queue.async { [weak self] in
                let result: Result<String, Error> = autoreleasepool {
                    defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                    return Result { try BookParser().parseFileToManifest(at: url) }
                }
                DispatchQueue.main.async {
                    switch result {
                    case .success(let json): ReaderRuntime.shared.importManifest(json: json)
                    case .failure(let error):
                        // Never send OS errors, archive paths, or book text to logs/UI.
                        let message = (error as? ImportFailure)?.errorDescription ?? "导入失败：文件结构异常或读取中断。"
                        ReaderRuntime.shared.reportError(message: message)
                    }
                    self?.pending -= 1
                }
            }
        }
    }
}
''',
    'iosApp/Sources/Host/LeafReaderApp.swift': r'''import SwiftUI
import UIKit
import Shared

@main
@MainActor
struct LeafReaderApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var importer = ImportCoordinator()

    var body: some Scene {
        WindowGroup {
            ReaderController(onImportRequested: { importer.presentPicker() })
                .ignoresSafeArea()
                .sheet(isPresented: $importer.pickerPresented) {
                    VStack(spacing: 0) {
                        Text("导入 TXT / EPUB · 仅正文\n图像、CSS 和固定版式暂不支持；不运行脚本。")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                            .padding()
                        DocumentPicker(onSelection: importer.importFiles, onCancel: { importer.pickerPresented = false })
                    }
                }
                .overlay(alignment: .bottom) {
                    if importer.pending > 0 {
                        HStack {
                            ProgressView()
                            Text("正在导入，剩余 \(importer.pending) 本")
                        }
                        .font(.footnote)
                        .padding(12)
                        .background(.regularMaterial, in: Capsule())
                        .padding(.bottom, 24)
                        .accessibilityElement(children: .combine)
                    }
                }
                .onOpenURL { importer.importFiles([$0]) }
        }
        .onChange(of: scenePhase) { phase in
            if phase != .active { ReaderRuntime.shared.flush() }
        }
    }
}

private struct ReaderController: UIViewControllerRepresentable {
    let onImportRequested: () -> Void

    func makeUIViewController(context: Context) -> UIViewController {
        MainViewControllerKt.MainViewController(onImportRequested: onImportRequested)
    }
    func updateUIViewController(_ controller: UIViewController, context: Context) {}
}
''',
    'iosApp/Sources/Parser/BookParser.swift': r'''import Foundation
import CryptoKit
import CoreFoundation

struct ImportedChapter: Codable, Equatable {
    let title: String
    let paragraphs: [String]
}

struct ImportedBook: Codable, Equatable {
    let id: String
    let title: String
    let author: String
    let format: String
    let chapters: [ImportedChapter]

    func validated() throws -> ImportedBook {
        let units = chapters.reduce(title.utf16.count + author.utf16.count) { total, chapter in
            total + chapter.title.utf16.count + chapter.paragraphs.reduce(0) { $0 + $1.utf16.count }
        }
        guard units <= 8 * 1_024 * 1_024 else { throw ImportFailure.oversized }
        return self
    }

    func json() throws -> String {
        _ = try validated()
        let data = try JSONEncoder().encode(self)
        guard let result = String(data: data, encoding: .utf8) else { throw ImportFailure.invalidText }
        return result
    }
}

// Legacy in-memory fixture limits. User-selected file imports instead use
// StreamingImportLimits and never cross the bridge with all chapter text.
enum ImportLimits {
    static let fileBytes = 32 * 1_024 * 1_024
    static let entryBytes = 8 * 1_024 * 1_024
    static let expandedBytes = 64 * 1_024 * 1_024
    static let textBytes = 12 * 1_024 * 1_024
    static let xmlBytes = 1 * 1_024 * 1_024
    static let entries = 4_096
    static let compressionRatio = 200
    static let paragraphUTF16 = 2_000
    static let paragraphs = 50_000
    static let chapters = 2_000
}

enum ImportFailure: Error, LocalizedError {
    case unsupported, unreadable, oversized, invalidText, empty, malformedEPUB
    case encrypted, unsafePath, archiveLimit, unsupportedLayout, complexMarkup

    var errorDescription: String? {
        switch self {
        case .unsupported: return "请选择 TXT 或 EPUB 文件。"
        case .unreadable: return "文件读取失败，请重新从文件 App 选择。"
        case .oversized: return "超过导入上限：TXT 512 MiB、EPUB 1 GiB、章节 50000、段落 2000000；单章正文分块保存。"
        case .invalidText: return "文本编码异常；支持 UTF-8、带 BOM 的 UTF-16 和 GB18030。"
        case .empty: return "文件中没有可阅读的正文。"
        case .malformedEPUB: return "EPUB 结构或校验异常，请检查文件是否完整。"
        case .encrypted: return "此 EPUB 含 DRM 或加密内容，暂不支持。"
        case .unsafePath: return "EPUB 含异常路径或重复条目。"
        case .archiveLimit: return "EPUB 超过解压限制，或使用暂未支持的 ZIP64／多卷格式。"
        case .unsupportedLayout: return "暂不支持固定版式或非文本 EPUB；图像和 CSS 不参与导入。"
        case .complexMarkup: return "EPUB 标记嵌套或节点数量超过导入限制。"
        }
    }
}

struct BookParser {
    // Legacy small-book adapter only. DocumentPicker uses parseFileToManifest.
    @available(*, deprecated, message: "Use parseFileToManifest for document imports")
    func parseFile(at url: URL) throws -> ImportedBook {
        guard url.isFileURL else { throw ImportFailure.unreadable }
        let ext = url.pathExtension.lowercased()
        guard ext == "txt" || ext == "epub" else { throw ImportFailure.unsupported }
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .fileSizeKey])
        guard values.isRegularFile == true else { throw ImportFailure.unreadable }
        if let size = values.fileSize, size > ImportLimits.fileBytes { throw ImportFailure.oversized }
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        var data = Data()
        while let chunk = try handle.read(upToCount: 64 * 1_024), !chunk.isEmpty {
            guard chunk.count <= ImportLimits.fileBytes - data.count else { throw ImportFailure.oversized }
            data.append(chunk)
        }
        return try parse(data: data, filename: url.lastPathComponent)
    }

    func parse(data: Data, filename: String) throws -> ImportedBook {
        guard data.count <= ImportLimits.fileBytes else { throw ImportFailure.oversized }
        guard !data.isEmpty else { throw ImportFailure.empty }
        let title = String((filename as NSString).deletingPathExtension.prefix(240))
        let id = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        switch (filename as NSString).pathExtension.lowercased() {
        case "txt":
            let text = try TextDecoding.decode(data, allowGB18030: true)
            guard text.utf8.count <= ImportLimits.textBytes else { throw ImportFailure.oversized }
            var builder = ChapterBuilder(defaultTitle: title.isEmpty ? "正文" : title)
            // enumerateLines does not allocate an array containing every line.
            var failure: Error?
            text.enumerateLines { line, stop in
                do {
                    if Self.isChapterHeading(line) {
                        try builder.startChapter(String(line.trimmingCharacters(in: .whitespaces).prefix(240)))
                    } else {
                        try builder.addParagraph(line)
                    }
                } catch { failure = error; stop = true }
            }
            if let failure { throw failure }
            let chapters = try builder.finish()
            return try ImportedBook(id: id, title: title, author: "", format: "TXT", chapters: chapters).validated()
        case "epub":
            return try EPUBParser().parse(data: data, id: id, fallbackTitle: title).validated()
        default: throw ImportFailure.unsupported
        }
    }

    private static func isChapterHeading(_ line: String) -> Bool {
        guard line.utf16.count <= 120 else { return false }
        return line.range(of: #"^\s*(第[零〇一二三四五六七八九十百千万两0-9０-９]+[章节卷部篇回集].*|[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+[0-9IVXivx]+(\s.*|[：:、.．].*|)|序章|序言|前言|楔子|尾声|后记)\s*$"#,
                          options: .regularExpression) != nil
    }
}

enum TextDecoding {
    static func decode(_ data: Data, allowGB18030: Bool) throws -> String {
        let prefix = [UInt8](data.prefix(4))
        // UTF-32 is intentionally not guessed as UTF-16.
        if prefix == [0xff, 0xfe, 0, 0] || prefix == [0, 0, 0xfe, 0xff] { throw ImportFailure.invalidText }
        let result: String?
        if prefix.starts(with: [0xef, 0xbb, 0xbf]) {
            result = String(data: data.dropFirst(3), encoding: .utf8)
        } else if prefix.starts(with: [0xff, 0xfe]) {
            result = String(data: data.dropFirst(2), encoding: .utf16LittleEndian)
        } else if prefix.starts(with: [0xfe, 0xff]) {
            result = String(data: data.dropFirst(2), encoding: .utf16BigEndian)
        } else if let utf8 = String(data: data, encoding: .utf8) {
            result = utf8
        } else if allowGB18030 {
            let cf = CFStringEncoding(CFStringEncodings.GB_18030_2000.rawValue)
            let encoding = String.Encoding(rawValue: CFStringConvertEncodingToNSStringEncoding(cf))
            result = String(data: data, encoding: encoding)
        } else {
            result = nil
        }
        guard let result, !result.unicodeScalars.contains(where: { $0.value == 0 }) else {
            throw ImportFailure.invalidText
        }
        return result
    }
}

struct ChapterBuilder {
    private var chapters: [ImportedChapter] = []
    private var title: String
    private var paragraphs: [String] = []
    private var paragraphCount = 0
    private var textBytes = 0
    private var explicitHeading = false

    init(defaultTitle: String) { title = String(defaultTitle.prefix(240)) }

    mutating func startChapter(_ newTitle: String) throws {
        // Preserve consecutive headings as empty chapters, not discarded text.
        if !paragraphs.isEmpty || explicitHeading { try flushChapter() }
        title = String(newTitle.prefix(240))
        explicitHeading = true
    }

    mutating func addParagraph(_ source: String) throws {
        var buffer = String.UnicodeScalarView()
        var units = 0
        // Scalar iteration also bounds pathological single grapheme clusters.
        for scalar in source.unicodeScalars {
            if [0x0a, 0x0d, 0x2028, 0x2029].contains(scalar.value) {
                try append(String(buffer))
                buffer = String.UnicodeScalarView()
                units = 0
                continue
            }
            if scalar.value < 0x20 && scalar != "\t" { continue }
            let cost = scalar.value > 0xffff ? 2 : 1
            if units + cost > ImportLimits.paragraphUTF16 {
                try append(String(buffer))
                buffer = String.UnicodeScalarView()
                units = 0
            }
            buffer.append(scalar)
            units += cost
        }
        try append(String(buffer))
    }

    private mutating func append(_ source: String) throws {
        let value = source.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return }
        guard paragraphCount < ImportLimits.paragraphs,
              value.utf8.count <= ImportLimits.textBytes - textBytes else { throw ImportFailure.oversized }
        paragraphCount += 1
        textBytes += value.utf8.count
        paragraphs.append(value)
    }

    private mutating func flushChapter() throws {
        guard chapters.count < ImportLimits.chapters else { throw ImportFailure.oversized }
        chapters.append(ImportedChapter(title: title.isEmpty ? "正文" : title, paragraphs: paragraphs))
        paragraphs = []
    }

    mutating func finish() throws -> [ImportedChapter] {
        if !paragraphs.isEmpty || explicitHeading { try flushChapter() }
        guard paragraphCount > 0 else { throw ImportFailure.empty }
        return chapters
    }
}
''',
    'iosApp/Sources/Parser/EPUBParser.swift': r'''import Foundation
import ZIPFoundation
import SwiftSoup

struct EPUBParser {
    // The in-memory API remains restricted to the original small test fixtures.
    func parse(data: Data, id: String, fallbackTitle: String) throws -> ImportedBook {
        let preflight = try ZIPPreflight(data: data)
        let archive = try Archive(data: data, accessMode: .read)
        var builder = ChapterBuilder(defaultTitle: fallbackTitle)
        let metadata = try parseArchive(archive, preflight: preflight, fallbackTitle: fallbackTitle,
                                        expandedLimit: ImportLimits.expandedBytes) { title, paragraphs in
            try builder.startChapter(title)
            for paragraph in paragraphs { try builder.addParagraph(paragraph) }
        }
        return ImportedBook(id: id, title: metadata.title, author: metadata.author,
                            format: "EPUB", chapters: try builder.finish())
    }

    func parseFile(at url: URL, writer: ChapterFileWriter) throws -> (title: String, author: String) {
        let preflight = try ZIPPreflight(fileURL: url)
        // Crucially this is the URL-backed initializer, not Archive(data:).
        let archive = try Archive(url: url, accessMode: .read)
        return try parseArchive(archive, preflight: preflight, fallbackTitle: url.deletingPathExtension().lastPathComponent,
                                expandedLimit: StreamingImportLimits.expandedBytes) { title, paragraphs in
            try writer.startChapter(title)
            for paragraph in paragraphs { try writer.addParagraph(paragraph) }
        }
    }

    private func parseArchive(_ archive: Archive, preflight: ZIPPreflight, fallbackTitle: String,
                              expandedLimit: Int,
                              emit: (String, [String]) throws -> Void) throws -> (title: String, author: String) {
        var entries: [String: Entry] = [:]
        for entry in archive {
            guard let checked = preflight.records[entry.path], entry.type != .symlink,
                  entry.uncompressedSize == UInt64(checked.uncompressedSize),
                  entry.compressedSize == UInt64(checked.compressedSize),
                  entry.checksum == checked.checksum,
                  (entry.type == .directory) == checked.isDirectory else { throw ImportFailure.malformedEPUB }
            entries[entry.path] = entry
        }
        guard entries.count == preflight.records.count else { throw ImportFailure.malformedEPUB }
        var reader = EntryReader(archive: archive, entries: entries, expandedLimit: expandedLimit)
        let mimetype = try reader.read("mimetype", limit: 64)
        guard String(data: mimetype, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) == "application/epub+zip" else {
            throw ImportFailure.malformedEPUB
        }
        let container = PackageXML(mode: .container)
        try container.parse(try reader.read("META-INF/container.xml", limit: ImportLimits.xmlBytes))
        guard let packageHref = container.rootfiles.first else { throw ImportFailure.malformedEPUB }
        let packagePath = try ArchivePath.resolve(packageHref)
        let package = PackageXML(mode: .package)
        try package.parse(try reader.read(packagePath, limit: ImportLimits.xmlBytes))
        guard !package.fixedLayout else { throw ImportFailure.unsupportedLayout }
        guard !package.spine.isEmpty else { throw ImportFailure.malformedEPUB }
        let title = package.bookTitle.isEmpty ? fallbackTitle : package.bookTitle
        var linear = package.spine.filter { $0.linear }
        // A book with only non-linear entries has no primary reading order.
        if linear.isEmpty { linear = package.spine }
        var seen = Set<String>()
        for reference in linear {
            guard let item = package.manifest[reference.id] else { throw ImportFailure.malformedEPUB }
            guard ["application/xhtml+xml", "text/html"].contains(item.mediaType) else {
                throw ImportFailure.unsupportedLayout
            }
            guard !reference.properties.contains("rendition:layout-pre-paginated") else { throw ImportFailure.unsupportedLayout }
            let path = try ArchivePath.resolve(item.href, relativeTo: packagePath)
            // Duplicate spine references otherwise inflate the output and repeat chapters.
            guard seen.insert(path).inserted else { throw ImportFailure.malformedEPUB }
            // Drain Foundation/SwiftSoup temporaries after EACH document, not
            // after the entire book. The one-document 8MiB ceiling is deliberate.
            try autoreleasepool {
                let chapterData = try reader.read(path, limit: StreamingImportLimits.xhtmlBytes)
                let markup = try TextDecoding.decode(chapterData, allowGB18030: false)
                // Validate depth/node budgets without resolving external DTDs.
                try PackageXML(mode: .content).parse(chapterData)
                let document = try SwiftSoup.parse(markup)
                try document.select("script,style,noscript,iframe,object,embed,svg,math,img,picture,audio,video,canvas,link,template").remove()
                guard let body = document.body() else { throw ImportFailure.empty }
                let heading = try body.select("h1,h2,h3").first()?.text() ?? ""
                let chapterTitle = heading.isEmpty ? "第 \(seen.count) 章" : boundedTitle(heading)
                let visitor = PlainTextVisitor()
                try body.traverse(visitor)
                try emit(chapterTitle, visitor.paragraphs)
            }
        }
        return (boundedTitle(title), package.author)
    }
}

private struct EntryReader {
    let archive: Archive
    let entries: [String: Entry]
    let expandedLimit: Int
    var consumed = 0

    mutating func read(_ path: String, limit: Int) throws -> Data {
        guard let entry = entries[path], entry.type == .file else { throw ImportFailure.malformedEPUB }
        guard entry.uncompressedSize <= UInt64(limit) else { throw ImportFailure.archiveLimit }
        var data = Data()
        var newConsumed = consumed
        let checksum = try archive.extract(entry, bufferSize: 16 * 1_024, skipCRC32: false) { chunk in
            guard chunk.count <= limit - data.count,
                  chunk.count <= expandedLimit - newConsumed else { throw ImportFailure.archiveLimit }
            newConsumed += chunk.count
            data.append(chunk)
        }
        consumed = newConsumed
        guard checksum == entry.checksum, data.count == Int(entry.uncompressedSize) else {
            throw ImportFailure.malformedEPUB
        }
        return data
    }
}

// An offline, bounded XML metadata reader. No filesystem or URL resolvers.
private final class PackageXML: NSObject, XMLParserDelegate {
    enum Mode { case container, package, content }
    struct ManifestItem { let href: String; let mediaType: String }
    struct SpineItem { let id: String; let linear: Bool; let properties: String }
    let mode: Mode
    var rootfiles: [String] = []
    var manifest: [String: ManifestItem] = [:]
    var spine: [SpineItem] = []
    var bookTitle = ""
    var author = ""
    var fixedLayout = false
    private var stack: [String] = []
    private var capture: String?
    private var captureText = ""
    private var captureDepth = 0
    private var metaProperty = ""
    private var failure: Error?
    private var nodes = 0
    private var root = ""

    init(mode: Mode) { self.mode = mode }

    func parse(_ data: Data) throws {
        let source = try TextDecoding.decode(data, allowGB18030: false)
        guard source.range(of: "<!ENTITY", options: .caseInsensitive) == nil,
              mode == .content || source.range(of: "<!DOCTYPE", options: .caseInsensitive) == nil else {
            throw ImportFailure.malformedEPUB
        }
        let xmlData = mode == .content ? try XHTMLNamedEntities.validationData(data, source: source) : data
        let parser = XMLParser(data: xmlData)
        parser.shouldProcessNamespaces = true
        parser.shouldResolveExternalEntities = false
        parser.externalEntityResolvingPolicy = .never
        parser.delegate = self
        let success = parser.parse()
        if let failure { throw failure }
        guard success, stack.isEmpty else { throw ImportFailure.malformedEPUB }
        if mode == .container && root != "container" { throw ImportFailure.malformedEPUB }
        if mode == .package && root != "package" { throw ImportFailure.malformedEPUB }
        if mode == .content && root != "html" { throw ImportFailure.malformedEPUB }
    }

    func parser(_ parser: XMLParser, didStartElement elementName: String, namespaceURI: String?,
                qualifiedName qName: String?, attributes: [String: String]) {
        nodes += 1
        guard stack.count < 128, nodes <= 100_000 else { fail(parser, ImportFailure.complexMarkup); return }
        let name = elementName.lowercased()
        if stack.isEmpty { root = name }
        stack.append(name)
        if mode == .container, name == "rootfile", attributes["media-type"] == "application/oebps-package+xml",
           let href = attributes["full-path"] { rootfiles.append(href) }
        guard mode == .package else { return }
        if name == "item", stack.dropLast().last == "manifest" {
            guard let id = attributes["id"], !id.isEmpty, manifest[id] == nil,
                  let href = attributes["href"], let media = attributes["media-type"] else {
                fail(parser, ImportFailure.malformedEPUB); return
            }
            manifest[id] = ManifestItem(href: href, mediaType: media)
        }
        if name == "itemref", stack.dropLast().last == "spine" {
            guard let id = attributes["idref"], spine.count < StreamingImportLimits.chapters else {
                fail(parser, ImportFailure.malformedEPUB); return
            }
            spine.append(SpineItem(id: id, linear: attributes["linear"]?.lowercased() != "no",
                                  properties: attributes["properties"] ?? ""))
        }
        if ["title", "creator", "meta"].contains(name), stack.dropLast().last == "metadata" {
            capture = name; captureText = ""; captureDepth = stack.count
            metaProperty = attributes["property"] ?? ""
            if attributes["name"] == "fixed-layout", attributes["content"] == "true" { fixedLayout = true }
        }
    }

    func parser(_ parser: XMLParser, foundCharacters string: String) {
        if capture != nil {
            guard captureText.utf16.count + string.utf16.count <= 4_096 else {
                fail(parser, ImportFailure.malformedEPUB); return
            }
            captureText += string
        }
    }

    func parser(_ parser: XMLParser, didEndElement elementName: String, namespaceURI: String?, qualifiedName qName: String?) {
        if let captured = capture, captureDepth == stack.count {
            let value = captureText.trimmingCharacters(in: .whitespacesAndNewlines)
            if captured == "title", bookTitle.isEmpty { bookTitle = String(value.prefix(240)) }
            if captured == "creator", author.isEmpty { author = String(value.prefix(240)) }
            if captured == "meta", metaProperty == "rendition:layout", value.lowercased() == "pre-paginated" {
                fixedLayout = true
            }
            capture = nil
        }
        if !stack.isEmpty { stack.removeLast() }
    }

    func parser(_ parser: XMLParser, foundCDATA CDATABlock: Data) {
        if let text = String(data: CDATABlock, encoding: .utf8) { self.parser(parser, foundCharacters: text) }
    }
    func parser(_ parser: XMLParser, resolveExternalEntityName name: String, systemID: String?) -> Data? { nil }
    func parser(_ parser: XMLParser, parseErrorOccurred parseError: Error) {
        if failure == nil { failure = ImportFailure.malformedEPUB }
    }
    func parser(_ parser: XMLParser, validationErrorOccurred validationError: Error) {
        if failure == nil { failure = ImportFailure.malformedEPUB }
    }
    func parser(_ parser: XMLParser, foundInternalEntityDeclarationWithName name: String, value: String?) {
        fail(parser, ImportFailure.malformedEPUB)
    }
    func parser(_ parser: XMLParser, foundExternalEntityDeclarationWithName name: String, publicID: String?, systemID: String?) {
        fail(parser, ImportFailure.malformedEPUB)
    }
    private func fail(_ parser: XMLParser, _ error: Error) { failure = error; parser.abortParsing() }
}

// EPUB2 frequently uses &nbsp; and other HTML names supplied by an external
// XHTML DTD. Resolve only SwiftSoup's built-in finite table to numeric XML
// references for validation; never load the DTD or accept custom entities.
// Rendering still parses the ORIGINAL markup, so escaped '<' stays text.
private enum XHTMLNamedEntities {
    static func validationData(_ original: Data, source: String) throws -> Data {
        let expression = try NSRegularExpression(pattern: "&([A-Za-z][A-Za-z0-9]{0,31});")
        let ns = source as NSString
        var output = ""
        var cursor = 0
        var count = 0
        var failure: Error?
        expression.enumerateMatches(in: source, range: NSRange(location: 0, length: ns.length)) { match, _, stop in
            guard let match else { return }
            count += 1
            guard count <= 100_000 else {
                failure = ImportFailure.complexMarkup; stop.pointee = true; return
            }
            output += ns.substring(with: NSRange(location: cursor, length: match.range.location - cursor))
            let name = ns.substring(with: match.range(at: 1))
            if ["amp", "lt", "gt", "quot", "apos"].contains(name) {
                output += ns.substring(with: match.range)
            } else if Entities.isNamedEntity(name), let scalars = Entities.codepointsForName(name), scalars.count <= 2 {
                for scalar in scalars { output += "&#x" + String(scalar.value, radix: 16) + ";" }
            } else {
                failure = ImportFailure.malformedEPUB; stop.pointee = true; return
            }
            guard output.utf8.count <= ImportLimits.entryBytes * 2 else {
                failure = ImportFailure.archiveLimit; stop.pointee = true; return
            }
            cursor = NSMaxRange(match.range)
        }
        if let failure { throw failure }
        output += ns.substring(from: cursor)
        guard output.utf8.count <= ImportLimits.entryBytes * 2 else { throw ImportFailure.archiveLimit }
        // Preserve BOM encoding so an existing XML encoding declaration agrees.
        if original.starts(with: [0xff, 0xfe]) {
            guard let encoded = output.data(using: .utf16LittleEndian) else { throw ImportFailure.invalidText }
            return Data([0xff, 0xfe]) + encoded
        }
        if original.starts(with: [0xfe, 0xff]) {
            guard let encoded = output.data(using: .utf16BigEndian) else { throw ImportFailure.invalidText }
            return Data([0xfe, 0xff]) + encoded
        }
        return Data(output.utf8)
    }
}

private final class PlainTextVisitor: NodeVisitor {
    private(set) var paragraphs: [String] = []
    private var current = ""
    private var textBytes = 0
    private var nodes = 0
    private static let blocks: Set<String> = ["p", "div", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "tr", "dt", "dd", "hr"]

    func head(_ node: Node, _ depth: Int) throws {
        nodes += 1
        guard depth <= 128, nodes <= 100_000 else { throw ImportFailure.complexMarkup }
        if let text = node as? TextNode {
            let whole = text.getWholeText()
            guard whole.utf8.count <= ImportLimits.textBytes - textBytes else { throw ImportFailure.oversized }
            textBytes += whole.utf8.count
            current += whole
        } else if let element = node as? Element {
            let tag = element.tagName().lowercased()
            if Self.blocks.contains(tag) || tag == "br" { try flush() }
            if tag == "td" || tag == "th" { current += " " }
        }
    }
    func tail(_ node: Node, _ depth: Int) throws {
        if let element = node as? Element,
           Self.blocks.contains(element.tagName().lowercased()) || depth == 0 { try flush() }
    }
    private func flush() throws {
        let value = current.trimmingCharacters(in: .whitespacesAndNewlines)
        if !value.isEmpty {
            guard paragraphs.count < ImportLimits.paragraphs else { throw ImportFailure.oversized }
            paragraphs.append(value)
        }
        current = ""
    }
}
''',
    'iosApp/Sources/Parser/STREAMING_IMPORT.md': r'''# Native file import (schema 2)

`DocumentPicker` uses `BookParser.parseFileToManifest(at:)`, then calls
`ReaderRuntime.shared.importManifest(json:)` on the main queue. The bridge carries
only the chapter index, never all chapter text. `parse(data:filename:)` and the
deprecated `parseFile(at:)` remain small-book/fixture compatibility APIs with their
original in-memory limits; they are not used for user-selected imports.

## Transaction and storage

- SHA256 is computed incrementally over original bytes, including any BOM.
- TXT: first bounded pass hashes and validates UTF-8 to select the encoding;
  second pass incrementally decodes and writes chapters. A second hash confirms
  that the source has not changed. No full decoded String is constructed.
- EPUB: hash, bounded file-based ZIP preflight, ZIPFoundation `Archive(url:)`,
  bounded extraction of each selected XHTML, then a final source hash check.
  Assets are not extracted. No archive-sized Data preflight is used.
- Chapters are atomically written under Application Support/LeafReader as
  `book-{sha256}-{lowercaseUUIDWithoutDashes}-c{index}.json`.
- Native code never writes the canonical manifest. Kotlin validates the completed
  index and publishes it together with the shelf entry.
- On native failure, only the exact chapter paths successfully written by this
  writer/revision are removed. Source files, earlier revisions and canonical
  manifests are left untouched. Kotlin validation failures and process death can
  leave unreferenced revision files; storage-layer cleanup owns that lifecycle.

## Limits and memory envelope

- Original TXT: 512 MiB; original EPUB: 1 GiB, inclusive.
- Byte reads: at most 64 KiB; incomplete decoder carry: at most 3 bytes.
- Paragraphs: at most 2000 UTF-16 units, split on Unicode scalar boundaries.
- Stored chapter text: at most 256 Ki UTF-16 units AND 512 KiB raw paragraph UTF-8.
  The byte target is **text**, not the physical JSON file: delimiters, escaped
  quotes/backslashes and many tiny paragraphs can make chapter JSON around
  1–1.25 MiB. The shared reader's 4 Mi-character JSON envelope covers that.
- Whole-book index: at most 50,000 chapters and 2,000,000 paragraphs. Counts are
  exact; characterCount excludes chapter titles and counts UTF-16 paragraph units.
- EPUB: 50,000 ZIP entries; per-entry expansion at most 64 MiB; aggregate declared
  expansion at most 2 GiB; compression ratio at most 200:1; central/local header
  metadata together at most 32 MiB. These also bound retained ZIPFoundation Entry
  extras/comments. Preflight reads an EOCD tail of at most 65,557 bytes and one
  bounded central/local header/name/extra field at a time.
- One XHTML at a time, at most 8 MiB uncompressed; metadata XML at most 1 MiB.
  SwiftSoup, validation markup and paragraphs are document-scoped, not book-scoped.
  Foundation temporaries are drained per byte chunk/document. One XHTML may
  produce multiple stored chapters; an XHTML larger than 8 MiB is rejected rather
  than parsed unboundedly.
- Existing per-document markup depth 128, node budget 100,000 and entity budget
  100,000 remain in force. Large indexes/metadata have a bounded but nonconstant
  cost within their explicit entry/chapter ceilings.

## Encoding and compatibility

UTF-8 (optional BOM), UTF-16 LE/BE with BOM, and GB18030 are supported for TXT.
Without a BOM, a full-file bounded UTF-8 validation pass precedes GB18030 fallback;
this handles a late non-UTF8 byte without guessing from only the first buffer.
GB18030 decoding uses Foundation's GB_18030_2000 converter on strictly framed
1/2/4-byte units. Invalid/unavailable conversions fail explicitly. Strict UTF-8
decoding rejects malformed sequences; a no-BOM file can instead be valid GB18030.
UTF-32, stray/truncated UTF-16 surrogates and incomplete final sequences in the
selected encoding are rejected. A UTF-8 BOM is authoritative and is not silently
reinterpreted as GB18030.

Long physical TXT lines are fragmented before a chapter buffer grows. Fragments
are never independently recognized as chapter headings. Consecutive actual short
headings remain empty chapters; books with no TOC/headings get bounded sequential
chapters. Paragraph normalization trims boundary whitespace and skips low control
characters, as the legacy parser does; it is not a byte-for-byte text exporter.

EPUB imports retain metadata/spine order and finite built-in named entities;
external DTD/entity resolution and remote resources are never loaded. Images,
CSS, script, audio/video, SVG and other non-text content are omitted. ZIP64,
multi-volume archives, encrypted/DRM entries, symlinks, unsafe/duplicate paths,
unsupported ZIP flags/methods, unsigned data descriptors, fixed layout, non-text
spines and non-XML HTML are outside this text importer. This is not full Legado
EPUB/rendering compatibility. Large asset-heavy EPUBs work subject to the limits
above; raising the original-file ceiling does not remove archive-bomb limits.

## Tests

`StreamingImportTests.swift` adds strict multibyte tests at every 1–7-byte chunk
size (UTF8/UTF16/GB18030), one-byte BOM/file reads, late GB fallback across the
64KiB boundary, file-size rejection with sparse fixtures, schema/id/revision and
atomic chapter publication checks, independent reimports, long-line heading
regression, failure rollback isolation, a generated >32MiB no-TOC TXT, a URL-backed
EPUB with a >32MiB unused asset and a split logical chapter, malformed stored-entry
size, CRC and bomb checks.
The existing BookParserTests fixtures remain supported.

These tests and Swift compilation have **not been run in the current Android /
Ubuntu session**: its shell/glob executors return ENOENT and no Xcode/Swift test
runner was available through the permitted tools. Source was statically reviewed;
run the ParserTests scheme on a macOS/Xcode runner before release. No claimed
512MiB/1GiB end-to-end device performance measurement has been made.
''',
    'iosApp/Sources/Parser/StreamingImport.swift': r'''import Foundation
import CryptoKit
import CoreFoundation

// File imports never use ImportedBook, all-book Data or all-book JSON.
// Only the current byte buffer, paragraph, chapter and the small index live here.
enum StreamingImportLimits {
    static let txtBytes = 512 * 1_024 * 1_024
    static let epubBytes = 1_024 * 1_024 * 1_024
    static let chunkBytes = 64 * 1_024
    static let chapterUTF16 = 256 * 1_024
    // Raw paragraph UTF-8 only, not JSON syntax/escaping. Encoded chapter JSON
    // can be larger (~1.25MiB for many tiny quoted paragraphs); core allows 4Mi.
    static let chapterBytes = 512 * 1_024
    static let chapterParagraphs = 2_000
    static let paragraphs = 2_000_000
    static let chapters = 50_000
    static let archiveEntries = 50_000
    static let archiveEntryBytes = 64 * 1_024 * 1_024
    static let archiveMetadataBytes = 32 * 1_024 * 1_024
    static let expandedBytes = 2 * 1_024 * 1_024 * 1_024
    static let xhtmlBytes = 8 * 1_024 * 1_024
}

struct ImportedChapterEntry: Codable, Equatable {
    let title: String
    let fileName: String
    let paragraphCount: Int
    let characterCount: Int
}

struct ImportedManifest: Codable, Equatable {
    let schema: Int
    let id: String
    let title: String
    let author: String
    let format: String
    let revision: String
    let chapters: [ImportedChapterEntry]
}

extension BookParser {
    // storageRoot/readSize are injectable for hostless parser tests only.
    // Production uses exactly the shared ReaderFiles Application Support root.
    func parseFileToManifest(at url: URL, storageRoot: URL? = nil,
                             readSize: Int = StreamingImportLimits.chunkBytes) throws -> String {
        guard url.isFileURL, readSize > 0, readSize <= StreamingImportLimits.chunkBytes else {
            throw ImportFailure.unreadable
        }
        let ext = url.pathExtension.lowercased()
        guard ext == "txt" || ext == "epub" else { throw ImportFailure.unsupported }
        let limit = ext == "txt" ? StreamingImportLimits.txtBytes : StreamingImportLimits.epubBytes
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .fileSizeKey])
        guard values.isRegularFile == true else { throw ImportFailure.unreadable }
        guard let size = values.fileSize, size > 0 else { throw ImportFailure.empty }
        guard size <= limit else { throw ImportFailure.oversized }
        let scan = try FileScan.scan(url, limit: limit, detectText: ext == "txt")
        let root: URL
        if let storageRoot { root = storageRoot } else {
            root = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                               appropriateFor: nil, create: true)
                .appendingPathComponent("LeafReader", isDirectory: true)
        }
        let fallback = boundedTitle((url.lastPathComponent as NSString).deletingPathExtension)
        let writer = try ChapterFileWriter(root: root, id: scan.id, defaultTitle: fallback)
        do {
            var title = fallback
            var author = ""
            if ext == "txt" {
                let handle = try FileHandle(forReadingFrom: url)
                defer { try? handle.close() }
                var decoder = IncrementalTextDecoder(encoding: scan.encoding)
                var hasher = SHA256()
                var total = 0
                var skip = scan.bomBytes
                while let bytes = try autoreleasepool(invoking: { try handle.read(upToCount: readSize) }), !bytes.isEmpty {
                    guard bytes.count <= limit - total else { throw ImportFailure.oversized }
                    total += bytes.count
                    hasher.update(data: bytes)
                    let removed = min(skip, bytes.count)
                    skip -= removed
                    try autoreleasepool {
                        try writer.consume(try decoder.decode(Data(bytes.dropFirst(removed))))
                    }
                }
                try writer.consume(try decoder.decode(Data(), final: true))
                guard total == scan.size, FileScan.hex(hasher.finalize()) == scan.id else {
                    throw ImportFailure.unreadable
                }
            } else {
                let metadata = try EPUBParser().parseFile(at: url, writer: writer)
                title = metadata.title
                author = metadata.author
                // Reject a provider changing the source during the transaction.
                let after = try FileScan.scan(url, limit: limit, detectText: false)
                guard after.id == scan.id, after.size == scan.size else { throw ImportFailure.unreadable }
            }
            return try writer.finish(title: title, author: author, format: ext.uppercased())
        } catch {
            writer.rollback()
            throw error
        }
    }
}

private struct FileScan {
    let id: String
    let size: Int
    let encoding: IncrementalTextDecoder.Encoding
    let bomBytes: Int

    static func hex(_ digest: SHA256.Digest) -> String {
        digest.map { String(format: "%02x", $0) }.joined()
    }

    static func scan(_ url: URL, limit: Int, detectText: Bool) throws -> FileScan {
        let file = try FileHandle(forReadingFrom: url)
        defer { try? file.close() }
        var hash = SHA256()
        var size = 0
        var encoding = IncrementalTextDecoder.Encoding.utf8
        var bom = 0
        if detectText {
            // FileHandle may return a short read even before EOF. Sniff a full
            // four-byte prefix (or EOF) without assuming the first read fills.
            var prefix = Data()
            while prefix.count < 4 {
                guard let bytes = try file.read(upToCount: 4 - prefix.count), !bytes.isEmpty else { break }
                prefix.append(bytes)
            }
            if prefix == Data([0xff, 0xfe, 0, 0]) || prefix == Data([0, 0, 0xfe, 0xff]) {
                throw ImportFailure.invalidText
            }
            if prefix.starts(with: [0xef, 0xbb, 0xbf]) { bom = 3 }
            if prefix.starts(with: [0xff, 0xfe]) { encoding = .utf16LE; bom = 2 }
            if prefix.starts(with: [0xfe, 0xff]) { encoding = .utf16BE; bom = 2 }
            try file.seek(toOffset: 0)
        }
        var skip = bom
        var utf8Valid = true
        var validator = IncrementalTextDecoder(encoding: .utf8)
        while let bytes = try autoreleasepool(invoking: { try file.read(upToCount: StreamingImportLimits.chunkBytes) }), !bytes.isEmpty {
            guard bytes.count <= limit - size else { throw ImportFailure.oversized }
            hash.update(data: bytes)
            if detectText, encoding == .utf8, utf8Valid {
                let removed = min(skip, bytes.count)
                skip -= removed
                do {
                    try autoreleasepool { _ = try validator.decode(Data(bytes.dropFirst(removed))) }
                } catch { utf8Valid = false }
            }
            size += bytes.count
        }
        guard size > 0 else { throw ImportFailure.empty }
        if detectText, encoding == .utf8, utf8Valid {
            do { _ = try validator.decode(Data(), final: true) } catch { utf8Valid = false }
        }
        if detectText, encoding == .utf8, !utf8Valid {
            // A UTF-8 BOM is a declaration, not an encoding guess.
            guard bom == 0 else { throw ImportFailure.invalidText }
            encoding = .gb18030
        }
        return FileScan(id: hex(hash.finalize()), size: size, encoding: encoding, bomBytes: bom)
    }
}

// Strict unit framing retains at most three incomplete bytes between calls.
// Foundation decodes only complete, bounded runs, including GB18030 four-byte
// sequences. No replacement characters, byte loss or split UTF-16 surrogates.
struct IncrementalTextDecoder {
    enum Encoding { case utf8, utf16LE, utf16BE, gb18030 }
    let encoding: Encoding
    private var carry: [UInt8] = []

    init(encoding: Encoding) { self.encoding = encoding }

    mutating func decode(_ data: Data, final: Bool = false) throws -> String {
        var bytes = carry
        bytes.append(contentsOf: data)
        var index = 0
        scanUnits: while index < bytes.count {
            let first = bytes[index]
            let length: Int
            switch encoding {
            case .utf8:
                if first <= 0x7f { length = 1 }
                else if (0xc2...0xdf).contains(first) { length = 2 }
                else if (0xe0...0xef).contains(first) { length = 3 }
                else if (0xf0...0xf4).contains(first) { length = 4 }
                else { throw ImportFailure.invalidText }
                if bytes.count - index >= length {
                    for offset in 1..<length where !(0x80...0xbf).contains(bytes[index + offset]) {
                        throw ImportFailure.invalidText
                    }
                    if length >= 3 {
                        let second = bytes[index + 1]
                        if first == 0xe0 && second < 0xa0 || first == 0xed && second >= 0xa0 ||
                            first == 0xf0 && second < 0x90 || first == 0xf4 && second >= 0x90 {
                            throw ImportFailure.invalidText
                        }
                    }
                }
            case .utf16LE, .utf16BE:
                guard bytes.count - index >= 2 else { break scanUnits }
                let unit = utf16Unit(bytes, index)
                if (0xd800...0xdbff).contains(unit) {
                    length = 4
                    if bytes.count - index >= 4, !(0xdc00...0xdfff).contains(utf16Unit(bytes, index + 2)) {
                        throw ImportFailure.invalidText
                    }
                } else {
                    guard !(0xdc00...0xdfff).contains(unit) else { throw ImportFailure.invalidText }
                    length = 2
                }
            case .gb18030:
                if first <= 0x7f { length = 1 } else {
                    guard (0x81...0xfe).contains(first) else { throw ImportFailure.invalidText }
                    guard bytes.count - index >= 2 else { break scanUnits }
                    let second = bytes[index + 1]
                    if (0x30...0x39).contains(second) {
                        length = 4
                        if bytes.count - index >= 4 {
                            guard (0x81...0xfe).contains(bytes[index + 2]),
                                  (0x30...0x39).contains(bytes[index + 3]) else { throw ImportFailure.invalidText }
                        }
                    } else {
                        guard (0x40...0xfe).contains(second), second != 0x7f else { throw ImportFailure.invalidText }
                        length = 2
                    }
                }
            }
            if bytes.count - index < length { break }
            index += length
        }
        carry = Array(bytes[index...])
        guard carry.count <= 3, !final || carry.isEmpty else { throw ImportFailure.invalidText }
        guard index > 0 else { return "" }
        let stringEncoding: String.Encoding
        switch encoding {
        case .utf8: stringEncoding = .utf8
        case .utf16LE: stringEncoding = .utf16LittleEndian
        case .utf16BE: stringEncoding = .utf16BigEndian
        case .gb18030:
            stringEncoding = String.Encoding(rawValue: CFStringConvertEncodingToNSStringEncoding(
                CFStringEncoding(CFStringEncodings.GB_18030_2000.rawValue)))
        }
        guard let result = String(data: Data(bytes[..<index]), encoding: stringEncoding),
              !result.unicodeScalars.contains(where: { $0.value == 0 }) else { throw ImportFailure.invalidText }
        return result
    }

    private func utf16Unit(_ bytes: [UInt8], _ index: Int) -> UInt16 {
        if encoding == .utf16LE { return UInt16(bytes[index]) | UInt16(bytes[index + 1]) << 8 }
        return UInt16(bytes[index]) << 8 | UInt16(bytes[index + 1])
    }
}

func boundedTitle(_ source: String) -> String {
    var result = String.UnicodeScalarView()
    var units = 0
    for scalar in source.unicodeScalars {
        let cost = scalar.value > 0xffff ? 2 : 1
        if units + cost > 240 { break }
        result.append(scalar)
        units += cost
    }
    let title = String(result).trimmingCharacters(in: .whitespacesAndNewlines)
    return title.isEmpty ? "正文" : title
}

final class ChapterFileWriter {
    private let root: URL
    private let id: String
    private let revision = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    private var entries: [ImportedChapterEntry] = []
    private var published: [URL] = []
    private var title: String
    private var paragraphs: [String] = []
    private var chapterUnits = 0
    private var chapterBytes = 0
    private var paragraphTotal = 0
    private var explicitHeading = false
    private var part = 1
    private var line = String.UnicodeScalarView()
    private var lineUnits = 0
    private var continuedLine = false
    private var previousCR = false

    init(root: URL, id: String, defaultTitle: String) throws {
        self.root = root
        self.id = id
        title = boundedTitle(defaultTitle)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    }

    func startChapter(_ heading: String) throws {
        try flushLine()
        if !paragraphs.isEmpty || explicitHeading { try flushChapter() }
        title = boundedTitle(heading)
        part = 1
        explicitHeading = true
    }

    func consume(_ text: String) throws {
        for scalar in text.unicodeScalars {
            if scalar.value == 0x0a, previousCR { previousCR = false; continue }
            previousCR = scalar.value == 0x0d
            if [0x0a, 0x0d, 0x2028, 0x2029].contains(scalar.value) {
                try flushLine()
                continuedLine = false
                continue
            }
            if scalar.value < 0x20 && scalar != "\t" { continue }
            let cost = scalar.value > 0xffff ? 2 : 1
            if lineUnits + cost > ImportLimits.paragraphUTF16 {
                // This is a fragment of a longer physical line, never a heading.
                continuedLine = true
                try flushLine()
            }
            line.append(scalar)
            lineUnits += cost
        }
    }

    // EPUB block boundaries are intentional paragraphs, not TXT headings.
    func addParagraph(_ text: String) throws {
        var buffer = String.UnicodeScalarView()
        var units = 0
        for scalar in text.unicodeScalars {
            if [0x0a, 0x0d, 0x2028, 0x2029].contains(scalar.value) {
                try appendParagraph(String(buffer)); buffer = String.UnicodeScalarView(); units = 0
                continue
            }
            if scalar.value < 0x20 && scalar != "\t" { continue }
            let cost = scalar.value > 0xffff ? 2 : 1
            if units + cost > ImportLimits.paragraphUTF16 {
                try appendParagraph(String(buffer)); buffer = String.UnicodeScalarView(); units = 0
            }
            buffer.append(scalar)
            units += cost
        }
        try appendParagraph(String(buffer))
    }

    private func flushLine() throws {
        let sourceUnits = lineUnits
        let value = String(line).trimmingCharacters(in: .whitespacesAndNewlines)
        line = String.UnicodeScalarView()
        lineUnits = 0
        if !continuedLine, sourceUnits <= 120,
           value.range(of: #"^\s*(第[零〇一二三四五六七八九十百千万两0-9０-９]+[章节卷部篇回集].*|[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+[0-9IVXivx]+(\s.*|[：:、.．].*|)|序章|序言|前言|楔子|尾声|后记)\s*$"#,
                       options: .regularExpression) != nil {
            // The line buffer is already empty; no recursive reprocessing.
            try startChapter(value)
        } else { try appendParagraph(value) }
    }

    private func appendParagraph(_ source: String) throws {
        let value = source.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return }
        let units = value.utf16.count
        let bytes = value.utf8.count
        guard paragraphTotal < StreamingImportLimits.paragraphs,
              units <= ImportLimits.paragraphUTF16 else { throw ImportFailure.oversized }
        if paragraphs.count >= StreamingImportLimits.chapterParagraphs ||
            chapterUnits + units > StreamingImportLimits.chapterUTF16 ||
            chapterBytes + bytes > StreamingImportLimits.chapterBytes {
            try flushChapter()
            part += 1
        }
        paragraphs.append(value)
        chapterUnits += units
        chapterBytes += bytes
        paragraphTotal += 1
    }

    private func flushChapter() throws {
        guard entries.count < StreamingImportLimits.chapters else { throw ImportFailure.oversized }
        let chapterTitle = part == 1 ? title : boundedTitle("\(title) · \(part)")
        let name = "book-\(id)-\(revision)-c\(entries.count).json"
        let path = root.appendingPathComponent(name, isDirectory: false)
        let chapter = ImportedChapter(title: chapterTitle, paragraphs: paragraphs)
        // JSONEncoder only sees one bounded chapter, never the complete book.
        try JSONEncoder().encode(chapter).write(to: path, options: .atomic)
        published.append(path)
        entries.append(ImportedChapterEntry(title: chapterTitle, fileName: name,
                                            paragraphCount: paragraphs.count, characterCount: chapterUnits))
        paragraphs = []
        chapterUnits = 0
        chapterBytes = 0
    }

    func finish(title: String, author: String, format: String) throws -> String {
        try flushLine()
        if !paragraphs.isEmpty || explicitHeading { try flushChapter() }
        guard paragraphTotal > 0 else { throw ImportFailure.empty }
        let manifest = ImportedManifest(schema: 2, id: id, title: boundedTitle(title),
                                        author: author.isEmpty ? "" : boundedTitle(author), format: format,
                                        revision: revision, chapters: entries)
        let data = try JSONEncoder().encode(manifest)
        guard let json = String(data: data, encoding: .utf8) else { throw ImportFailure.invalidText }
        // Canonical manifest and shelf publication belong exclusively to Kotlin.
        return json
    }

    func rollback() {
        // Only paths created by this exact id/revision transaction are touched.
        for path in published { try? FileManager.default.removeItem(at: path) }
        published = []
    }
}
''',
    'iosApp/Sources/Parser/ZIPPreflight.swift': r'''import Foundation

// ZIPFoundation hides encrypted entries during iteration. Inspect every central
// and local header first. File imports read only the EOCD tail and one bounded
// header/extra field at a time; compressed payloads are never loaded here.
// Narrow ZIP32 only: reject ZIP64, multi-volume and unsigned descriptors.
struct ZIPPreflight {
    struct Record {
        let path: String
        let compressedSize: Int
        let uncompressedSize: Int
        let checksum: UInt32
        let isDirectory: Bool
    }
    let records: [String: Record]

    init(data: Data) throws {
        try self.init(size: data.count, fileLimit: ImportLimits.fileBytes,
                      entryLimit: ImportLimits.entryBytes, expandedLimit: ImportLimits.expandedBytes,
                      entryCountLimit: ImportLimits.entries) { offset, length in
            guard offset >= 0, length >= 0, offset <= data.count, length <= data.count - offset else {
                throw ImportFailure.malformedEPUB
            }
            return data.subdata(in: offset..<offset + length)
        }
    }

    init(fileURL: URL) throws {
        let file = try FileHandle(forReadingFrom: fileURL)
        defer { try? file.close() }
        let length = try file.seekToEnd()
        guard length <= UInt64(StreamingImportLimits.epubBytes) else { throw ImportFailure.oversized }
        try self.init(size: Int(length), fileLimit: StreamingImportLimits.epubBytes,
                      entryLimit: StreamingImportLimits.archiveEntryBytes,
                      expandedLimit: StreamingImportLimits.expandedBytes,
                      entryCountLimit: StreamingImportLimits.archiveEntries) { offset, count in
            guard offset >= 0, count >= 0, offset <= Int(length), count <= Int(length) - offset else {
                throw ImportFailure.malformedEPUB
            }
            try file.seek(toOffset: UInt64(offset))
            var result = Data()
            while result.count < count {
                guard let bytes = try autoreleasepool(invoking: { try file.read(upToCount: count - result.count) }), !bytes.isEmpty else {
                    throw ImportFailure.malformedEPUB
                }
                result.append(bytes)
            }
            return result
        }
    }

    private init(size: Int, fileLimit: Int, entryLimit: Int, expandedLimit: Int,
                 entryCountLimit: Int, read: (Int, Int) throws -> Data) throws {
        guard size >= 22, size <= fileLimit else { throw ImportFailure.malformedEPUB }
        let tailOffset = max(0, size - 22 - 65_535)
        let tail = try read(tailOffset, size - tailOffset)
        var found: Int?
        for offset in stride(from: tail.count - 22, through: 0, by: -1) {
            if try tail.zipU32(offset) == 0x06054b50,
               offset + 22 + Int(try tail.zipU16(offset + 20)) == tail.count {
                found = offset; break
            }
        }
        guard let endInTail = found else { throw ImportFailure.malformedEPUB }
        let end = tailOffset + endInTail
        let disk = try tail.zipU16(endInTail + 4)
        let directoryDisk = try tail.zipU16(endInTail + 6)
        let diskEntries = Int(try tail.zipU16(endInTail + 8))
        let count = Int(try tail.zipU16(endInTail + 10))
        let directorySize = Int(try tail.zipU32(endInTail + 12))
        let directoryOffset = Int(try tail.zipU32(endInTail + 16))
        guard disk == 0, directoryDisk == 0, diskEntries == count,
              count > 0, count <= entryCountLimit, count != 65_535,
              directoryOffset <= end, directorySize == end - directoryOffset,
              directorySize <= StreamingImportLimits.archiveMetadataBytes else {
            throw ImportFailure.archiveLimit
        }
        var cursor = directoryOffset
        var expandedTotal = 0
        var metadataBytes = 0
        var result: [String: Record] = [:]
        var ranges: [Range<Int>] = []
        for _ in 0..<count {
            guard cursor <= end - 46 else { throw ImportFailure.malformedEPUB }
            let central = try read(cursor, 46)
            guard try central.zipU32(0) == 0x02014b50 else { throw ImportFailure.malformedEPUB }
            let needed = try central.zipU16(6)
            let flags = try central.zipU16(8)
            let method = try central.zipU16(10)
            let crc = try central.zipU32(16)
            let compressed = Int(try central.zipU32(20))
            let uncompressed = Int(try central.zipU32(24))
            let nameSize = Int(try central.zipU16(28))
            let extraSize = Int(try central.zipU16(30))
            let commentSize = Int(try central.zipU16(32))
            let startDisk = try central.zipU16(34)
            let attributes = try central.zipU32(38)
            let localOffset = Int(try central.zipU32(42))
            guard flags & 0x2041 == 0 else { throw ImportFailure.encrypted }
            guard needed < 45, startDisk == 0, method == 0 || method == 8,
                  flags & ~UInt16(0x080e) == 0, method != 0 || compressed == uncompressed,
                  compressed <= fileLimit, uncompressed <= entryLimit,
                  uncompressed <= expandedLimit - expandedTotal,
                  uncompressed <= max(compressed, 1) * ImportLimits.compressionRatio else {
                throw ImportFailure.archiveLimit
            }
            let next = cursor + 46 + nameSize + extraSize + commentSize
            guard nameSize > 0, nameSize <= 1_024, next <= end else { throw ImportFailure.malformedEPUB }
            let nameData = try read(cursor + 46, nameSize)
            guard let path = String(data: nameData, encoding: .utf8) else { throw ImportFailure.unsafePath }
            try ArchivePath.validateEntry(path)
            guard result[path] == nil else { throw ImportFailure.unsafePath }
            let mode = (attributes >> 16) & 0xf000
            guard mode == 0 || mode == 0x8000 || mode == 0x4000 else { throw ImportFailure.unsafePath }
            try Self.validateExtra(try read(cursor + 46 + nameSize, extraSize))
            guard localOffset <= directoryOffset - 30 else { throw ImportFailure.malformedEPUB }
            let local = try read(localOffset, 30)
            guard try local.zipU32(0) == 0x04034b50 else { throw ImportFailure.malformedEPUB }
            let localFlags = try local.zipU16(6)
            guard localFlags & 0x2041 == 0 else { throw ImportFailure.encrypted }
            let localNameSize = Int(try local.zipU16(26))
            let localExtraSize = Int(try local.zipU16(28))
            let contentOffset = localOffset + 30 + localNameSize + localExtraSize
            metadataBytes += 46 + nameSize + extraSize + commentSize + 30 + localNameSize + localExtraSize
            // Entry retains central/local extras. Bound their aggregate as well
            // as individual reads, before ZIPFoundation constructs those objects.
            guard metadataBytes <= StreamingImportLimits.archiveMetadataBytes else { throw ImportFailure.archiveLimit }
            guard localFlags == flags, try local.zipU16(8) == method, try local.zipU16(4) < 45,
                  localNameSize == nameSize, contentOffset <= directoryOffset,
                  compressed <= directoryOffset - contentOffset else { throw ImportFailure.malformedEPUB }
            guard try read(localOffset + 30, localNameSize) == nameData else { throw ImportFailure.malformedEPUB }
            try Self.validateExtra(try read(localOffset + 30 + localNameSize, localExtraSize))
            var contentEnd = contentOffset + compressed
            if flags & 8 != 0 {
                guard contentEnd <= directoryOffset - 16 else { throw ImportFailure.malformedEPUB }
                let descriptor = try read(contentEnd, 16)
                guard try descriptor.zipU32(0) == 0x08074b50, try descriptor.zipU32(4) == crc,
                      Int(try descriptor.zipU32(8)) == compressed,
                      Int(try descriptor.zipU32(12)) == uncompressed else { throw ImportFailure.malformedEPUB }
                contentEnd += 16
            } else {
                guard try local.zipU32(14) == crc, Int(try local.zipU32(18)) == compressed,
                      Int(try local.zipU32(22)) == uncompressed else { throw ImportFailure.malformedEPUB }
            }
            ranges.append(localOffset..<contentEnd)
            expandedTotal += uncompressed
            result[path] = Record(path: path, compressedSize: compressed, uncompressedSize: uncompressed,
                                  checksum: crc, isDirectory: path.hasSuffix("/"))
            cursor = next
        }
        guard cursor == end else { throw ImportFailure.malformedEPUB }
        let sorted = ranges.sorted { $0.lowerBound < $1.lowerBound }
        for index in 1..<sorted.count where sorted[index - 1].upperBound > sorted[index].lowerBound {
            throw ImportFailure.malformedEPUB
        }
        if result.keys.contains(where: {
            ["meta-inf/encryption.xml", "meta-inf/rights.xml", "meta-inf/license.lcpl"].contains($0.lowercased())
        }) { throw ImportFailure.encrypted }
        records = result
    }

    private static func validateExtra(_ data: Data) throws {
        var offset = 0
        while offset < data.count {
            guard offset <= data.count - 4 else { throw ImportFailure.malformedEPUB }
            let kind = try data.zipU16(offset)
            let size = Int(try data.zipU16(offset + 2))
            guard kind != 0x0001 else { throw ImportFailure.archiveLimit }
            guard kind != 0x9901 else { throw ImportFailure.encrypted }
            offset += 4 + size
            guard offset <= data.count else { throw ImportFailure.malformedEPUB }
        }
    }
}

enum ArchivePath {
    static func validateEntry(_ path: String) throws {
        guard !path.isEmpty, !path.hasPrefix("/"), !path.contains("\\"), !path.contains(":"),
              !path.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else {
            throw ImportFailure.unsafePath
        }
        let body = path.hasSuffix("/") ? String(path.dropLast()) : path
        let parts = body.split(separator: "/", omittingEmptySubsequences: false)
        guard !parts.contains(where: { $0.isEmpty || $0 == "." || $0 == ".." }) else { throw ImportFailure.unsafePath }
        if let decoded = path.removingPercentEncoding, decoded != path {
            guard !decoded.contains("\\"), !decoded.contains(":"),
                  decoded.split(separator: "/", omittingEmptySubsequences: false).count == path.split(separator: "/", omittingEmptySubsequences: false).count,
                  !decoded.split(separator: "/").contains(where: { $0 == "." || $0 == ".." }),
                  !decoded.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else {
                throw ImportFailure.unsafePath
            }
        }
    }

    static func resolve(_ href: String, relativeTo file: String = "") throws -> String {
        let reference = String(href.prefix { $0 != "#" && $0 != "?" })
        guard let decoded = reference.removingPercentEncoding, !decoded.isEmpty,
              !decoded.hasPrefix("/"), !decoded.contains("\\"), !decoded.contains(":"),
              !decoded.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else {
            throw ImportFailure.unsafePath
        }
        var parts = file.split(separator: "/").dropLast().map(String.init)
        for part in decoded.split(separator: "/", omittingEmptySubsequences: false) {
            if part == ".." {
                guard !parts.isEmpty else { throw ImportFailure.unsafePath }
                parts.removeLast()
            } else if part != "." {
                guard !part.isEmpty else { throw ImportFailure.unsafePath }
                parts.append(String(part))
            }
        }
        let path = parts.joined(separator: "/")
        try validateEntry(path)
        return path
    }
}

private extension Data {
    func zipU16(_ offset: Int) throws -> UInt16 {
        guard offset >= 0, offset <= count - 2 else { throw ImportFailure.malformedEPUB }
        return UInt16(self[offset]) | (UInt16(self[offset + 1]) << 8)
    }
    func zipU32(_ offset: Int) throws -> UInt32 {
        guard offset >= 0, offset <= count - 4 else { throw ImportFailure.malformedEPUB }
        return UInt32(self[offset]) | (UInt32(self[offset + 1]) << 8)
            | (UInt32(self[offset + 2]) << 16) | (UInt32(self[offset + 3]) << 24)
    }
}
''',
    'iosApp/Tests/BookParserTests.swift': r'''import XCTest
import Foundation
import ZIPFoundation

final class BookParserTests: XCTestCase {
    private let parser = BookParser()

    func testOriginalByteSHA256AndJSONContract() throws {
        let book = try parser.parse(data: Data("abc".utf8), filename: "Example.TXT")
        XCTAssertEqual(book.id, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        XCTAssertEqual(book.title, "Example")
        XCTAssertEqual(book.format, "TXT")
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(book.json().utf8)) as? [String: Any])
        XCTAssertEqual(Set(object.keys), Set(["id", "title", "author", "format", "chapters"]))
        XCTAssertEqual(book.chapters[0].paragraphs, ["abc"])
    }

    func testBOMAwareDecodingAndGB18030() throws {
        let expected = "中文正文"
        let variants: [Data] = [
            Data([0xef, 0xbb, 0xbf]) + Data(expected.utf8),
            Data([0xff, 0xfe]) + expected.data(using: .utf16LittleEndian)!,
            Data([0xfe, 0xff]) + expected.data(using: .utf16BigEndian)!,
            Data([0xd6, 0xd0, 0xce, 0xc4, 0xd5, 0xfd, 0xce, 0xc4])
        ]
        for bytes in variants {
            XCTAssertEqual(try parser.parse(data: bytes, filename: "编码.txt").chapters[0].paragraphs, [expected])
        }
        XCTAssertNotEqual(try parser.parse(data: variants[0], filename: "a.txt").id,
                          try parser.parse(data: Data(expected.utf8), filename: "a.txt").id)
    }

    func testLongLinesAndSingleGraphemeAreBoundedWithoutTextLoss() throws {
        for source in [String(repeating: "文", count: 10_001), "a" + String(repeating: "\u{0301}", count: 10_001)] {
            let book = try parser.parse(data: Data(source.utf8), filename: "long.txt")
            let paragraphs = book.chapters.flatMap(\.paragraphs)
            XCTAssertTrue(paragraphs.allSatisfy { $0.utf16.count <= ImportLimits.paragraphUTF16 })
            XCTAssertEqual(paragraphs.joined(), source)
        }
    }

    func testChapterSplittingPreservesConsecutiveHeadings() throws {
        let source = "序言\n第一章开始\n正文一\r\n\r\nChapter 2 End\n正文二"
        let book = try parser.parse(data: Data(source.utf8), filename: "chapters.txt")
        XCTAssertEqual(book.chapters.map(\.title), ["序言", "第一章开始", "Chapter 2 End"])
        XCTAssertEqual(book.chapters.map(\.paragraphs), [[], ["正文一"], ["正文二"]])
    }

    func testEmptyBinaryUTF32AndOversizedTextAreRejected() {
        for bytes in [Data(), Data([0, 1, 2]), Data([0xff, 0xfe, 0, 0, 65, 0, 0, 0]), Data(" \n\t".utf8)] {
            XCTAssertThrowsError(try parser.parse(data: bytes, filename: "bad.txt"))
        }
        XCTAssertThrowsError(try parser.parse(data: Data(repeating: 65, count: ImportLimits.fileBytes + 1), filename: "big.txt"))
        XCTAssertThrowsError(try parser.parse(data: Data(repeating: 65, count: 8 * 1_024 * 1_024 + 1), filename: "big.txt"))
    }

    func testEPUBMetadataSpineOrderNonLinearAndNoActiveContent() throws {
        let book = try parser.parse(data: EPUBFixture.book(), filename: "fallback.epub")
        XCTAssertEqual(book.title, "原创示例")
        XCTAssertEqual(book.author, "测试作者")
        XCTAssertEqual(book.format, "EPUB")
        XCTAssertEqual(book.chapters.map(\.title), ["第二章", "第一章"])
        let text = book.chapters.flatMap(\.paragraphs).joined(separator: " ")
        XCTAssertTrue(text.contains("第二章乙正文"))
        XCTAssertTrue(text.contains("甲正文 inline"))
        XCTAssertFalse(text.contains("SCRIPT_SENTINEL"))
        XCTAssertFalse(text.contains("STYLE_SENTINEL"))
        XCTAssertFalse(text.contains("NONLINEAR_SENTINEL"))
        XCTAssertFalse(text.contains("IMAGE_SENTINEL"))
    }

    func testDeflatedArchiveUsesSameTextAndSpine() throws {
        let source = try Archive(data: EPUBFixture.book(), accessMode: .read)
        let compressed = try Archive(data: Data(), accessMode: .create)
        for entry in source {
            var bytes = Data()
            _ = try source.extract(entry) { bytes.append($0) }
            try compressed.addEntry(with: entry.path, type: .file, uncompressedSize: Int64(bytes.count),
                                    compressionMethod: entry.path == "mimetype" ? .none : .deflate) { offset, size in
                let start = Int(offset)
                return bytes.subdata(in: start..<min(bytes.count, start + size))
            }
        }
        let book = try parser.parse(data: XCTUnwrap(compressed.data), filename: "compressed.epub")
        XCTAssertEqual(book.chapters.map(\.title), ["第二章", "第一章"])
    }

    func testSignedZIP32DataDescriptor() throws {
        let data = EPUBFixture.book(extra: [.init("unused.txt", bytes: Data("plain".utf8), flags: 8)])
        XCTAssertEqual(try parser.parse(data: data, filename: "descriptor.epub").title, "原创示例")
    }

    func testArchiveEncryptionDRMTraversalDuplicatesAndSymlinksAreRejected() {
        let cases: [[ZIPFixture.Item]] = [
            [.init("unused.bin", bytes: Data([1]), flags: 1)],
            [.init("META-INF/encryption.xml", text: "<encryption/>")],
            [.init("META-INF/rights.xml", text: "rights")],
            [.init("../escape.txt", text: "no")],
            [.init("/absolute.txt", text: "no")],
            [.init("a\\escape.txt", text: "no")],
            [.init("%2e%2e/escape.txt", text: "no")],
            [.init("mimetype", text: "duplicate")],
            [.init("link", text: "target", unixMode: 0xa000)]
        ]
        for extra in cases {
            XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(extra: extra), filename: "bad.epub"))
        }
    }

    func testBadCRCAndTruncatedArchiveAreRejected() {
        var bytes = EPUBFixture.book()
        // First entry's data follows its 30-byte local header and UTF-8 name.
        bytes[30 + "mimetype".utf8.count] ^= 1
        XCTAssertThrowsError(try parser.parse(data: bytes, filename: "bad.epub"))
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book().dropLast(10), filename: "bad.epub"))
    }

    func testDeclaredEntryTotalAndCompressionRatioLimits() {
        let tooBig = ZIPFixture.make([.init("big", bytes: Data([1]), declaredSize: ImportLimits.entryBytes + 1)])
        XCTAssertThrowsError(try ZIPPreflight(data: tooBig))
        let ratio = ZIPFixture.make([.init("bomb", bytes: Data([1]), declaredSize: 100_000)])
        XCTAssertThrowsError(try ZIPPreflight(data: ratio))
        let entries = (0..<10).map { ZIPFixture.Item("\($0)", bytes: Data(repeating: 0, count: 45_000),
                                                 declaredSize: ImportLimits.entryBytes, method: 8) }
        XCTAssertThrowsError(try ZIPPreflight(data: ZIPFixture.make(entries)))
        XCTAssertThrowsError(try ZIPPreflight(data: ZIPFixture.make((0...ImportLimits.entries).map {
            .init("\($0)", text: "a")
        })))
    }

    func testPathResolutionRejectsRootEscapeAndRemoteResources() throws {
        XCTAssertEqual(try ArchivePath.resolve("../Text/a%20b.xhtml#part", relativeTo: "OPS/Packages/content.opf"), "OPS/Text/a b.xhtml")
        for href in ["../../escape.xhtml", "https://example.org/x", "//example.org/x", "%2e%2e/%2e%2e/x", "a%00b"] {
            XCTAssertThrowsError(try ArchivePath.resolve(href, relativeTo: "OPS/content.opf"))
        }
    }

    func testFixedLayoutDTDAndMissingSpineAreRejected() {
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(fixed: true), filename: "fixed.epub"))
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(spineContent: ""), filename: "spine.epub"))
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(href: "../../escape.xhtml"), filename: "path.epub"))
        let entity = "<!DOCTYPE html [<!ENTITY secret 'value'>]><html><body><p>&secret;</p></body></html>"
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(firstBody: entity), filename: "entity.epub"))
        let deep = "<html><body>" + String(repeating: "<div>", count: 130) + "text" + String(repeating: "</div>", count: 130) + "</body></html>"
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(firstBody: deep), filename: "depth.epub"))
    }

    func testEPUB2NamedEntitiesDoNotRequireExternalDTD() throws {
        let body = """
        <?xml version='1.0' encoding='UTF-8'?>
        <!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.1//EN' 'https://example.invalid/never-fetch.dtd'>
        <html xmlns='http://www.w3.org/1999/xhtml'><body><p>A&nbsp;B &mdash; &copy; &fjlig; &lt;script&gt;literal&lt;/script&gt;</p></body></html>
        """
        let book = try parser.parse(data: EPUBFixture.book(firstBody: body), filename: "epub2.epub")
        let paragraph = try XCTUnwrap(book.chapters[1].paragraphs.first)
        XCTAssertTrue(paragraph.contains("A\u{00a0}B"))
        XCTAssertTrue(paragraph.contains("— © fj"))
        XCTAssertTrue(paragraph.contains("<script>literal</script>"))
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(firstBody:
            "<html><body><p>&unknownCustomEntity;</p></body></html>"), filename: "unknown.epub"))
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(firstBody:
            "<html><body><p>" + String(repeating: "&nbsp;", count: 100_001) + "</p></body></html>"), filename: "entities.epub"))
    }

    func testParagraphsIncludingNestedBlocksAreNotDuplicatedOrLost() throws {
        let body = "<html><body>leading<div>outer<p>inner <b>bold</b></p>tail</div>ending<br/>after</body></html>"
        let book = try parser.parse(data: EPUBFixture.book(firstBody: body), filename: "nested.epub")
        XCTAssertEqual(book.chapters[1].paragraphs, ["leading", "outer", "inner bold", "tail", "ending", "after"])
    }
}

// Small generated, original fixtures: no downloaded books and no bundled text.
private enum EPUBFixture {
    static func book(extra: [ZIPFixture.Item] = [], fixed: Bool = false,
                     href: String = "a.xhtml", firstBody: String? = nil, spineContent: String? = nil) -> Data {
        let fixedMeta = fixed ? "<meta property='rendition:layout'>pre-paginated</meta>" : ""
        let spine = spineContent ?? "<itemref idref='b'/><itemref idref='n' linear='no'/><itemref idref='a'/>"
        let container = "<container xmlns='urn:oasis:names:tc:opendocument:xmlns:container'><rootfiles><rootfile full-path='OPS/content.opf' media-type='application/oebps-package+xml'/></rootfiles></container>"
        let opf = """
        <package xmlns='http://www.idpf.org/2007/opf' version='3.0'>
        <metadata xmlns:dc='http://purl.org/dc/elements/1.1/'><dc:title>原创示例</dc:title><dc:creator>测试作者</dc:creator>\(fixedMeta)</metadata>
        <manifest><item id='a' href='\(href)' media-type='application/xhtml+xml'/><item id='b' href='b.xhtml' media-type='application/xhtml+xml'/><item id='n' href='n.xhtml' media-type='application/xhtml+xml'/></manifest>
        <spine>\(spine)</spine>
        </package>
        """
        let a = firstBody ?? "<html xmlns='http://www.w3.org/1999/xhtml'><head><style>STYLE_SENTINEL</style></head><body><h1>第一章</h1><p>甲正文 <b>inline</b></p><script>SCRIPT_SENTINEL</script><img src='https://example.org/no-fetch' alt='IMAGE_SENTINEL'/></body></html>"
        return ZIPFixture.make([
            .init("mimetype", text: "application/epub+zip"),
            .init("META-INF/container.xml", text: container),
            .init("OPS/content.opf", text: opf),
            .init("OPS/a.xhtml", text: a),
            .init("OPS/b.xhtml", text: "<html><body><h1>第二章</h1><p>第二章乙正文</p></body></html>"),
            .init("OPS/n.xhtml", text: "<html><body><p>NONLINEAR_SENTINEL</p></body></html>")
        ] + extra)
    }
}

private enum ZIPFixture {
    struct Item {
        let name: String
        let bytes: Data
        var flags: UInt16 = 0
        var unixMode: UInt32 = 0x8000
        var declaredSize: Int? = nil
        var method: UInt16 = 0
        init(_ name: String, bytes: Data, flags: UInt16 = 0, unixMode: UInt32 = 0x8000,
             declaredSize: Int? = nil, method: UInt16 = 0) {
            self.name = name; self.bytes = bytes; self.flags = flags; self.unixMode = unixMode
            self.declaredSize = declaredSize; self.method = method
        }
        init(_ name: String, text: String, unixMode: UInt32 = 0x8000) {
            self.init(name, bytes: Data(text.utf8), unixMode: unixMode)
        }
    }

    static func make(_ items: [Item]) -> Data {
        var local = Data()
        var central = Data()
        for item in items {
            let name = Data(item.name.utf8)
            let offset = UInt32(local.count)
            let crc = crc32(item.bytes)
            let size = UInt32(item.declaredSize ?? item.bytes.count)
            local.le32(0x04034b50); local.le16(20); local.le16(item.flags); local.le16(item.method)
            local.le16(0); local.le16(0); local.le32(crc); local.le32(UInt32(item.bytes.count)); local.le32(size)
            local.le16(UInt16(name.count)); local.le16(0); local.append(name); local.append(item.bytes)
            if item.flags & 8 != 0 {
                local.le32(0x08074b50); local.le32(crc); local.le32(UInt32(item.bytes.count)); local.le32(size)
            }
            central.le32(0x02014b50); central.le16(0x0314); central.le16(20); central.le16(item.flags)
            central.le16(item.method); central.le16(0); central.le16(0); central.le32(crc)
            central.le32(UInt32(item.bytes.count)); central.le32(size); central.le16(UInt16(name.count))
            central.le16(0); central.le16(0); central.le16(0); central.le16(0)
            central.le32(item.unixMode << 16); central.le32(offset); central.append(name)
        }
        let centralOffset = UInt32(local.count)
        local.append(central)
        local.le32(0x06054b50); local.le16(0); local.le16(0)
        local.le16(UInt16(items.count)); local.le16(UInt16(items.count))
        local.le32(UInt32(central.count)); local.le32(centralOffset); local.le16(0)
        return local
    }

    private static func crc32(_ bytes: Data) -> UInt32 {
        var value: UInt32 = 0xffffffff
        for byte in bytes {
            value ^= UInt32(byte)
            for _ in 0..<8 { value = (value >> 1) ^ ((value & 1) == 1 ? 0xedb88320 : 0) }
        }
        return value ^ 0xffffffff
    }
}

private extension Data {
    mutating func le16(_ value: UInt16) { append(UInt8(truncatingIfNeeded: value)); append(UInt8(truncatingIfNeeded: value >> 8)) }
    mutating func le32(_ value: UInt32) {
        for shift in stride(from: 0, to: 32, by: 8) { append(UInt8(truncatingIfNeeded: value >> shift)) }
    }
}
''',
    'iosApp/Tests/StreamingImportTests.swift': r'''import XCTest
import Foundation
import ZIPFoundation

final class StreamingImportTests: XCTestCase {
    private let parser = BookParser()

    private func workspace() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }

    private func manifest(_ source: URL, _ root: URL, readSize: Int = 64 * 1_024) throws -> ImportedManifest {
        let json = try parser.parseFileToManifest(at: source, storageRoot: root, readSize: readSize)
        return try JSONDecoder().decode(ImportedManifest.self, from: Data(json.utf8))
    }

    private func chapter(_ entry: ImportedChapterEntry, in root: URL) throws -> ImportedChapter {
        // Tests load just one bounded chapter, as the shared storage layer does.
        try JSONDecoder().decode(ImportedChapter.self, from: Data(contentsOf: root.appendingPathComponent(entry.fileName)))
    }

    func testMultibyteDecoderAtEveryByteBoundary() throws {
        let text = "甲😀乙𠀀€文"
        let variants: [(IncrementalTextDecoder.Encoding, Data)] = [
            (.utf8, Data(text.utf8)),
            (.utf16LE, try XCTUnwrap(text.data(using: .utf16LittleEndian))),
            (.utf16BE, try XCTUnwrap(text.data(using: .utf16BigEndian))),
            // U+0080 uses a four-byte GB18030 sequence, beside two-byte Chinese.
            (.gb18030, Data([0xd6, 0xd0, 0x81, 0x30, 0x81, 0x30, 0xce, 0xc4]))
        ]
        for (encoding, bytes) in variants {
            let expected = encoding == .gb18030 ? "中\u{0080}文" : text
            for size in 1...7 {
                var decoder = IncrementalTextDecoder(encoding: encoding)
                var output = ""
                var offset = 0
                while offset < bytes.count {
                    let end = min(offset + size, bytes.count)
                    output += try decoder.decode(bytes.subdata(in: offset..<end))
                    offset = end
                }
                output += try decoder.decode(Data(), final: true)
                XCTAssertEqual(output, expected)
            }
        }
    }

    func testStrictDecoderRejectsTruncationOverlongAndStraySurrogates() {
        let cases: [(IncrementalTextDecoder.Encoding, [UInt8])] = [
            (.utf8, [0xf0, 0x9f, 0x98]), (.utf8, [0xc0, 0xaf]),
            (.utf8, [0xed, 0xa0, 0x80]), (.utf8, [0xf4, 0x90, 0x80, 0x80]),
            (.utf16LE, [0x00, 0xd8]), (.utf16BE, [0xdc, 0x00]),
            (.utf16LE, [0x41]), (.gb18030, [0x81, 0x30, 0x81]),
            (.gb18030, [0x81, 0x30, 0x40, 0x30])
        ]
        for (encoding, bytes) in cases {
            XCTAssertThrowsError(try {
                var decoder = IncrementalTextDecoder(encoding: encoding)
                for byte in bytes { _ = try decoder.decode(Data([byte])) }
                _ = try decoder.decode(Data(), final: true)
            }())
        }
    }

    func testFileBOMAndGBFallbackWithOneByteReads() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let variants: [(Data, String)] = [
            (Data([0xef, 0xbb, 0xbf]) + Data("甲😀乙".utf8), "甲😀乙"),
            (Data([0xff, 0xfe]) + "甲😀乙".data(using: .utf16LittleEndian)!, "甲😀乙"),
            (Data([0xfe, 0xff]) + "甲😀乙".data(using: .utf16BigEndian)!, "甲😀乙"),
            (Data([0xd6, 0xd0, 0x81, 0x30, 0x81, 0x30, 0xce, 0xc4]), "中\u{0080}文")
        ]
        for (index, pair) in variants.enumerated() {
            let source = base.appendingPathComponent("\(index).txt")
            let root = base.appendingPathComponent("store-\(index)", isDirectory: true)
            try pair.0.write(to: source)
            let result = try manifest(source, root, readSize: 1)
            XCTAssertEqual(result.chapters.count, 1)
            XCTAssertEqual(try chapter(result.chapters[0], in: root).paragraphs, [pair.1])
            XCTAssertEqual(result.chapters[0].characterCount, pair.1.utf16.count)
        }
    }

    func testLateGB18030FallbackReplaysPrefixAndCarriesBoundaryBytes() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("late-gb.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        let prefix = String(repeating: "a", count: 65_535)
        try (Data(prefix.utf8) + Data([0xd6, 0xd0, 0x81, 0x30, 0x81, 0x30])).write(to: source)
        let result = try manifest(source, root)
        let paragraphs = try result.chapters.flatMap { try chapter($0, in: root).paragraphs }
        XCTAssertEqual(paragraphs.joined(), prefix + "中\u{0080}")
    }

    func testOriginalFileLimitsBeforeAnyPublication() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        for (ext, limit) in [("txt", StreamingImportLimits.txtBytes), ("epub", StreamingImportLimits.epubBytes)] {
            let source = base.appendingPathComponent("oversized.\(ext)")
            let root = base.appendingPathComponent("store-\(ext)", isDirectory: true)
            XCTAssertTrue(FileManager.default.createFile(atPath: source.path, contents: nil))
            let file = try FileHandle(forWritingTo: source)
            try file.truncate(atOffset: UInt64(limit) + 1) // Sparse fixture; no giant Data.
            try file.close()
            XCTAssertThrowsError(try manifest(source, root))
            XCTAssertFalse(FileManager.default.fileExists(atPath: root.path))
        }
    }

    func testManifestContractAtomicChaptersAndIndependentRevisions() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("Example.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        try Data("abc".utf8).write(to: source)
        let first = try manifest(source, root)
        XCTAssertEqual(first.schema, 2)
        XCTAssertEqual(first.id, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        XCTAssertEqual(first.title, "Example")
        XCTAssertEqual(first.format, "TXT")
        XCTAssertNotNil(first.revision.range(of: "^[0-9a-f]{32}$", options: .regularExpression))
        XCTAssertEqual(first.chapters[0].fileName, "book-\(first.id)-\(first.revision)-c0.json")
        XCTAssertEqual(first.chapters[0].paragraphCount, 1)
        XCTAssertEqual(first.chapters[0].characterCount, 3)
        XCTAssertEqual(try chapter(first.chapters[0], in: root).paragraphs, ["abc"])
        let canonical = root.appendingPathComponent("book-\(first.id).manifest.json")
        XCTAssertFalse(FileManager.default.fileExists(atPath: canonical.path))
        try Data("KOTLIN_OWNS_CANONICAL".utf8).write(to: canonical)
        let second = try manifest(source, root)
        XCTAssertEqual(first.id, second.id)
        XCTAssertNotEqual(first.revision, second.revision)
        XCTAssertTrue(FileManager.default.fileExists(atPath: root.appendingPathComponent(first.chapters[0].fileName).path))
        XCTAssertEqual(try String(contentsOf: canonical, encoding: .utf8), "KOTLIN_OWNS_CANONICAL")
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(second)) as? [String: Any])
        let entries = try XCTUnwrap(object["chapters"] as? [[String: Any]])
        XCTAssertEqual(Set(entries[0].keys), Set(["title", "fileName", "paragraphCount", "characterCount"]))
        XCTAssertNil(entries[0]["paragraphs"])
    }

    func testLargeNoTOCTXTAboveLegacyLimitProducesBoundedChapters() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("large-no-toc.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        XCTAssertTrue(FileManager.default.createFile(atPath: source.path, contents: nil))
        let output = try FileHandle(forWritingTo: source)
        let line = Data((String(repeating: "文😀", count: 2_048) + "\n").utf8)
        let repeats = 2_400 // >32MiB on disk; never constructs the entire fixture.
        for _ in 0..<repeats { try output.write(contentsOf: line) }
        try output.close()
        XCTAssertGreaterThan(line.count * repeats, ImportLimits.fileBytes)
        let result = try manifest(source, root)
        XCTAssertGreaterThan(result.chapters.count, 1)
        var characters = 0
        for (index, entry) in result.chapters.enumerated() {
            XCTAssertEqual(entry.fileName, "book-\(result.id)-\(result.revision)-c\(index).json")
            let value = try chapter(entry, in: root)
            XCTAssertEqual(entry.paragraphCount, value.paragraphs.count)
            XCTAssertEqual(entry.characterCount, value.paragraphs.reduce(0) { $0 + $1.utf16.count })
            XCTAssertLessThanOrEqual(entry.characterCount, StreamingImportLimits.chapterUTF16)
            XCTAssertLessThanOrEqual(value.paragraphs.reduce(0) { $0 + $1.utf8.count }, StreamingImportLimits.chapterBytes)
            XCTAssertTrue(value.paragraphs.allSatisfy { $0.utf16.count <= ImportLimits.paragraphUTF16 && !$0.contains("�") })
            characters += entry.characterCount
        }
        XCTAssertEqual(characters, 3 * 2_048 * repeats)
    }

    func testConsecutiveHeadingsAndCRLFAcrossChunks() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("chapters.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        try Data("序言\r\n第一章开始\r\n正文😀\r\nChapter 2 End\n正文二".utf8).write(to: source)
        let result = try manifest(source, root, readSize: 1)
        XCTAssertEqual(result.chapters.map(\.title), ["序言", "第一章开始", "Chapter 2 End"])
        XCTAssertEqual(try result.chapters.map { try chapter($0, in: root).paragraphs }, [[], ["正文😀"], ["正文二"]])
    }

    func testLongPhysicalLineFragmentIsNeverPromotedToHeading() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("long-line.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        // First 2000-unit fragment trims to a heading, but the line continues.
        let text = String(repeating: " ", count: 1_996) + "第一章A后续正文\n"
        try Data(text.utf8).write(to: source)
        let result = try manifest(source, root, readSize: 7)
        XCTAssertEqual(result.chapters.map(\.title), ["long-line"])
        XCTAssertEqual(try chapter(result.chapters[0], in: root).paragraphs.joined(), "第一章A后续正文")
    }

    func testFailureRollsBackOnlyCurrentRevisionFiles() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("truncated.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let previous = root.appendingPathComponent("book-existing-revision-c0.json")
        try Data("PRESERVE".utf8).write(to: previous)
        XCTAssertTrue(FileManager.default.createFile(atPath: source.path, contents: Data([0xff, 0xfe])))
        let output = try FileHandle(forWritingTo: source)
        try output.seekToEnd()
        let chunk = (String(repeating: "正文😀", count: 8_192) + "\n").data(using: .utf16LittleEndian)!
        for _ in 0..<20 { try output.write(contentsOf: chunk) }
        // Fails only at EOF, after several chapters have already been published.
        try output.write(contentsOf: Data([0x00, 0xd8]))
        try output.close()
        XCTAssertThrowsError(try manifest(source, root))
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: root.path), [previous.lastPathComponent])
        XCTAssertEqual(try String(contentsOf: previous, encoding: .utf8), "PRESERVE")
    }

    func testFileBackedEPUBNoTOCSplitsSingleLogicalChapterAndIgnoresAssets() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("no-nav.epub")
        let root = base.appendingPathComponent("store", isDirectory: true)
        let text = String(repeating: "文😀", count: 180_000)
        try makeEPUB(at: source, body: "<html><body><p>\(text)</p></body></html>", largeAsset: true)
        let preflight = try ZIPPreflight(fileURL: source)
        XCTAssertEqual(preflight.records.count, 5)
        let result = try manifest(source, root)
        XCTAssertEqual(result.title, "文件归档示例")
        XCTAssertEqual(result.author, "测试作者")
        XCTAssertEqual(result.format, "EPUB")
        XCTAssertGreaterThan(result.chapters.count, 1)
        var units = 0
        for entry in result.chapters {
            let value = try chapter(entry, in: root)
            XCTAssertEqual(entry.paragraphCount, value.paragraphs.count)
            XCTAssertEqual(entry.characterCount, value.paragraphs.reduce(0) { $0 + $1.utf16.count })
            XCTAssertLessThanOrEqual(entry.characterCount, StreamingImportLimits.chapterUTF16)
            units += entry.characterCount
        }
        XCTAssertEqual(units, text.utf16.count)
    }

    func testFilePreflightRejectsStoredEntryWithMismatchedSizes() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("stored.zip")
        do {
            let archive = try Archive(url: source, accessMode: .create)
            let payload = Data("hello".utf8)
            try archive.addEntry(with: "stored.txt", type: .file, uncompressedSize: Int64(5), compressionMethod: .none) { offset, size in
                let start = Int(offset)
                return payload.subdata(in: start..<min(start + size, payload.count))
            }
        }
        let file = try FileHandle(forUpdating: source)
        let length = try file.seekToEnd()
        try file.seek(toOffset: length - 22)
        let end = try XCTUnwrap(file.read(upToCount: 22))
        XCTAssertEqual(end.count, 22)
        let directory = UInt64(end[16]) | UInt64(end[17]) << 8 | UInt64(end[18]) << 16 | UInt64(end[19]) << 24
        // Keep original uncompressed size and CRC, shrink only compressed size
        // in both headers. Stored entries must not read past declared ranges.
        try file.seek(toOffset: 18)
        try file.write(contentsOf: Data([4, 0, 0, 0]))
        try file.seek(toOffset: directory + 20)
        try file.write(contentsOf: Data([4, 0, 0, 0]))
        try file.close()
        XCTAssertThrowsError(try ZIPPreflight(fileURL: source))
    }

    func testFileBackedArchiveRetainsBombCRCAndPathChecks() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("bad.epub")
        try makeEPUB(at: source, body: "<html><body><p>正文</p></body></html>")
        let file = try FileHandle(forUpdating: source)
        try file.seek(toOffset: UInt64(30 + "mimetype".utf8.count))
        try file.write(contentsOf: Data([0])) // CRC mismatch in a consumed entry.
        try file.close()
        XCTAssertThrowsError(try manifest(source, base.appendingPathComponent("store")))
        XCTAssertThrowsError(try ArchivePath.validateEntry("../escape"))
        XCTAssertThrowsError(try ArchivePath.resolve("https://example.invalid/a.xhtml"))
        let bomb = base.appendingPathComponent("bomb.epub")
        do {
            let archive = try Archive(url: bomb, accessMode: .create)
            let bytes = Data(repeating: 65, count: 1_024 * 1_024)
            try archive.addEntry(with: "bomb", type: .file, uncompressedSize: Int64(bytes.count), compressionMethod: .deflate) { offset, size in
                let start = Int(offset)
                return bytes.subdata(in: start..<min(start + size, bytes.count))
            }
        }
        XCTAssertThrowsError(try ZIPPreflight(fileURL: bomb))
    }

    private func makeEPUB(at url: URL, body: String, largeAsset: Bool = false) throws {
        let archive = try Archive(url: url, accessMode: .create)
        let entries: [(String, String)] = [
            ("mimetype", "application/epub+zip"),
            ("META-INF/container.xml", "<container><rootfiles><rootfile full-path='OPS/content.opf' media-type='application/oebps-package+xml'/></rootfiles></container>"),
            ("OPS/content.opf", "<package><metadata><title>文件归档示例</title><creator>测试作者</creator></metadata><manifest><item id='a' href='a.xhtml' media-type='application/xhtml+xml'/></manifest><spine><itemref idref='a'/></spine></package>"),
            ("OPS/a.xhtml", body)
        ]
        for (path, text) in entries {
            let bytes = Data(text.utf8)
            // Stored fixtures avoid triggering ratio protection on repeated text.
            try archive.addEntry(with: path, type: .file, uncompressedSize: Int64(bytes.count), compressionMethod: .none) { offset, size in
                let start = Int(offset)
                return bytes.subdata(in: start..<min(start + size, bytes.count))
            }
        }
        if largeAsset {
            // >legacy 32MiB archive, but no giant Data or arbitrary extraction.
            try archive.addEntry(with: "unused-image.bin", type: .file,
                                 uncompressedSize: Int64(33 * 1_024 * 1_024), compressionMethod: .none) { _, size in
                Data(repeating: 7, count: size)
            }
        }
    }
}
''',
    'scripts/build-ios.sh': r'''#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ "$(uname -s)" != Darwin ]]; then
  printf 'This build requires macOS and Xcode. Use the GitHub Actions Build iOS IPA workflow.\n' >&2
  exit 1
fi
python3 scripts/check_project.py
bash ./gradlew :shared:linkReleaseFrameworkIosArm64 -PenableApple=true --stacktrace
(cd iosApp && xcodegen generate)
xcodebuild \
  -project iosApp/LeafReader.xcodeproj \
  -scheme LeafReader \
  -configuration Release \
  -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath build/ios \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY='' DEVELOPMENT_TEAM='' \
  build
APP="$ROOT/build/ios/Build/Products/Release-iphoneos/LeafReader.app"
test -f "$APP/LeafReader"
plutil -lint "$APP/Info.plist"
ARCHS="$(xcrun lipo -archs "$APP/LeafReader")"
case "$ARCHS" in
  *arm64*) printf 'Architectures: %s\n' "$ARCHS" ;;
  *) printf 'Expected a thin arm64 binary, got: %s\n' "$ARCHS" >&2; exit 1 ;;
esac
APP_VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Info.plist")"
python3 scripts/package_ipa.py --app "$APP" --output "$ROOT/dist/LeafReader-${APP_VERSION}-unsigned.ipa"
''',
    'scripts/tests/test_upgrade_v04.py': '"""Self-contained installer regression tests. Every mutation is in TemporaryDirectory.\n\nRun: python3 -m unittest discover -s scripts/tests -p test_upgrade_v04.py -v\nNo Gradle, network, package installer, downloaded code or real project upgrade.\n"""\nimport ast\nimport contextlib\nimport hashlib\nimport importlib.util\nimport io\nimport json\nimport os\nfrom pathlib import Path\nimport plistlib\nimport tempfile\nimport unittest\nfrom unittest import mock\nimport zipfile\n\nROOT = Path(__file__).resolve().parents[2]\n\n\ndef load_tool(name, filename):\n    spec = importlib.util.spec_from_file_location(name, ROOT / \'tools\' / filename)\n    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n\n\nrunner = load_tool(\'leaf_upgrade_v04_runtime\', \'upgrade_runner.py\')\npacker = load_tool(\'leaf_upgrade_v04_packer\', \'make_upgrade.py\')\nUI = \'top.yukonga.miuix.kmp:miuix-ui:0.9.4\'\nBLUR = \'top.yukonga.miuix.kmp:miuix-blur:0.9.4\'\nBUILD = (\'// user configuration stays verbatim\\n\'\n         \'plugins { kotlin("multiplatform") }\\n\'\n         \'repositories { maven("https://custom.invalid/maven") }\\n\'\n         \'kotlin {\\n    sourceSets {\\n        commonMain.dependencies {\\n\'\n         \'            implementation("\' + UI + \'") // user comment\\n\'\n         \'            implementation("custom:reader-addon:7")\\n\'\n         \'        }\\n    }\\n}\\n\')\nPAYLOAD = {\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderChrome.kt\': \'// new UI source\\n\',\n    \'scripts/new_probe.py\': \'VALUE = "😀"\\n\',\n    \'README.md\': \'# LeafReader v0.4\\n\',\n}\n\n\nclass UpgradeV04Tests(unittest.TestCase):\n    def setUp(self):\n        self.temporary = tempfile.TemporaryDirectory(prefix=\'leaf-v04-test-\')\n        self.addCleanup(self.temporary.cleanup)\n        self.project = Path(self.temporary.name).resolve() / \'project\'\n        self.project.mkdir()\n        self.put(\'settings.gradle.kts\', \'rootProject.name = "UserLeaf"\\n\')\n        self.put(\'shared/build.gradle.kts\', BUILD)\n        self.put(\'iosApp/project.yml\', self.yml(\'0.3.0\', \'3\'))\n        self.put(\'iosApp/Info.plist\', plistlib.dumps({\'CFBundleIdentifier\': \'user.custom.reader\'}))\n        self.put(\'README.md\', \'# existing user project\\n\')\n        self.put(\'scripts/existing.py\', \'VALUE = 1\\n\')\n        self.files_patch = mock.patch.object(runner, \'FILES\', dict(PAYLOAD))\n        self.files_patch.start()\n        self.addCleanup(self.files_patch.stop)\n        self.hash_patch = mock.patch.object(runner, \'EXPECTED_PAYLOAD_SHA256\', {\n            name: hashlib.sha256(text.encode()).hexdigest() for name, text in PAYLOAD.items()\n        })\n        self.hash_patch.start()\n        self.addCleanup(self.hash_patch.stop)\n\n    @staticmethod\n    def yml(marketing, build):\n        return (\'name: UserLeaf\\nsettings:\\n  base:\\n\'\n                \'    PRODUCT_BUNDLE_IDENTIFIER: user.custom.reader\\n\'\n                \'    CUSTOM_SETTING: "keep-me"\\n\'\n                \'    MARKETING_VERSION: "\' + marketing + \'" # preserve comment\\n\'\n                \'    CURRENT_PROJECT_VERSION: "\' + build + \'"\\n\')\n\n    def put(self, name, content):\n        path = self.project / name\n        path.parent.mkdir(parents=True, exist_ok=True)\n        path.write_bytes(content if isinstance(content, bytes) else content.encode())\n        return path\n\n    def snapshot(self):\n        return {path.relative_to(self.project).as_posix(): path.read_bytes()\n                for path in self.project.rglob(\'*\') if path.is_file() and not path.is_symlink()}\n\n    def apply(self, archive=None):\n        arguments = [\'--project\', str(self.project)]\n        if archive:\n            arguments += [\'--archive\', archive]\n        with contextlib.redirect_stdout(io.StringIO()):\n            runner.main(arguments)\n\n    def assert_preflight_stops_without_writes(self):\n        before = self.snapshot()\n        with self.assertRaises((ValueError, SyntaxError)):\n            self.apply()\n        self.assertEqual(before, self.snapshot())\n        self.assertFalse((self.project / \'.leaf-upgrade-backup\').exists())\n        self.assertFalse(list(self.project.rglob(\'.leaf-*.tmp\')))\n\n    def test_blur_is_adjacent_and_user_configuration_is_byte_preserved(self):\n        patched = runner.patch_shared_gradle(BUILD)\n        self.assertEqual(patched.replace(\'            implementation("\' + BLUR + \'")\\n\', \'\', 1), BUILD)\n        self.assertIn(\'implementation("\' + UI + \'") // user comment\\n\'\n                      \'            implementation("\' + BLUR + \'")\\n\', patched)\n        self.assertEqual(runner.patch_shared_gradle(patched), patched)\n\n    def test_existing_blur_dependency_needs_no_insertion(self):\n        existing = BUILD.replace(\'commonMain.dependencies {\',\n                                 \'commonMain.dependencies {\\n            implementation("\' + BLUR + \'")\')\n        self.assertEqual(runner.patch_shared_gradle(existing), existing)\n        self.put(\'shared/build.gradle.kts\', existing)\n        self.apply()\n        self.assertEqual((self.project / \'shared/build.gradle.kts\').read_bytes(), existing.encode())\n\n    def test_crlf_and_final_line_without_newline_are_preserved(self):\n        text = BUILD.replace(\'\\n\', \'\\r\\n\')\n        patched = runner.patch_shared_gradle(text)\n        self.assertNotIn(\'\\n\', patched.replace(\'\\r\\n\', \'\'))\n        self.assertEqual(patched.replace(\'            implementation("\' + BLUR + \'")\\r\\n\', \'\', 1), text)\n        eof = \'implementation("\' + UI + \'")\'\n        self.assertEqual(runner.patch_shared_gradle(eof), eof + \'\\nimplementation("\' + BLUR + \'")\\n\')\n        yml = self.yml(\'0.1.0\', \'1\').replace(\'\\n\', \'\\r\\n\')\n        patched_yml = runner.patch_project_yml(yml)\n        self.assertEqual(patched_yml, yml.replace(\'"0.1.0"\', \'"0.4.0"\').replace(\'"1"\', \'"4"\'))\n\n    def test_upgrades_v01_v02_v03_preserving_bundle_and_build_settings(self):\n        for minor in (1, 2, 3):\n            original = self.yml(\'0.%d.0\' % minor, str(minor))\n            self.put(\'iosApp/project.yml\', original)\n            self.put(\'shared/build.gradle.kts\', BUILD)\n            self.apply()\n            actual = (self.project / \'iosApp/project.yml\').read_text()\n            expected = original.replace(\'"0.%d.0"\' % minor, \'"0.4.0"\').replace(\'"%d"\' % minor, \'"4"\')\n            self.assertEqual(actual, expected)\n            self.assertIn(\'user.custom.reader\', actual)\n            self.assertIn(\'custom:reader-addon:7\', (self.project / \'shared/build.gradle.kts\').read_text())\n\n    def test_whole_upgrade_is_idempotent_and_preserves_file_modes(self):\n        script = self.put(\'scripts/new_probe.py\', \'VALUE = 0\\n\')\n        script.chmod(0o755)\n        self.apply()\n        first = {key: value for key, value in self.snapshot().items() if not key.startswith(\'.leaf-upgrade-backup/\')}\n        self.apply()\n        second = {key: value for key, value in self.snapshot().items() if not key.startswith(\'.leaf-upgrade-backup/\')}\n        self.assertEqual(first, second)\n        self.assertEqual(script.stat().st_mode & 0o777, 0o755)\n        self.assertEqual((self.project / \'shared/build.gradle.kts\').read_text().count(BLUR), 1)\n        manifests = list((self.project / \'.leaf-upgrade-backup\').glob(\'*/change-manifest.json\'))\n        self.assertEqual(len(manifests), 2)\n        latest = sorted(manifests)[-1]\n        self.assertTrue(all(item[\'unchanged\'] for item in json.loads(latest.read_text())[\'changes\']))\n\n    def test_missing_anchor_is_detected_before_any_file_or_backup_write(self):\n        self.put(\'shared/build.gradle.kts\', BUILD.replace(UI, \'user:another-reader:1\'))\n        self.assert_preflight_stops_without_writes()\n\n    def test_commented_anchor_does_not_count(self):\n        self.put(\'shared/build.gradle.kts\', \'/*\\nimplementation("\' + UI + \'")\\n*/\\n\')\n        self.assert_preflight_stops_without_writes()\n\n    def test_wrong_or_duplicate_blur_versions_stop_before_writes(self):\n        for declaration in (\'implementation("\' + BLUR.replace(\'0.9.4\', \'0.9.3\') + \'")\',\n                            \'implementation("\' + BLUR + \'")\\nimplementation("\' + BLUR + \'")\'):\n            self.put(\'shared/build.gradle.kts\', BUILD + declaration + \'\\n\')\n            self.assert_preflight_stops_without_writes()\n\n    def test_missing_version_scalar_stops_before_any_write(self):\n        self.put(\'iosApp/project.yml\', self.yml(\'0.3.0\', \'3\').replace(\'MARKETING_VERSION\', \'USER_VERSION\'))\n        self.assert_preflight_stops_without_writes()\n\n    def test_invalid_python_or_plist_stops_before_any_write(self):\n        self.put(\'scripts/existing.py\', \'def broken(:\\n\')\n        self.assert_preflight_stops_without_writes()\n        self.put(\'scripts/existing.py\', \'VALUE = 1\\n\')\n        self.put(\'iosApp/Info.plist\', \'<plist><dict>broken</plist>\')\n        self.assert_preflight_stops_without_writes()\n\n    def test_invalid_late_payload_path_stops_before_any_write(self):\n        with mock.patch.object(runner, \'FILES\', {**PAYLOAD, \'zz/../../escape.py\': \'pass\\n\'}), \\\n                mock.patch.object(runner, \'EXPECTED_PAYLOAD_SHA256\', {}):\n            self.assert_preflight_stops_without_writes()\n        for name in (\'/absolute\', \'./relative\', \'a//b\', \'a/../b\', \'a\\\\b\', \'C:drive\', \'a\\x00b\'):\n            with self.assertRaises(ValueError):\n                runner.validate_relative(name)\n\n    def test_symlink_target_stops_without_touching_external_file(self):\n        external = Path(self.temporary.name).resolve() / \'external.md\'\n        external.write_text(\'keep outside\')\n        target = self.project / \'README.md\'\n        target.unlink()\n        target.symlink_to(external)\n        self.assert_preflight_stops_without_writes()\n        self.assertEqual(external.read_text(), \'keep outside\')\n\n    def test_invalid_archive_is_preflighted_before_source_write(self):\n        before = self.snapshot()\n        with self.assertRaises(ValueError):\n            self.apply(\'../outside.zip\')\n        self.assertEqual(before, self.snapshot())\n        self.assertFalse((self.project / \'.leaf-upgrade-backup\').exists())\n\n    def test_backup_change_manifest_and_payload_sha_are_complete(self):\n        original_yml = (self.project / \'iosApp/project.yml\').read_bytes()\n        self.apply()\n        backup = next((self.project / \'.leaf-upgrade-backup\').iterdir())\n        manifest = json.loads((backup / \'change-manifest.json\').read_text())\n        self.assertEqual(manifest[\'status\'], \'applied\')\n        self.assertEqual(manifest[\'file_count\'], len(PAYLOAD))\n        self.assertEqual(len(manifest[\'changes\']), len(PAYLOAD) + 2)\n        self.assertEqual((backup / \'files/iosApp/project.yml\').read_bytes(), original_yml)\n        self.assertEqual((backup / \'files/shared/build.gradle.kts\').read_bytes(), BUILD.encode())\n        hashes = json.loads((backup / \'payload-sha256.json\').read_text())\n        self.assertEqual(hashes, runner.EXPECTED_PAYLOAD_SHA256)\n        for change in manifest[\'changes\']:\n            self.assertEqual(change[\'sha256_after\'], hashlib.sha256((self.project / change[\'path\']).read_bytes()).hexdigest())\n\n    def test_apply_failure_rolls_back_replacements_and_new_files(self):\n        before = self.snapshot()\n        original_write = runner.atomic_write\n\n        def fail_on_new_script(target, payload, mode=0o644):\n            if target == self.project / \'scripts/new_probe.py\':\n                raise OSError(\'injected write failure\')\n            return original_write(target, payload, mode)\n\n        with mock.patch.object(runner, \'atomic_write\', side_effect=fail_on_new_script):\n            with self.assertRaises(OSError):\n                self.apply()\n        sources = {key: value for key, value in self.snapshot().items() if not key.startswith(\'.leaf-upgrade-backup/\')}\n        self.assertEqual(sources, before)\n        backup = next((self.project / \'.leaf-upgrade-backup\').iterdir())\n        self.assertEqual(json.loads((backup / \'change-manifest.json\').read_text())[\'status\'], \'rolled-back\')\n\n    def test_archive_keeps_wrapper_native_tests_icons_tools_original_ci(self):\n        keep = (\'gradle/wrapper/gradle-wrapper.jar\', \'gradle/wrapper/gradle-wrapper.properties\',\n                \'gradlew\', \'gradlew.bat\', \'iosApp/Tests/BookParserTests.swift\',\n                \'iosApp/Assets.xcassets/AppIcon.appiconset/icon.png\',\n                \'iosApp/Tools/generate_app_icon.py\', \'.github/workflows/original.yml\',\n                \'tools/upgrade_runner.py\', \'LeafReader-v0.4-upgrade.py\')\n        omit = (\'local.properties\', \'.git/config\', \'shared/build/output.bin\',\n                \'iosApp/secret.pem\', \'scripts/.env\', \'gradle/.gradle/cache.bin\',\n                \'iosApp/credentials/token.txt\', \'shared/.cache/file\',\n                \'.leaf-upgrade-backup/old/original.txt\')\n        for name in keep:\n            self.put(name, \'VALUE = 1\\n\' if name.endswith(\'.py\') else \'source\\n\')\n        for name in omit:\n            self.put(name, \'not for archive\\n\')\n        self.apply(\'dist/source.zip\')\n        with zipfile.ZipFile(self.project / \'dist/source.zip\') as archive:\n            names = set(archive.namelist())\n        self.assertTrue(set(keep) <= names)\n        self.assertFalse(set(omit) & names)\n        self.assertNotIn(\'dist/source.zip\', names)\n        self.assertFalse(any(name.startswith(\'.leaf-upgrade-backup/\') for name in names))\n\n    def test_python_literal_roundtrip_retains_exact_payload_bytes(self):\n        values = [\'no final newline\', \'ends with slash\\\\\', "has \'\'\' and \\"\\"\\" both",\n                  "terminal quote\'", \'Swift \\\\(value) \\\\.title\\n😀\\r\\n\']\n        for value in values:\n            self.assertEqual(ast.literal_eval(packer.literal(value)), value)\n\n    def test_packer_missing_required_files_is_explicit(self):\n        with self.assertRaisesRegex(ValueError, \'Missing/linked source tree|Missing required sources\'):\n            packer.discover_source_files(self.project)\n\n\nif __name__ == \'__main__\':\n    unittest.main()\n',
    'scripts/tests/test_upgrade_v05.py': r'''"""v0.5 packaging tests, using synthetic local source trees and temp projects.

No final release installer is created. Synthetic material coordinates exercise
configuration, not a choice of a production library or API.
"""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def load_tool(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_tool('leaf_upgrade_v05_runtime', 'upgrade_runner.py')
packer = load_tool('leaf_upgrade_v05_packer', 'make_upgrade.py')
UI = 'top.yukonga.miuix.kmp:miuix-ui:0.9.4'
BLUR = 'top.yukonga.miuix.kmp:miuix-blur:0.9.4'
# Deliberately nonexistent fixture coordinate; never a release dependency.
MATERIAL = 'test.material:fixture-surface:1.2.3'
BUILD = ('// user Gradle configuration\n'
         'repositories { maven("https://mirror.invalid/custom") }\n'
         'commonMain.dependencies {\n'
         '    implementation("' + UI + '") // keep this comment\n'
         '    implementation("user:feature:9")\n}\n')
YML = ('settings:\n  base:\n    PRODUCT_BUNDLE_IDENTIFIER: user.existing.leaf\n'
       '    CUSTOM_BUILD_SETTING: "retain"\n'
       '    MARKETING_VERSION: "0.1.0" # keep this comment\n'
       '    CURRENT_PROJECT_VERSION: "1"\n')


class UpgradeV05Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='leaf-v05-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name).resolve() / 'project'
        self.project.mkdir()
        self.put('settings.gradle.kts', 'rootProject.name = "Fixture"\n')
        self.put('shared/build.gradle.kts', BUILD)
        self.put('iosApp/project.yml', YML)
        self.put('iosApp/Info.plist', plistlib.dumps({'CFBundleIdentifier': 'user.existing.leaf'}))
        for tree in packer.DISCOVER_TREES:
            (self.project / tree).mkdir(parents=True, exist_ok=True)
        self.patch('INSTALLER_VERSION', '0.5')
        self.patch('VERSION_PATCHES', {'MARKETING_VERSION': '0.5.0', 'CURRENT_PROJECT_VERSION': '5'})
        self.patch('REQUIRED_MATERIAL_DEPENDENCIES', (BLUR, MATERIAL))
        self.patch('FILES', {'README.md': '# v0.5 fixture\n', 'scripts/new.py': 'VALUE = 5\n'})
        self.patch('EXPECTED_PAYLOAD_SHA256', {})

    def patch(self, name, value):
        patcher = mock.patch.object(runner, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def put(self, name, content):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode('utf-8'))
        return path

    def snapshot(self):
        return {path.relative_to(self.project).as_posix(): path.read_bytes()
                for path in self.project.rglob('*') if path.is_file()}

    def apply(self):
        with contextlib.redirect_stdout(io.StringIO()):
            runner.main(['--project', str(self.project)])

    def source_fixture(self, version='0.5'):
        extra, _ = packer.release_profile(version)
        names = set(packer.FILES + packer.REQUIRED_V04_FILES + packer.REQUIRED_DIRECTORY_TESTS + extra)
        for name in names:
            content = '{}\n' if name.endswith('.json') else ('VALUE = 1\n' if name.endswith('.py') else '// fixture\n')
            self.put(name, content)
        self.put('tools/upgrade_runner.py', (ROOT / 'tools/upgrade_runner.py').read_bytes())
        return names

    def test_configurable_materials_are_adjacent_preserving_user_config(self):
        result = runner.patch_shared_gradle(BUILD)
        added = '    implementation("' + BLUR + '")\n    implementation("' + MATERIAL + '")\n'
        self.assertIn(' // keep this comment\n' + added, result)
        self.assertEqual(result.replace(added, '', 1), BUILD)
        self.assertEqual(runner.patch_shared_gradle(result), result)

    def test_existing_blur_adds_only_the_new_material(self):
        existing = BUILD + 'implementation("' + BLUR + '")\n'
        result = runner.patch_shared_gradle(existing)
        self.assertEqual(result.count(BLUR), 1)
        self.assertEqual(result.count(MATERIAL), 1)
        self.assertEqual(result.replace('    implementation("' + MATERIAL + '")\n', '', 1), existing)

    def test_any_material_conflict_prevents_all_project_writes(self):
        self.put('shared/build.gradle.kts', BUILD + 'implementation("' + MATERIAL.replace('1.2.3', '1.0.0') + '")\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'pinned'):
            self.apply()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.project / '.leaf-upgrade-backup').exists())

    def test_example_raw_string_is_not_a_dependency_anchor(self):
        raw = 'val example = """\nimplementation("' + UI + '")\n"""\n'
        with self.assertRaisesRegex(ValueError, 'anchor'):
            runner.patch_shared_gradle(raw)
        real = raw + BUILD
        patched = runner.patch_shared_gradle(real)
        self.assertTrue(patched.startswith(raw))
        self.assertEqual(patched.count(MATERIAL), 1)

    def test_bad_material_specs_or_duplicate_requirements_are_preflight_errors(self):
        for requirements in (('not-a-coordinate',), (BLUR, BLUR), ('group:artifact:1.+',)):
            with self.assertRaises(ValueError):
                runner.patch_shared_gradle(BUILD, requirements)

    def test_all_old_versions_keep_bundle_settings_and_upgrade_idempotently(self):
        for minor in (1, 2, 3, 4):
            original = YML.replace('0.1.0', '0.%d.0' % minor).replace('"1"', '"%d"' % minor)
            self.put('iosApp/project.yml', original)
            self.put('shared/build.gradle.kts', BUILD)
            self.apply()
            self.apply()
            self.assertEqual((self.project / 'iosApp/project.yml').read_text(),
                             original.replace('0.%d.0' % minor, '0.5.0').replace('"%d"' % minor, '"5"'))
            result = (self.project / 'shared/build.gradle.kts').read_text()
            self.assertEqual(result.count(MATERIAL), 1)
            self.assertIn('user:feature:9', result)
        manifests = list((self.project / '.leaf-upgrade-backup').glob('*/change-manifest.json'))
        self.assertEqual(len(manifests), 8)
        manifest = json.loads(sorted(manifests)[-1].read_text())
        self.assertTrue(all(change['unchanged'] for change in manifest['changes']))
        self.assertEqual(manifest['material_dependencies'], [BLUR, MATERIAL])

    def test_profile_retains_v04_and_v05_explicit_payloads(self):
        self.source_fixture('0.5')
        legacy = set(packer.discover_source_files(self.project, '0.4'))
        current = set(packer.discover_source_files(self.project, '0.5'))
        self.assertTrue(legacy <= current)
        self.assertTrue(set(packer.REQUIRED_V05_FILES) <= current)
        self.assertNotIn('shared/build.gradle.kts', current)
        self.assertNotIn('iosApp/project.yml', current)

    def test_dynamic_sources_and_confirmed_critical_files_are_never_omitted(self):
        self.source_fixture()
        new = ('iosApp/Sources/FixtureMaterial.swift',
               'shared/src/commonTest/kotlin/dev/leaf/reader/ui/FixtureMaterialTest.kt',
               'shared/src/desktopTest/kotlin/dev/leaf/reader/ui/FixtureHostTest.kt',
               'shared/src/commonMain/kotlin/dev/leaf/reader/FixtureState.kt')
        for name in new:
            self.put(name, '// new fixture\n')
        self.assertTrue(set(new) <= set(packer.discover_source_files(self.project)))
        critical = 'shared/src/commonMain/kotlin/dev/leaf/reader/ui/LeadConfirmedFixture.kt'
        with mock.patch.object(packer, 'REQUIRED_V05_SOURCE_FILES', [critical]):
            with self.assertRaisesRegex(ValueError, 'LeadConfirmedFixture'):
                packer.discover_source_files(self.project)

    def test_generated_fixture_has_exact_payloads_version_and_material_profile(self):
        self.source_fixture()
        exact = 'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ExactFixture.kt'
        self.put(exact, b'// no trailing newline; backslash \\')
        with mock.patch.object(packer, 'MATERIAL_DEPENDENCIES_V05', (BLUR, MATERIAL)):
            source, hashes = packer.assemble_installer(self.project)
        namespace = {'__name__': 'local_fixture_not_main'}
        # Execute only the locally generated fixture runtime, never downloaded code.
        exec(compile(source, '<local-v05-fixture>', 'exec'), namespace)
        self.assertEqual(namespace['VERSION_PATCHES'], {'MARKETING_VERSION': '0.5.0', 'CURRENT_PROJECT_VERSION': '5'})
        self.assertEqual(namespace['REQUIRED_MATERIAL_DEPENDENCIES'], (BLUR, MATERIAL))
        self.assertEqual(namespace['FILES'][exact].encode(), (self.project / exact).read_bytes())
        self.assertEqual(namespace['EXPECTED_PAYLOAD_SHA256'], hashes)
        for name, text in namespace['FILES'].items():
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), hashes[name])
        with contextlib.redirect_stdout(io.StringIO()):
            namespace['main'](['--project', str(self.project), '--archive', 'dist/fixture.zip'])
            namespace['main'](['--project', str(self.project)])
        self.assertIn('user.existing.leaf', (self.project / 'iosApp/project.yml').read_text())
        with zipfile.ZipFile(self.project / 'dist/fixture.zip') as archive:
            self.assertIn('tools/upgrade_runner.py', archive.namelist())
            self.assertIn('scripts/tests/test_upgrade_v05.py', archive.namelist())
            for name in packer.REQUIRED_V05_SOURCE_FILES:
                self.assertIn(name, archive.namelist())
                self.assertIn(name, namespace['FILES'])
            # Host structure regressions inspect these source paths. Preserve the
            # package layout under shared/src for old repositories and source ZIPs.
            for filename in ('ReaderApp.kt', 'ReaderChrome.kt', 'ReadingScreen.kt'):
                self.assertIn('shared/src/commonMain/kotlin/dev/leaf/reader/ui/' + filename,
                              archive.namelist())
            self.assertIn('UPGRADE-v0.5.md', archive.namelist())
            self.assertFalse(any(name.startswith('.leaf-upgrade-backup/') for name in archive.namelist()))

    def test_v04_generation_still_embeds_v04_version_and_dependency_profile(self):
        self.source_fixture('0.4')
        source, _ = packer.assemble_installer(self.project, '0.4')
        tree = ast.parse(source)
        values = {target.id: ast.literal_eval(node.value)
                  for node in tree.body if isinstance(node, ast.Assign)
                  for target in node.targets if isinstance(target, ast.Name) and
                  target.id in ('VERSION_PATCHES', 'REQUIRED_MATERIAL_DEPENDENCIES') and
                  isinstance(node.value, (ast.Dict, ast.Tuple))}
        self.assertEqual(values['VERSION_PATCHES'], {'MARKETING_VERSION': '0.4.0', 'CURRENT_PROJECT_VERSION': '4'})
        self.assertEqual(values['REQUIRED_MATERIAL_DEPENDENCIES'], packer.MATERIAL_DEPENDENCIES_V04)

    def test_workflow_orders_source_kotlin_ipa_upload_and_swift_tests(self):
        text = (ROOT / '.github/workflows/upgrade-v05.yml').read_text()
        source = text.index('name: Upload complete upgraded source')
        kotlin = text.index('name: Compile shared UI')
        ios = text.index('name: Build and package device IPA')
        ipa = text.index('name: Upload IPA before native')
        swift = text.index('name: Run native streaming importer tests')
        self.assertLess(source, kotlin)
        self.assertLess(kotlin, ios)
        self.assertLess(ios, ipa)
        self.assertLess(ipa, swift)
        self.assertIn('LeafReader-v0.5-upgrade.py', text)
        self.assertIn('persist-credentials: false', text)
        self.assertNotIn('git push', text)


if __name__ == '__main__':
    unittest.main()
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/Models.kt': r'''package dev.leaf.reader

import kotlinx.serialization.Serializable

@Serializable
data class BookChapter(val title: String, val paragraphs: List<String>)

/** Legacy import DTO. Opened books now carry titles only; state.chapter owns the loaded body. */
@Serializable
data class BookDocument(val id: String, val title: String, val author: String = "", val format: String = "TXT", val chapters: List<BookChapter>)

@Serializable
data class ChapterEntry(
    val title: String,
    val fileName: String,
    val paragraphCount: Int,
    val characterCount: Int,
    val sourceChapterIndex: Int? = null,
    val sourceParagraphStart: Int = 0,
)

@Serializable
data class BookManifest(
    val schema: Int = 2,
    val id: String,
    val title: String,
    val author: String = "",
    val format: String = "TXT",
    val revision: String,
    val chapters: List<ChapterEntry>,
) {
    fun metadata(): BookDocument = BookDocument(id, title, author, format, chapters.map { BookChapter(it.title, emptyList()) })
    fun paragraphCount(): Int = chapters.sumOf { it.paragraphCount }
    fun characterCount(): Long = chapters.sumOf { it.characterCount.toLong() }
    fun chapterStart(index: Int): Int = chapters.take(index).sumOf { it.paragraphCount + 1 }
    fun totalItems(): Int = paragraphCount() + chapters.size
}

@Serializable
data class ReadingProgress(
    val itemIndex: Int = 0,
    val scrollOffset: Int = 0,
    val chapterIndex: Int = -1,
    val paragraphIndex: Int = 0,
    val characterOffset: Int = 0,
)

@Serializable
data class ShelfBook(
    val id: String,
    val title: String,
    val author: String,
    val format: String,
    val chapterCount: Int,
    val paragraphCount: Int,
    val addedAt: Long,
    val lastOpenedAt: Long = 0,
    val progress: ReadingProgress = ReadingProgress(),
    val characterCount: Long = 0,
)

@Serializable enum class ReaderTheme { SYSTEM, LIGHT, DARK, SEPIA }
@Serializable enum class ReadingMode { SCROLL, SLIDE, INSTANT }
@Serializable enum class ColumnMode { AUTO, SINGLE, DOUBLE }
@Serializable enum class ShelfLayout { GRID, LIST, COMPACT }
@Serializable enum class ReaderFont { SERIF, SANS, MONO }

@Serializable
data class ReaderSettings(
    val fontSize: Float = 20f,
    val lineHeight: Float = 1.7f,
    val theme: ReaderTheme = ReaderTheme.SYSTEM,
    val readingMode: ReadingMode = ReadingMode.SLIDE,
    val columnMode: ColumnMode = ColumnMode.AUTO,
    val shelfLayout: ShelfLayout = ShelfLayout.GRID,
    val fontFamily: ReaderFont = ReaderFont.SERIF,
    val horizontalMargin: Float = 24f,
    val paragraphSpacing: Float = 12f,
    val letterSpacing: Float = 0f,
    val firstLineIndent: Boolean = true,
    val bold: Boolean = false,
    val autoHideControls: Boolean = true,
    val showReadingFooter: Boolean = true,
) {
    fun sanitized() = copy(
        fontSize = fontSize.finiteOr(20f).coerceIn(14f, 40f),
        lineHeight = lineHeight.finiteOr(1.7f).coerceIn(1.2f, 2.4f),
        horizontalMargin = horizontalMargin.finiteOr(24f).coerceIn(8f, 56f),
        paragraphSpacing = paragraphSpacing.finiteOr(12f).coerceIn(0f, 40f),
        letterSpacing = letterSpacing.finiteOr(0f).coerceIn(-0.5f, 3f),
    )
}
private fun Float.finiteOr(fallback: Float): Float = if (isFinite()) this else fallback

data class LibraryState(
    val books: List<ShelfBook> = emptyList(),
    val currentBook: BookDocument? = null,
    val currentProgress: ReadingProgress = ReadingProgress(),
    val settings: ReaderSettings = ReaderSettings(),
    val busy: Boolean = false,
    val error: String? = null,
    val manifest: BookManifest? = null,
    val chapter: BookChapter? = null,
    val chapterIndex: Int = 0,
    val chapterBusy: Boolean = false,
    val chromeVisible: Boolean = false,
)

@Serializable
internal data class LibrarySnapshot(val schema: Int = 2, val books: List<ShelfBook> = emptyList(), val settings: ReaderSettings = ReaderSettings())
internal val documentIdPattern = Regex("[a-f0-9]{64}")
internal val revisionPattern = Regex("[a-f0-9]{32}")
internal const val MAX_CHAPTER_UNITS = 512 * 1024

internal fun BookManifest.validate() {
    require(schema == 2 && documentIdPattern.matches(id) && revisionPattern.matches(revision)) { "书籍索引版本或标识异常。" }
    require(title.isNotBlank() && title.length <= 1000 && author.length <= 2000) { "书籍信息异常。" }
    require(format in setOf("TXT", "EPUB")) { "支持 TXT 和 EPUB。" }
    require(chapters.isNotEmpty() && chapters.size <= 50000) { "章节数量超出范围。" }
    require(chapters.sumOf { it.paragraphCount.toLong() } in 1L..2_000_000L) { "段落数量超出范围。" }
    require(characterCount() in 1L..(512L * 1024 * 1024)) { "正文数量超出范围。" }
    chapters.forEachIndexed { index, chapter ->
        require(chapter.fileName == "book-$id-$revision-c$index.json") { "章节文件标识异常。" }
        require(chapter.title.length <= 1000 && chapter.paragraphCount in 0..100000 && chapter.characterCount in 0..MAX_CHAPTER_UNITS) { "章节信息异常。" }
    }
    if (chapters.any { it.sourceChapterIndex != null }) {
        require(chapters.all { it.sourceChapterIndex != null } && chapters.first().sourceChapterIndex == 0) { "旧章节映射不完整。" }
        var source = 0
        var start = 0
        chapters.forEach { entry ->
            val index = checkNotNull(entry.sourceChapterIndex)
            if (index != source) {
                require(index == source + 1) { "旧章节映射顺序异常。" }
                source = index; start = 0
            }
            require(index == source && index in 0..49999 && entry.sourceParagraphStart == start) { "旧段落映射异常。" }
            start += entry.paragraphCount
        }
    }
}

internal fun BookChapter.validate(entry: ChapterEntry? = null) {
    require(title.length <= 1000 && paragraphs.size <= 100000) { "章节大小异常。" }
    var units = 0L
    paragraphs.forEach { paragraph ->
        require(paragraph.length <= 16000) { "单段文字过长，请重新导入分段。" }
        units += paragraph.length
    }
    require(units <= MAX_CHAPTER_UNITS) { "章节过长，请使用分章导入。" }
    if (entry != null) require(title == entry.title && paragraphs.size == entry.paragraphCount && units == entry.characterCount.toLong()) { "章节文件与索引不一致。" }
}

internal fun BookDocument.validate() {
    require(documentIdPattern.matches(id)) { "书籍标识异常。" }
    require(title.isNotBlank() && title.length <= 1000 && author.length <= 2000) { "书籍信息异常。" }
    require(format in setOf("TXT", "EPUB") && chapters.isNotEmpty() && chapters.size <= 50000)
    require(chapters.sumOf { it.paragraphs.size.toLong() } in 1L..2_000_000L)
    var units = 0L
    var text = false
    chapters.forEach { chapter ->
        require(chapter.title.length <= 1000)
        chapter.paragraphs.forEach { paragraph ->
            require(paragraph.length <= 16000)
            units += paragraph.length
            if (paragraph.isNotBlank()) text = true
        }
    }
    require(text && units <= 24L * 1024 * 1024) { "旧格式导入仅用于兼容；大书请使用新版分章导入。" }
}

internal fun BookDocument.itemCount(): Int = chapters.sumOf { 1 + it.paragraphs.size }
internal fun ReadingProgress.clamp(itemCount: Int): ReadingProgress = copy(itemIndex = itemIndex.coerceIn(0, (itemCount - 1).coerceAtLeast(0)), scrollOffset = scrollOffset.coerceIn(0, 100000))

internal fun BookManifest.normalize(progress: ReadingProgress): ReadingProgress {
    val global = progress.itemIndex.coerceIn(0, totalItems() - 1)
    var chapterIndex = progress.chapterIndex
    var local = progress.paragraphIndex
    if (chapterIndex !in chapters.indices) {
        var offset = global
        chapterIndex = 0
        for ((index, entry) in chapters.withIndex()) {
            chapterIndex = index
            if (offset <= entry.paragraphCount) break
            offset -= entry.paragraphCount + 1
        }
        local = offset
    }
    val entry = chapters[chapterIndex]
    local = local.coerceIn(0, entry.paragraphCount)
    return progress.copy(itemIndex = chapterStart(chapterIndex) + local, chapterIndex = chapterIndex,
        paragraphIndex = local, characterOffset = progress.characterOffset.coerceAtLeast(0), scrollOffset = progress.scrollOffset.coerceIn(0, 100000))
}

internal fun clampUtf16(text: String, offset: Int): Int {
    val result = offset.coerceIn(0, text.length)
    return if (result > 0 && result < text.length && text[result - 1].isHighSurrogate() && text[result].isLowSurrogate()) result - 1 else result
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ReaderFiles.kt': r'''package dev.leaf.reader

/** App-private storage. writeText must replace atomically or throw without damaging the old file. */
interface ReaderFiles {
    fun readText(name: String): String?
    fun writeText(name: String, value: String)
    fun delete(name: String)
    fun nowMillis(): Long
}

expect fun defaultReaderFiles(): ReaderFiles
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ReaderStore.kt': r'''package dev.leaf.reader

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.random.Random

/** Main-thread state host. Book bodies are stored and loaded one bounded chapter at a time. */
class ReaderStore(
    private val files: ReaderFiles = defaultReaderFiles(),
    private val scope: CoroutineScope = MainScope(),
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.Default,
) {
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val mutableState = MutableStateFlow(LibraryState())
    val state: StateFlow<LibraryState> = mutableState.asStateFlow()
    private val documentOperations = Mutex()
    private val chapterCache = LinkedHashMap<String, BookChapter>()
    private var saveJob: Job? = null
    private var openGeneration = 0L
    private var chapterGeneration = 0L
    private var persistenceBlocked = false

    init { loadLibrary() }

    private fun loadLibrary() {
        try {
            val raw = files.readText("library.json") ?: return
            val snapshot = json.decodeFromString<LibrarySnapshot>(raw)
            require(snapshot.schema in 1..2) { "书库版本较新，请使用匹配的应用版本。" }
            require(snapshot.books.size <= 10000)
            require(snapshot.books.all {
                documentIdPattern.matches(it.id) && it.title.isNotBlank() && it.chapterCount in 1..50000 &&
                    it.paragraphCount in 1..2_000_000 && it.format in setOf("TXT", "EPUB")
            })
            require(snapshot.books.map { it.id }.distinct().size == snapshot.books.size)
            if (snapshot.schema == 1 && files.readText("library.v1-backup.json") == null) {
                files.writeText("library.v1-backup.json", raw)
            }
            mutableState.value = LibraryState(
                books = snapshot.books.map { it.copy(progress = it.progress.clamp(it.paragraphCount + it.chapterCount)) },
                settings = snapshot.settings.sanitized(),
            )
        } catch (_: Exception) {
            persistenceBlocked = true
            mutableState.value = LibraryState(error = "书库索引读取失败，原文件已保留；已暂停自动覆盖，请先备份应用数据。")
        }
    }

    fun openBook(id: String) {
        if (!documentIdPattern.matches(id) || mutableState.value.books.none { it.id == id }) return
        val generation = ++openGeneration
        ++chapterGeneration
        flush()
        mutableState.value = mutableState.value.copy(busy = true, chapterBusy = false, error = null)
        scope.launch {
            try {
                val oldEntry = mutableState.value.books.firstOrNull { it.id == id } ?: return@launch
                val loaded = withContext(ioDispatcher) {
                    val raw = files.readText(manifestName(id))
                    if (raw != null) {
                        val manifest = json.decodeFromString<BookManifest>(raw).also { it.validate(); require(it.id == id) }
                        manifest to legacyAwareProgress(manifest, oldEntry.progress)
                    } else {
                        val legacy = files.readText("book-$id.json") ?: error("书籍副本缺失，请重新导入。")
                        val document = json.decodeFromString<BookDocument>(legacy).also { it.validate(); require(it.id == id) }
                        val migrated = createChapterFiles(document)
                        files.writeText(manifestName(id), json.encodeToString(migrated))
                        migrated to legacyAwareProgress(migrated, oldEntry.progress)
                    }
                }
                if (generation != openGeneration || mutableState.value.books.none { it.id == id }) return@launch
                val manifest = loaded.first
                val progress = loaded.second
                mutableState.value = mutableState.value.copy(
                    books = mutableState.value.books.map { if (it.id == id) it.copy(lastOpenedAt = files.nowMillis(),
                        chapterCount = manifest.chapters.size, paragraphCount = manifest.paragraphCount(),
                        characterCount = manifest.characterCount(), progress = progress) else it },
                    currentBook = manifest.metadata(), manifest = manifest, chapter = null,
                    chapterIndex = progress.chapterIndex, currentProgress = progress, busy = false,
                    chapterBusy = true, chromeVisible = false,
                )
                persistSnapshot()
                requestChapter(manifest, progress)
            } catch (e: Exception) {
                if (e is CancellationException) throw e
                if (generation == openGeneration) mutableState.value = mutableState.value.copy(busy = false,
                    chapterBusy = false, error = "打开失败：${e.message.orEmpty().take(160)}")
            }
        }
    }

    fun selectChapter(index: Int, atEnd: Boolean = false) {
        val manifest = mutableState.value.manifest ?: return
        if (index !in manifest.chapters.indices) return
        val local = if (atEnd) manifest.chapters[index].paragraphCount else 0
        val target = ReadingProgress(manifest.chapterStart(index) + local, 0, index, local,
            if (atEnd) Int.MAX_VALUE else 0)
        requestChapter(manifest, target)
    }

    private fun requestChapter(manifest: BookManifest, progress: ReadingProgress) {
        val generation = ++chapterGeneration
        val index = progress.chapterIndex.coerceIn(manifest.chapters.indices)
        mutableState.value = mutableState.value.copy(chapter = null, chapterIndex = index,
            currentProgress = progress, chapterBusy = true)
        scope.launch {
            try {
                val entry = manifest.chapters[index]
                val chapter = chapterCache[entry.fileName] ?: withContext(ioDispatcher) { readChapter(entry) }
                if (generation != chapterGeneration || mutableState.value.manifest?.revision != manifest.revision ||
                    mutableState.value.currentBook?.id != manifest.id) return@launch
                cache(entry.fileName, chapter)
                val local = progress.paragraphIndex.coerceIn(0, chapter.paragraphs.size)
                val text = if (local == 0) chapter.title else chapter.paragraphs[local - 1]
                val restored = progress.copy(chapterIndex = index, paragraphIndex = local,
                    itemIndex = manifest.chapterStart(index) + local, characterOffset = clampUtf16(text, progress.characterOffset))
                mutableState.value = mutableState.value.copy(chapter = chapter, chapterBusy = false, currentProgress = restored,
                    books = mutableState.value.books.map { if (it.id == manifest.id) it.copy(progress = restored) else it })
                scheduleSave()
            } catch (e: Exception) {
                if (e is CancellationException) throw e
                if (generation == chapterGeneration) mutableState.value = mutableState.value.copy(chapterBusy = false,
                    error = "章节加载失败：${e.message.orEmpty().take(120)}")
            }
        }
    }

    private fun readChapter(entry: ChapterEntry): BookChapter {
        val raw = files.readText(entry.fileName) ?: error("章节文件缺失，请重新导入这本书。")
        require(raw.length <= 4 * 1024 * 1024) { "章节文件超过分章上限。" }
        return json.decodeFromString<BookChapter>(raw).also { it.validate(entry) }
    }

    private fun cache(name: String, chapter: BookChapter) {
        chapterCache.remove(name)
        chapterCache[name] = chapter
        while (chapterCache.size > 3) chapterCache.remove(chapterCache.keys.first())
    }

    fun closeBook() {
        ++openGeneration; ++chapterGeneration
        flush()
        chapterCache.clear()
        mutableState.value = mutableState.value.copy(currentBook = null, manifest = null, chapter = null,
            busy = false, chapterBusy = false, chromeVisible = false)
    }

    fun setChromeVisible(visible: Boolean) { mutableState.value = mutableState.value.copy(chromeVisible = visible) }

    fun updateChapterProgress(paragraphIndex: Int, characterOffset: Int = 0, scrollOffset: Int = 0) {
        val value = mutableState.value
        val manifest = value.manifest ?: return
        val chapter = value.chapter ?: return
        if (value.chapterBusy || value.busy) return
        val local = paragraphIndex.coerceIn(0, chapter.paragraphs.size)
        val text = if (local == 0) chapter.title else chapter.paragraphs[local - 1]
        val progress = ReadingProgress(manifest.chapterStart(value.chapterIndex) + local,
            scrollOffset.coerceIn(0, 100000), value.chapterIndex, local, clampUtf16(text, characterOffset))
        if (progress == value.currentProgress) return
        mutableState.value = value.copy(currentProgress = progress,
            books = value.books.map { if (it.id == manifest.id) it.copy(progress = progress) else it })
        scheduleSave()
    }

    /** Compatibility for old global flattened coordinates; new renderers use chapter anchors. */
    fun updateProgress(itemIndex: Int, scrollOffset: Int) {
        val manifest = mutableState.value.manifest ?: return
        val progress = manifest.normalize(ReadingProgress(itemIndex, scrollOffset))
        if (progress.chapterIndex != mutableState.value.chapterIndex) {
            requestChapter(manifest, progress)
        } else updateChapterProgress(progress.paragraphIndex, 0, scrollOffset)
    }

    fun updateSettings(settings: ReaderSettings) {
        mutableState.value = mutableState.value.copy(settings = settings.sanitized())
        scheduleSave()
    }

    /** Legacy bridge retained for old callers/tests. Native large-file import uses importManifestJson. */
    fun importBookJson(raw: String) {
        if (persistenceBlocked) { reportError("书库索引异常，已保留旧数据并暂停修改。"); return }
        mutableState.value = mutableState.value.copy(busy = true, error = null)
        scope.launch {
            documentOperations.withLock {
                try {
                    val manifest = withContext(ioDispatcher) {
                        require(raw.length <= 96 * 1024 * 1024) { "请使用新版分章导入大文件。" }
                        val document = json.decodeFromString<BookDocument>(raw).also { it.validate() }
                        files.writeText("book-${document.id}.json", raw)
                        createChapterFiles(document)
                    }
                    publishManifest(manifest)
                } catch (e: Exception) {
                    importFailure(e)
                }
            }
        }
    }

    /** Only small manifest metadata crosses Swift/Kotlin; chapter bodies already exist on disk. */
    fun importManifestJson(raw: String) {
        if (persistenceBlocked) { reportError("书库索引异常，已保留旧数据并暂停修改。"); return }
        mutableState.value = mutableState.value.copy(busy = true, error = null)
        scope.launch {
            documentOperations.withLock {
                try {
                    val manifest = withContext(ioDispatcher) {
                        require(raw.length <= 16 * 1024 * 1024) { "书籍目录元数据过大。" }
                        json.decodeFromString<BookManifest>(raw).also { it.validate() }
                    }
                    withContext(ioDispatcher) {
                        readChapter(manifest.chapters.first())
                        if (manifest.chapters.size > 1) readChapter(manifest.chapters.last())
                    }
                    publishManifest(manifest)
                } catch (e: Exception) {
                    importFailure(e)
                }
            }
        }
    }

    private fun publishManifest(manifest: BookManifest): Boolean {
        manifest.validate()
        val name = manifestName(manifest.id)
        val previousRaw = files.readText(name)
        val previousState = mutableState.value
        try {
            files.writeText(name, json.encodeToString(manifest))
            val existing = previousState.books.firstOrNull { it.id == manifest.id }
            val progress = legacyAwareProgress(manifest, existing?.progress ?: ReadingProgress())
            val entry = ShelfBook(manifest.id, manifest.title, manifest.author, manifest.format,
                manifest.chapters.size, manifest.paragraphCount(), existing?.addedAt ?: files.nowMillis(),
                existing?.lastOpenedAt ?: 0, progress, manifest.characterCount())
            mutableState.value = previousState.copy(books = if (existing == null) previousState.books + entry else
                previousState.books.map { if (it.id == manifest.id) entry else it }, busy = false)
            if (!persistSnapshot()) {
                mutableState.value = mutableState.value.copy(books = previousState.books)
                if (previousRaw == null) files.delete(name) else files.writeText(name, previousRaw)
                return false
            }
            return true
        } catch (e: Exception) {
            mutableState.value = previousState.copy(busy = false, error = "导入保存失败，旧书架已保留。")
            if (previousRaw != null) runCatching { files.writeText(name, previousRaw) }
            throw e
        }
    }

    private fun importFailure(e: Exception) {
        if (e is CancellationException) throw e
        mutableState.value = mutableState.value.copy(busy = false, error = "导入失败：${e.message.orEmpty().take(160)}")
    }

    private fun createChapterFiles(document: BookDocument): BookManifest {
        val revision = Random.nextBytes(16).joinToString("") { it.toUByte().toString(16).padStart(2, '0') }
        val entries = mutableListOf<ChapterEntry>()
        document.chapters.forEachIndexed { sourceIndex, source ->
            var part = mutableListOf<String>()
            var units = 0
            var sourceStart = 0
            fun flushPart(force: Boolean = false) {
                if (part.isEmpty() && !force) return
                val title = if (sourceStart == 0) source.title else "${source.title.take(990)}（续）"
                val file = "book-${document.id}-$revision-c${entries.size}.json"
                val chapter = BookChapter(title, part.toList())
                chapter.validate()
                files.writeText(file, json.encodeToString(chapter))
                entries += ChapterEntry(title, file, part.size, units, sourceIndex, sourceStart)
                sourceStart += part.size; part = mutableListOf(); units = 0
            }
            source.paragraphs.forEach { paragraph ->
                if (units + paragraph.length > 256 * 1024 || part.size >= 2000) flushPart()
                part += paragraph; units += paragraph.length
            }
            flushPart(force = source.paragraphs.isEmpty())
        }
        return BookManifest(id = document.id, title = document.title, author = document.author,
            format = document.format, revision = revision, chapters = entries).also { it.validate() }
    }

    /** A manifest may already be durable while cancellation/disk failure left the shelf in v1 coordinates. */
    private fun legacyAwareProgress(manifest: BookManifest, old: ReadingProgress): ReadingProgress {
        if (old.chapterIndex >= 0 || manifest.chapters.any { it.sourceChapterIndex == null }) return manifest.normalize(old)
        val sourceCounts = linkedMapOf<Int, Int>()
        manifest.chapters.forEach { entry ->
            val source = checkNotNull(entry.sourceChapterIndex)
            sourceCounts[source] = (sourceCounts[source] ?: 0) + entry.paragraphCount
        }
        var remaining = old.itemIndex.coerceIn(0, sourceCounts.values.sum() + sourceCounts.size - 1)
        var sourceIndex = 0
        for ((source, count) in sourceCounts) {
            sourceIndex = source
            if (remaining <= count) break
            remaining -= count + 1
        }
        val paragraph = (remaining - 1).coerceAtLeast(0)
        val target = if (remaining == 0) manifest.chapters.indexOfFirst { it.sourceChapterIndex == sourceIndex }
            else manifest.chapters.indexOfLast { it.sourceChapterIndex == sourceIndex && it.sourceParagraphStart <= paragraph }
        check(target >= 0)
        val local = if (remaining == 0) 0 else paragraph - manifest.chapters[target].sourceParagraphStart + 1
        return manifest.normalize(old.copy(itemIndex = manifest.chapterStart(target) + local, chapterIndex = target,
            paragraphIndex = local, characterOffset = 0))
    }

    fun deleteBook(id: String) {
        if (persistenceBlocked || !documentIdPattern.matches(id)) return
        scope.launch {
            documentOperations.withLock {
                val previous = mutableState.value
                if (previous.books.none { it.id == id }) return@withLock
                ++openGeneration; ++chapterGeneration; saveJob?.cancel()
                val removingCurrent = previous.currentBook?.id == id
                mutableState.value = previous.copy(books = previous.books.filterNot { it.id == id },
                    currentBook = previous.currentBook?.takeUnless { it.id == id },
                    manifest = if (removingCurrent) null else previous.manifest,
                    chapter = if (removingCurrent) null else previous.chapter, busy = false, chapterBusy = false)
                if (!persistSnapshot()) { mutableState.value = previous.copy(error = mutableState.value.error); return@withLock }
                try {
                    withContext(ioDispatcher) {
                        val raw = files.readText(manifestName(id))
                        if (raw != null) {
                            val manifest = json.decodeFromString<BookManifest>(raw).also { it.validate(); require(it.id == id) }
                            manifest.chapters.forEach { files.delete(it.fileName) }
                            files.delete(manifestName(id))
                        }
                        files.delete("book-$id.json")
                    }
                    chapterCache.clear()
                } catch (e: Exception) {
                    if (e is CancellationException) throw e
                    reportError("已移出书架，部分缓存仍保留。")
                }
            }
        }
    }

    fun dismissError() { mutableState.value = mutableState.value.copy(error = null) }
    fun reportError(message: String) { mutableState.value = mutableState.value.copy(error = message.take(300)) }
    fun flush() { saveJob?.cancel(); saveJob = null; persistSnapshot() }
    private fun scheduleSave() { saveJob?.cancel(); saveJob = scope.launch { delay(700); persistSnapshot() } }
    private fun persistSnapshot(): Boolean {
        if (persistenceBlocked) return false
        return try {
            val value = mutableState.value
            files.writeText("library.json", json.encodeToString(LibrarySnapshot(books = value.books, settings = value.settings)))
            true
        } catch (_: Exception) { reportError("保存失败，请检查可用存储空间；旧索引未主动清除。"); false }
    }
    private fun manifestName(id: String): String = "book-$id.manifest.json"
}

object ReaderRuntime {
    val store: ReaderStore by lazy { ReaderStore() }
    fun importBook(json: String) { store.importBookJson(json) }
    fun importManifest(json: String) { store.importManifestJson(json) }
    fun reportError(message: String) { store.reportError(message) }
    fun flush() { store.flush() }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ContentsScreen.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.paneTitle
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.BookDocument
import dev.leaf.reader.BookManifest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.theme.MiuixTheme

/** Metadata-only filtering; positions always retain their real chapter index, even in reverse order. */
internal fun contentsChapterIndices(titles: List<String>, query: String, descending: Boolean): List<Int> {
    val term = query.trim()
    val numbered = term.toIntOrNull()?.takeIf { it > 0 }?.minus(1)
    val matches = titles.indices.filter { index ->
        term.isEmpty() || index == numbered ||
            titles[index].ifBlank { "第 ${index + 1} 章" }.contains(term, ignoreCase = true)
    }
    return if (descending) matches.asReversed() else matches
}

internal fun contentsChapterPosition(indices: List<Int>, chapterIndex: Int): Int? =
    indices.indexOf(chapterIndex).takeIf { it >= 0 }

/** Keyboard-reduced / landscape / large-font windows favour the chapter list over decoration. */
internal fun compactContentsLayout(heightDp: Float, fontScale: Float): Boolean =
    heightDp < 520f || heightDp / fontScale.coerceAtLeast(1f) < 480f

// The requested 60dp * 2/3 = 40dp visual density is floored at a 44dp touch target.
// No maximum height: long titles and Dynamic Type are allowed to grow the row.
internal const val ContentsRowMinimumHeightDp = 44f

private data class ContentsResult(val query: String, val descending: Boolean, val indices: List<Int>)

/**
 * Full-height contents page, not a small dialog squeezed under a bottom-sheet title.
 * All rows are lazy. Search works on title metadata only and never loads chapter bodies.
 */
@Composable
internal fun ContentsScreen(
    book: BookDocument,
    manifest: BookManifest?,
    currentChapter: Int,
    onSelectChapter: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    val titles = remember(book.chapters, manifest?.revision) {
        if (manifest != null) manifest.chapters.map { it.title }
        else book.chapters.map { it.title }
    }
    val focusManager = LocalFocusManager.current
    val closePage = { focusManager.clearFocus(); onDismiss() }
    val total = titles.size
    val current = currentChapter.coerceIn(0, (total - 1).coerceAtLeast(0))
    val currentTitle = titles.getOrNull(current)?.ifBlank { "第 ${current + 1} 章" } ?: "暂无章节"
    var tab by remember(book.id) { mutableIntStateOf(0) }
    var query by remember(book.id) { mutableStateOf("") }
    var descending by remember(book.id) { mutableStateOf(false) }
    var showCounts by remember(book.id) { mutableStateOf(true) }
    var denseRows by remember(book.id) { mutableStateOf(false) }
    var pendingChapter by remember(book.id) { mutableStateOf<Int?>(current) }
    val list = rememberLazyListState(initialFirstVisibleItemIndex = current)
    var result by remember(titles) { mutableStateOf(ContentsResult("", false, titles.indices.toList())) }
    val trimmedQuery = query.trim()
    val filtering = result.query != trimmedQuery || result.descending != descending
    LaunchedEffect(titles, trimmedQuery, descending) {
        if (trimmedQuery.isNotEmpty()) delay(140)
        result = ContentsResult(trimmedQuery, descending,
            withContext(Dispatchers.Default) { contentsChapterIndices(titles, trimmedQuery, descending) })
    }
    LaunchedEffect(result, pendingChapter, tab) {
        val target = pendingChapter ?: return@LaunchedEffect
        if (filtering || tab != 0) return@LaunchedEffect
        if (result.indices.isNotEmpty()) {
            // Direct lookup/jump is bounded even for 50,000 chapters; no animated traversal.
            list.scrollToItem(contentsChapterPosition(result.indices, target) ?: 0)
        }
        pendingChapter = null
    }
    val locateCurrent: () -> Unit = {
        query = ""
        tab = 0
        pendingChapter = current
    }
    BoxWithConstraints(
        Modifier.fillMaxSize().background(MiuixTheme.colorScheme.surfaceContainer)
            .windowInsetsPadding(WindowInsets.safeDrawing).imePadding()
            .pointerInput(Unit) { detectTapGestures { /* Modal page consumes blank-area taps. */ } }
            .semantics { paneTitle = "书籍目录" },
    ) {
        val compact = compactContentsLayout(maxHeight.value, LocalDensity.current.fontScale)
        Column(Modifier.widthIn(max = 920.dp).fillMaxSize().align(Alignment.TopCenter)) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = if (compact) 6.dp else 12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                if (!compact) ContentsCover(book.title)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(book.title, fontSize = if (compact) 16.sp else 18.sp, fontWeight = FontWeight.SemiBold,
                        maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.semantics { heading() })
                    if (!compact) Text(currentTitle, fontSize = 13.sp,
                        color = MiuixTheme.colorScheme.onSurfaceVariantSummary, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                if (!compact) CountPill("${if (total > 0) current + 1 else 0} / $total")
                if (compact) TextButton(if (tab == 0) "信息" else "目录", { focusManager.clearFocus(); tab = if (tab == 0) 1 else 0 },
                    minHeight = 48.dp)
                ReaderIconButton(Glyph.CLOSE, "关闭目录，返回阅读", closePage)
            }
            if (!compact) {
                TabRowWithContour(tabs = listOf("目录", "信息", "书签", "笔记"), selectedTabIndex = tab,
                    onTabSelected = { focusManager.clearFocus(); tab = it }, height = 48.dp, minWidth = 52.dp,
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp))
                Spacer(Modifier.height(12.dp))
            }
            if (tab == 0) {
                Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    TextField(value = query, onValueChange = {
                        query = it.take(200)
                        pendingChapter = if (it.isBlank()) current else -1
                    }, modifier = Modifier.weight(1f).heightIn(min = 48.dp)
                        .semantics { contentDescription = "按章节标题或章序号搜索" },
                        insideMargin = DpSize(12.dp, 10.dp), cornerRadius = 24.dp,
                        label = "搜索章节或序号", useLabelAsPlaceholder = true, singleLine = true,
                        textStyle = MiuixTheme.textStyles.body2,
                        colors = TextFieldDefaults.textFieldColors(backgroundColor = MiuixTheme.colorScheme.surfaceContainerHigh),
                        leadingIcon = {
                            Box(Modifier.padding(start = 14.dp, end = 6.dp)) {
                                MiuixGlyph(Glyph.SEARCH, MiuixTheme.colorScheme.onSurfaceVariantSummary, 20.dp)
                            }
                        })
                    if (compact) {
                        ReaderIconButton(Glyph.REFRESH, "清除搜索并定位当前章节", locateCurrent)
                        ReaderIconButton(Glyph.SORT, if (descending) "切换为正序" else "切换为倒序", {
                            descending = !descending
                            pendingChapter = current
                        }, highlighted = descending)
                    } else if (query.isNotEmpty()) {
                        ReaderIconButton(Glyph.CLOSE, "清除章节搜索", { query = ""; pendingChapter = current })
                    }
                }
                if (!compact) {
                    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text(if (filtering) "正在筛选…" else "${result.indices.size} 章", Modifier.weight(1f),
                            fontSize = 13.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
                        ReaderIconButton(Glyph.TAG, if (showCounts) "隐藏章节字数" else "显示章节字数",
                            { showCounts = !showCounts }, highlighted = showCounts)
                        ReaderIconButton(Glyph.SORT, if (descending) "切换为正序" else "切换为倒序", {
                            descending = !descending
                            pendingChapter = current
                        }, highlighted = descending)
                        ReaderIconButton(Glyph.MORE, if (denseRows) "切换宽松行距" else "切换紧凑行距",
                            { denseRows = !denseRows }, highlighted = denseRows)
                        ReaderIconButton(Glyph.REFRESH, "清除搜索并定位当前章节", locateCurrent)
                    }
                    CurrentContentsChapter(currentTitle, manifest?.chapters?.getOrNull(current)?.characterCount,
                        closePage, Modifier.padding(horizontal = 16.dp, vertical = 4.dp))
                } else {
                    Text(if (filtering) "正在筛选…" else "${result.indices.size} 章 · 当前 ${current + 1}/$total",
                        Modifier.padding(horizontal = 20.dp, vertical = 6.dp), fontSize = 12.sp,
                        color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
                }
                if (result.indices.isEmpty()) {
                    Column(Modifier.weight(1f).fillMaxWidth().padding(24.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(if (total == 0) "这本书没有目录" else "没有匹配的章节", fontWeight = FontWeight.SemiBold)
                        if (query.isNotEmpty()) TextButton("清除搜索", { query = ""; pendingChapter = current }, minHeight = 48.dp)
                        TextButton("返回阅读", closePage, minHeight = 48.dp)
                    }
                } else {
                    LazyColumn(state = list, modifier = Modifier.weight(1f).fillMaxWidth(),
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        items(result.indices.size, key = { result.indices[it] }) { position ->
                            val index = result.indices[position]
                            ContentsChapterRow(index, titles[index].ifBlank { "第 ${index + 1} 章" },
                                if (showCounts) manifest?.chapters?.getOrNull(index)?.characterCount else null,
                                index == current, denseRows, {
                                    // Selecting the active row must preserve its exact text anchor.
                                    if (index == current) closePage() else {
                                        focusManager.clearFocus()
                                        onSelectChapter(index)
                                    }
                                })
                        }
                    }
                }
            } else {
                Column(Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(24.dp),
                    verticalArrangement = Arrangement.spacedBy(18.dp)) {
                    if (tab == 1) {
                        ContentsInfo("书名", book.title)
                        ContentsInfo("作者", book.author.ifBlank { "佚名" })
                        ContentsInfo("格式", book.format)
                        ContentsInfo("章节", "$total 章")
                        manifest?.let { ContentsInfo("正文字符", it.characterCount().toString()) }
                        ContentsInfo("当前章节", currentTitle)
                        TextButton("定位当前章节", locateCurrent, Modifier.fillMaxWidth(), minHeight = 48.dp)
                    } else {
                        Text(if (tab == 2) "尚未启用书签" else "尚未启用笔记", fontWeight = FontWeight.SemiBold)
                        Text("当前版本提供章节目录与阅读位置恢复；这里没有已保存的书签或笔记。",
                            fontSize = 14.sp, lineHeight = 22.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
                        TextButton("返回目录", { tab = 0 }, Modifier.fillMaxWidth(), minHeight = 48.dp)
                    }
                }
            }
        }
    }
}

@Composable
private fun ContentsCover(title: String) {
    Box(Modifier.width(42.dp).height(58.dp).clip(RoundedCornerShape(8.dp))
        .background(MiuixTheme.colorScheme.primary.copy(alpha = 0.14f)), contentAlignment = Alignment.Center) {
        Text(title.take(2).ifBlank { "书" }, fontSize = 15.sp, fontWeight = FontWeight.SemiBold,
            color = MiuixTheme.colorScheme.primary, maxLines = 1)
    }
}

@Composable
private fun CurrentContentsChapter(title: String, count: Int?, onClick: () -> Unit, modifier: Modifier) {
    Row(modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp))
        .background(MiuixTheme.colorScheme.surfaceContainerHigh)
        .clickable(role = Role.Button, onClick = onClick).heightIn(min = ContentsRowMinimumHeightDp.dp)
        .padding(horizontal = 12.dp, vertical = 4.dp)
        .semantics { contentDescription = "返回当前章节：$title"; stateDescription = "当前章节" },
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f)) {
            Text("正在阅读", fontSize = 11.sp, color = MiuixTheme.colorScheme.primary)
            Text(title, fontSize = 14.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        count?.let { CountPill("${it}字", container = MiuixTheme.colorScheme.primaryContainer,
            content = MiuixTheme.colorScheme.onPrimaryContainer) }
    }
}

@Composable
private fun ContentsChapterRow(index: Int, title: String, count: Int?, current: Boolean,
    dense: Boolean, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp))
        .then(if (current) Modifier.background(MiuixTheme.colorScheme.primary.copy(alpha = 0.10f)) else Modifier)
        .clickable(role = Role.Button, onClick = onClick).heightIn(min = ContentsRowMinimumHeightDp.dp)
        .padding(horizontal = 12.dp, vertical = 2.dp)
        .semantics { if (current) stateDescription = "当前章节"; contentDescription = "第 ${index + 1} 项，$title" },
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Text((index + 1).toString(), Modifier.widthIn(min = 28.dp), fontSize = 12.sp,
            color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
        Text(title, Modifier.weight(1f), fontSize = 15.sp,
            fontWeight = if (current) FontWeight.SemiBold else FontWeight.Normal,
            maxLines = if (dense) 1 else 2, overflow = TextOverflow.Ellipsis,
            color = if (current) MiuixTheme.colorScheme.primary else MiuixTheme.colorScheme.onSurface)
        count?.let { CountPill("${it}字") }
    }
}

@Composable
private fun ContentsInfo(label: String, value: String) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, fontSize = 12.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
        Text(value, fontSize = 16.sp, lineHeight = 24.sp)
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/MiuixAtoms.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import top.yukonga.miuix.kmp.blur.Backdrop
import top.yukonga.miuix.kmp.blur.progressiveTextureBlur
import top.yukonga.miuix.kmp.blur.textureBlur
import top.yukonga.miuix.kmp.blur.isRuntimeShaderSupported
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.theme.lightColorScheme
import top.yukonga.miuix.kmp.theme.darkColorScheme

/** Same curves the reference sheets use: open 360ms ease-out, close 280ms ease-in. */
internal val MiuixEaseOut = CubicBezierEasing(0.22f, 1f, 0.36f, 1f)
internal val MiuixEaseIn = CubicBezierEasing(0.4f, 0f, 0.2f, 1f)
internal const val BookOpenMillis = 360
internal const val BookCloseMillis = 280

internal fun <T> bookOpen() = tween<T>(BookOpenMillis, easing = MiuixEaseOut)
internal fun <T> bookClose() = tween<T>(BookCloseMillis, easing = MiuixEaseIn)

/** Touch target spacing from the reference: 12dp between floating controls. */
internal val ControlGap = 12.dp
internal val PageMargin = 20.dp
internal val CircleControlSize = 40.dp

/** A captured sibling content layer is progressively blurred behind the header.
 * The translucent surface wash is also the fallback where runtime shaders are unavailable.
 * Capture must exclude this header to avoid sampling the effect into itself.
 */
@Composable
internal fun GradientHeaderScrim(backdrop: Backdrop? = null, content: @Composable BoxScope.() -> Unit) {
    val surface = MiuixTheme.colorScheme.surface
    val useBlur = backdrop != null && isRuntimeShaderSupported()
    val blur = if (useBlur) {
        Modifier.progressiveTextureBlur(backdrop = backdrop, shape = RectangleShape, blurRadius = 22f)
    } else Modifier
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .then(blur)
            .background(
                Brush.verticalGradient(
                    0f to surface.copy(alpha = if (useBlur) 0.84f else 1f),
                    0.55f to surface.copy(alpha = if (useBlur) 0.72f else 0.94f),
                    0.82f to surface.copy(alpha = 0.42f),
                    1f to Color.Transparent,
                ),
            ),
    ) {
        content()
    }
}

/** Circular 40dp Miuix floating control (squircle-ish pill, soft shadow, generous gap). */
@Composable
internal fun MiuixCircleButton(
    glyph: Glyph,
    description: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    size: Dp = CircleControlSize,
    container: Color = MiuixTheme.colorScheme.surfaceContainerHigh,
    tint: Color = MiuixTheme.colorScheme.onSurface,
) {
    Box(
        modifier = modifier
            .size(size)
            .clip(RoundedCornerShape(size / 2))
            .background(container)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics {
                role = Role.Button
                contentDescription = description
            },
        contentAlignment = Alignment.Center,
    ) {
        MiuixGlyph(glyph, if (enabled) tint else tint.copy(alpha = 0.4f), size * 0.55f)
    }
}

/** Pill used by the floating dock rows. */
@Composable
internal fun MiuixDockPill(
    modifier: Modifier = Modifier,
    backdrop: Backdrop? = null,
    verticalPadding: Dp = 10.dp,
    horizontalPadding: Dp = 16.dp,
    content: @Composable RowScope.() -> Unit,
) {
    val shape = RoundedCornerShape(999.dp)
    val useBlur = backdrop != null && isRuntimeShaderSupported()
    val material = if (useBlur) Modifier.textureBlur(backdrop, shape, blurRadius = 18f, noiseCoefficient = 0f) else Modifier
    Row(
        modifier = modifier
            .clip(shape)
            .then(material)
            .background(MiuixTheme.colorScheme.surfaceContainerHigh.copy(alpha = if (useBlur) 0.78f else 1f))
            .padding(horizontal = horizontalPadding, vertical = verticalPadding),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        content = content,
    )
}

/** Selected/unselected pill tab for the bottom dock. */
@Composable
internal fun DockTab(
    glyph: Glyph,
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val container = if (selected) MiuixTheme.colorScheme.primary else Color.Transparent
    val content = if (selected) MiuixTheme.colorScheme.onPrimary else MiuixTheme.colorScheme.onSurfaceVariantSummary
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(999.dp))
            .background(container)
            .clickable(onClick = onClick)
            .padding(horizontal = 20.dp, vertical = 10.dp)
            .semantics { contentDescription = label },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        MiuixGlyph(glyph, content, 20.dp)
        Text(label, color = content, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1)
    }
}

/** Small rounded count badge (chapter word counts, progress). */
@Composable
internal fun CountPill(
    text: String,
    modifier: Modifier = Modifier,
    container: Color = MiuixTheme.colorScheme.surfaceContainerHighest,
    content: Color = MiuixTheme.colorScheme.onSurfaceVariantSummary,
) {
    Text(
        text = text,
        modifier = modifier
            .clip(RoundedCornerShape(999.dp))
            .background(container)
            .padding(horizontal = 10.dp, vertical = 3.dp),
        color = content,
        fontSize = 12.sp,
        fontWeight = FontWeight.Medium,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
    )
}

/** Miuix-coloured reader themes; sepia keeps a warm paper wash over the light scheme. */
@Composable
internal fun readerColorScheme(theme: dev.leaf.reader.ReaderTheme): top.yukonga.miuix.kmp.theme.Colors = when (theme) {
    dev.leaf.reader.ReaderTheme.SEPIA -> lightColorScheme(
        primary = Color(0xFF706044),
        onPrimary = Color(0xFFFFFFFF),
        surface = Color(0xFFF3ECD9),
        onSurface = Color(0xFF473E30),
        surfaceContainer = Color(0xFFFBF5E7),
        surfaceContainerHigh = Color(0xFFEFE5CE),
        surfaceContainerHighest = Color(0xFFE6DAC0),
        onSurfaceVariantSummary = Color(0xFF6B5F4B),
        background = Color(0xFFF3ECD9),
        onBackground = Color(0xFF473E30),
    )
    dev.leaf.reader.ReaderTheme.LIGHT -> lightColorScheme()
    else -> darkColorScheme()
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/MiuixGlyphs.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Small Canvas glyphs used by the floating controls. Miuix 0.9.4 ships only a
 * narrow icon set, so these keep the controls dependency-free instead of pulling
 * an extra icon artifact into the Kotlin/Native framework.
 */
internal enum class Glyph {
    BACK, SEARCH, ADD, TOC, TUNE, CLOSE, SORT, REFRESH, TAG, MORE, BOOK, SHELVES, GEAR, CHEVRON_UP,
}

@Composable
internal fun MiuixGlyph(glyph: Glyph, tint: Color, size: Dp = 22.dp) {
    Canvas(Modifier.size(size)) {
        val unit = this.size.minDimension / 24f
        val stroke = 2f * unit
        fun at(x: Float, y: Float) = Offset(x * unit, y * unit)
        fun line(x1: Float, y1: Float, x2: Float, y2: Float) =
            drawLine(tint, at(x1, y1), at(x2, y2), strokeWidth = stroke, cap = StrokeCap.Round)
        fun dot(x: Float, y: Float, r: Float = 1.35f) = drawCircle(tint, r * unit, at(x, y))
        when (glyph) {
            Glyph.BACK -> {
                line(14.5f, 5f, 7.5f, 12f)
                line(7.5f, 12f, 14.5f, 19f)
            }
            Glyph.SEARCH -> {
                drawCircle(tint, 6.2f * unit, at(10.5f, 10.5f), style = Stroke(stroke))
                line(15.1f, 15.1f, 20f, 20f)
            }
            Glyph.ADD -> {
                line(12f, 6f, 12f, 18f)
                line(6f, 12f, 18f, 12f)
            }
            Glyph.TOC -> {
                dot(5.5f, 6.5f, 1.2f); line(9f, 6.5f, 19f, 6.5f)
                dot(5.5f, 12f, 1.2f); line(9f, 12f, 19f, 12f)
                dot(5.5f, 17.5f, 1.2f); line(9f, 17.5f, 19f, 17.5f)
            }
            Glyph.TUNE -> {
                line(4f, 7f, 20f, 7f); dot(9f, 7f, 2f)
                line(4f, 12f, 20f, 12f); dot(15f, 12f, 2f)
                line(4f, 17f, 20f, 17f); dot(11.5f, 17f, 2f)
            }
            Glyph.CLOSE -> {
                line(6.5f, 6.5f, 17.5f, 17.5f)
                line(17.5f, 6.5f, 6.5f, 17.5f)
            }
            Glyph.SORT -> {
                line(12f, 4.5f, 12f, 19.5f)
                line(8.5f, 8f, 12f, 4.5f)
                line(15.5f, 8f, 12f, 4.5f)
                line(8.5f, 16f, 12f, 19.5f)
                line(15.5f, 16f, 12f, 19.5f)
            }
            Glyph.REFRESH -> {
                drawArc(
                    color = tint, startAngle = -40f, sweepAngle = 280f, useCenter = false,
                    topLeft = at(4f, 4f), size = androidx.compose.ui.geometry.Size(16f * unit, 16f * unit),
                    style = Stroke(stroke, cap = StrokeCap.Round),
                )
                line(17.5f, 3f, 19.5f, 7f)
                line(19.5f, 7f, 15f, 7.5f)
            }
            Glyph.TAG -> {
                line(9f, 4.5f, 7.5f, 19.5f)
                line(16.5f, 4.5f, 15f, 19.5f)
                line(4.5f, 9.5f, 19.5f, 9.5f)
                line(4f, 15f, 19f, 15f)
            }
            Glyph.MORE -> {
                dot(12f, 5.5f); dot(12f, 12f); dot(12f, 18.5f)
            }
            Glyph.BOOK -> {
                val path = Path().apply {
                    moveTo(6f * unit, 4.5f * unit)
                    lineTo(6f * unit, 19.5f * unit)
                    lineTo(18f * unit, 19.5f * unit)
                    lineTo(18f * unit, 6.5f * unit)
                    lineTo(8.5f * unit, 6.5f * unit)
                }
                drawPath(path, tint, style = Stroke(stroke, cap = StrokeCap.Round))
                line(6f, 16.5f, 18f, 16.5f)
                line(9.5f, 10f, 15f, 10f)
            }
            Glyph.SHELVES -> {
                line(4.5f, 7f, 4.5f, 19f)
                line(11.5f, 5f, 11.5f, 19f)
                line(18.5f, 8f, 18.5f, 19f)
                line(3f, 19f, 21f, 19f)
            }
            Glyph.GEAR -> {
                drawCircle(tint, 3.2f * unit, at(12f, 12f), style = Stroke(stroke))
                for (index in 0 until 8) {
                    val angle = index * (kotlin.math.PI / 4).toFloat()
                    val inner = 6.2f
                    val outer = 9.2f
                    line(
                        12f + kotlin.math.cos(angle) * inner,
                        12f + kotlin.math.sin(angle) * inner,
                        12f + kotlin.math.cos(angle) * outer,
                        12f + kotlin.math.sin(angle) * outer,
                    )
                }
            }
            Glyph.CHEVRON_UP -> {
                line(7f, 14.5f, 12f, 9.5f)
                line(17f, 14.5f, 12f, 9.5f)
            }
        }
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/Pagination.kt': r'''package dev.leaf.reader.ui

import dev.leaf.reader.BookChapter

/** Local item coordinates only: metadata chapters are deliberately not accepted here. */
internal fun chapterReadingTexts(chapter: BookChapter, chapterIndex: Int): List<String> =
    listOf(chapter.title.ifBlank { "第 ${chapterIndex + 1} 章" }) + chapter.paragraphs

/** UTF-16 coordinates in the loaded chapter: heading=0, body paragraphs=1..n. */
internal data class TextAnchor(val paragraphIndex: Int = 0, val characterOffset: Int = 0)

internal data class MeasuredLine(val start: Int, val end: Int, val top: Float, val bottom: Float)
internal data class PageSlice(
    val paragraphIndex: Int,
    val start: Int,
    val end: Int,
    val top: Float,
    val sourceTop: Float,
    val height: Float,
    val lines: List<MeasuredLine>,
)
internal data class MeasuredPage(val columns: List<List<PageSlice>>) {
    val anchor: TextAnchor get() = columns.firstNotNullOfOrNull { column ->
        column.firstOrNull()?.let { TextAnchor(it.paragraphIndex, it.start) }
    } ?: TextAnchor()
}

/** Move a UTF-16 boundary backwards if it would separate a surrogate pair. */
internal fun safeTextOffset(text: String, offset: Int): Int {
    val value = offset.coerceIn(0, text.length)
    return if (value > 0 && value < text.length && text[value].isLowSurrogate() &&
        text[value - 1].isHighSurrogate()) value - 1 else value
}

internal fun clampAnchor(texts: List<String>, anchor: TextAnchor): TextAnchor {
    if (texts.isEmpty()) return TextAnchor()
    val item = anchor.paragraphIndex.coerceIn(0, texts.lastIndex)
    return TextAnchor(item, safeTextOffset(texts[item], anchor.characterOffset))
}

/**
 * Pure chapter-only paginator. The injected callback is the only platform-dependent operation.
 * It measures each item once at the actual column width, not once per candidate substring.
 * Line ranges must cover the original text (including newline characters), without overlaps.
 * Empty paragraphs still occupy a measured line and retain an anchor.
 */
internal fun paginateChapter(
    texts: List<String>,
    columnWidth: Int,
    columnHeight: Float,
    columnCount: Int,
    paragraphSpacing: Float,
    measure: (paragraphIndex: Int, text: String, width: Int) -> List<MeasuredLine>,
): List<MeasuredPage> {
    require(columnWidth > 0 && columnHeight.isFinite() && columnHeight > 0f)
    require(columnCount in 1..2)
    require(paragraphSpacing.isFinite() && paragraphSpacing >= 0f)
    if (texts.isEmpty()) return listOf(MeasuredPage(List(columnCount) { emptyList() }))
    val pages = mutableListOf<MeasuredPage>()
    var columns = MutableList(columnCount) { mutableListOf<PageSlice>() }
    var column = 0
    var y = 0f
    fun advance() {
        y = 0f
        column++
        if (column == columnCount) {
            pages += MeasuredPage(columns.map { it.toList() })
            columns = MutableList(columnCount) { mutableListOf() }
            column = 0
        }
    }
    texts.forEachIndexed { item, text ->
        val lines = measure(item, text, columnWidth)
        require(lines.isNotEmpty()) { "A paragraph must have at least one measured line" }
        var covered = 0
        lines.forEach { line ->
            require(line.start == covered && line.end in line.start..text.length)
            require(safeTextOffset(text, line.start) == line.start && safeTextOffset(text, line.end) == line.end)
            require(line.top.isFinite() && line.bottom.isFinite() && line.bottom > line.top)
            covered = line.end
        }
        require(covered == text.length) { "Measured lines must cover the original text" }
        var first = 0
        while (first < lines.size) {
            if (y >= columnHeight && columns[column].isNotEmpty()) advance()
            val sourceTop = lines[first].top
            val remaining = columnHeight - y
            var until = first
            while (until < lines.size && lines[until].bottom - sourceTop <= remaining + 0.01f) until++
            if (until == first) {
                if (columns[column].isNotEmpty()) {
                    advance()
                    continue
                }
                // Ensure progress even for an oversized accessibility font / tiny viewport.
                until++
            }
            val height = lines[until - 1].bottom - sourceTop
            columns[column] += PageSlice(item, lines[first].start, lines[until - 1].end,
                y, sourceTop, height, lines.subList(first, until).toList())
            y += height
            first = until
            if (first < lines.size) advance()
        }
        y += paragraphSpacing
    }
    if (columns.any { it.isNotEmpty() }) pages += MeasuredPage(columns.map { it.toList() })
    return pages.ifEmpty { listOf(MeasuredPage(List(columnCount) { emptyList() })) }
}

/** Inclusive start, exclusive end: an exact page boundary belongs to the following page. */
internal fun pageForAnchor(pages: List<MeasuredPage>, anchor: TextAnchor): Int {
    pages.forEachIndexed { index, page ->
        page.columns.forEach { column -> column.forEach { slice ->
            if (slice.paragraphIndex == anchor.paragraphIndex &&
                anchor.characterOffset >= slice.start &&
                (anchor.characterOffset < slice.end || slice.start == slice.end)) return index
        } }
    }
    // End-of-paragraph/chapter anchors map to the last fragment of that item.
    return pages.indexOfLast { page -> page.columns.any { column ->
        column.any { it.paragraphIndex <= anchor.paragraphIndex }
    } }.coerceAtLeast(0)
}

internal fun anchorAtY(page: MeasuredPage, y: Float): TextAnchor {
    // In a two-column spread the left column is the reading-order start.
    val slices = page.columns.firstOrNull { it.isNotEmpty() }.orEmpty()
    val slice = slices.lastOrNull { it.top <= y } ?: return page.anchor
    val line = slice.lines.lastOrNull { it.top - slice.sourceTop + slice.top <= y }
    return TextAnchor(slice.paragraphIndex, line?.start ?: slice.start)
}

internal fun yForAnchor(page: MeasuredPage, anchor: TextAnchor): Float =
    page.columns.flatten().firstOrNull { it.paragraphIndex == anchor.paragraphIndex &&
        anchor.characterOffset >= it.start && anchor.characterOffset <= it.end }?.let { slice ->
        val line = slice.lines.lastOrNull { it.start <= anchor.characterOffset }
        slice.top + (line?.top ?: slice.sourceTop) - slice.sourceTop
    } ?: 0f
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderApp.kt': r'''package dev.leaf.reader.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.unit.IntSize
import kotlinx.coroutines.launch
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.Card
import top.yukonga.miuix.kmp.basic.CircularProgressIndicator
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.basic.Scaffold
import top.yukonga.miuix.kmp.basic.TextButton
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.theme.darkColorScheme
import top.yukonga.miuix.kmp.theme.lightColorScheme

/** Keep the shelf mounted under the reading layer. The same progress drives the
 * entire reader surface in both directions; book state survives until exit ends.
 */
@Composable
fun ReaderApp(store: ReaderStore, onImportRequested: () -> Unit) {
    val state by store.state.collectAsState()
    val systemDark = isSystemInDarkTheme()
    val colors = when (state.settings.theme) {
        ReaderTheme.SEPIA -> readerColorScheme(ReaderTheme.SEPIA)
        ReaderTheme.LIGHT -> lightColorScheme()
        ReaderTheme.DARK -> darkColorScheme()
        ReaderTheme.SYSTEM -> if (systemDark) darkColorScheme() else lightColorScheme()
    }
    MiuixTheme(colors = colors) {
        // Root overlay host is needed by global error dialogs. Child screens may
        // use their own local hosts, without consuming the window's safe insets.
        Scaffold(contentWindowInsets = WindowInsets(0, 0, 0, 0)) {
        val shelfState = rememberSaveableStateHolder()
        val scope = rememberCoroutineScope()
        val entrance = remember { Animatable(0f) }
        var rootSize by remember { mutableStateOf(IntSize.Zero) }
        var origin by remember { mutableStateOf<Offset?>(null) }
        var originSize by remember { mutableStateOf(IntSize.Zero) }
        var frozenShelfBooks by remember { mutableStateOf(state.books) }
        var closing by remember { mutableStateOf(false) }
        val book = state.currentBook
        LaunchedEffect(book?.id) {
            closing = false
            if (book != null) {
                entrance.snapTo(0f)
                entrance.animateTo(1f, animationSpec = bookOpen())
            }
        }
        Box(Modifier.fillMaxSize().onSizeChanged { rootSize = it }.background(MiuixTheme.colorScheme.surface)) {
            // Hidden from both touch and accessibility while the reader is on top.
            val shelfBlocker = if (book != null) Modifier
                .clearAndSetSemantics { }
                .pointerInput(book.id) {
                    awaitPointerEventScope { while (true) awaitPointerEvent(PointerEventPass.Initial).changes.forEach { it.consume() } }
                } else Modifier
            Box(Modifier.fillMaxSize().then(shelfBlocker)) {
                shelfState.SaveableStateProvider("shelf") {
                    ShelfScreen(state = if (book == null) state else state.copy(books = frozenShelfBooks),
                        store = store, onImportRequested = onImportRequested,
                        onOpenBook = { id, center ->
                            frozenShelfBooks = state.books
                            origin = center
                            originSize = rootSize
                            store.openBook(id)
                        })
                }
            }
            if (book != null) {
                key(book.id) {
                    val target = origin?.takeIf {
                        originSize == rootSize && rootSize.width > 0 && rootSize.height > 0 &&
                            it.x in 0f..rootSize.width.toFloat() && it.y in 0f..rootSize.height.toFloat()
                    }
                    val progress = entrance.value
                    val startingScale = if (target != null) 0.28f else 0.94f
                    Box(Modifier.fillMaxSize().graphicsLayer {
                        val scale = startingScale + (1f - startingScale) * progress
                        scaleX = scale
                        scaleY = scale
                        alpha = progress
                        translationX = ((target?.x ?: size.width / 2f) - size.width / 2f) * (1f - progress)
                        translationY = ((target?.y ?: size.height / 2f) - size.height / 2f) * (1f - progress)
                    }) {
                        ReadingScreen(state = state, store = store, onRequestClose = {
                            if (!closing) {
                                closing = true
                                // The shelf book list stays frozen during reading, so an unchanged
                                // window can reverse toward the tapped item without a re-sort jump.
                                // A resized or rotated window uses the centered fallback above.
                                val closingBookId = book.id
                                scope.launch {
                                    entrance.animateTo(0f, animationSpec = bookClose())
                                    if (store.state.value.currentBook?.id == closingBookId) store.closeBook()
                                }
                            }
                        })
                    }
                }
                if (closing) {
                    Box(Modifier.fillMaxSize().pointerInput(Unit) {
                        awaitPointerEventScope { while (true) awaitPointerEvent(PointerEventPass.Initial).changes.forEach { it.consume() } }
                    })
                }
            }
            if (state.busy) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.22f))
                        .pointerInput(Unit) {
                            awaitPointerEventScope {
                                while (true) awaitPointerEvent().changes.forEach { it.consume() }
                            }
                        },
                    contentAlignment = Alignment.Center,
                ) {
                    Card(insideMargin = PaddingValues(28.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(16.dp),
                        ) {
                            CircularProgressIndicator(size = 26.dp)
                            Text(
                                "正在整理书页…",
                                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                            )
                        }
                    }
                }
            }
            OverlayDialog(
                show = state.error != null,
                title = "暂时未能完成",
                summary = state.error,
                onDismissRequest = store::dismissError,
            ) {
                TextButton(
                    text = "知道了", onClick = store::dismissError,
                    modifier = Modifier.fillMaxWidth(), minHeight = 48.dp,
                    colors = top.yukonga.miuix.kmp.basic.ButtonDefaults.textButtonColorsPrimary(),
                )
            }
        }
        }
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderChrome.kt': r'''package dev.leaf.reader.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.border
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import top.yukonga.miuix.kmp.basic.IconButton
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.blur.LayerBackdrop
import top.yukonga.miuix.kmp.theme.MiuixTheme

/** Chrome is a sibling overlay: its visibility never changes the measured reading viewport. */
@Composable
internal fun BoxScope.ReaderChrome(
    visible: Boolean,
    title: String,
    progressText: String,
    backdrop: LayerBackdrop,
    onClose: () -> Unit,
    onDirectory: () -> Unit,
    onSettings: () -> Unit,
) {
    AnimatedVisibility(
        visible = visible,
        enter = slideInVertically(tween(ReaderChromeEnterMillis, easing = MiuixEaseOut)) { -it } +
            fadeIn(tween(ReaderChromeEnterMillis)),
        exit = slideOutVertically(tween(ReaderChromeExitMillis, easing = MiuixEaseIn)) { -it } +
            fadeOut(tween(ReaderChromeExitMillis)),
        modifier = Modifier.align(Alignment.TopCenter),
    ) {
        // Shared scrim combines a transparent tint with real miuix-blur sampling of body only.
        GradientHeaderScrim(backdrop = backdrop) {
            Row(
                modifier = Modifier.fillMaxWidth()
                    .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Top + WindowInsetsSides.Horizontal))
                    .padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 20.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                ReaderIconButton(Glyph.BACK, "保存进度并返回书架", onClose)
                Text(title, Modifier.weight(1f), fontSize = 15.sp,
                    color = MiuixTheme.colorScheme.onSurfaceVariantSummary, maxLines = 1,
                    overflow = TextOverflow.Ellipsis)
            }
        }
    }
    AnimatedVisibility(
        visible = visible,
        enter = slideInVertically(tween(ReaderChromeEnterMillis, easing = MiuixEaseOut)) { it } +
            fadeIn(tween(ReaderChromeEnterMillis)),
        exit = slideOutVertically(tween(ReaderChromeExitMillis, easing = MiuixEaseIn)) { it } +
            fadeOut(tween(ReaderChromeExitMillis)),
        modifier = Modifier.align(Alignment.BottomCenter),
    ) {
        Box(
            Modifier.fillMaxWidth()
                .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Bottom + WindowInsetsSides.Horizontal))
                .padding(horizontal = 16.dp, vertical = 12.dp),
            contentAlignment = Alignment.Center,
        ) {
            MiuixDockPill(Modifier.widthIn(max = 640.dp).fillMaxWidth(), backdrop = backdrop,
                verticalPadding = ReaderDockVerticalPaddingDp.dp) {
                ReaderDockAction(Glyph.BOOK, "目录", onDirectory)
                Text(progressText, Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite },
                    fontSize = 12.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                    textAlign = TextAlign.Center, maxLines = 1, overflow = TextOverflow.Ellipsis)
                // Settings is deliberately the rightmost dock action, matching the reader template.
                ReaderDockAction(Glyph.TUNE, "设置", onSettings)
            }
        }
    }
}

/** The shelf's 40dp circle inside a separate 44dp Miuix IconButton touch target. */
@Composable
internal fun ReaderIconButton(
    glyph: Glyph,
    description: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    highlighted: Boolean = false,
    enabled: Boolean = true,
) {
    val colors = MiuixTheme.colorScheme
    IconButton(
        onClick = onClick,
        modifier = modifier.size(ReaderControlTouchDp.dp).semantics { contentDescription = description },
        enabled = enabled,
        minWidth = ReaderControlTouchDp.dp,
        minHeight = ReaderControlTouchDp.dp,
        cornerRadius = 22.dp,
        backgroundColor = Color.Transparent,
    ) {
        Box(Modifier.size(ReaderControlVisualDp.dp).shadow(2.dp, CircleShape)
            .border(1.dp, colors.onSurface.copy(alpha = 0.07f), CircleShape)
            .background(if (highlighted) colors.primaryContainer else colors.surfaceContainerHigh, CircleShape),
            contentAlignment = Alignment.Center) {
            MiuixGlyph(glyph, if (highlighted) colors.onPrimaryContainer else colors.onSurface, 20.dp)
        }
    }
}

@Composable
private fun ReaderDockAction(glyph: Glyph, label: String, onClick: () -> Unit) {
    IconButton(onClick = onClick, minHeight = ReaderControlTouchDp.dp, minWidth = 64.dp, cornerRadius = 24.dp,
        modifier = Modifier.semantics { contentDescription = label }) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            MiuixGlyph(glyph, MiuixTheme.colorScheme.onSurface, 20.dp)
            Text(label, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1)
        }
    }
}

internal enum class ReaderTapAction { TOGGLE_CHROME, PREVIOUS_PAGE, NEXT_PAGE, NONE }

/** Keep central chrome taps distinct from the page-turn zones, including in scroll mode. */
internal fun readerTapAction(horizontalFraction: Float, paged: Boolean): ReaderTapAction = when {
    !horizontalFraction.isFinite() || horizontalFraction !in 0f..1f -> ReaderTapAction.NONE
    horizontalFraction in 0.32f..0.68f -> ReaderTapAction.TOGGLE_CHROME
    !paged -> ReaderTapAction.NONE
    horizontalFraction < 0.32f -> ReaderTapAction.PREVIOUS_PAGE
    else -> ReaderTapAction.NEXT_PAGE
}

internal const val ReaderControlVisualDp = 40f
internal const val ReaderControlTouchDp = 44f
internal const val ReaderDockVerticalPaddingDp = 4f
// 44dp actions + 8dp padding = 52dp, versus the previous 48 + 20 = 68dp.
// Only minimums are specified; dynamic text can grow the dock instead of being clipped.
internal const val ReaderDockMinimumHeightDp = ReaderControlTouchDp + 2 * ReaderDockVerticalPaddingDp

internal const val ReaderChromeEnterMillis = 240
internal const val ReaderChromeExitMillis = 200
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReadingScreen.kt': r'''package dev.leaf.reader.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFontFamilyResolver
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.text
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextIndent
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Constraints
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.launch
import kotlinx.coroutines.yield
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.blur.layerBackdrop
import top.yukonga.miuix.kmp.blur.rememberLayerBackdrop
import top.yukonga.miuix.kmp.theme.MiuixTheme
import kotlin.math.abs
import kotlin.math.roundToInt

internal enum class ReaderPanel { NONE, CONTENTS, SETTINGS }
internal enum class ReaderPanelAction { OPEN_CONTENTS, OPEN_SETTINGS, CLOSE_CONTENTS, CLOSE_SETTINGS }

/** One panel at a time; delayed dismiss callbacks from a previous panel cannot close a new one. */
internal fun reduceReaderPanel(current: ReaderPanel, action: ReaderPanelAction): ReaderPanel = when (action) {
    ReaderPanelAction.OPEN_CONTENTS -> ReaderPanel.CONTENTS
    ReaderPanelAction.OPEN_SETTINGS -> ReaderPanel.SETTINGS
    ReaderPanelAction.CLOSE_CONTENTS -> if (current == ReaderPanel.CONTENTS) ReaderPanel.NONE else current
    ReaderPanelAction.CLOSE_SETTINGS -> if (current == ReaderPanel.SETTINGS) ReaderPanel.NONE else current
}

/** Only the loaded chapter is measured. currentBook contains chapter titles, never body text. */
@Composable
internal fun ReadingScreen(state: LibraryState, store: ReaderStore, onRequestClose: () -> Unit) {
    val book = state.currentBook ?: return
    var panel by remember(book.id) { mutableStateOf(ReaderPanel.NONE) }
    val directory = panel == ReaderPanel.CONTENTS
    val settingsOpen = panel == ReaderPanel.SETTINGS
    var showHint by remember(book.id) { mutableStateOf(true) }
    var interaction by remember { mutableIntStateOf(0) }
    LaunchedEffect(book.id, state.chapter != null) {
        if (state.chapter != null) {
            delay(4500)
            showHint = false
        }
    }
    LaunchedEffect(state.chromeVisible, state.settings.autoHideControls, directory, settingsOpen, interaction) {
        if (state.chromeVisible && state.settings.autoHideControls && !directory && !settingsOpen) {
            delay(5000)
            store.setChromeVisible(false)
        }
    }
    // ReaderApp owns the book transition and keeps shelf/reader state alive until exit finishes.
    val leave = onRequestClose
    // OverlayBottomSheet/OverlayListPopup register with MiuixPopupHost. A sibling shelf's
    // Scaffold is not an ancestor host; this local Scaffold makes reader settings render.
    Scaffold(modifier = Modifier.fillMaxSize(), containerColor = MiuixTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets(0, 0, 0, 0)) {
    BoxWithConstraints(Modifier.fillMaxSize().background(MiuixTheme.colorScheme.surface)) {
        val settingsMaxHeight = maxHeight * 0.90f
        Box(Modifier.fillMaxSize().then(if (panel != ReaderPanel.NONE) Modifier.clearAndSetSemantics { } else Modifier)) {
            val chapter = state.chapter
            if (chapter != null && !state.chapterBusy) {
                key(book.id, state.chapterIndex, chapter) {
                    ChapterReader(state, chapter, store,
                        onToggleChrome = { interaction++; store.setChromeVisible(!store.state.value.chromeVisible) },
                        onInteraction = { interaction++ },
                        onDirectory = { panel = reduceReaderPanel(panel, ReaderPanelAction.OPEN_CONTENTS) },
                        onSettings = { panel = reduceReaderPanel(panel, ReaderPanelAction.OPEN_SETTINGS) },
                        onClose = leave)
                }
            } else {
                Column(Modifier.align(Alignment.Center), horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    if (state.chapterBusy) {
                        CircularProgressIndicator(size = 28.dp)
                        Text("正在装入章节…")
                    } else {
                        Text("章节尚未载入")
                        TextButton("重试本章", { store.selectChapter(state.chapterIndex) }, minHeight = 48.dp)
                        TextButton("选择其他章节", { panel = reduceReaderPanel(panel, ReaderPanelAction.OPEN_CONTENTS) }, minHeight = 48.dp)
                    }
                    TextButton("阅读设置", {
                        panel = reduceReaderPanel(panel, ReaderPanelAction.OPEN_SETTINGS)
                    }, minHeight = 48.dp)
                    TextButton("返回书架", leave, minHeight = 48.dp)
                }
            }
            // Passive hint: no pointer modifier and no place in the measured reading viewport.
            if (showHint && chapter != null && !state.chapterBusy && !state.chromeVisible) {
                Text(if (state.settings.readingMode == ReadingMode.SCROLL)
                    "点击中间显示工具栏 · 上下滑动阅读" else "点击中间显示工具栏 · 左右滑动翻页",
                    modifier = Modifier.align(Alignment.BottomCenter).padding(horizontal = 20.dp, vertical = 64.dp)
                        .background(MiuixTheme.colorScheme.surfaceContainer).padding(12.dp),
                    style = MiuixTheme.textStyles.footnote1)
            }
        }
        AnimatedVisibility(visible = directory, modifier = Modifier.fillMaxSize(),
            enter = slideInVertically(tween(280, easing = MiuixEaseOut)) { it } + fadeIn(tween(180)),
            exit = slideOutVertically(tween(220, easing = MiuixEaseIn)) { it } + fadeOut(tween(180))) {
            ContentsScreen(book = book, manifest = state.manifest, currentChapter = state.chapterIndex,
                onSelectChapter = {
                    if (it != state.chapterIndex) store.selectChapter(it)
                    panel = reduceReaderPanel(panel, ReaderPanelAction.CLOSE_CONTENTS)
                }, onDismiss = { panel = reduceReaderPanel(panel, ReaderPanelAction.CLOSE_CONTENTS) })
        }
        ReadingSettings(settingsOpen, state.settings, store::updateSettings, { panel = reduceReaderPanel(panel, ReaderPanelAction.CLOSE_SETTINGS) },
            maxHeight = settingsMaxHeight)
    }
    }
}

private data class ChapterLayout(val pages: List<MeasuredPage>, val paragraphs: List<TextLayoutResult>)
private data class ReadingMetrics(
    val fontSize: Float, val lineHeight: Float, val font: ReaderFont, val bold: Boolean,
    val indent: Boolean, val letterSpacing: Float, val paragraphSpacing: Float,
)

@Composable
private fun ChapterReader(
    state: LibraryState,
    chapter: BookChapter,
    store: ReaderStore,
    onToggleChrome: () -> Unit,
    onInteraction: () -> Unit,
    onDirectory: () -> Unit,
    onSettings: () -> Unit,
    onClose: () -> Unit,
) {
    val book = state.currentBook ?: return
    val settings = state.settings
    val density = LocalDensity.current
    val resolver = LocalFontFamilyResolver.current
    val textMeasurer = rememberTextMeasurer(cacheSize = 16)
    val paper = MiuixTheme.colorScheme.surface
    // Capture an opaque paper base, not transparent glyphs; updated theme colours are read
    // through rememberLayerBackdrop's latest onDraw lambda. Chrome is never captured.
    val backdrop = rememberLayerBackdrop { drawRect(paper); drawContent() }
    var chromeProgress by remember { mutableStateOf("") }
    val texts = remember(chapter) { chapterReadingTexts(chapter, state.chapterIndex) }
    var stableAnchor by remember { mutableStateOf(clampAnchor(texts,
        TextAnchor(state.currentProgress.paragraphIndex, state.currentProgress.characterOffset))) }
    var layout by remember { mutableStateOf<ChapterLayout?>(null) }
    var appliedLayout by remember { mutableStateOf<ChapterLayout?>(null) }
    var appliedMode by remember { mutableStateOf<ReadingMode?>(null) }
    var instantPage by remember { mutableIntStateOf(0) }
    val list = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val previousChapter = state.chapterIndex > 0
    val nextChapter = state.chapterIndex < book.chapters.lastIndex
    val firstPage = if (previousChapter) 1 else 0
    val pager = rememberPagerState(pageCount = {
        (layout?.pages?.size ?: 1) + firstPage + if (nextChapter) 1 else 0
    })
    val metrics = ReadingMetrics(settings.fontSize, settings.lineHeight, settings.fontFamily,
        settings.bold, settings.firstLineIndent, settings.letterSpacing, settings.paragraphSpacing)
    val family = when (settings.fontFamily) {
        ReaderFont.SERIF -> FontFamily.Serif
        ReaderFont.SANS -> FontFamily.SansSerif
        ReaderFont.MONO -> FontFamily.Monospace
    }
    val bodyStyle = TextStyle(fontFamily = family, fontSize = settings.fontSize.sp,
        lineHeight = (settings.fontSize * settings.lineHeight).sp,
        fontWeight = if (settings.bold) FontWeight.Bold else FontWeight.Normal,
        letterSpacing = settings.letterSpacing.sp,
        textIndent = TextIndent(firstLine = if (settings.firstLineIndent) 2.em else 0.em))
    val headingStyle = bodyStyle.copy(fontSize = (settings.fontSize + 6).sp,
        lineHeight = ((settings.fontSize + 6) * 1.5f).sp,
        fontWeight = FontWeight.Bold, textIndent = TextIndent.None)

    Box(Modifier.fillMaxSize()) {
    // Full-window capture includes the status-bar band; only its child consumes safeDrawing.
    // Header and dock remain siblings outside this recorded layer, preventing recursive sampling.
    Box(Modifier.fillMaxSize().layerBackdrop(backdrop)) {
    BoxWithConstraints(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing)) {
        val columns = when (settings.columnMode) {
            ColumnMode.SINGLE -> 1
            ColumnMode.DOUBLE -> 2
            ColumnMode.AUTO -> if (maxWidth >= 840.dp) 2 else 1
        }
        val margin = settings.horizontalMargin.dp.coerceAtMost((maxWidth / 5).coerceAtLeast(0.dp))
        val gap = if (columns == 2) 28.dp else 0.dp
        // Chrome and footer never participate in these constraints: toggling them cannot reflow text.
        val pageHeight = (maxHeight - 72.dp).coerceAtLeast(1.dp)
        val columnWidth = with(density) { ((maxWidth - margin * 2 - gap) / columns).roundToPx().coerceAtLeast(1) }
        val columnHeight = with(density) { pageHeight.toPx().coerceAtLeast(1f) }
        val gapPx = with(density) { gap.toPx() }
        val spacingPx = with(density) { settings.paragraphSpacing.dp.toPx() }

        LaunchedEffect(chapter, columnWidth, columnHeight, columns, metrics, density.density, density.fontScale, resolver) {
            appliedLayout = null
            layout = null
            // TextMeasurer stays on the composition dispatcher. Yield between bounded batches so
            // chapter layout can be cancelled on resize/settings changes without measuring a book.
            val measured = ArrayList<TextLayoutResult>(texts.size)
            texts.forEachIndexed { index, text ->
                measured += textMeasurer.measure(AnnotatedString(text),
                    style = if (index == 0) headingStyle else bodyStyle,
                    constraints = Constraints(maxWidth = columnWidth))
                if (index % 12 == 0) yield()
            }
            val pages = paginateChapter(texts, columnWidth, columnHeight, columns, spacingPx) { index, text, _ ->
                val result = measured[index]
                List(result.lineCount) { line ->
                    MeasuredLine(safeTextOffset(text, result.getLineStart(line)),
                        if (line == result.lineCount - 1) text.length
                        else safeTextOffset(text, result.getLineStart(line + 1)),
                        result.getLineTop(line), result.getLineBottom(line))
                }
            }
            layout = ChapterLayout(pages, measured)
        }
        val currentLayout = layout
        val ready = currentLayout != null && appliedLayout === currentLayout && appliedMode == settings.readingMode
        LaunchedEffect(currentLayout, settings.readingMode) {
            appliedLayout = null
            val measured = currentLayout ?: return@LaunchedEffect
            val target = pageForAnchor(measured.pages, clampAnchor(texts, stableAnchor))
            // Never scroll an unattached LazyList/Pager state: it can await first layout forever.
            when (settings.readingMode) {
                ReadingMode.INSTANT -> instantPage = target
                ReadingMode.SLIDE -> pager.scrollToPage(target + firstPage)
                ReadingMode.SCROLL -> list.scrollToItem(target,
                    yForAnchor(measured.pages[target], stableAnchor).roundToInt().coerceAtLeast(0))
            }
            withFrameNanos { }
            appliedMode = settings.readingMode
            appliedLayout = measured
        }
        fun saveAnchor(anchor: TextAnchor, offset: Int = 0) {
            val live = store.state.value
            if (live.currentBook?.id == book.id && live.chapterIndex == state.chapterIndex &&
                !live.chapterBusy && !live.busy) {
                stableAnchor = clampAnchor(texts, anchor)
                store.updateChapterProgress(stableAnchor.paragraphIndex, stableAnchor.characterOffset, offset)
            }
        }
        LaunchedEffect(currentLayout, settings.readingMode) {
            val measured = currentLayout ?: return@LaunchedEffect
            // Ignore the first restored viewport: retain the exact text anchor, not its new page start.
            snapshotFlow {
                if (appliedLayout !== measured || appliedMode != settings.readingMode) null
                else when (settings.readingMode) {
                    ReadingMode.SLIDE -> if (pager.isScrollInProgress) null else pager.settledPage to 0
                    ReadingMode.INSTANT -> instantPage to 0
                    ReadingMode.SCROLL -> list.firstVisibleItemIndex to list.firstVisibleItemScrollOffset
                }
            }.filterNotNull().distinctUntilChanged().drop(1).collect { (rawPage, offset) ->
                if (settings.readingMode == ReadingMode.SLIDE && rawPage < firstPage) {
                    store.selectChapter(state.chapterIndex - 1, atEnd = true)
                } else if (settings.readingMode == ReadingMode.SLIDE && rawPage >= firstPage + measured.pages.size) {
                    store.selectChapter(state.chapterIndex + 1)
                } else {
                    val page = (rawPage - if (settings.readingMode == ReadingMode.SLIDE) firstPage else 0)
                        .coerceIn(0, measured.pages.lastIndex)
                    saveAnchor(if (settings.readingMode == ReadingMode.SCROLL)
                        anchorAtY(measured.pages[page], offset.toFloat()) else measured.pages[page].anchor, offset)
                }
                onInteraction()
            }
        }
        val visiblePage = when (settings.readingMode) {
            ReadingMode.SLIDE -> pager.currentPage - firstPage
            ReadingMode.INSTANT -> instantPage
            ReadingMode.SCROLL -> list.firstVisibleItemIndex
        }.coerceIn(0, (currentLayout?.pages?.lastIndex ?: 0))
        val move: (Int) -> Unit = move@{ direction ->
            if (!ready) return@move
            onInteraction()
            val measured = currentLayout ?: return@move
            val target = visiblePage + direction
            if (target < 0) {
                if (previousChapter) store.selectChapter(state.chapterIndex - 1, atEnd = true)
            } else if (target > measured.pages.lastIndex) {
                if (nextChapter) store.selectChapter(state.chapterIndex + 1)
            } else {
                saveAnchor(measured.pages[target].anchor)
                scope.launch {
                    when (settings.readingMode) {
                        ReadingMode.SLIDE -> pager.animateScrollToPage(target + firstPage)
                        ReadingMode.INSTANT -> instantPage = target
                        ReadingMode.SCROLL -> list.animateScrollToItem(target)
                    }
                }
            }
        }
        val tapModifier = Modifier.pointerInput(settings.readingMode, ready, visiblePage, state.chromeVisible) {
            detectTapGestures { position ->
                when (readerTapAction(position.x / size.width.toFloat(), settings.readingMode != ReadingMode.SCROLL)) {
                    ReaderTapAction.TOGGLE_CHROME -> onToggleChrome()
                    ReaderTapAction.PREVIOUS_PAGE -> move(-1)
                    ReaderTapAction.NEXT_PAGE -> move(1)
                    ReaderTapAction.NONE -> Unit
                }
            }
        }
        val accessibility = Modifier.semantics {
            stateDescription = "第 ${state.chapterIndex + 1} 章，第 ${visiblePage + 1} / ${currentLayout?.pages?.size ?: 1} 页"
            customActions = listOf(
                CustomAccessibilityAction("显示或隐藏阅读控制") { onToggleChrome(); true },
                CustomAccessibilityAction("上一页") { move(-1); true },
                CustomAccessibilityAction("下一页") { move(1); true })
        }
        Box(Modifier.fillMaxSize().then(tapModifier).then(accessibility)) {
            if (currentLayout == null) {
                CircularProgressIndicator(Modifier.align(Alignment.Center), size = 28.dp)
            } else {
                val pageModifier = Modifier.fillMaxWidth().height(pageHeight)
                val viewport = Modifier.fillMaxSize().padding(start = margin, end = margin, top = 26.dp, bottom = 46.dp)
                when (settings.readingMode) {
                    ReadingMode.SLIDE -> HorizontalPager(state = pager, modifier = viewport,
                        userScrollEnabled = ready, beyondViewportPageCount = 0) { page ->
                        val index = page - firstPage
                        if (index in currentLayout.pages.indices) {
                            MeasuredSpread(currentLayout.pages[index], currentLayout.paragraphs, texts,
                                columnWidth, gapPx, pageModifier)
                        } else Box(pageModifier, contentAlignment = Alignment.Center) {
                            Text(if (index < 0) "松开进入上一章" else "松开进入下一章")
                        }
                    }
                    ReadingMode.INSTANT -> {
                        var drag by remember { mutableFloatStateOf(0f) }
                        Box(viewport.pointerInput(ready, visiblePage) {
                            detectHorizontalDragGestures(onDragStart = { drag = 0f },
                                onDragEnd = { if (abs(drag) > 48.dp.toPx()) move(if (drag < 0) 1 else -1) },
                                onHorizontalDrag = { change, amount -> change.consume(); drag += amount })
                        }) {
                            MeasuredSpread(currentLayout.pages[visiblePage], currentLayout.paragraphs, texts,
                                columnWidth, gapPx, pageModifier)
                        }
                    }
                    ReadingMode.SCROLL -> LazyColumn(state = list, modifier = viewport, userScrollEnabled = ready) {
                        itemsIndexed(currentLayout.pages, key = { index, _ -> index }) { _, page ->
                            MeasuredSpread(page, currentLayout.paragraphs, texts, columnWidth, gapPx, pageModifier)
                        }
                        item {
                            Row(Modifier.fillMaxWidth().padding(vertical = 16.dp), horizontalArrangement = Arrangement.Center) {
                                TextButton(if (nextChapter) "继续下一章" else "已读至全书末尾", {
                                    if (nextChapter) store.selectChapter(state.chapterIndex + 1)
                                }, enabled = ready && nextChapter, minHeight = 48.dp)
                            }
                        }
                    }
                }
            }
        }
        // The floating dock replaces the footer line while the chrome is up, so they never overlap.
        if (settings.showReadingFooter && !state.chromeVisible) {
            Row(Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(horizontal = margin, vertical = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                MutedText(chapter.title.ifBlank { "正文" }, Modifier.weight(1f), maxLines = 1)
                MutedText("${visiblePage + 1} / ${currentLayout?.pages?.size ?: "…"} · ${state.chapterIndex + 1}/${book.chapters.size}")
            }
        }
        val totalChapters = (state.manifest?.chapters?.size ?: book.chapters.size).coerceAtLeast(1)
        val pageCount = (currentLayout?.pages?.size ?: 1).coerceAtLeast(1)
        val chapterFraction = ((visiblePage + 1).toFloat() / pageCount).coerceIn(0f, 1f)
        val percent = (((state.chapterIndex + chapterFraction) / totalChapters) * 100f).roundToInt().coerceIn(1, 100)
        val progressText = "${(state.chapterIndex + 1).coerceAtMost(totalChapters)} / $totalChapters · $percent%"
        SideEffect { chromeProgress = progressText }
    }
    }
    ReaderChrome(visible = state.chromeVisible, title = chapter.title.ifBlank { "正文" },
        progressText = chromeProgress, backdrop = backdrop,
        onClose = onClose, onDirectory = onDirectory, onSettings = onSettings)
    }
}

/** Draw the exact measured paragraphs, clipped by original line bounds; no substring reflow. */
@Composable
private fun MeasuredSpread(page: MeasuredPage, paragraphs: List<TextLayoutResult>, texts: List<String>,
    columnWidth: Int, gap: Float, modifier: Modifier) {
    val color = MiuixTheme.colorScheme.onSurface
    val spoken = remember(page, texts) {
        page.columns.flatMap { it }.joinToString("\n") { texts[it.paragraphIndex].substring(it.start, it.end) }
    }
    Canvas(modifier.clipToBounds().semantics { text = AnnotatedString(spoken) }) {
        page.columns.forEachIndexed { columnIndex, slices ->
            val x = columnIndex * (columnWidth + gap)
            slices.forEach { slice ->
                clipRect(left = x, top = slice.top, right = x + columnWidth, bottom = slice.top + slice.height) {
                    drawText(paragraphs[slice.paragraphIndex], color = color,
                        topLeft = Offset(x, slice.top - slice.sourceTop))
                }
            }
        }
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReadingSettings.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.selection.toggleable
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.overlay.OverlayBottomSheet
import top.yukonga.miuix.kmp.overlay.OverlayListPopup
import top.yukonga.miuix.kmp.theme.MiuixTheme

/**
 * Scrollable typography sheet with a pinned close action, including on short landscape windows.
 * Every interactive row keeps at least a 48dp target and clearly separated groups.
 */
@Composable
internal fun ReadingSettings(
    show: Boolean,
    settings: ReaderSettings,
    onChange: (ReaderSettings) -> Unit,
    onDismiss: () -> Unit,
    maxHeight: Dp = 560.dp,
) {
    OverlayBottomSheet(
        show = show,
        title = null,
        onDismissRequest = onDismiss,
        cornerRadius = 28.dp,
        renderInRootScaffold = false,
    ) {
        Column(Modifier.fillMaxWidth().heightIn(max = maxHeight)
            .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Bottom + WindowInsetsSides.Horizontal))) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("排版设置", Modifier.weight(1f).semantics { heading() },
                    fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
                ReaderIconButton(Glyph.CLOSE, "关闭排版设置", onDismiss)
            }
            Column(Modifier.fillMaxWidth().weight(1f, fill = false)
                .verticalScroll(rememberScrollState())
                .padding(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 20.dp),
                verticalArrangement = Arrangement.spacedBy(22.dp)) {
            SettingsSection("翻页与分栏") {
                Choice("阅读方式", listOf("滑动", "无动画", "滚动"),
                    listOf(ReadingMode.SLIDE, ReadingMode.INSTANT, ReadingMode.SCROLL).indexOf(settings.readingMode)) {
                    onChange(settings.copy(readingMode = listOf(ReadingMode.SLIDE, ReadingMode.INSTANT, ReadingMode.SCROLL)[it]))
                }
                Choice("分栏", listOf("自动", "单栏", "双栏"),
                    listOf(ColumnMode.AUTO, ColumnMode.SINGLE, ColumnMode.DOUBLE).indexOf(settings.columnMode)) {
                    onChange(settings.copy(columnMode = listOf(ColumnMode.AUTO, ColumnMode.SINGLE, ColumnMode.DOUBLE)[it]))
                }
                SettingsNote("自动在宽度达到 840dp 时使用双栏。双栏从左至右阅读；滚动模式按双栏书页连续排列。")
            }
            SettingsSection("文字与留白") {
                Choice("字体", listOf("衬线", "无衬线", "等宽"),
                    listOf(ReaderFont.SERIF, ReaderFont.SANS, ReaderFont.MONO).indexOf(settings.fontFamily)) {
                    onChange(settings.copy(fontFamily = listOf(ReaderFont.SERIF, ReaderFont.SANS, ReaderFont.MONO)[it]))
                }
                StepSetting("字号", settings.fontSize, 14f, 40f, 1f, "sp") { onChange(settings.copy(fontSize = it)) }
                StepSetting("行距", settings.lineHeight, 1.2f, 2.4f, 0.1f, "倍") { onChange(settings.copy(lineHeight = it)) }
                StepSetting("页边距", settings.horizontalMargin, 8f, 56f, 4f, "dp") { onChange(settings.copy(horizontalMargin = it)) }
                StepSetting("段间距", settings.paragraphSpacing, 0f, 40f, 2f, "dp") { onChange(settings.copy(paragraphSpacing = it)) }
                StepSetting("字间距", settings.letterSpacing, -0.5f, 3f, 0.25f, "sp") { onChange(settings.copy(letterSpacing = it)) }
                ToggleSetting("首行缩进", settings.firstLineIndent) { onChange(settings.copy(firstLineIndent = it)) }
                ToggleSetting("加粗正文", settings.bold) { onChange(settings.copy(bold = it)) }
            }
            SettingsSection("阅读主题") {
                Choice("纸张", listOf("系统", "明亮", "纸色", "深色"),
                    listOf(ReaderTheme.SYSTEM, ReaderTheme.LIGHT, ReaderTheme.SEPIA, ReaderTheme.DARK).indexOf(settings.theme)) {
                    onChange(settings.copy(theme = listOf(ReaderTheme.SYSTEM, ReaderTheme.LIGHT, ReaderTheme.SEPIA, ReaderTheme.DARK)[it]))
                }
            }
            SettingsSection("阅读控制") {
                ToggleSetting("控制栏自动隐藏", settings.autoHideControls) { onChange(settings.copy(autoHideControls = it)) }
                ToggleSetting("显示阅读页脚", settings.showReadingFooter) { onChange(settings.copy(showReadingFooter = it)) }
                SettingsNote("轻点中央显示 / 隐藏控制栏；分页时轻点两侧翻页。字号、分栏或旋转后按文字位置恢复，不存储页码。")
            }
            PrimaryAction("完成", onDismiss, Modifier.fillMaxWidth())
            }
        }
    }
}

@Composable
private fun SettingsSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(title, fontSize = 14.sp, fontWeight = FontWeight.SemiBold,
            color = MiuixTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 4.dp).semantics { heading() })
        Card(Modifier.fillMaxWidth(), insideMargin = PaddingValues(18.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(16.dp), content = content)
        }
    }
}

@Composable
private fun Choice(label: String, labels: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    var expanded by remember(label) { mutableStateOf(false) }
    // The parent Box is the real anchor measured by OverlayListPopup's position provider.
    Box(Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().heightIn(min = 52.dp)
            .clickable(role = Role.Button) { expanded = true }
            .semantics { contentDescription = "$label：${labels.getOrNull(selected).orEmpty()}，选择选项" }
            .padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(label, Modifier.weight(1f), style = MiuixTheme.textStyles.body2, maxLines = 2)
            Text(labels.getOrNull(selected).orEmpty(), Modifier.weight(1f),
                color = MiuixTheme.colorScheme.onSurfaceVariantSummary, textAlign = TextAlign.End,
                style = MiuixTheme.textStyles.body2, maxLines = 2, overflow = TextOverflow.Ellipsis)
            DropdownArrowEndAction(actionColor = MiuixTheme.colorScheme.onSurfaceVariantSummary)
        }
        OverlayListPopup(show = expanded, alignment = PopupPositionProvider.Align.End,
            enableWindowDim = false, onDismissRequest = { expanded = false },
            renderInRootScaffold = false) {
            ListPopupColumn {
                labels.forEachIndexed { index, title ->
                    DropdownImpl(text = title, optionSize = labels.size, isSelected = selected == index,
                        index = index, onSelectedIndexChange = {
                            expanded = false
                            onSelect(it)
                        })
                }
            }
        }
    }
}

@Composable
private fun StepSetting(label: String, value: Float, minimum: Float, maximum: Float,
    step: Float, unit: String, onChange: (Float) -> Unit) {
    val rounded = (value * 100).toInt() / 100f
    val controls: @Composable () -> Unit = {
        StepButton("−", "减小$label", enabled = value > minimum) {
            onChange((value - step).coerceAtLeast(minimum))
        }
        StepButton("＋", "增大$label", enabled = value < maximum) {
            onChange((value + step).coerceAtMost(maximum))
        }
    }
    BoxWithConstraints(Modifier.fillMaxWidth()) {
        if (stackedReaderSetting(LocalDensity.current.fontScale, maxWidth.value)) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(label, Modifier.weight(1f), fontSize = 15.sp, maxLines = 2)
                    Text("$rounded$unit", fontSize = 14.sp,
                        color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.End)) {
                    controls()
                }
            }
        } else {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(label, Modifier.weight(1f), fontSize = 15.sp, maxLines = 1)
                Text("$rounded$unit", fontSize = 14.sp, maxLines = 1,
                    color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
                controls()
            }
        }
    }
}

/** 48dp square stepper button; the symbol is text, not an icon dependency. */
@Composable
private fun StepButton(symbol: String, description: String, enabled: Boolean, onClick: () -> Unit) {
    val container = MiuixTheme.colorScheme.surfaceContainerHigh
    Box(
        modifier = Modifier.size(SettingsTouchTarget)
            .clip(RoundedCornerShape(12.dp))
            .background(if (enabled) container else container.copy(alpha = 0.5f))
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics {
                role = Role.Button
                contentDescription = description
            },
        contentAlignment = Alignment.Center,
    ) {
        Text(symbol, fontSize = 18.sp, fontWeight = FontWeight.Medium,
            color = if (enabled) MiuixTheme.colorScheme.onSurface
            else MiuixTheme.colorScheme.onSurfaceVariantSummary)
    }
}

@Composable
private fun ToggleSetting(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 52.dp)
        .toggleable(value = checked, role = Role.Switch, onValueChange = onChange)
        .semantics { contentDescription = label }, verticalAlignment = Alignment.CenterVertically) {
        Text(label, Modifier.weight(1f), fontSize = 15.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
        Switch(checked = checked, onCheckedChange = null,
            modifier = Modifier.clearAndSetSemantics { })
    }
}

@Composable
private fun SettingsNote(text: String) {
    Text(text, fontSize = 12.sp, lineHeight = 18.sp,
        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f))
}

internal fun stackedReaderSetting(fontScale: Float, widthDp: Float): Boolean =
    fontScale > 1.3f || widthDp < 240f

private val SettingsTouchTarget = 48.dp

@Composable
internal fun PrimaryAction(label: String, action: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) =
    TextButton(label, action, modifier, enabled = enabled, minHeight = 48.dp,
        colors = ButtonDefaults.textButtonColorsPrimary())

@Composable
internal fun MutedText(text: String, modifier: Modifier = Modifier, maxLines: Int = Int.MAX_VALUE) = Text(
    text, modifier, fontSize = 13.sp, lineHeight = 20.sp, maxLines = maxLines,
    overflow = TextOverflow.Ellipsis, color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
)

@Composable
internal fun ProgressTrack(progress: Float, modifier: Modifier = Modifier) {
    LinearProgressIndicator(modifier = modifier, progress = progress.coerceIn(0f, 1f), height = 3.dp)
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ShelfScreen.kt': r'''package dev.leaf.reader.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.ContentTransform
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyGridState
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.blur.Backdrop
import top.yukonga.miuix.kmp.blur.layerBackdrop
import top.yukonga.miuix.kmp.blur.textureBlur
import top.yukonga.miuix.kmp.blur.isRuntimeShaderSupported
import top.yukonga.miuix.kmp.blur.rememberLayerBackdrop
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme

private enum class ShelfOrder(val label: String) {
    RECENT("最近阅读"), ADDED("最近导入"), TITLE("书名"), LENGTH("篇幅"),
}

/** Keeps the floating dock from covering the last row; >= 96dp by contract. */
private val ShelfDockClearance = 128.dp

/** Scroll distance over which the large title folds into the compact top bar. */
private val ShelfCollapseDistance = 72.dp

@Composable
internal fun ShelfScreen(
    state: LibraryState,
    store: ReaderStore,
    onImportRequested: () -> Unit,
    onOpenBook: (String, Offset?) -> Unit = { id, _ -> store.openBook(id) },
) {
    var panel by rememberSaveable { mutableIntStateOf(0) }
    var query by rememberSaveable { mutableStateOf("") }
    var searching by rememberSaveable { mutableStateOf(false) }
    var orderIndex by rememberSaveable { mutableIntStateOf(0) }
    var deleting by remember { mutableStateOf<ShelfBook?>(null) }
    var headerHeightPx by remember { mutableIntStateOf(0) }
    val gridState = rememberLazyGridState()
    val settingsState = rememberLazyListState()
    val paper = MiuixTheme.colorScheme.surface
    val backdrop = rememberLayerBackdrop { drawRect(paper); drawContent() }
    val focusManager = LocalFocusManager.current
    val density = LocalDensity.current
    val enabled = !state.busy
    val layout = state.settings.shelfLayout
    val order = ShelfOrder.entries[orderIndex.coerceIn(0, ShelfOrder.entries.lastIndex)]
    val books = remember(state.books, query, order) {
        val keyword = query.trim()
        val filtered = state.books.filter {
            keyword.isEmpty() ||
                it.title.contains(keyword, ignoreCase = true) ||
                it.author.contains(keyword, ignoreCase = true) ||
                it.format.contains(keyword, ignoreCase = true)
        }
        when (order) {
            ShelfOrder.RECENT -> filtered.sortedWith(
                compareByDescending<ShelfBook> { it.lastOpenedAt }.thenByDescending { it.addedAt }.thenBy { it.id },
            )
            ShelfOrder.ADDED -> filtered.sortedWith(
                compareByDescending<ShelfBook> { it.addedAt }.thenBy { it.id },
            )
            ShelfOrder.TITLE -> filtered.sortedWith(
                compareBy<ShelfBook> { it.title.lowercase() }.thenBy { it.id },
            )
            ShelfOrder.LENGTH -> filtered.sortedWith(
                compareByDescending<ShelfBook> { it.characterCount }
                    .thenByDescending { it.paragraphCount }.thenBy { it.id },
            )
        }
    }
    val continuing = remember(state.books) {
        state.books.filter { it.lastOpenedAt > 0 }.maxByOrNull { it.lastOpenedAt }
    }

    // Collapse follows the active pane: grid index 0 scroll offset, or a full fold once scrolled.
    // Read through a provider so scroll frames only invalidate the header, never the grid itself.
    val collapseDistance = with(density) { ShelfCollapseDistance.toPx() }
    val collapseTarget: () -> Float = remember(collapseDistance) {
        val progress = derivedStateOf {
            val index: Int
            val offset: Int
            if (panel == 0) {
                index = gridState.firstVisibleItemIndex
                offset = gridState.firstVisibleItemScrollOffset
            } else {
                index = settingsState.firstVisibleItemIndex
                offset = settingsState.firstVisibleItemScrollOffset
            }
            if (index > 0) 1f else (offset / collapseDistance).coerceIn(0f, 1f)
        }
        val provider: () -> Float = { progress.value }
        provider
    }
    val shelfMode = panel == 0

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MiuixTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets.systemBars.union(WindowInsets.displayCutout),
        floatingToolbarPosition = ToolbarPosition.BottomCenter,
        floatingToolbar = {
            ShelfDock(panel, backdrop) { next ->
                panel = next
                focusManager.clearFocus()
            }
        },
    ) { insets ->
        val safeTop = insets.calculateTopPadding()
        val direction = LocalLayoutDirection.current
        val contentTopPadding = (with(density) { headerHeightPx.toDp() } - safeTop).coerceAtLeast(0.dp) + 10.dp
        Box(Modifier.fillMaxSize()) {
            // Capture an opaque full-window paper, including the status-bar band;
            // the interactive pane alone is inset. Header and dock stay outside capture.
            Box(Modifier.fillMaxSize().layerBackdrop(backdrop)) {
                AnimatedContent(
                    targetState = panel,
                    modifier = Modifier.fillMaxSize().padding(insets).consumeWindowInsets(insets),
                    transitionSpec = {
                        val direction = if (targetState > initialState) 1 else -1
                        ContentTransform(
                            targetContentEnter = slideInHorizontally(tween(280, easing = MiuixEaseOut)) { it * direction } + fadeIn(tween(180)),
                            initialContentExit = slideOutHorizontally(tween(280, easing = MiuixEaseOut)) { -it * direction } + fadeOut(tween(180)),
                        )
                    },
                    label = "shelf-panel",
                ) { activePanel ->
                if (activePanel == 0) {
                    ShelfGridPane(
                        books = books,
                        continuing = continuing,
                        layout = layout,
                        order = order,
                        query = query,
                        enabled = enabled,
                        topPadding = contentTopPadding,
                        state = gridState,
                        onOpen = { book, origin ->
                            focusManager.clearFocus()
                            onOpenBook(book.id, origin)
                        },
                        onDelete = { deleting = it },
                        onImport = onImportRequested,
                        onClearSearch = { query = ""; focusManager.clearFocus() },
                    )
                } else {
                    ShelfSettingsPane(
                        state = state,
                        store = store,
                        onImportRequested = onImportRequested,
                        orderIndex = orderIndex,
                        onOrderChange = { orderIndex = it },
                        listState = settingsState,
                        topPadding = contentTopPadding,
                        modifier = Modifier.fillMaxSize(),
                    )
                }
                }
            }
            Box(Modifier.fillMaxWidth().padding(
                start = insets.calculateStartPadding(direction),
                end = insets.calculateEndPadding(direction),
            )) {
            ShelfHeader(
                backdrop = backdrop,
                safeTop = safeTop,
                compactTitle = if (shelfMode) "书架" else "设置",
                largeTitle = if (shelfMode) "书架" else "设置",
                detail = if (shelfMode) "共 ${state.books.size} 本本地书籍" else "你的书架，你的阅读习惯",
                showActions = shelfMode,
                searching = searching && shelfMode,
                query = query,
                enabled = enabled,
                collapseTarget = collapseTarget,
                onHeaderHeight = { height -> if (height != headerHeightPx) headerHeightPx = height },
                onSearchToggle = {
                    if (searching) {
                        searching = false
                        query = ""
                        focusManager.clearFocus()
                    } else {
                        searching = true
                    }
                },
                onImport = onImportRequested,
                onQueryChange = { query = it },
                onCollapseSearch = { query = ""; searching = false; focusManager.clearFocus() },
            )
            }
        }
        OverlayDialog(
            show = deleting != null,
            title = "移出书架？",
            summary = "将移除《${deleting?.title.orEmpty()}》及阅读进度，原始文件保留。",
            onDismissRequest = { deleting = null },
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                TextButton("保留", { deleting = null }, Modifier.weight(1f), minHeight = 48.dp)
                TextButton(
                    "移除书籍",
                    {
                        deleting?.let { store.deleteBook(it.id) }
                        deleting = null
                    },
                    Modifier.weight(1f),
                    enabled = enabled,
                    minHeight = 48.dp,
                    colors = ButtonDefaults.textButtonColorsPrimary(color = MiuixTheme.colorScheme.error),
                )
            }
        }
    }
}

/** One compact floating surface with a shared, smoothly moving selection pill. */
@Composable
private fun ShelfDock(panel: Int, backdrop: Backdrop?, onSelect: (Int) -> Unit) {
    val shape = RoundedCornerShape(999.dp)
    val surface = MiuixTheme.colorScheme.surfaceContainerHigh
    val material = if (backdrop != null && isRuntimeShaderSupported()) {
        Modifier.clip(shape).textureBlur(
            backdrop = backdrop, shape = shape, blurRadius = 18f, noiseCoefficient = 0f,
        ).background(surface.copy(alpha = 0.78f))
    } else {
        Modifier.clip(shape).background(surface)
    }
    Box(
        Modifier.padding(horizontal = 12.dp, vertical = 12.dp)
            .widthIn(max = 236.dp).fillMaxWidth()
            .shadow(8.dp, shape).then(material)
            .padding(4.dp).selectableGroup(),
    ) {
        BoxWithConstraints(Modifier.fillMaxWidth().height(48.dp)) {
            val tabWidth = maxWidth / 2
            val indicatorOffset by animateDpAsState(
                targetValue = if (panel == 0) 0.dp else tabWidth,
                animationSpec = tween(280, easing = MiuixEaseOut),
                label = "dock-selection",
            )
            Box(
                Modifier.offset(x = indicatorOffset).width(tabWidth).fillMaxHeight()
                    .clip(shape).background(MiuixTheme.colorScheme.primary),
            )
            Row(Modifier.fillMaxSize()) {
                listOf(Glyph.SHELVES to "书架", Glyph.GEAR to "设置").forEachIndexed { index, (glyph, title) ->
                    val active = panel == index
                    val tint = if (active) MiuixTheme.colorScheme.onPrimary else MiuixTheme.colorScheme.onSurfaceVariantSummary
                    Row(
                        Modifier.weight(1f).fillMaxHeight().clip(shape)
                            .selectable(selected = active, role = Role.Tab, onClick = { onSelect(index) }),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        MiuixGlyph(glyph, tint, 20.dp)
                        Spacer(Modifier.width(8.dp))
                        Text(title, color = tint, style = MiuixTheme.textStyles.footnote1, maxLines = 1)
                    }
                }
            }
        }
    }
}

/**
 * Collapsing header laid over the list: gradient scrim (no divider), compact title fading in
 * while the large title scales and fades out, then the search row that expands underneath.
 */
@Composable
private fun ShelfHeader(
    backdrop: Backdrop,
    safeTop: Dp,
    compactTitle: String,
    largeTitle: String,
    detail: String,
    showActions: Boolean,
    searching: Boolean,
    query: String,
    enabled: Boolean,
    collapseTarget: () -> Float,
    onHeaderHeight: (Int) -> Unit,
    onSearchToggle: () -> Unit,
    onImport: () -> Unit,
    onQueryChange: (String) -> Unit,
    onCollapseSearch: () -> Unit,
) {
    val collapseProgress = animateFloatAsState(
        targetValue = collapseTarget(),
        animationSpec = tween(140, easing = MiuixEaseOut),
        label = "shelf-collapse",
    )
    val collapse: () -> Float = { collapseProgress.value }
    GradientHeaderScrim(backdrop = backdrop) {
        Column(Modifier.fillMaxWidth().onSizeChanged { onHeaderHeight(it.height) }.padding(top = safeTop)) {
            Column(Modifier.fillMaxWidth()) {
                Row(
                    Modifier.fillMaxWidth()
                        .heightIn(min = 48.dp)
                        .padding(start = PageMargin, end = PageMargin, top = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        compactTitle,
                        modifier = Modifier.weight(1f).graphicsLayer {
                            val appear = ((collapse() - 0.55f) / 0.45f).coerceIn(0f, 1f)
                            alpha = appear
                            translationY = (1f - appear) * 6.dp.toPx()
                        },
                        style = MiuixTheme.textStyles.title3,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (showActions) {
                        Row(horizontalArrangement = Arrangement.spacedBy(ControlGap)) {
                            MiuixCircleButton(
                                Glyph.SEARCH, "搜索书架", onSearchToggle,
                                size = CircleControlSize,
                            )
                            MiuixCircleButton(
                                Glyph.ADD, "导入本地书籍", onImport,
                                enabled = enabled,
                                size = CircleControlSize,
                            )
                        }
                    }
                }
                Row(
                    Modifier.fillMaxWidth()
                        .padding(start = PageMargin, end = PageMargin, top = 2.dp, bottom = 14.dp),
                    verticalAlignment = Alignment.Bottom,
                ) {
                    Text(
                        largeTitle,
                        modifier = Modifier.graphicsLayer {
                            val progress = collapse()
                            alpha = (1f - progress * 1.15f).coerceIn(0f, 1f)
                            val scale = 1f - progress * 0.32f
                            scaleX = scale
                            scaleY = scale
                            transformOrigin = TransformOrigin(0f, 0.85f)
                        }.semantics { heading() },
                        style = MiuixTheme.textStyles.title1,
                        fontSize = 32.sp,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Spacer(Modifier.weight(1f))
                    Text(
                        detail,
                        modifier = Modifier.padding(start = 12.dp),
                        style = MiuixTheme.textStyles.footnote1,
                        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
                        textAlign = TextAlign.End,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            AnimatedVisibility(
                visible = searching,
                enter = expandVertically(expandFrom = Alignment.Top) + fadeIn(),
                exit = shrinkVertically(shrinkTowards = Alignment.Top) + fadeOut(),
            ) {
                ShelfSearchRow(
                    query = query,
                    onQueryChange = onQueryChange,
                    onCollapse = onCollapseSearch,
                    modifier = Modifier.padding(start = PageMargin, end = PageMargin, top = 2.dp, bottom = 10.dp),
                )
            }
        }
    }
}

@Composable
private fun ShelfSearchRow(
    query: String,
    onQueryChange: (String) -> Unit,
    onCollapse: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val focusManager = LocalFocusManager.current
    Row(
        modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(ControlGap),
    ) {
        Box(Modifier.weight(1f), contentAlignment = Alignment.CenterStart) {
        InputField(
            query = query,
            onQueryChange = onQueryChange,
            onSearch = { focusManager.clearFocus() },
            expanded = true,
            onExpandedChange = { },
            modifier = Modifier.fillMaxWidth().semantics { contentDescription = "搜索书名、作者或格式" },
            label = "搜索书名、作者或格式",
            leadingIcon = {
                Box(Modifier.padding(start = 14.dp, end = 8.dp)) {
                    MiuixGlyph(Glyph.SEARCH, MiuixTheme.colorScheme.onSurfaceVariantSummary, 18.dp)
                }
            },
            trailingIcon = {
                if (query.isNotEmpty()) {
                    Box(Modifier.padding(end = 6.dp)) {
                        MiuixCircleButton(
                            Glyph.CLOSE,
                            "清空搜索",
                            { onQueryChange("") },
                            size = 28.dp,
                            container = MiuixTheme.colorScheme.surfaceContainerHighest,
                            tint = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                        )
                    }
                }
            },
        )
        // Miuix 0.9.4 hides its label while expanded, so keep a visible empty-state hint.
        if (query.isEmpty()) {
            Text(
                "搜索书名、作者或格式",
                modifier = Modifier.padding(start = 40.dp, end = 8.dp).clearAndSetSemantics { },
                style = MiuixTheme.textStyles.footnote1,
                color = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        }
        MiuixCircleButton(Glyph.CLOSE, "收起搜索", onCollapse, size = CircleControlSize)
    }
}

/** Shelf pane: hero, 3-column cover grid (1-column list/compact), notes. */
@Composable
private fun ShelfGridPane(
    books: List<ShelfBook>,
    continuing: ShelfBook?,
    layout: ShelfLayout,
    order: ShelfOrder,
    query: String,
    enabled: Boolean,
    topPadding: Dp,
    state: LazyGridState,
    onOpen: (ShelfBook, Offset?) -> Unit,
    onDelete: (ShelfBook) -> Unit,
    onImport: () -> Unit,
    onClearSearch: () -> Unit,
) {
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val narrow = maxWidth < 360.dp
        LazyVerticalGrid(
            columns = when {
                layout != ShelfLayout.GRID -> GridCells.Fixed(1)
                narrow -> GridCells.Adaptive(96.dp)
                else -> GridCells.Fixed(3)
            },
            state = state,
            modifier = Modifier.fillMaxSize().imePadding(),
            contentPadding = PaddingValues(
                start = PageMargin,
                end = PageMargin,
                top = topPadding,
                bottom = ShelfDockClearance,
            ),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(if (layout == ShelfLayout.COMPACT) 10.dp else 20.dp),
        ) {
            val hero = continuing
            if (query.isBlank() && hero != null) {
                item(key = "continue", span = { GridItemSpan(maxLineSpan) }) {
                    ContinueReadingHero(hero, enabled) { origin -> onOpen(hero, origin) }
                }
            }
            item(key = "section", span = { GridItemSpan(maxLineSpan) }) {
                ShelfSectionHeader(
                    title = if (query.isBlank()) "本地藏书" else "搜索结果",
                    detail = if (query.isBlank()) "按${order.label}排序"
                    else "“${query.trim()}” · ${books.size} 本",
                )
            }
            if (books.isEmpty()) {
                item(key = "empty", span = { GridItemSpan(maxLineSpan) }) {
                    ShelfEmptyCard(query.isNotBlank(), enabled, onImport, onClearSearch)
                }
            }
            items(books, key = { it.id }, contentType = { layout }) { book ->
                when (layout) {
                    ShelfLayout.GRID -> ShelfCoverTile(book, enabled, { origin -> onOpen(book, origin) }, { onDelete(book) })
                    ShelfLayout.LIST -> ShelfListRow(book, enabled, false, { origin -> onOpen(book, origin) }, { onDelete(book) })
                    ShelfLayout.COMPACT -> ShelfListRow(book, enabled, true, { origin -> onOpen(book, origin) }, { onDelete(book) })
                }
            }
            item(key = "local-note", span = { GridItemSpan(maxLineSpan) }) {
                ShelfMuted(
                    "本地存储 · 无需联网阅读\n长按书卡可移除；TXT / 基础 EPUB 纯文本，不还原 EPUB 图片、CSS、脚本、固定版式或 DRM 内容。",
                    Modifier.padding(top = 12.dp),
                )
            }
        }
    }
}

/** Settings pane: same grouped Miuix cards as the previous version, re-spaced and re-titled. */
@Composable
private fun ShelfSettingsPane(
    state: LibraryState,
    store: ReaderStore,
    onImportRequested: () -> Unit,
    orderIndex: Int,
    onOrderChange: (Int) -> Unit,
    listState: LazyListState,
    topPadding: Dp,
    modifier: Modifier,
) {
    val settings = state.settings
    val enabled = !state.busy
    LazyColumn(
        modifier = modifier.imePadding(),
        state = listState,
        contentPadding = PaddingValues(
            start = PageMargin,
            end = PageMargin,
            top = topPadding,
            bottom = ShelfDockClearance,
        ),
        verticalArrangement = Arrangement.spacedBy(24.dp),
    ) {
        item(key = "appearance") {
            ShelfSettingGroup("书架外观") {
                ShelfChoice("书架布局", listOf("封面", "列表", "紧凑"), settings.shelfLayout.ordinal) {
                    store.updateSettings(settings.copy(shelfLayout = ShelfLayout.entries[it]))
                }
                ShelfChoice(
                    "排序方式",
                    ShelfOrder.entries.map { it.label },
                    orderIndex.coerceIn(0, ShelfOrder.entries.lastIndex),
                    onOrderChange,
                )
                ShelfChoice("主题", listOf("跟随系统", "浅色", "深色", "纸色"), settings.theme.ordinal) {
                    store.updateSettings(settings.copy(theme = ReaderTheme.entries[it]))
                }
            }
        }
        item(key = "reading") {
            ShelfSettingGroup("默认阅读方式") {
                ShelfChoice("翻页方式", listOf("滚动", "滑动", "即时"), settings.readingMode.ordinal) {
                    store.updateSettings(settings.copy(readingMode = ReadingMode.entries[it]))
                }
                ShelfChoice("分栏", listOf("自动", "单栏", "双栏"), settings.columnMode.ordinal) {
                    store.updateSettings(settings.copy(columnMode = ColumnMode.entries[it]))
                }
                ShelfChoice("字体", listOf("衬线", "无衬线", "等宽"), settings.fontFamily.ordinal) {
                    store.updateSettings(settings.copy(fontFamily = ReaderFont.entries[it]))
                }
                ShelfSliderSetting("字号", settings.fontSize, 14f..40f, 25, "sp") {
                    store.updateSettings(settings.copy(fontSize = it))
                }
                ShelfNote("阅读页的「排版」还可调整行距、页边距、段距、字间距、首行缩进与字重。")
            }
        }
        item(key = "immersive") {
            ShelfSettingGroup("沉浸阅读") {
                ShelfSwitchSetting(
                    "自动收起工具栏",
                    "阅读时自动隐藏；轻点正文中央再次显示",
                    settings.autoHideControls,
                ) { store.updateSettings(settings.copy(autoHideControls = it)) }
                ShelfSwitchSetting(
                    "阅读页脚",
                    "显示当前章节与阅读进度",
                    settings.showReadingFooter,
                ) { store.updateSettings(settings.copy(showReadingFooter = it)) }
            }
        }
        item(key = "library") {
            ShelfSettingGroup("本地书库") {
                BasicComponent(
                    title = "导入书籍",
                    summary = "从「文件」选择 TXT 或 EPUB",
                    insideMargin = PaddingValues(0.dp),
                    onClick = onImportRequested,
                    onClickLabel = "选择本地书籍",
                    enabled = enabled,
                    endActions = {
                        MiuixCircleButton(Glyph.ADD, "导入本地书籍", onImportRequested, enabled = enabled)
                    },
                )
                BasicComponent(
                    title = "${state.books.size} 本藏书",
                    summary = "正文按章节存储，阅读按需加载；进度与偏好保存在本机。",
                    insideMargin = PaddingValues(0.dp),
                )
                BasicComponent(
                    title = "移除与原始文件",
                    summary = "长按书卡或使用列表中的「移除」，确认后只清理应用内副本和阅读进度，原始文件保留。",
                    insideMargin = PaddingValues(0.dp),
                )
                ShelfNote("格式兼容：TXT 与基础 EPUB 纯文本。EPUB 图片、CSS 排版、脚本、固定版式与 DRM 内容不在当前纯文本引擎内。")
            }
        }
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ShelfWidgets.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.layout.LayoutCoordinates
import androidx.compose.ui.layout.boundsInRoot
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.ShelfBook
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.overlay.OverlayListPopup
import top.yukonga.miuix.kmp.utils.PressFeedbackType

// Keep coordinates rather than a cached offset: scrolling can move a card between frames.
private class BookOrigin {
    var coordinates: LayoutCoordinates? = null

    fun center(): Offset? {
        val current = coordinates ?: return null
        if (!current.isAttached) return null
        val bounds = current.boundsInRoot()
        return if (bounds.isEmpty) null else bounds.center
    }
}

/** Uses the store's compatible global anchor, never a chapter-relative index as book progress. */
private fun shelfPercent(book: ShelfBook): Int {
    val last = (book.chapterCount.toLong() + book.paragraphCount - 1).coerceAtLeast(1)
    return ((book.progress.itemIndex.toLong() * 100) / last).coerceIn(0, 100).toInt()
}

private fun readingLabel(book: ShelfBook): String =
    if (book.lastOpenedAt > 0) "已读约 ${shelfPercent(book)}%" else "尚未开始"

private fun lengthLabel(book: ShelfBook): String {
    val count = book.characterCount
    return when {
        count >= 10000 -> "${count / 10000}.${count % 10000 / 1000} 万字"
        count > 0 -> "$count 字"
        else -> "${book.paragraphCount} 段"
    }
}

/** Compact badge text for the cover corner: unread / percent / finished. */
private fun progressBadge(book: ShelfBook): String = when {
    book.lastOpenedAt <= 0 -> "未读"
    shelfPercent(book) >= 100 -> "已读完"
    else -> "${shelfPercent(book)}%"
}

/**
 * "Continue reading" hero: cover, current badge, title, chapter/length metadata and the
 * progress track. The whole card is one reading target; removal is never offered here.
 */
@Composable
internal fun ContinueReadingHero(book: ShelfBook, enabled: Boolean, onOpen: (Offset?) -> Unit) {
    val origin = remember(book.id) { BookOrigin() }
    val primary = MiuixTheme.colorScheme.primary
    Card(
        modifier = Modifier.fillMaxWidth().semantics {
            contentDescription = "继续阅读《${book.title}》，${readingLabel(book)}"
        },
        colors = CardDefaults.defaultColors(
            color = MiuixTheme.colorScheme.surfaceContainer.copy(alpha = if (enabled) 1f else 0.7f),
            contentColor = MiuixTheme.colorScheme.onSurface,
        ),
        insideMargin = PaddingValues(0.dp),
        pressFeedbackType = PressFeedbackType.Sink,
        onClick = if (enabled) ({ onOpen(origin.center()) }) else null,
    ) {
        Row(
            Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            BookCover(book, Modifier.width(64.dp).aspectRatio(0.75f).onGloballyPositioned { origin.coordinates = it }, small = true)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    CountPill("继续阅读", container = primary.copy(alpha = 0.14f), content = primary)
                    Spacer(Modifier.weight(1f))
                    Text(
                        "${shelfPercent(book)}%",
                        style = MiuixTheme.textStyles.footnote1,
                        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
                        maxLines = 1,
                    )
                }
                Text(
                    book.title,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                MutedLabel(
                    "${book.author.ifBlank { "佚名" }} · ${book.format} · ${book.chapterCount} 章 · ${lengthLabel(book)}",
                    maxLines = 1,
                )
                LinearProgressIndicator(
                    modifier = Modifier.fillMaxWidth().padding(top = 2.dp),
                    progress = shelfPercent(book) / 100f,
                    height = 5.dp,
                )
            }
        }
    }
}

/**
 * Grid tile: 3:4 generated cover with a progress badge in the bottom-right corner, then
 * title/author. Long press is the removal affordance so the title keeps its full width.
 */
@Composable
internal fun ShelfCoverTile(book: ShelfBook, enabled: Boolean, onOpen: (Offset?) -> Unit, onDelete: () -> Unit) {
    val origin = remember(book.id) { BookOrigin() }
    Card(
        modifier = Modifier.fillMaxWidth().semantics {
            contentDescription = "《${book.title}》，${book.author.ifBlank { "佚名" }}，${progressBadge(book)}；长按可移除"
        },
        colors = CardDefaults.defaultColors(
            color = Color.Transparent,
            contentColor = MiuixTheme.colorScheme.onSurface,
        ),
        insideMargin = PaddingValues(0.dp),
        pressFeedbackType = PressFeedbackType.Sink,
        onClick = if (enabled) ({ onOpen(origin.center()) }) else null,
        onLongPress = if (enabled) onDelete else null,
    ) {
        Column(Modifier.fillMaxWidth()) {
            Box(Modifier.fillMaxWidth().aspectRatio(0.75f).onGloballyPositioned { origin.coordinates = it }) {
                BookCover(book, Modifier.fillMaxSize())
                CountPill(
                    progressBadge(book),
                    Modifier.align(Alignment.BottomEnd).padding(6.dp),
                    container = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.72f),
                    content = MiuixTheme.colorScheme.surface,
                )
            }
            Text(
                book.title,
                modifier = Modifier.fillMaxWidth().padding(start = 2.dp, end = 2.dp, top = 8.dp),
                fontSize = 15.sp,
                lineHeight = 20.sp,
                fontWeight = FontWeight.Medium,
                minLines = 2,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                book.author.ifBlank { "佚名" },
                modifier = Modifier.fillMaxWidth().padding(start = 2.dp, end = 2.dp, top = 2.dp),
                fontSize = 12.sp,
                color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

/** One-column list / compact row. Removal sits at the trailing edge, never next to the title. */
@Composable
internal fun ShelfListRow(
    book: ShelfBook, enabled: Boolean, compact: Boolean, onOpen: (Offset?) -> Unit, onDelete: () -> Unit,
) {
    val origin = remember(book.id) { BookOrigin() }
    val coverOrigin = remember(book.id) { BookOrigin() }
    val primary = MiuixTheme.colorScheme.primary
    Card(
        modifier = Modifier.fillMaxWidth().onGloballyPositioned { origin.coordinates = it }.semantics {
            contentDescription = "《${book.title}》，${book.author.ifBlank { "佚名" }}，${readingLabel(book)}"
        },
        colors = CardDefaults.defaultColors(
            color = MiuixTheme.colorScheme.surfaceContainer,
            contentColor = MiuixTheme.colorScheme.onSurface,
        ),
        insideMargin = PaddingValues(0.dp),
        pressFeedbackType = PressFeedbackType.Sink,
        onClick = if (enabled) ({ onOpen(if (compact) origin.center() else coverOrigin.center() ?: origin.center()) }) else null,
        onLongPress = if (enabled) onDelete else null,
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = if (compact) 10.dp else 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            if (compact) {
                Box(
                    Modifier.width(4.dp).height(34.dp)
                        .background(primary.copy(alpha = 0.55f), RoundedCornerShape(2.dp)),
                )
            } else {
                BookCover(book, Modifier.width(54.dp).aspectRatio(0.75f).onGloballyPositioned { coverOrigin.coordinates = it }, small = true)
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(
                    book.title,
                    fontSize = if (compact) 16.sp else 18.sp,
                    fontWeight = FontWeight.Medium,
                    maxLines = if (compact) 1 else 2,
                    overflow = TextOverflow.Ellipsis,
                )
                MutedLabel(
                    if (compact) "${book.author.ifBlank { "佚名" }} · ${readingLabel(book)}"
                    else "${book.author.ifBlank { "佚名" }} · ${book.format} · ${book.chapterCount} 章 · ${lengthLabel(book)}",
                    maxLines = 1,
                )
                if (!compact) {
                    LinearProgressIndicator(
                        modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                        progress = shelfPercent(book) / 100f,
                        height = 3.dp,
                    )
                }
            }
            if (compact) {
                CountPill(progressBadge(book))
            }
            ShelfRemoveAction(book, enabled, onDelete)
        }
    }
}

@Composable
private fun ShelfRemoveAction(book: ShelfBook, enabled: Boolean, onDelete: () -> Unit) {
    TextButton(
        "移除", onDelete,
        enabled = enabled,
        minWidth = 48.dp,
        minHeight = 48.dp,
        insideMargin = PaddingValues(horizontal = 8.dp, vertical = 8.dp),
        textStyle = MiuixTheme.textStyles.footnote1,
        colors = ButtonDefaults.textButtonColors(
            color = Color.Transparent,
            textColor = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
        ),
        modifier = Modifier.semantics { contentDescription = "移除《${book.title}》，打开确认" },
    )
}

/**
 * Section heading above the grid. The count is announced politely when a search narrows it.
 */
@Composable
internal fun ShelfSectionHeader(title: String, detail: String, modifier: Modifier = Modifier) {
    Row(
        modifier.fillMaxWidth().padding(top = 6.dp, bottom = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            title,
            modifier = Modifier.weight(1f).semantics { heading() },
            style = MiuixTheme.textStyles.title4,
            fontWeight = FontWeight.SemiBold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            detail,
            modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
            style = MiuixTheme.textStyles.footnote1,
            color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
internal fun ShelfEmptyCard(
    querying: Boolean, enabled: Boolean, onImport: () -> Unit, onClearSearch: () -> Unit,
) {
    Card(
        Modifier.fillMaxWidth(),
        insideMargin = PaddingValues(20.dp),
        colors = CardDefaults.defaultColors(
            color = MiuixTheme.colorScheme.surfaceContainer,
            contentColor = MiuixTheme.colorScheme.onSurface,
        ),
    ) {
        Text(
            if (querying) "还没有找到这本书" else "让第一本书，住进来",
            style = MiuixTheme.textStyles.title4,
            fontWeight = FontWeight.SemiBold,
        )
        MutedLabel(
            if (querying) "换一个书名、作者或格式试试。" else "导入本地 TXT 或 EPUB，下次从上次的位置接着读。",
            modifier = Modifier.padding(top = 8.dp),
        )
        TextButton(
            if (querying) "清空搜索" else "选择本地书籍",
            { if (querying) onClearSearch() else onImport() },
            modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
            enabled = enabled,
            minHeight = 48.dp,
            colors = ButtonDefaults.textButtonColorsPrimary(),
        )
    }
}

/** Typographic covers are generated locally; they do not pretend to be fetched cover artwork. */
@Composable
private fun BookCover(book: ShelfBook, modifier: Modifier, small: Boolean = false) {
    val palette = listOf(
        Color(0xFF355E50), Color(0xFF465B73), Color(0xFF745749),
        Color(0xFF635774), Color(0xFF61613F), Color(0xFF6E4C58),
    )
    val color = palette[(book.id.hashCode() and Int.MAX_VALUE) % palette.size]
    val radius = if (small) 8.dp else 12.dp
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(radius))
            .background(Brush.linearGradient(listOf(color, color.copy(alpha = 0.76f))))
            .clearAndSetSemantics { },
    ) {
        Box(
            Modifier.fillMaxHeight().width(if (small) 4.dp else 7.dp)
                .background(Color.Black.copy(alpha = 0.14f)),
        )
        Column(
            Modifier.fillMaxSize().padding(if (small) 8.dp else 12.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(
                book.format,
                fontSize = if (small) 8.sp else 9.sp,
                color = Color.White.copy(alpha = 0.72f),
                letterSpacing = 1.sp,
                maxLines = 1,
            )
            Text(
                book.title,
                fontSize = if (small) 15.sp else 18.sp,
                lineHeight = if (small) 19.sp else 23.sp,
                color = Color.White,
                fontWeight = FontWeight.SemiBold,
                maxLines = if (small) 2 else 3,
                overflow = TextOverflow.Ellipsis,
            )
            if (!small) {
                Text(
                    book.author.ifBlank { "叶读 · 本地藏书" },
                    fontSize = 10.sp,
                    color = Color.White.copy(alpha = 0.8f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
internal fun ShelfMuted(text: String, modifier: Modifier = Modifier, maxLines: Int = Int.MAX_VALUE) {
    Text(
        text, modifier,
        fontSize = 13.sp,
        lineHeight = 20.sp,
        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.65f),
        maxLines = maxLines,
        overflow = TextOverflow.Ellipsis,
    )
}

/** Same muted voice, styled through the shared Miuix type scale. */
@Composable
private fun MutedLabel(text: String, modifier: Modifier = Modifier, maxLines: Int = Int.MAX_VALUE) {
    Text(
        text, modifier,
        style = MiuixTheme.textStyles.footnote1,
        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
        maxLines = maxLines,
        overflow = TextOverflow.Ellipsis,
    )
}

@Composable
internal fun ShelfNote(text: String, modifier: Modifier = Modifier) {
    Text(
        text, modifier.fillMaxWidth(),
        fontSize = 12.sp,
        lineHeight = 18.sp,
        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.55f),
    )
}

/** Grouped settings card: section heading outside, roomy rows inside, no sticky dividers. */
@Composable
internal fun ShelfSettingGroup(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(
            title,
            modifier = Modifier.padding(start = 4.dp).semantics { heading() },
            style = MiuixTheme.textStyles.subtitle,
            color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
        Card(Modifier.fillMaxWidth(), insideMargin = PaddingValues(18.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(18.dp), content = content)
        }
    }
}

/** Anchored Miuix popup with selected check mark and a compact settings row. */
@Composable
internal fun ShelfChoice(label: String, options: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    if (options.isEmpty()) return
    var expanded by remember { mutableStateOf(false) }
    val index = selected.coerceIn(0, options.lastIndex)
    Box(Modifier.fillMaxWidth()) {
        BasicComponent(
            title = label,
            insideMargin = PaddingValues(0.dp),
            onClick = { expanded = true },
            onClickLabel = "选择$label",
            endActions = {
                Text(options[index], color = MiuixTheme.colorScheme.onSurfaceVariantSummary, maxLines = 1)
                Spacer(Modifier.width(8.dp))
                DropdownArrowEndAction(MiuixTheme.colorScheme.onSurfaceVariantSummary)
            },
        )
        OverlayListPopup(
            show = expanded,
            alignment = PopupPositionProvider.Align.End,
            onDismissRequest = { expanded = false },
        ) {
            ListPopupColumn {
                options.forEachIndexed { optionIndex, option ->
                    DropdownImpl(
                        text = option,
                        optionSize = options.size,
                        isSelected = optionIndex == index,
                        index = optionIndex,
                        onSelectedIndexChange = {
                            expanded = false
                            onSelect(it)
                        },
                    )
                }
            }
        }
    }
}

@Composable
internal fun ShelfSwitchSetting(
    title: String, summary: String, checked: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 52.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(title, style = MiuixTheme.textStyles.body1)
            MutedLabel(summary, maxLines = 2)
        }
        Spacer(Modifier.width(12.dp))
        Switch(
            checked = checked,
            onCheckedChange = onChange,
            modifier = Modifier.semantics { contentDescription = title },
            enabled = enabled,
        )
    }
}

@Composable
internal fun ShelfSliderSetting(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    steps: Int,
    unit: String,
    onChange: (Float) -> Unit,
) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(label, Modifier.weight(1f), style = MiuixTheme.textStyles.body1)
            CountPill("${value.toInt()}$unit")
        }
        Slider(
            value = value,
            onValueChange = onChange,
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).semantics {
                contentDescription = label
            },
            valueRange = range,
            steps = steps,
        )
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/TocSheet.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.BookDocument
import dev.leaf.reader.BookManifest
import top.yukonga.miuix.kmp.basic.TabRowWithContour
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.basic.TextField
import top.yukonga.miuix.kmp.basic.TextFieldDefaults
import top.yukonga.miuix.kmp.theme.MiuixTheme

/**
 * Table-of-contents sheet body. It only renders state it is given: chapter titles and the
 * manifest's character counts. Nothing here invents chapters, bookmarks or notes.
 */
@Composable
internal fun TocSheet(
    book: BookDocument,
    manifest: BookManifest?,
    currentChapter: Int,
    progressText: String,
    maxHeight: Dp,
    onSelectChapter: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    val total = manifest?.chapters?.size?.takeIf { it > 0 } ?: book.chapters.size
    val current = currentChapter.coerceIn(0, (total - 1).coerceAtLeast(0))
    var tab by remember(book.id) { mutableIntStateOf(TocDirectoryTab) }
    var query by remember(book.id) { mutableStateOf("") }
    var descending by remember(book.id) { mutableStateOf(false) }
    var showCounts by remember(book.id) { mutableStateOf(true) }
    var compact by remember(book.id) { mutableStateOf(false) }
    var pendingScroll by remember(book.id) { mutableStateOf<Int?>(null) }
    val matches = remember(book.chapters, query, descending) {
        val trimmed = query.trim()
        val filtered = if (trimmed.isEmpty()) {
            book.chapters.indices.toList()
        } else {
            book.chapters.indices.filter { index ->
                book.chapters[index].title.ifBlank { "正文" }.contains(trimmed, ignoreCase = true)
            }
        }
        if (descending) filtered.asReversed() else filtered
    }
    val listState = rememberLazyListState(initialFirstVisibleItemIndex = current)
    LaunchedEffect(pendingScroll, matches) {
        val target = pendingScroll ?: return@LaunchedEffect
        pendingScroll = null
        listState.animateScrollToItem(target.coerceIn(0, (matches.size - 1).coerceAtLeast(0)))
    }
    val currentTitle = chapterTitle(book, current)

    Column(
        Modifier.fillMaxWidth()
            .heightIn(max = maxHeight)
            .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Bottom))
            .padding(bottom = 14.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            TocCover(book, Modifier.width(40.dp).height(54.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(book.title, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, maxLines = 1,
                    overflow = TextOverflow.Ellipsis, modifier = Modifier.semantics { heading() })
                Text(currentTitle, fontSize = 12.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            CountPill(progressText)
        }
        Spacer(Modifier.height(12.dp))
        TabRowWithContour(
            tabs = TocTabs,
            selectedTabIndex = tab,
            onTabSelected = { tab = it },
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp)
                .semantics { contentDescription = "目录分区" },
        )
        Spacer(Modifier.height(12.dp))
        when (tab) {
            TocDirectoryTab -> {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    TextField(
                        value = query,
                        onValueChange = { query = it },
                        modifier = Modifier.weight(1f).heightIn(min = TocButtonSize)
                            .semantics { contentDescription = "搜索章节" },
                        insideMargin = DpSize(12.dp, 8.dp),
                        cornerRadius = 22.dp,
                        label = "搜索章节…",
                        useLabelAsPlaceholder = true,
                        singleLine = true,
                        textStyle = MiuixTheme.textStyles.body2,
                        colors = TextFieldDefaults.textFieldColors(
                            backgroundColor = MiuixTheme.colorScheme.surfaceContainerHigh,
                            labelColor = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                        ),
                        leadingIcon = {
                            Box(Modifier.padding(start = 12.dp, end = 4.dp)) {
                                MiuixGlyph(Glyph.SEARCH, MiuixTheme.colorScheme.onSurfaceVariantSummary, 18.dp)
                            }
                        },
                    )
                    TocIconButton(Glyph.REFRESH, "回到当前章节") {
                        query = ""
                        pendingScroll = if (descending) total - 1 - current else current
                    }
                    TocIconButton(Glyph.TAG,
                        if (showCounts) "隐藏章节字数" else "显示章节字数",
                        highlighted = showCounts) { showCounts = !showCounts }
                    TocIconButton(Glyph.SORT,
                        if (descending) "切换为正序" else "切换为倒序",
                        highlighted = descending) { descending = !descending }
                    TocIconButton(Glyph.MORE,
                        if (compact) "切换为宽松行距" else "切换为紧凑行距",
                        highlighted = compact) { compact = !compact }
                }
                // Very short panels (16:9 landscape) drop the extra card so the list keeps real space.
                val shortPanel = maxHeight < 400.dp
                Spacer(Modifier.height(if (shortPanel) 8.dp else 14.dp))
                if (!shortPanel) {
                    CurrentChapterCard(
                        title = currentTitle,
                        countText = countText(manifest, current),
                        onClick = onDismiss,
                    )
                    Spacer(Modifier.height(8.dp))
                }
                if (matches.isEmpty()) {
                    Text("没有匹配“${query.trim()}”的章节",
                        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 24.dp),
                        fontSize = 14.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxWidth().weight(1f, fill = false),
                    ) {
                        items(count = matches.size, key = { matches[it] }) { position ->
                            val index = matches[position]
                            TocChapterRow(
                                title = chapterTitle(book, index),
                                countText = if (showCounts) countText(manifest, index) else "",
                                current = index == current,
                                compact = compact,
                                onClick = { onSelectChapter(index) },
                            )
                        }
                    }
                }
            }
            TocInfoTab -> TocInfoPanel(book, total, currentTitle, progressText)
            TocBookmarkTab -> TocPlaceholder("书签功能即将加入", "阅读时长按段落添加书签，之后会集中显示在这里。")
            else -> TocPlaceholder("笔记功能即将加入", "划线摘录与阅读想法会集中显示在这里。")
        }
    }
}

private val TocTabs = listOf("信息", "目录", "书签", "笔记")
private const val TocInfoTab = 0
private const val TocDirectoryTab = 1
private const val TocBookmarkTab = 2
private val TocButtonSize = 44.dp
private val TocButtonVisual = 36.dp

private fun chapterTitle(book: BookDocument, index: Int): String =
    book.chapters.getOrNull(index)?.title?.ifBlank { "正文" } ?: "正文"

/** Character counts come from the manifest; a missing entry shows a dash instead of a guess. */
private fun countText(manifest: BookManifest?, index: Int): String {
    val count = manifest?.chapters?.getOrNull(index)?.characterCount ?: return "—"
    return "${count}字"
}

/** Typographic cover in Miuix colours; the reader ships no artwork, so nothing is fetched. */
@Composable
private fun TocCover(book: BookDocument, modifier: Modifier) {
    val primary = MiuixTheme.colorScheme.primary
    Box(
        modifier.clip(RoundedCornerShape(8.dp))
            .background(primary.copy(alpha = 0.14f))
            .clearAndSetSemantics { },
    ) {
        Box(Modifier.fillMaxHeight().width(4.dp).background(primary.copy(alpha = 0.5f)))
        Text(book.title.take(2), Modifier.align(Alignment.Center).padding(start = 4.dp, end = 3.dp),
            fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = primary, maxLines = 1)
    }
}

/** 44dp touch target with a 36dp rounded-square visual, as in the reference sheet. */
@Composable
private fun TocIconButton(
    glyph: Glyph,
    description: String,
    highlighted: Boolean = false,
    onClick: () -> Unit,
) {
    Box(
        modifier = Modifier.size(TocButtonSize).clip(RoundedCornerShape(12.dp))
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier.size(TocButtonVisual).clip(RoundedCornerShape(11.dp))
                .background(
                    if (highlighted) MiuixTheme.colorScheme.surfaceContainerHighest
                    else MiuixTheme.colorScheme.surfaceContainerHigh,
                ),
            contentAlignment = Alignment.Center,
        ) {
            MiuixGlyph(
                glyph,
                if (highlighted) MiuixTheme.colorScheme.onSurface
                else MiuixTheme.colorScheme.onSurfaceVariantSummary,
                17.dp,
            )
        }
    }
}

@Composable
private fun CurrentChapterCard(title: String, countText: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(MiuixTheme.colorScheme.surfaceContainerHigh)
            .clickable(role = Role.Button, onClick = onClick)
            .heightIn(min = 48.dp)
            .padding(start = 16.dp, end = 14.dp, top = 8.dp, bottom = 8.dp)
            .semantics {
                contentDescription = "返回当前章节：$title"
                stateDescription = "当前章节"
            },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(title, Modifier.weight(1f), fontSize = 15.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
            color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
        CountPill(
            text = countText,
            container = MiuixTheme.colorScheme.primaryContainer,
            content = MiuixTheme.colorScheme.onPrimaryContainer,
        )
    }
}

@Composable
private fun TocChapterRow(
    title: String,
    countText: String,
    current: Boolean,
    compact: Boolean,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .then(if (current) Modifier.background(MiuixTheme.colorScheme.surfaceContainerHigh) else Modifier)
            .clickable(role = Role.Button, onClick = onClick)
            .heightIn(min = if (compact) 44.dp else 48.dp)
            .padding(horizontal = 12.dp, vertical = if (compact) 2.dp else 6.dp)
            .then(if (current) Modifier.semantics { stateDescription = "当前章节" } else Modifier),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            title,
            Modifier.weight(1f),
            fontSize = 15.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            color = if (current) MiuixTheme.colorScheme.onSurfaceVariantSummary
            else MiuixTheme.colorScheme.onSurface,
        )
        if (countText.isNotEmpty()) {
            CountPill(
                text = countText,
                container = if (current) MiuixTheme.colorScheme.primaryContainer
                else MiuixTheme.colorScheme.surfaceContainerHighest,
                content = if (current) MiuixTheme.colorScheme.onPrimaryContainer
                else MiuixTheme.colorScheme.onSurfaceVariantSummary,
            )
        }
    }
}

@Composable
private fun TocInfoPanel(book: BookDocument, total: Int, currentTitle: String, progressText: String) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        TocInfoLine("书名", book.title)
        TocInfoLine("作者", book.author.ifBlank { "佚名" })
        TocInfoLine("格式", book.format)
        TocInfoLine("章数", "$total 章")
        TocInfoLine("当前章", currentTitle)
        TocInfoLine("进度", progressText)
    }
}

@Composable
private fun TocInfoLine(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(label, Modifier.width(56.dp), fontSize = 13.sp,
            color = MiuixTheme.colorScheme.onSurfaceVariantSummary, maxLines = 1)
        Text(value, Modifier.weight(1f), fontSize = 14.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun TocPlaceholder(title: String, detail: String) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(title, fontSize = 15.sp, fontWeight = FontWeight.Medium)
        Text(detail, fontSize = 13.sp, lineHeight = 20.sp,
            color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
    }
}
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ManifestStorageTest.kt': r'''@file:OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)

package dev.leaf.reader

import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class ManifestStorageTest {
    private val id = "c".repeat(64)
    private val revision = "1".repeat(32)
    private fun canonical(bookId: String = id) = "book-$bookId.manifest.json"

    private data class Fixture(val manifest: BookManifest, val chapters: List<BookChapter>)

    private fun fixture(
        chapters: List<BookChapter> = List(5) { BookChapter("第 ${it + 1} 章", listOf("正文 $it 😀", "尾段 $it")) },
        revision: String = this.revision,
        title: String = "分章书籍",
    ): Fixture = Fixture(
        BookManifest(id = id, title = title, revision = revision, chapters = chapters.mapIndexed { index, chapter ->
            ChapterEntry(chapter.title, "book-$id-$revision-c$index.json", chapter.paragraphs.size,
                chapter.paragraphs.sumOf { it.length })
        }), chapters,
    )

    private fun ManifestFiles.install(fixture: Fixture) {
        fixture.chapters.forEachIndexed { index, chapter ->
            values[fixture.manifest.chapters[index].fileName] = Json.encodeToString(chapter)
        }
    }

    @Test fun chapterUtf16LimitAcceptsExact512KiAndRejectsOneMoreUnit() {
        assertEquals(512 * 1024, MAX_CHAPTER_UNITS)
        fun chapter(units: Int): BookChapter = BookChapter("边界", buildList {
            var remaining = units
            while (remaining > 0) {
                val size = minOf(remaining, 16000)
                add("字".repeat(size))
                remaining -= size
            }
        })
        val exact = chapter(512 * 1024)
        val entry = fixture(listOf(exact)).manifest.chapters.single()
        exact.validate(entry)
        assertEquals(512 * 1024, entry.characterCount)
        assertFailsWith<IllegalArgumentException> { chapter(512 * 1024 + 1).validate() }
        assertFailsWith<IllegalArgumentException> {
            fixture(listOf(exact)).manifest.copy(chapters = listOf(entry.copy(characterCount = 512 * 1024 + 1))).validate()
        }
        // UTF-16 units, not Unicode code points: each emoji occupies two units.
        assertEquals(16000, "😀".repeat(8000).length)
        assertFailsWith<IllegalArgumentException> { BookChapter("段落边界", listOf("😀".repeat(8001))).validate() }
    }

    @Test fun manifestRejectsTraversalAbsoluteAndWrongRevisionOrIndexNames() {
        val valid = fixture().manifest
        valid.validate()
        val name = valid.chapters.first().fileName
        val invalid = listOf(
            "../$name", "/$name", "folder/$name", "folder\\$name", "./$name",
            "book-${"d".repeat(64)}-$revision-c0.json",
            "book-$id-${"2".repeat(32)}-c0.json", "book-$id-$revision-c00.json",
            "book-$id-$revision-c1.json", "$name/..", "$name\u0000",
        )
        invalid.forEach { candidate ->
            assertFailsWith<IllegalArgumentException>(candidate) {
                valid.copy(chapters = valid.chapters.toMutableList().also {
                    it[0] = it[0].copy(fileName = candidate)
                }).validate()
            }
        }
        assertFailsWith<IllegalArgumentException> { valid.copy(schema = 1).validate() }
        assertFailsWith<IllegalArgumentException> { valid.copy(revision = "A".repeat(32)).validate() }
        assertFailsWith<IllegalArgumentException> { valid.copy(id = "../bad").validate() }
    }

    @Test fun invalidManifestPathIsRejectedBeforeAnyBodyReadOrPublication() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        files.values["unrelated.json"] = "keep"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.reads.clear()
        val invalid = draft.manifest.copy(chapters = draft.manifest.chapters.toMutableList().also {
            it[1] = it[1].copy(fileName = "../unrelated.json")
        })
        store.importManifestJson(Json.encodeToString(invalid)); advanceUntilIdle()
        assertTrue(files.reads.isEmpty())
        assertTrue(store.state.value.books.isEmpty())
        assertNull(files.values[canonical()])
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.busy)
        assertEquals("keep", files.values["unrelated.json"])
    }

    @Test fun paragraphLimitUsesLongArithmeticBeforeSummingManifestMetadata() {
        val counts = List(42949) { 100000 } + 67297 // 2^32 + 1, not one paragraph.
        val manifest = BookManifest(id = id, title = "溢出边界", revision = revision,
            chapters = counts.mapIndexed { index, count ->
                ChapterEntry("章", "book-$id-$revision-c$index.json", count, 1)
            })
        assertEquals(4_294_967_297L, counts.sumOf { it.toLong() })
        assertFailsWith<IllegalArgumentException> { manifest.validate() }
    }

    @Test fun schema1LibraryKeepsBackupAndMigratesSplitChapterProgressLazily() = runTest {
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "字".repeat(10000) }), BookChapter("后记", listOf("尾")),
        ))
        val original = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":2,"paragraphCount":41,"addedAt":10,"lastOpenedAt":20,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{"fontSize":23,"lineHeight":1.8,"theme":"SEPIA"}}"""
        val files = ManifestFiles()
        files.values["library.json"] = original
        val legacyRaw = Json.encodeToString(legacy)
        files.values["book-$id.json"] = legacyRaw
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertEquals(original, files.values["library.v1-backup.json"])
        assertEquals(original, files.values["library.json"])
        assertNull(files.values[canonical()]) // Startup does not decode every old book body.
        assertEquals(ReadingMode.SLIDE, store.state.value.settings.readingMode)
        assertEquals(ShelfLayout.GRID, store.state.value.settings.shelfLayout)
        store.openBook(id); advanceUntilIdle()
        val state = store.state.value
        val manifest = assertNotNull(state.manifest)
        assertEquals(3, manifest.chapters.size)
        assertTrue(manifest.chapters.all { it.characterCount <= 512 * 1024 })
        assertEquals(400001L, state.books.single().characterCount)
        assertTrue(state.currentBook!!.chapters.all { it.paragraphs.isEmpty() })
        assertEquals("长章（续）", state.chapter?.title)
        assertEquals(1, state.currentProgress.chapterIndex)
        assertEquals(5, state.currentProgress.paragraphIndex)
        assertEquals(32, state.currentProgress.itemIndex) // New split heading shifts the legacy global index.
        assertEquals(57, state.currentProgress.scrollOffset)
        assertEquals(0, state.currentProgress.characterOffset)
        assertEquals(legacyRaw, files.values["book-$id.json"])
        store.closeBook()
        assertEquals(2, Json.decodeFromString<LibrarySnapshot>(files.values.getValue("library.json")).schema)
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(1, restarted.state.value.currentProgress.chapterIndex)
        assertEquals(5, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(57, restarted.state.value.currentProgress.scrollOffset)
        assertEquals(original, files.values["library.v1-backup.json"])
        assertEquals(23f, restarted.state.value.settings.fontSize)
        assertEquals(ReaderTheme.SEPIA, restarted.state.value.settings.theme)
    }

    @Test fun canceledLegacyMigrationKeepsOriginalParagraphAnchor() = runTest {
        val files = ManifestFiles()
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "段${it.toString().padStart(2, '0')}" + "字".repeat(9997) }),
        ))
        files.values["book-$id.json"] = Json.encodeToString(legacy)
        files.values["library.json"] = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":1,"paragraphCount":40,"addedAt":10,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{}}"""
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.openBook(id)
        store.closeBook() // The queued migration can finish I/O but must not publish a wrong anchor.
        advanceUntilIdle()
        assertNull(store.state.value.currentBook)
        store.openBook(id); advanceUntilIdle()
        assertEquals(1, store.state.value.currentProgress.chapterIndex)
        assertEquals(5, store.state.value.currentProgress.paragraphIndex)
        assertEquals(32, store.state.value.currentProgress.itemIndex)
        assertEquals(57, store.state.value.currentProgress.scrollOffset)
        val state = store.state.value
        assertEquals(legacy.chapters.single().paragraphs[30],
            state.chapter?.paragraphs?.get(state.currentProgress.paragraphIndex - 1))
    }

    @Test fun migrationIndexWriteFailureRetainsOriginalParagraphAfterRestart() = runTest {
        val files = ManifestFiles()
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "段${it.toString().padStart(2, '0')}" + "字".repeat(9997) }),
        ))
        files.values["book-$id.json"] = Json.encodeToString(legacy)
        files.values["library.json"] = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":1,"paragraphCount":40,"addedAt":10,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{}}"""
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        // Initial flush may succeed; every later index write fails once the migrated manifest exists.
        files.blockWrites = { name -> name == "library.json" && canonical() in files.values }
        store.openBook(id); advanceUntilIdle()
        assertNotNull(store.state.value.error)
        val onDisk = Json.decodeFromString<LibrarySnapshot>(files.values.getValue("library.json"))
        assertEquals(-1, onDisk.books.single().progress.chapterIndex)
        assertEquals(31, onDisk.books.single().progress.itemIndex)
        files.blockWrites = { false }
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        val state = restarted.state.value
        assertEquals(1, state.currentProgress.chapterIndex)
        assertEquals(5, state.currentProgress.paragraphIndex)
        assertEquals(32, state.currentProgress.itemIndex)
        assertEquals(57, state.currentProgress.scrollOffset)
        assertEquals(legacy.chapters.single().paragraphs[30],
            state.chapter?.paragraphs?.get(state.currentProgress.paragraphIndex - 1))
    }

    @Test fun legacyReimportMapsUnmigratedShelfAnchorBeforeFirstOpen() = runTest {
        val files = ManifestFiles()
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "段${it.toString().padStart(2, '0')}" + "字".repeat(9997) }),
        ))
        files.values["library.json"] = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":1,"paragraphCount":40,"addedAt":10,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{}}"""
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(Json.encodeToString(legacy)); advanceUntilIdle()
        val saved = store.state.value.books.single().progress
        assertEquals(1, saved.chapterIndex)
        assertEquals(5, saved.paragraphIndex)
        assertEquals(32, saved.itemIndex)
        store.openBook(id); advanceUntilIdle()
        val state = store.state.value
        assertEquals(57, state.currentProgress.scrollOffset)
        assertEquals(legacy.chapters.single().paragraphs[30],
            state.chapter?.paragraphs?.get(state.currentProgress.paragraphIndex - 1))
    }

    @Test fun existingV1BackupIsNeverOverwritten() = runTest {
        val files = ManifestFiles()
        files.values["library.json"] = """{"schema":1,"books":[],"settings":{}}"""
        files.values["library.v1-backup.json"] = "earlier backup"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.flush()
        assertNull(store.state.value.error)
        assertEquals("earlier backup", files.values["library.v1-backup.json"])
    }

    @Test fun failedV1BackupPreventsOverwritingTheOnlyLegacyIndex() = runTest {
        val files = ManifestFiles()
        val original = """{"schema":1,"books":[],"settings":{"fontSize":22}}"""
        files.values["library.json"] = original
        files.failNextWrites["library.v1-backup.json"] = 1
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertNotNull(store.state.value.error)
        store.dismissError()
        store.updateSettings(ReaderSettings(fontSize = 30f))
        advanceUntilIdle()
        store.flush()
        assertEquals(original, files.values["library.json"])
        assertNull(files.values["library.v1-backup.json"])
    }

    @Test fun importSamplesEndpointsAndOpeningLoadsOnlyCurrentChapterBody() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.reads.clear()
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        val bodyNames = draft.manifest.chapters.map { it.fileName }.toSet()
        assertEquals(listOf(draft.manifest.chapters.first().fileName, draft.manifest.chapters.last().fileName),
            files.reads.filter { it in bodyNames })
        files.reads.clear()
        store.openBook(id); advanceUntilIdle()
        assertEquals(listOf(canonical(), draft.manifest.chapters[0].fileName), files.reads)
        assertEquals(draft.chapters[0], store.state.value.chapter)
        assertTrue(store.state.value.currentBook!!.chapters.all { it.paragraphs.isEmpty() })
        assertEquals(5, store.state.value.currentBook!!.chapters.size)
        assertFalse(files.reads.contains("book-$id.json"))
        files.reads.clear()
        store.selectChapter(2); advanceUntilIdle()
        assertEquals(listOf(draft.manifest.chapters[2].fileName), files.reads)
        assertEquals(draft.chapters[2], store.state.value.chapter)
    }

    @Test fun chapterCacheIsBoundedAndCloseDropsCachedBodies() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        store.openBook(id); advanceUntilIdle()
        files.reads.clear()
        store.selectChapter(0); advanceUntilIdle()
        assertTrue(files.reads.isEmpty())
        for (index in 1..3) { store.selectChapter(index); advanceUntilIdle() }
        files.reads.clear()
        store.selectChapter(0); advanceUntilIdle()
        assertEquals(listOf(draft.manifest.chapters[0].fileName), files.reads)
        store.closeBook()
        files.reads.clear()
        store.openBook(id); advanceUntilIdle()
        assertTrue(draft.manifest.chapters[0].fileName in files.reads)
    }

    @Test fun mismatchedMiddleChapterFailsOnDemandAndRetainsLastReadableShelfAnchor() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        files.values[draft.manifest.chapters[1].fileName] = Json.encodeToString(BookChapter("损坏", listOf("不匹配")))
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        assertNull(store.state.value.error) // Import validates bounded endpoints, not every chapter body.
        store.openBook(id); advanceUntilIdle()
        store.updateChapterProgress(1, 2, 17)
        store.selectChapter(1); advanceUntilIdle()
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.chapterBusy)
        assertNull(store.state.value.chapter)
        val saved = store.state.value.books.single().progress
        assertEquals(0, saved.chapterIndex)
        assertEquals(1, saved.paragraphIndex)
        assertEquals(2, saved.characterOffset)
        assertEquals(17, saved.scrollOffset)
        store.closeBook()
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(draft.chapters[0], restarted.state.value.chapter)
        assertEquals(0, restarted.state.value.currentProgress.chapterIndex)
        assertEquals(1, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(2, restarted.state.value.currentProgress.characterOffset)
    }

    @Test fun newManifestIndexFailureRemovesCanonicalAndAllowsRetry() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        val original = Json.encodeToString(LibrarySnapshot())
        files.values["library.json"] = original
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.failNextWrites["library.json"] = 1
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertEquals(original, files.values["library.json"])
        assertNull(files.values[canonical()])
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.busy)
        assertTrue(draft.manifest.chapters.all { it.fileName in files.values }) // Draft revision is recoverable.
        store.dismissError()
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        assertEquals(id, store.state.value.books.single().id)
        assertNotNull(files.values[canonical()])
        assertNull(store.state.value.error)
    }

    @Test fun replacementIndexFailureRestoresPriorManifestShelfAndAnchorThenRecovers() = runTest {
        val files = ManifestFiles()
        val old = fixture()
        val replacement = fixture(revision = "2".repeat(32), title = "新版书名")
        files.install(old); files.install(replacement)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(old.manifest)); advanceUntilIdle()
        store.openBook(id); advanceUntilIdle()
        store.updateChapterProgress(1, 2, 13)
        store.closeBook()
        val oldCanonical = files.values.getValue(canonical())
        val oldIndex = files.values.getValue("library.json")
        files.failNextWrites["library.json"] = 1
        store.importManifestJson(Json.encodeToString(replacement.manifest)); advanceUntilIdle()
        assertEquals(oldCanonical, files.values[canonical()])
        assertEquals(oldIndex, files.values["library.json"])
        assertEquals(old.manifest.title, store.state.value.books.single().title)
        assertNotNull(store.state.value.error)
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(old.manifest.revision, restarted.state.value.manifest?.revision)
        assertEquals(1, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(2, restarted.state.value.currentProgress.characterOffset)
        assertEquals(13, restarted.state.value.currentProgress.scrollOffset)
        restarted.closeBook()
        restarted.importManifestJson(Json.encodeToString(replacement.manifest)); advanceUntilIdle()
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(replacement.manifest.revision, restarted.state.value.manifest?.revision)
        assertEquals(replacement.manifest.title, restarted.state.value.books.single().title)
        assertEquals(1, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(2, restarted.state.value.currentProgress.characterOffset)
        assertNull(restarted.state.value.error)
    }

    @Test fun failedAtomicCanonicalWritePreservesPreviouslyPublishedRevision() = runTest {
        val files = ManifestFiles()
        val old = fixture()
        val replacement = fixture(revision = "2".repeat(32), title = "未发布副本")
        files.install(old); files.install(replacement)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(old.manifest)); advanceUntilIdle()
        val oldCanonical = files.values.getValue(canonical())
        val oldIndex = files.values.getValue("library.json")
        files.failNextWrites[canonical()] = 1
        store.importManifestJson(Json.encodeToString(replacement.manifest)); advanceUntilIdle()
        assertEquals(oldCanonical, files.values[canonical()])
        assertEquals(oldIndex, files.values["library.json"])
        assertEquals(old.manifest.title, store.state.value.books.single().title)
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.busy)
    }
}

/** Faults occur before commit, matching ReaderFiles' atomic-replacement contract. */
private class ManifestFiles : ReaderFiles {
    val values = mutableMapOf<String, String>()
    val reads = mutableListOf<String>()
    val failNextWrites = mutableMapOf<String, Int>()
    var blockWrites: (String) -> Boolean = { false }
    override fun readText(name: String): String? {
        reads += name
        return values[name]
    }
    override fun writeText(name: String, value: String) {
        if (blockWrites(name)) error("injected persistent pre-commit failure")
        val remaining = failNextWrites[name] ?: 0
        if (remaining > 0) {
            failNextWrites[name] = remaining - 1
            error("injected pre-commit write failure")
        }
        values[name] = value
    }
    override fun delete(name: String) { values.remove(name) }
    override fun nowMillis() = 2000L
}
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ReaderStoreTest.kt': r'''@file:OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)

package dev.leaf.reader

import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlin.test.assertFailsWith

class ReaderStoreTest {
    private val sample = BookDocument(
        id = "a".repeat(64), title = "测试书", author = "作者", format = "TXT",
        chapters = listOf(BookChapter("第一章", listOf("第一段。", "第二段 😀。")), BookChapter("第二章", listOf("结束。"))),
    )
    private fun BookDocument.encoded() = Json.encodeToString(this)

    @Test fun importsAndReopensWithoutDuplicating() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded())
        advanceUntilIdle()
        assertEquals(1, store.state.value.books.size)
        store.openBook(sample.id)
        advanceUntilIdle()
        store.updateProgress(3, 42)
        advanceUntilIdle() // The legacy adapter loads a different chapter asynchronously.
        store.importBookJson(sample.encoded())
        advanceUntilIdle()
        assertEquals(1, store.state.value.books.size)
        assertProgress(store.state.value.currentProgress, item = 3, scroll = 42, chapter = 1, paragraph = 0)
    }

    @Test fun positionAndSettingsSurviveRestart() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(2, 75)
        store.updateSettings(ReaderSettings(fontSize = 25f, theme = ReaderTheme.SEPIA))
        store.flush()
        val restored = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertEquals(25f, restored.state.value.settings.fontSize)
        assertEquals(ReaderTheme.SEPIA, restored.state.value.settings.theme)
        restored.openBook(sample.id); advanceUntilIdle()
        assertProgress(restored.state.value.currentProgress, item = 2, scroll = 75, chapter = 0, paragraph = 2)
    }

    @Test fun clampsInvalidProgressToExistingItems() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(9999, -3)
        advanceUntilIdle()
        assertProgress(store.state.value.currentProgress, item = 4, scroll = 0, chapter = 1, paragraph = 1)
    }

    @Test fun closingBeforeOpenFinishesDoesNotReopen() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id)
        store.closeBook()
        advanceUntilIdle()
        assertNull(store.state.value.currentBook)
        assertFalse(store.state.value.busy)
    }

    @Test fun deletingDuringOpenDoesNotLeaveLoadingOverlay() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id)
        store.deleteBook(sample.id)
        advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertNull(store.state.value.currentBook)
        assertFalse(store.state.value.busy)
    }

    @Test fun removesShelfAndDerivedBookButNotOtherFiles() = runTest {
        val files = MemoryFiles()
        files.values["unrelated"] = "keep"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.deleteBook(sample.id); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertNull(files.values["book-${sample.id}.json"])
        assertNull(files.values["book-${sample.id}.manifest.json"])
        assertTrue(files.values.keys.none { it.startsWith("book-${sample.id}-") })
        assertEquals("keep", files.values["unrelated"])
    }

    @Test fun rejectedDocumentDoesNotReachShelf() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.copy(id = "../escape").encoded()); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertNotNull(store.state.value.error)
        assertTrue(files.values.keys.none { it.contains("escape") })
    }

    @Test fun failedIndexWriteRollsBackShelfAndPreservesOldIndex() = runTest {
        val files = MemoryFiles()
        val original = "{\"schema\":1,\"books\":[],\"settings\":{}}"
        files.values["library.json"] = original
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.failIndexWrite = true
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertEquals(original, files.values["library.json"])
        assertNotNull(store.state.value.error)
    }

    @Test fun corruptIndexIsNeverSilentlyOverwritten() = runTest {
        val files = MemoryFiles()
        files.values["library.json"] = "corrupt original"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.dismissError()
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.flush()
        assertEquals("corrupt original", files.values["library.json"])
        assertTrue(store.state.value.books.isEmpty())
        assertNotNull(store.state.value.error)
    }

    @Test fun reimportRepairsMissingDerivedFileWithoutLosingProgress() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(2, 7)
        val missingChapter = store.state.value.manifest!!.chapters[0].fileName
        store.closeBook()
        files.values.remove(missingChapter)
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        assertNotNull(store.state.value.currentBook)
        assertProgress(store.state.value.currentProgress, item = 2, scroll = 7, chapter = 0, paragraph = 2)
        assertNotNull(store.state.value.chapter)
    }

    @Test fun rapidOpeningKeepsLatestBook() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        val second = sample.copy(id = "b".repeat(64), title = "另一本")
        store.importBookJson(sample.encoded()); store.importBookJson(second.encoded()); advanceUntilIdle()
        store.openBook(sample.id)
        store.openBook(second.id)
        advanceUntilIdle()
        assertEquals(second.id, store.state.value.currentBook?.id)
    }

    @Test fun debounceSavesAndDismissErrorDoesNotLoseBook() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(1, 3)
        runCurrent(); advanceUntilIdle()
        assertTrue(files.values.getValue("library.json").contains("\"scrollOffset\":3"))
        store.reportError("测试提示"); store.dismissError()
        assertNull(store.state.value.error)
        assertEquals(sample.id, store.state.value.currentBook?.id)
    }

    @Test fun chapterAnchorsPersistAcrossAsyncNavigationAndRestart() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateChapterProgress(paragraphIndex = 2, characterOffset = 5, scrollOffset = 11)
        // UTF-16 index 5 bisects the emoji and must move back to the high surrogate.
        assertProgress(store.state.value.currentProgress, 2, 11, 0, 2, character = 4)
        store.selectChapter(1)
        assertTrue(store.state.value.chapterBusy)
        assertNull(store.state.value.chapter)
        store.updateChapterProgress(0, 0, 0) // Initial/unmeasured UI saves must be ignored.
        assertProgress(store.state.value.books.single().progress, 2, 11, 0, 2, character = 4)
        advanceUntilIdle()
        assertEquals("第二章", store.state.value.chapter?.title)
        store.updateChapterProgress(1, 2, 9)
        store.flush()
        val restored = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restored.openBook(sample.id); advanceUntilIdle()
        assertEquals(1, restored.state.value.chapterIndex)
        assertFalse(restored.state.value.chapterBusy)
        assertProgress(restored.state.value.currentProgress, 4, 9, 1, 1, character = 2)
        assertProgress(restored.state.value.books.single().progress, 4, 9, 1, 1, character = 2)
    }

    @Test fun previousChapterAtEndClampsSentinelAfterBodyLoads() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.selectChapter(1); advanceUntilIdle()
        store.selectChapter(0, atEnd = true)
        assertTrue(store.state.value.chapterBusy)
        assertEquals(Int.MAX_VALUE, store.state.value.currentProgress.characterOffset)
        advanceUntilIdle()
        assertProgress(store.state.value.currentProgress, 2, 0, 0, 2,
            character = sample.chapters[0].paragraphs.last().length)
    }

    @Test fun rapidChapterSelectionAndCloseDiscardObsoleteLoads() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.selectChapter(1)
        store.selectChapter(0)
        advanceUntilIdle()
        assertEquals("第一章", store.state.value.chapter?.title)
        assertProgress(store.state.value.currentProgress, 0, 0, 0, 0)
        store.selectChapter(1)
        store.closeBook()
        advanceUntilIdle()
        assertNull(store.state.value.currentBook)
        assertNull(store.state.value.manifest)
        assertNull(store.state.value.chapter)
        assertFalse(store.state.value.chapterBusy)
        assertFalse(store.state.value.busy)
    }

    @Test fun allReadingAndShelfOptionsSurviveRestart() = runTest {
        val files = MemoryFiles()
        val settings = ReaderSettings(
            fontSize = 27f, lineHeight = 2f, theme = ReaderTheme.DARK,
            readingMode = ReadingMode.INSTANT, columnMode = ColumnMode.DOUBLE,
            shelfLayout = ShelfLayout.COMPACT, fontFamily = ReaderFont.MONO,
            horizontalMargin = 32f, paragraphSpacing = 18f, letterSpacing = 1.5f,
            firstLineIndent = false, bold = true, autoHideControls = false, showReadingFooter = false,
        )
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.updateSettings(settings)
        advanceUntilIdle()
        val restored = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertEquals(settings, restored.state.value.settings)
    }

    private fun assertProgress(
        actual: ReadingProgress, item: Int, scroll: Int, chapter: Int, paragraph: Int, character: Int = 0,
    ) {
        assertEquals(item, actual.itemIndex, "global item")
        assertEquals(scroll, actual.scrollOffset, "pixel offset")
        assertEquals(chapter, actual.chapterIndex, "chapter anchor")
        assertEquals(paragraph, actual.paragraphIndex, "chapter-local heading/paragraph")
        assertEquals(character, actual.characterOffset, "UTF-16 text anchor")
    }

    @Test fun settingsAndDocumentLimitsAreEnforced() {
        assertEquals(40f, ReaderSettings(fontSize = 100f).sanitized().fontSize)
        assertEquals(20f, ReaderSettings(fontSize = Float.NaN).sanitized().fontSize)
        assertFailsWith<IllegalArgumentException> { sample.copy(chapters = emptyList()).validate() }
        assertFailsWith<IllegalArgumentException> { sample.copy(format = "PDF").validate() }
        assertFailsWith<IllegalArgumentException> { sample.copy(chapters = listOf(BookChapter("", listOf(" ")))).validate() }
        assertFailsWith<IllegalArgumentException> { sample.copy(chapters = listOf(BookChapter("", listOf("x".repeat(16001))))).validate() }
        sample.validate()
    }
}

private class MemoryFiles : ReaderFiles {
    val values = mutableMapOf<String, String>()
    var failIndexWrite = false
    override fun readText(name: String) = values[name]
    override fun writeText(name: String, value: String) {
        if (failIndexWrite && name == "library.json") error("disk full")
        values[name] = value
    }
    override fun delete(name: String) { values.remove(name) }
    override fun nowMillis() = 1000L
}
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ContentsNavigationTest.kt': r'''package dev.leaf.reader.ui

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class ContentsNavigationTest {
    @Test fun searchKeepsRealChapterIndicesAndIgnoresCase() {
        val titles = listOf("Alpha", "第二章", "ALPHA 续", "尾声")
        assertEquals(listOf(0, 2), contentsChapterIndices(titles, "  alpha  ", false))
        assertEquals(listOf(2, 0), contentsChapterIndices(titles, "alpha", true))
        assertEquals(listOf(1), contentsChapterIndices(titles, "第二", false))
    }

    @Test fun duplicatesAndBlankHeadingsAreNotMerged() {
        val titles = listOf("重复", "", "重复")
        assertEquals(listOf(0, 1, 2), contentsChapterIndices(titles, "", false))
        assertEquals(listOf(0, 2), contentsChapterIndices(titles, "重复", false))
        assertEquals(listOf(1), contentsChapterIndices(titles, "第 2 章", false))
    }

    @Test fun numericSearchUsesOneBasedChapterNumber() {
        val titles = listOf("序", "正文", "终")
        assertEquals(listOf(1), contentsChapterIndices(titles, "2", false))
        assertTrue(contentsChapterIndices(titles, "0", false).isEmpty())
        assertTrue(contentsChapterIndices(titles, "999999999999999999", false).isEmpty())
    }

    @Test fun locateUsesPositionInFilteredReversedListNotChapterNumber() {
        val titles = listOf("选中一", "其他", "选中二", "选中三")
        val matches = contentsChapterIndices(titles, "选中", true)
        assertEquals(listOf(3, 2, 0), matches)
        assertEquals(1, contentsChapterPosition(matches, 2))
        assertNull(contentsChapterPosition(matches, 1))
        assertNull(contentsChapterPosition(emptyList(), 0))
    }

    @Test fun fiftyThousandChapterMetadataRetainsLastChapter() {
        val titles = List(50_000) { "Chapter ${it + 1}" }
        val reversed = contentsChapterIndices(titles, "", true)
        assertEquals(50_000, reversed.size)
        assertEquals(49_999, reversed.first())
        assertEquals(0, contentsChapterPosition(reversed, 49_999))
        assertEquals(49_999, contentsChapterPosition(reversed, 0))
        assertEquals(listOf(49_999), contentsChapterIndices(titles, "50000", false))
    }

    @Test fun clearSearchRestoresCurrentChapterPositionForEitherOrder() {
        val titles = List(800) { "章节 $it" }
        assertEquals(405, contentsChapterPosition(contentsChapterIndices(titles, "", false), 405))
        assertEquals(394, contentsChapterPosition(contentsChapterIndices(titles, "", true), 405))
    }

    @Test fun shortWindowsKeyboardAndLargeFontsUseCompactContents() {
        assertTrue(compactContentsLayout(360f, 1f))
        assertTrue(compactContentsLayout(480f, 1f))
        assertTrue(compactContentsLayout(640f, 1.5f))
        assertFalse(compactContentsLayout(800f, 1f))
        assertFalse(compactContentsLayout(884f, 1.5f))
    }
}
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderChromeTest.kt': r'''package dev.leaf.reader.ui

import kotlin.test.Test
import kotlin.test.assertEquals

class ReaderChromeTest {
    @Test fun centralTapTogglesChromeInEveryReadingMode() {
        for (paged in listOf(false, true)) {
            for (fraction in listOf(0.32f, 0.5f, 0.68f)) {
                assertEquals(ReaderTapAction.TOGGLE_CHROME, readerTapAction(fraction, paged))
            }
        }
    }

    @Test fun pageTurnZonesDoNotToggleChrome() {
        assertEquals(ReaderTapAction.PREVIOUS_PAGE, readerTapAction(0f, true))
        assertEquals(ReaderTapAction.PREVIOUS_PAGE, readerTapAction(0.31f, true))
        assertEquals(ReaderTapAction.NEXT_PAGE, readerTapAction(0.69f, true))
        assertEquals(ReaderTapAction.NEXT_PAGE, readerTapAction(1f, true))
    }

    @Test fun scrollSideTapsHaveNoPageTurnOrChromeSideEffect() {
        assertEquals(ReaderTapAction.NONE, readerTapAction(0.2f, false))
        assertEquals(ReaderTapAction.NONE, readerTapAction(0.8f, false))
    }

    @Test fun invalidPointerCoordinatesProduceNoAction() {
        for (fraction in listOf(Float.NaN, Float.POSITIVE_INFINITY, -0.1f, 1.1f)) {
            assertEquals(ReaderTapAction.NONE, readerTapAction(fraction, true))
        }
    }
}
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderOverlayRegressionTest.kt': r'''package dev.leaf.reader.ui

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** Logic checks; actual popup rendering/touch delivery remains a device/UI-test responsibility. */
class ReaderOverlayRegressionTest {
    @Test fun settingsAlwaysReplacesThePreviousPanel() {
        ReaderPanel.entries.forEach { previous ->
            assertEquals(ReaderPanel.SETTINGS, reduceReaderPanel(previous, ReaderPanelAction.OPEN_SETTINGS))
        }
    }

    @Test fun directoryAlwaysReplacesSettingsWithoutLeavingBothOpen() {
        ReaderPanel.entries.forEach { previous ->
            assertEquals(ReaderPanel.CONTENTS, reduceReaderPanel(previous, ReaderPanelAction.OPEN_CONTENTS))
        }
    }

    @Test fun dismissClosesOnlyItsOwnPanel() {
        assertEquals(ReaderPanel.NONE, reduceReaderPanel(ReaderPanel.SETTINGS, ReaderPanelAction.CLOSE_SETTINGS))
        assertEquals(ReaderPanel.NONE, reduceReaderPanel(ReaderPanel.CONTENTS, ReaderPanelAction.CLOSE_CONTENTS))
        assertEquals(ReaderPanel.CONTENTS, reduceReaderPanel(ReaderPanel.CONTENTS, ReaderPanelAction.CLOSE_SETTINGS))
        assertEquals(ReaderPanel.SETTINGS, reduceReaderPanel(ReaderPanel.SETTINGS, ReaderPanelAction.CLOSE_CONTENTS))
    }

    @Test fun delayedOldDismissCannotUndoASecondSettingsOpen() {
        var panel = reduceReaderPanel(ReaderPanel.NONE, ReaderPanelAction.OPEN_CONTENTS)
        panel = reduceReaderPanel(panel, ReaderPanelAction.OPEN_SETTINGS)
        panel = reduceReaderPanel(panel, ReaderPanelAction.CLOSE_CONTENTS)
        assertEquals(ReaderPanel.SETTINGS, panel)
        panel = reduceReaderPanel(panel, ReaderPanelAction.CLOSE_SETTINGS)
        panel = reduceReaderPanel(panel, ReaderPanelAction.OPEN_SETTINGS)
        assertEquals(ReaderPanel.SETTINGS, panel)
    }

    @Test fun floatingCircleMatchesShelfButKeepsTheTouchTarget() {
        assertEquals(CircleControlSize.value, ReaderControlVisualDp)
        assertEquals(40f, ReaderControlVisualDp)
        assertTrue(ReaderControlTouchDp >= 44f)
        assertTrue(ReaderControlTouchDp > ReaderControlVisualDp)
    }

    @Test fun dockIsAboutThreeQuartersOfTheOldMinimumWithoutShrinkingTouchTargets() {
        val previousMinimum = 48f + 2 * 10f
        assertEquals(52f, ReaderDockMinimumHeightDp)
        assertTrue(ReaderDockMinimumHeightDp / previousMinimum in 0.70f..0.80f)
        assertTrue(ReaderDockMinimumHeightDp >= ReaderControlTouchDp)
    }

    @Test fun largeFontsAndNarrowSettingsMoveControlsToAnotherLine() {
        assertTrue(stackedReaderSetting(1.5f, 320f))
        assertTrue(stackedReaderSetting(1f, 220f))
        assertEquals(false, stackedReaderSetting(1f, 280f))
        assertEquals(false, stackedReaderSetting(1f, 560f))
    }

    @Test fun denserContentsKeepsAccessibleMinimumInsteadOfTheOldSixtyDp() {
        assertTrue(ContentsRowMinimumHeightDp >= 44f)
        assertTrue(ContentsRowMinimumHeightDp < 60f)
        assertTrue(ContentsRowMinimumHeightDp >= 60f * 2f / 3f)
    }
}
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderPaginationTest.kt': r'''package dev.leaf.reader.ui

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class ReaderPaginationTest {
    /** Fake monospace measurement: width is code points per line; height is always ten. */
    private fun measure(index: Int, text: String, width: Int): List<MeasuredLine> {
        if (text.isEmpty()) return listOf(MeasuredLine(0, 0, 0f, 10f))
        val lines = mutableListOf<MeasuredLine>()
        var offset = 0
        while (offset < text.length) {
            val start = offset
            var count = 0
            while (offset < text.length && count < width) {
                offset += if (text[offset].isHighSurrogate() && offset + 1 < text.length &&
                    text[offset + 1].isLowSurrogate()) 2 else 1
                count++
                if (text[offset - 1] == '\n') break
            }
            lines += MeasuredLine(start, offset, lines.size * 10f, (lines.size + 1) * 10f)
        }
        return lines
    }

    @Test fun everyCharacterAppearsExactlyOnceAcrossColumnsAndPages() {
        val texts = listOf("Heading", "中文 mixed 😀 text\nnext line", "", "尾段".repeat(53))
        val pages = paginateChapter(texts, 5, 32f, 2, 4f, ::measure)
        assertTrue(pages.size > 1)
        texts.forEachIndexed { index, expected ->
            val slices = pages.flatMap { it.columns.flatten() }.filter { it.paragraphIndex == index }
            assertEquals(expected, slices.joinToString("") { expected.substring(it.start, it.end) })
            assertEquals(0, slices.first().start)
            assertEquals(expected.length, slices.last().end)
            slices.zipWithNext().forEach { (a, b) -> assertEquals(a.end, b.start) }
        }
    }

    @Test fun surrogateBoundariesAndAnchorClamping() {
        val text = "a😀b𠀀c"
        assertEquals(1, safeTextOffset(text, 2))
        assertEquals(4, safeTextOffset(text, 5))
        assertEquals(TextAnchor(1, 1), clampAnchor(listOf("Title", text), TextAnchor(1, 2)))
        assertEquals(TextAnchor(1, text.length), clampAnchor(listOf("Title", text), TextAnchor(Int.MAX_VALUE, Int.MAX_VALUE)))
        val pages = paginateChapter(listOf(text), 1, 10f, 1, 0f, ::measure)
        pages.flatMap { it.columns.flatten() }.forEach {
            assertEquals(it.start, safeTextOffset(text, it.start))
            assertEquals(it.end, safeTextOffset(text, it.end))
        }
    }

    @Test fun pageStartAnchorsRoundTrip() {
        val texts = listOf("Heading", "abc😀def".repeat(90), "last")
        for (columns in 1..2) {
            val pages = paginateChapter(texts, 7, 30f, columns, 2f, ::measure)
            pages.forEachIndexed { index, page -> assertEquals(index, pageForAnchor(pages, page.anchor)) }
        }
    }

    @Test fun textAnchorSurvivesReflow() {
        val texts = listOf("Heading", "中文😀abcdef".repeat(50))
        val narrow = paginateChapter(texts, 4, 30f, 1, 6f, ::measure)
        val wide = paginateChapter(texts, 11, 60f, 2, 12f, ::measure)
        val anchor = narrow[narrow.size / 2].anchor
        val page = wide[pageForAnchor(wide, anchor)]
        assertTrue(page.columns.flatten().any { it.paragraphIndex == anchor.paragraphIndex &&
            anchor.characterOffset in it.start until it.end })
    }

    @Test fun exactBoundaryBelongsToNextPageAndEndBelongsToLast() {
        val pages = paginateChapter(listOf("abcdef"), 2, 10f, 1, 0f, ::measure)
        assertEquals(1, pageForAnchor(pages, TextAnchor(0, 2)))
        assertEquals(2, pageForAnchor(pages, TextAnchor(0, 6)))
    }

    @Test fun oversizedLineAlwaysAdvancesAndEmptyParagraphsRemain() {
        val pages = paginateChapter(listOf("", "😀", ""), 1, 1f, 1, 0f, ::measure)
        assertEquals(3, pages.size)
        assertEquals(listOf(0, 1, 2), pages.map { it.anchor.paragraphIndex })
        assertEquals(listOf(MeasuredPage(listOf(emptyList()))),
            paginateChapter(emptyList(), 10, 10f, 1, 0f, ::measure))
    }

    @Test fun scrollLineCoordinatesRoundTrip() {
        val pages = paginateChapter(listOf("abcdefghi"), 3, 50f, 1, 0f, ::measure)
        assertEquals(TextAnchor(0, 3), anchorAtY(pages.single(), 12f))
        assertEquals(10f, yForAnchor(pages.single(), TextAnchor(0, 3)))
    }
}
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReadingItemsTest.kt': r'''package dev.leaf.reader.ui

import dev.leaf.reader.BookChapter
import dev.leaf.reader.BookDocument
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** Replaces legacy whole-book flattening tests with the chapter-local coordinate contract. */
class ReadingItemsTest {
    @Test fun headingAndParagraphsKeepExactLocalOrder() {
        val texts = chapterReadingTexts(BookChapter("第一章", listOf("甲", "乙")), 0)
        assertEquals(listOf("第一章", "甲", "乙"), texts)
        assertEquals("甲", texts[TextAnchor(paragraphIndex = 1).paragraphIndex])
    }

    @Test fun titleOnlyMetadataNeverSuppliesBodyText() {
        val metadata = BookDocument(id = "a".repeat(64), title = "测试书籍", chapters =
            listOf(BookChapter("第一章", emptyList()), BookChapter("第二章", emptyList())))
        val loaded = BookChapter("第二章", listOf("当前章正文"))
        val texts = chapterReadingTexts(loaded, 1)
        assertEquals(listOf("第二章", "当前章正文"), texts)
        assertTrue(metadata.chapters.all { it.paragraphs.isEmpty() })
        assertEquals(TextAnchor(1, 2), clampAnchor(texts, TextAnchor(1, 2)))
    }

    @Test fun emptyChapterStillOccupiesOneHeadingIndex() {
        assertEquals(listOf("序"), chapterReadingTexts(BookChapter("序", emptyList()), 0))
    }

    @Test fun blankTitlesGetReadableFallbackWithoutAddingItems() {
        val texts = chapterReadingTexts(BookChapter("  ", listOf("原文")), 7)
        assertEquals(listOf("第 8 章", "原文"), texts)
    }

    @Test fun blankAndDuplicateParagraphsAreNotDroppedOrMerged() {
        assertEquals(listOf("章", "", "重复", "重复"),
            chapterReadingTexts(BookChapter("章", listOf("", "重复", "重复")), 0))
    }

    @Test fun localAnchorStillAddressesSameTextAfterRecreatingChapter() {
        val chapter = BookChapter("第二章", listOf("甲乙", "丙丁😀"))
        val anchor = TextAnchor(paragraphIndex = 2, characterOffset = 2)
        val before = chapterReadingTexts(chapter, 1)
        val after = chapterReadingTexts(chapter.copy(paragraphs = chapter.paragraphs.toList()), 1)
        assertEquals(before[anchor.paragraphIndex].substring(anchor.characterOffset),
            after[anchor.paragraphIndex].substring(anchor.characterOffset))
        assertEquals("😀", after[anchor.paragraphIndex].substring(anchor.characterOffset))
    }

    @Test fun endOfChapterRequestClampsAfterBodyLoad() {
        val texts = chapterReadingTexts(BookChapter("章", listOf("尾😀")), 0)
        assertEquals(TextAnchor(1, 3), clampAnchor(texts, TextAnchor(Int.MAX_VALUE, Int.MAX_VALUE)))
    }
}
''',
    'shared/src/desktopTest/kotlin/dev/leaf/reader/ui/ReaderHostStructureTest.kt': r'''package dev.leaf.reader.ui

import java.io.File
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * No DISPLAY/Skiko window required. These are source-structure guards, NOT simulated UI clicks.
 * They protect the real v0.4 regression: OverlayBottomSheet registered a dialog but no ancestor
 * Miuix Scaffold/MiuixPopupHost ever rendered that registration in the reading branch.
 */
class ReaderHostStructureTest {
    private fun source(name: String): String {
        val relative = "src/commonMain/kotlin/dev/leaf/reader/ui/$name"
        val module = File(System.getProperty("user.dir"))
        val candidates = listOf(File(module, relative), File(module, "shared/$relative"),
            File(module.parentFile, "shared/$relative"))
        val file = candidates.firstOrNull { it.isFile }
            ?: error("Run this source-structure test from the repository root or shared module: $name")
        return file.readText()
    }

    @Test fun readerSettingsIsComposedInsideItsOwnZeroInsetScaffold() {
        val screen = source("ReadingScreen.kt")
        val host = screen.indexOf("Scaffold(modifier = Modifier.fillMaxSize()")
        val settings = screen.indexOf("ReadingSettings(settingsOpen")
        assertTrue(host >= 0 && settings > host, "Reader settings requires an ancestor Miuix Scaffold popup host")
        assertTrue(screen.contains("contentWindowInsets = WindowInsets(0, 0, 0, 0)"),
            "The local popup host must not add a second safe area to measured chapter content")
    }

    @Test fun sheetAndRealDropdownUseTheReadersLocalHost() {
        val settings = source("ReadingSettings.kt")
        assertTrue(settings.contains("OverlayBottomSheet("))
        assertTrue(settings.contains("OverlayListPopup("))
        assertTrue(settings.contains("ListPopupColumn {"))
        assertTrue(settings.contains("DropdownImpl("))
        assertTrue(Regex("renderInRootScaffold\\s*=\\s*false").findAll(settings).count() >= 2,
            "Both sheet and option list must render through the local reader host")
        assertFalse(settings.contains("TabRowWithContour("), "Preferences now use an actual Miuix popup list")
    }

    @Test fun blurCaptureIncludesPaperAndExcludesTheChrome() {
        val screen = source("ReadingScreen.kt")
        assertTrue(screen.contains("rememberLayerBackdrop { drawRect(paper); drawContent() }"))
        val capture = screen.indexOf(".layerBackdrop(backdrop)")
        val header = screen.indexOf("ReaderChrome(visible = state.chromeVisible")
        assertTrue(capture >= 0 && header > capture)
        assertTrue(screen.contains("SideEffect { chromeProgress = progressText }"),
            "Chrome must be emitted outside the chapter safe-area metrics container")
    }

    @Test fun chromeHasNoTopContentsShortcutOrFixedDockHeight() {
        val chrome = source("ReaderChrome.kt")
        assertFalse(chrome.contains("ReaderIconButton(Glyph.TOC"))
        assertTrue(chrome.contains("ReaderDockAction(Glyph.BOOK, \"目录\", onDirectory)"))
        assertTrue(chrome.contains("ReaderDockAction(Glyph.TUNE, \"设置\", onSettings)"))
        assertTrue(chrome.contains("backdrop = backdrop"))
        assertFalse(chrome.contains(".height(ReaderDockMinimumHeightDp.dp)"),
            "Large Dynamic Type must be allowed to grow the dock rather than be clipped")
    }
}
''',
    'shared/src/iosMain/kotlin/dev/leaf/reader/MainViewController.kt': r'''package dev.leaf.reader

import androidx.compose.ui.window.ComposeUIViewController
import dev.leaf.reader.ui.ReaderApp
import platform.UIKit.UIViewController

fun MainViewController(onImportRequested: () -> Unit): UIViewController = ComposeUIViewController {
    ReaderApp(store = ReaderRuntime.store, onImportRequested = onImportRequested)
}
''',
    'shared/src/iosMain/kotlin/dev/leaf/reader/ReaderFiles.ios.kt': r'''@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package dev.leaf.reader

import kotlinx.cinterop.addressOf
import kotlinx.cinterop.usePinned
import platform.Foundation.NSApplicationSupportDirectory
import platform.Foundation.NSFileManager
import platform.Foundation.NSSearchPathForDirectoriesInDomains
import platform.Foundation.NSString
import platform.Foundation.NSUserDomainMask
import platform.Foundation.NSUTF8StringEncoding
import platform.Foundation.create
import platform.posix.fclose
import platform.posix.fflush
import platform.posix.fileno
import platform.posix.fopen
import platform.posix.fsync
import platform.posix.fwrite
import platform.posix.remove
import platform.posix.rename
import kotlin.time.Clock

actual fun defaultReaderFiles(): ReaderFiles = IosReaderFiles()

private class IosReaderFiles : ReaderFiles {
    private val manager = NSFileManager.defaultManager
    private val root: String = (NSSearchPathForDirectoriesInDomains(
        NSApplicationSupportDirectory, NSUserDomainMask, true,
    ).first() as String) + "/LeafReader"

    init { check(manager.createDirectoryAtPath(root, true, null, null)) { "建立本地书库目录失败。" } }

    private fun path(name: String): String {
        require(Regex("[a-zA-Z0-9_.-]+").matches(name))
        return "$root/$name"
    }

    override fun readText(name: String): String? {
        val file = path(name)
        if (!manager.fileExistsAtPath(file)) return null
        return (NSString.create(contentsOfFile = file, encoding = NSUTF8StringEncoding, error = null) as String?)
            ?: error("读取本地书库文件失败。")
    }

    /** Preserve the working POSIX bridge, but write a sibling then atomically rename over the old file. */
    override fun writeText(name: String, value: String) {
        val file = path(name)
        val temporary = "$file.tmp"
        val bytes = value.encodeToByteArray()
        val stream = fopen(temporary, "wb") ?: error("建立临时书库文件失败。")
        var closed = false
        var published = false
        try {
            if (bytes.isNotEmpty()) {
                val written = bytes.usePinned { pinned -> fwrite(pinned.addressOf(0), 1uL, bytes.size.toULong(), stream) }
                check(written.toLong() == bytes.size.toLong()) { "写入本地书库失败。" }
            }
            check(fflush(stream) == 0 && fsync(fileno(stream)) == 0) { "同步本地书库失败。" }
            val closeResult = fclose(stream)
            closed = true
            check(closeResult == 0) { "关闭书库文件失败。" }
            check(rename(temporary, file) == 0) { "提交书库文件失败，旧文件已保留。" }
            published = true
        } finally {
            if (!closed) fclose(stream)
            if (!published) remove(temporary)
        }
    }

    override fun delete(name: String) {
        val file = path(name)
        if (manager.fileExistsAtPath(file)) check(manager.removeItemAtPath(file, null)) { "清理书籍文件失败。" }
    }
    override fun nowMillis(): Long = Clock.System.now().toEpochMilliseconds()
}
''',
    'tools/make_upgrade.py': '#!/usr/bin/env python3\n"""Pack current LeafReader sources into one offline, inspectable Python installer.\n\nRun only after the release freeze:\n  python3 tools/make_upgrade.py 0.5 OUTPUT.py\n\nEvery payload is UTF-8 round-tripped exactly, including its final-newline state.\nAll v0.3 payloads remain required. New UI/tests are discovered AND checked against\nexplicit requirements; missing files abort rather than producing a partial pack.\nThis program only creates the requested installer, never applies it or builds.\n"""\nimport argparse\nimport ast\nimport hashlib\nimport json\nimport os\nfrom pathlib import Path\nimport re\nimport sys\nimport tempfile\n\nROOT = Path(__file__).resolve().parents[1]\nRUNNER = ROOT / \'tools\' / \'upgrade_runner.py\'\n\n# Historical v0.3 payloads: intentionally retained for v0.1/v0.2/v0.3 upgrades.\nFILES = [\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/Models.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ReaderStore.kt\',\n    \'shared/src/iosMain/kotlin/dev/leaf/reader/ReaderFiles.ios.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderApp.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/MiuixAtoms.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/MiuixGlyphs.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ShelfScreen.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ShelfWidgets.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReadingScreen.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReadingSettings.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/TocSheet.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/Pagination.kt\',\n    \'shared/src/commonTest/kotlin/dev/leaf/reader/ReaderStoreTest.kt\',\n    \'shared/src/commonTest/kotlin/dev/leaf/reader/ManifestStorageTest.kt\',\n    \'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReadingItemsTest.kt\',\n    \'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderPaginationTest.kt\',\n    \'iosApp/Sources/Parser/BookParser.swift\',\n    \'iosApp/Sources/Parser/EPUBParser.swift\',\n    \'iosApp/Sources/Parser/ZIPPreflight.swift\',\n    \'iosApp/Sources/Parser/StreamingImport.swift\',\n    \'iosApp/Sources/Parser/STREAMING_IMPORT.md\',\n    \'iosApp/Sources/Host/DocumentPicker.swift\',\n    \'iosApp/Tests/StreamingImportTests.swift\',\n    \'iosApp/README.md\',\n    \'scripts/build-ios.sh\',\n    \'README.md\',\n    \'VALIDATION.md\',\n    \'UPGRADE-v0.2.md\',\n    \'UPGRADE-v0.3.md\',\n    \'validation-summary.json\',\n    \'.github/workflows/upgrade-v02.yml\',\n    \'.github/workflows/upgrade-v03.yml\',\n]\nREQUIRED_V04_FILES = [\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderChrome.kt\',\n    \'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ContentsScreen.kt\',\n    \'UPGRADE-v0.4.md\',\n    \'.github/workflows/upgrade-v04.yml\',\n    \'scripts/tests/test_upgrade_v04.py\',\n    \'tools/make_upgrade.py\',\n    \'tools/upgrade_runner.py\',\n]\nREQUIRED_V05_FILES = [\n    \'UPGRADE-v0.5.md\',\n    \'.github/workflows/upgrade-v05.yml\',\n    \'scripts/tests/test_upgrade_v05.py\',\n]\n# Release-approved critical regression files; absence is a packaging error.\n# Dynamic discovery supplements, never replaces, these hard checks.\nREQUIRED_V05_SOURCE_FILES = [\n    \'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderOverlayRegressionTest.kt\',\n    \'shared/src/desktopTest/kotlin/dev/leaf/reader/ui/ReaderHostStructureTest.kt\',\n]\nMATERIAL_DEPENDENCIES_V04 = (\'top.yukonga.miuix.kmp:miuix-blur:0.9.4\',)\n# No new material coordinate is chosen without Lead confirmation.\nMATERIAL_DEPENDENCIES_V05 = MATERIAL_DEPENDENCIES_V04\nREQUIRED_DIRECTORY_TESTS = [\n    \'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ContentsNavigationTest.kt\',\n    \'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderChromeTest.kt\',\n]\nDISCOVER_TREES = (\n    \'shared/src/commonMain/kotlin/dev/leaf/reader\',\n    \'shared/src/commonTest/kotlin/dev/leaf/reader\',\n    \'shared/src/iosMain/kotlin/dev/leaf/reader\',\n    \'iosApp/Sources\',\n    \'iosApp/Tests\',\n)\n# desktopTest was absent in older source releases; v0.5\'s explicit mandatory\n# ReaderHostStructureTest above guarantees this tree exists for current packing.\nOPTIONAL_DISCOVER_TREES = (\'shared/src/desktopTest/kotlin/dev/leaf/reader\',)\nDISCOVER_SUFFIXES = (\'.kt\', \'.swift\', \'.md\')\nPATCH_ONLY = {\'shared/build.gradle.kts\', \'iosApp/project.yml\'}\n\n\ndef literal(text):\n    """Prefer readable raw triple strings; validate the syntax, not just collision.\n\n    repr is a plain Python string fallback when both delimiters collide or a\n    terminal quote/backslash would make a raw literal ambiguous. No encoding or\n    compression payload hides source text.\n    """\n    for quote in ("\'\'\'", \'"""\'):\n        if quote in text:\n            continue\n        candidate = \'r%s%s%s\' % (quote, text, quote)\n        try:\n            if ast.literal_eval(candidate) == text:\n                return candidate\n        except (SyntaxError, ValueError):\n            pass\n    candidate = repr(text)\n    if ast.literal_eval(candidate) != text:\n        raise ValueError(\'Python source literal failed round-trip\')\n    return candidate\n\n\ndef release_profile(version):\n    if version in (\'0.4\', \'0.4.0\'):\n        return [], MATERIAL_DEPENDENCIES_V04\n    if version in (\'0.5\', \'0.5.0\'):\n        return REQUIRED_V05_FILES + REQUIRED_V05_SOURCE_FILES, MATERIAL_DEPENDENCIES_V05\n    raise ValueError(\'Supported installer versions: 0.4 and 0.5\')\n\n\ndef discover_source_files(root, version=\'0.5\'):\n    release_files, _ = release_profile(version)\n    names = set(FILES + REQUIRED_V04_FILES + REQUIRED_DIRECTORY_TESTS + release_files)\n    for tree in DISCOVER_TREES + OPTIONAL_DISCOVER_TREES:\n        directory = root / tree\n        if tree in OPTIONAL_DISCOVER_TREES and not directory.exists() and not directory.is_symlink():\n            continue\n        if directory.is_symlink() or not directory.is_dir():\n            raise ValueError(\'Missing/linked source tree: %s\' % tree)\n        for current, directories, files in os.walk(str(directory), followlinks=False):\n            current = Path(current)\n            for name in directories:\n                if (current / name).is_symlink():\n                    raise ValueError(\'Linked source directory: %s\' % (current / name))\n            directories.sort()\n            for name in sorted(files):\n                if name.endswith(DISCOVER_SUFFIXES):\n                    path = current / name\n                    if path.is_symlink():\n                        raise ValueError(\'Linked source file: %s\' % path)\n                    names.add(path.relative_to(root).as_posix())\n    missing = [name for name in sorted(names) if not (root / name).is_file()]\n    if missing:\n        raise ValueError(\'Missing required sources (no partial installer emitted): %s\' % \', \'.join(missing))\n    directory_tests = [name for name in names if \'/commonTest/\' in name and\n                       re.search(r\'(Contents|Toc|Directory).*Test\\.kt$\', Path(name).name, re.IGNORECASE)]\n    if not directory_tests:\n        raise ValueError(\'Missing v0.4 contents/directory regression test; confirm its exact filename before packing\')\n    if names & PATCH_ONLY:\n        raise ValueError(\'Build configuration must be patched, not embedded whole\')\n    for name in names:\n        path = root / name\n        for ancestor in (path, *path.parents):\n            if ancestor.is_symlink():\n                raise ValueError(\'Linked payload path: %s\' % name)\n            if ancestor == root:\n                break\n    return sorted(names)\n\n\ndef assemble_installer(root, version=\'0.5\', build_number=None):\n    if not re.fullmatch(r\'[0-9]+\\.[0-9]+(?:\\.[0-9]+)?\', version):\n        raise ValueError(\'Use a numeric version, for example 0.5 or 0.5.0\')\n    marketing = version if version.count(\'.\') == 2 else version + \'.0\'\n    build_number = str(build_number) if build_number is not None else str(int(version.split(\'.\')[1]))\n    if not re.fullmatch(r\'[1-9][0-9]*\', build_number):\n        raise ValueError(\'Build number must be a positive integer\')\n    _, material_dependencies = release_profile(version)\n    names = discover_source_files(root, version)\n    runner_path = root / \'tools\' / \'upgrade_runner.py\'\n    runner = runner_path.read_bytes().decode(\'utf-8\')\n    ast.parse(runner, filename=str(runner_path))\n    payloads = {}\n    hashes = {}\n    parts = []\n    for name in names:\n        raw = (root / name).read_bytes()\n        text = raw.decode(\'utf-8\')\n        if text.encode(\'utf-8\') != raw:\n            raise ValueError(\'UTF-8 round-trip failure: %s\' % name)\n        payloads[name] = raw\n        hashes[name] = hashlib.sha256(raw).hexdigest()\n        parts.append(\'    %r: %s,\\n\' % (name, literal(text)))\n    header = \'\'\'#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n"""LeafReader v%s offline source upgrade (Python 3.8+, standard library only).\n\nUsage: python3 LeafReader-v%s-upgrade.py --project PATH [--archive PATH]\nPlain FILES payloads are reviewable. No network, installs, subprocess or Git.\nEmbeds %d complete source files; preserves the user\'s Gradle configuration and\nBundle ID by patching only approved material dependencies and Xcode version scalars.\nAll target, Python AST, plist, anchor and payload checks precede source writes.\nBackups, change manifest and payload SHA map live in .leaf-upgrade-backup/.\nKotlin/Swift compilation and tests remain CI/device verification tasks.\n"""\nINSTALLER_VERSION = %r\nVERSION_PATCHES = %r\nREQUIRED_MATERIAL_DEPENDENCIES = %r\nFILES = {\n\'\'\' % (version, version, len(names), version, {\n        \'MARKETING_VERSION\': marketing, \'CURRENT_PROJECT_VERSION\': build_number,\n    }, tuple(material_dependencies))\n    source = header + \'\'.join(parts) + \'}\\nEXPECTED_PAYLOAD_SHA256 = \' + json.dumps(hashes, indent=4, sort_keys=True) + \'\\n\\n\' + runner\n    tree = ast.parse(source, filename=\'LeafReader-upgrade.py\')\n    assignments = [node for node in tree.body if isinstance(node, ast.Assign) and\n                   any(isinstance(target, ast.Name) and target.id == \'FILES\' for target in node.targets) and\n                   isinstance(node.value, ast.Dict)]\n    if len(assignments) != 1:\n        raise ValueError(\'Expected exactly one literal FILES dictionary\')\n    recovered = ast.literal_eval(assignments[0].value)\n    if set(recovered) != set(payloads):\n        raise ValueError(\'Payload filename round-trip failure\')\n    for name in names:\n        if recovered[name].encode(\'utf-8\') != payloads[name]:\n            raise ValueError(\'Payload byte round-trip failure: %s\' % name)\n    return source, hashes\n\n\ndef main(argv=None):\n    parser = argparse.ArgumentParser(description=__doc__)\n    parser.add_argument(\'version\', nargs=\'?\', default=\'0.5\')\n    parser.add_argument(\'output\', nargs=\'?\')\n    parser.add_argument(\'--build-number\', type=int)\n    args = parser.parse_args(argv)\n    output = Path(args.output) if args.output else Path(\'/sdcard/Download/DSH-Go/LeafReader-v%s-upgrade.py\' % args.version)\n    source, hashes = assemble_installer(ROOT, args.version, args.build_number)\n    output = output.expanduser().absolute()\n    for path in (output, *output.parents):\n        if path.is_symlink():\n            raise ValueError(\'Linked output path: %s\' % path)\n    try:\n        output.relative_to(ROOT)\n    except ValueError:\n        pass\n    else:\n        if output.relative_to(ROOT).as_posix() in set(hashes) | PATCH_ONLY:\n            raise ValueError(\'Installer output collides with a source file\')\n    output.parent.mkdir(parents=True, exist_ok=True)\n    handle, temporary = tempfile.mkstemp(dir=str(output.parent), prefix=\'.leaf-pack-\', suffix=\'.tmp\')\n    try:\n        with os.fdopen(handle, \'wb\') as stream:\n            stream.write(source.encode(\'utf-8\'))\n            stream.flush()\n            os.fsync(stream.fileno())\n        os.replace(temporary, output)\n    finally:\n        if os.path.exists(temporary):\n            os.unlink(temporary)\n    print(\'Wrote %s (%d files, %d bytes, sha256=%s)\' % (\n        output, len(hashes), output.stat().st_size,\n        hashlib.sha256(output.read_bytes()).hexdigest()))\n    print(\'Payload SHA256: \' + json.dumps(hashes, sort_keys=True))\n    return 0\n\n\nif __name__ == \'__main__\':\n    try:\n        main()\n    except (OSError, ValueError, SyntaxError) as error:\n        raise SystemExit(\'Packing stopped: %s\' % error)\n',
    'tools/upgrade_runner.py': r'''#!/usr/bin/env python3
"""Offline LeafReader installer runtime; importable for temporary-project tests.

The packer prepends a literal FILES dictionary and its expected SHA256 map.
Preflight reads/validates EVERY replacement and patch before creating backups or
writing sources. Atomicity is per file; caught apply failures trigger a best-
effort rollback. No network, subprocess, credentials or Git operations are used.
"""
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import stat
import tempfile
import uuid
import zipfile

INSTALLER_VERSION = globals().get('INSTALLER_VERSION', '0.4')
VERSION_PATCHES = globals().get('VERSION_PATCHES', {
    'MARKETING_VERSION': '0.4.0',
    'CURRENT_PROJECT_VERSION': '4',
})
FILES = globals().get('FILES', {})
EXPECTED_PAYLOAD_SHA256 = globals().get('EXPECTED_PAYLOAD_SHA256', {})
PROJECT_MARKERS = ('settings.gradle.kts', 'iosApp/project.yml')
PATCH_TARGETS = ('iosApp/project.yml', 'shared/build.gradle.kts')
ARCHIVE_DIRS = (
    '.github', 'gradle', 'shared', 'iosApp', 'scripts', 'samples', 'licenses',
    'build-logic', 'tools', 'docs',
)
ARCHIVE_ROOT_FILES = (
    'gradlew', 'gradlew.bat', 'gradle.properties', 'settings.gradle.kts',
    'build.gradle.kts', '.gitignore', '.gitattributes', '.editorconfig',
    'LICENSE', 'NOTICE', 'validation-summary.json',
)
EXCLUDED_DIR_NAMES = {
    'build', '.gradle', '.kotlin', '.git', '__pycache__', '.leaf-upgrade-backup',
    'dist', 'xcuserdata', '.swiftpm', 'DerivedData', '.build', '.idea',
    '.cache', 'cache', 'caches', 'node_modules', '.venv', 'venv',
    'secrets', 'credentials', '.ssh', '.aws', 'backups',
}
EXCLUDED_SUFFIXES = (
    '.ipa', '.pyc', '.pyo', '.zip', '.tmp', '.bak', '.p12', '.pfx', '.pem',
    '.key', '.keystore', '.jks', '.mobileprovision', '.xcuserstate',
)
MIUIX_COORDINATE = 'top.yukonga.miuix.kmp:'
# The packer injects the release-approved coordinates. This legacy default keeps
# the v0.4 runtime/test contract; v0.5 coordinates are confirmed by the Lead.
REQUIRED_MATERIAL_DEPENDENCIES = globals().get('REQUIRED_MATERIAL_DEPENDENCIES', (
    'top.yukonga.miuix.kmp:miuix-blur:0.9.4',
))


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def validate_relative(rel):
    if (not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel or
            any(ord(char) < 32 or ord(char) == 127 for char in rel)):
        raise ValueError('Unsafe source path: %r' % (rel,))
    parts = rel.split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise ValueError('Unsafe source path: %r' % (rel,))
    pure = PurePosixPath(rel)
    if pure.is_absolute():
        raise ValueError('Absolute source path: %r' % (rel,))
    return pure


def no_symlinks(path):
    """Check the leaf too, including dangling symlinks, without following them."""
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError('Symlink in output/source path: %s' % candidate)


def target_for(project, rel):
    pure = validate_relative(rel)
    target = project.joinpath(*pure.parts)
    no_symlinks(target)
    try:
        target.resolve(strict=False).relative_to(project)
    except ValueError:
        raise ValueError('Target escapes project: %s' % rel)
    if target.exists() and not target.is_file():
        raise ValueError('Expected regular file at %s' % rel)
    for parent in target.parents:
        if parent == project:
            break
        if parent.exists() and not parent.is_dir():
            raise ValueError('Expected source directory at %s' % parent)
    return target


def validate_plist(payload, rel):
    try:
        plistlib.loads(payload)
    except Exception as error:
        raise ValueError('Invalid property list %s: %s' % (rel, error)) from error


def preflight(rel, content):
    data = content.encode('utf-8')
    if rel.endswith('.py'):
        ast.parse(data, filename=rel)
    elif rel.endswith('.json'):
        json.loads(content)
    elif rel.endswith('.plist'):
        validate_plist(data, rel)
    return data


def patch_project_yml(text):
    """Replace exactly two scalar values; preserve ID, comments and line endings."""
    for key, value in VERSION_PATCHES.items():
        pattern = re.compile(
            r'(?m)^([ \t]*' + re.escape(key) + r':[ \t]*)'
            r'("[^"\r\n]*"|\'[^\'\r\n]*\'|[^#\r\n \t]+)'
            r'([ \t]*(?:#[^\r\n]*)?)(\r?)$'
        )
        matches = list(pattern.finditer(text))
        if len(matches) != 1:
            raise ValueError('Expected exactly one %s scalar in iosApp/project.yml' % key)
        text = pattern.sub(lambda match: match.group(1) + '"' + value + '"' +
                           match.group(3) + match.group(4), text, count=1)
    return text


def mask_gradle_comments(text):
    """Keep character offsets/newlines while hiding // and nested /* comments.

    Ordinary quoted coordinates retain contents. Raw multiline strings are masked
    so example dependency lines inside them never become real patch anchors;
    comment markers in literals do not swallow later dependency declarations.
    """
    out = list(text)
    index = 0
    state = 'code'
    depth = 0
    while index < len(text):
        if state == 'line':
            if text[index] in '\r\n':
                state = 'code'
            else:
                out[index] = ' '
            index += 1
        elif state == 'block':
            if text.startswith('/*', index):
                out[index:index + 2] = '  '
                depth += 1
                index += 2
            elif text.startswith('*/', index):
                out[index:index + 2] = '  '
                depth -= 1
                index += 2
                if depth == 0:
                    state = 'code'
            else:
                if text[index] not in '\r\n':
                    out[index] = ' '
                index += 1
        elif state == 'triple':
            if text.startswith('"""', index):
                out[index:index + 3] = '   '
                state = 'code'
                index += 3
            else:
                if text[index] not in '\r\n':
                    out[index] = ' '
                index += 1
        elif state in ('"', "'"):
            if text[index] == '\\':
                index += 2
            elif text[index] == state:
                state = 'code'
                index += 1
            else:
                index += 1
        elif text.startswith('//', index):
            state = 'line'
            out[index:index + 2] = '  '
            index += 2
        elif text.startswith('/*', index):
            state = 'block'
            depth = 1
            out[index:index + 2] = '  '
            index += 2
        elif text.startswith('"""', index):
            out[index:index + 3] = '   '
            state = 'triple'
            index += 3
        elif text[index] in ('"', "'"):
            state = text[index]
            index += 1
        else:
            index += 1
    return ''.join(out)


def patch_shared_gradle(text, requirements=None):
    """Insert only approved missing coordinates beside miuix-ui, never replace.

    Existing exact dependencies are satisfied. Every required version and the
    insertion anchor are checked before returning any patch. Different groups
    are supported without assuming a material API or choosing release versions.
    """
    requirements = REQUIRED_MATERIAL_DEPENDENCIES if requirements is None else requirements
    required = {}
    for coordinate in requirements:
        if not isinstance(coordinate, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+', coordinate):
            raise ValueError('Expected an exact group:artifact:version material coordinate')
        group, artifact, version = coordinate.split(':')
        key = group + ':' + artifact
        if key in required:
            raise ValueError('Duplicate material requirement: %s' % key)
        required[key] = (version, coordinate)
    active = mask_gradle_comments(text)
    dependency = re.compile(
        r'(?m)^([ \t]*)implementation[ \t]*\([ \t]*"'
        r'([^":\r\n]+:[^":\r\n]+):([^"\r\n]+)"[ \t]*\)'
        r'[ \t]*;?[ \t]*(\r?\n|$)'
    )
    declarations = list(dependency.finditer(active))
    missing = []
    for key, (version, coordinate) in required.items():
        found = [match for match in declarations if match.group(2) == key]
        if found:
            if len(found) != 1 or found[0].group(3) != version:
                raise ValueError('Existing %s must be one implementation pinned to %s' % (key, version))
        elif key + ':' in active:
            raise ValueError('Unrecognized dependency %s; review shared/build.gradle.kts' % key)
        else:
            missing.append(coordinate)
    if not missing:
        return text
    anchors = [match for match in declarations if match.group(2) == MIUIX_COORDINATE + 'miuix-ui' and match.group(3) == '0.9.4']
    if len(anchors) != 1:
        raise ValueError('Expected exactly one implementation("%smiuix-ui:0.9.4") anchor' % MIUIX_COORDINATE)
    anchor = anchors[0]
    newline = anchor.group(4) or ('\r\n' if '\r\n' in text else '\n')
    addition = ''.join(anchor.group(1) + 'implementation("%s")' % coordinate + newline for coordinate in missing)
    prefix = text[:anchor.end()]
    if not anchor.group(4):
        prefix += newline
    return prefix + addition + text[anchor.end():]


def excluded_name(name):
    lower = name.lower()
    return (name in EXCLUDED_DIR_NAMES or lower in {'local.properties', '.ds_store'} or
            lower == '.env' or lower.startswith('.env.') or
            any(word in lower for word in ('secret', 'credential', 'signing-key')) or
            lower.endswith(EXCLUDED_SUFFIXES))


def collect_archive_files(project, archive_output=None):
    """Source allowlist only. Prune ignored/symlink directories before traversal."""
    result = set()
    for directory in ARCHIVE_DIRS:
        root = project / directory
        if root.is_symlink() or not root.is_dir():
            continue
        for current, directories, filenames in os.walk(str(root), followlinks=False):
            current = Path(current)
            directories[:] = sorted(name for name in directories if not excluded_name(name)
                                    and not (current / name).is_symlink()
                                    and not name.endswith(('.xcodeproj', '.xcworkspace')))
            for name in sorted(filenames):
                path = current / name
                if excluded_name(name) or path.is_symlink() or not path.is_file():
                    continue
                if archive_output is not None and path.resolve() == archive_output:
                    continue
                result.add(path)
    for path in project.iterdir():
        if path.is_symlink() or not path.is_file() or excluded_name(path.name):
            continue
        if (path.name in ARCHIVE_ROOT_FILES or path.suffix.lower() == '.md' or
                re.fullmatch(r'LeafReader-v[0-9.]+-upgrade\.py', path.name)):
            if archive_output is None or path.resolve() != archive_output:
                result.add(path)
    return sorted(result)


def atomic_write(target, payload, mode=0o644):
    no_symlinks(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(target.parent), prefix='.leaf-', suffix='.tmp')
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        no_symlinks(target)
        os.replace(temporary, str(target))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode('utf-8') + b'\n')


def archive_destination(project, argument):
    output = Path(argument).expanduser()
    if not output.is_absolute():
        output = project / output
    # Reject user traversal spellings too, before resolve normalizes them.
    if '..' in output.parts:
        raise ValueError('Archive path contains traversal')
    no_symlinks(output)
    output = output.resolve(strict=False)
    if output.suffix.lower() != '.zip':
        raise ValueError('--archive must end in .zip')
    if output.exists() and not output.is_file():
        raise ValueError('Archive output is not a regular file')
    for ancestor in output.parents:
        if ancestor.exists() and not ancestor.is_dir():
            raise ValueError('Archive parent is not a directory: %s' % ancestor)
    try:
        relative = output.relative_to(project)
    except ValueError:
        relative = None
    if relative and any(part in EXCLUDED_DIR_NAMES - {'dist'} for part in relative.parts[:-1]):
        raise ValueError('Archive output inside a cache/backup directory')
    return output


def write_archive(project, output):
    files = collect_archive_files(project, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(output.parent), prefix='.leaf-archive-', suffix='.tmp')
    os.close(handle)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in files:
                no_symlinks(path)
                archive.write(path, path.relative_to(project).as_posix())
        no_symlinks(output)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return files


def prepare_upgrade(project, archive_path=None):
    """Read-only phase. No mkdir, temporary file, backup or replacement here."""
    for marker in PROJECT_MARKERS:
        if not target_for(project, marker).is_file():
            raise ValueError('Missing LeafReader project marker: %s' % marker)
    if not FILES:
        raise ValueError('No embedded files; run tools/make_upgrade.py to create an installer')
    if any(rel in FILES for rel in PATCH_TARGETS):
        raise ValueError('Patch-only targets must not be embedded as full replacements')
    if EXPECTED_PAYLOAD_SHA256 and set(EXPECTED_PAYLOAD_SHA256) != set(FILES):
        raise ValueError('Payload SHA map does not match FILES')
    prepared = {}
    for rel, text in sorted(FILES.items()):
        target_for(project, rel)
        payload = preflight(rel, text)
        expected = EXPECTED_PAYLOAD_SHA256.get(rel)
        if expected and sha256_bytes(payload) != expected:
            raise ValueError('Embedded payload SHA mismatch: %s' % rel)
        prepared[rel] = payload
    patches = (
        ('iosApp/project.yml', patch_project_yml),
        ('shared/build.gradle.kts', patch_shared_gradle),
    )
    for rel, patch in patches:
        target = target_for(project, rel)
        if not target.is_file():
            raise ValueError('Missing patch target: %s' % rel)
        original = target.read_bytes()
        prepared[rel] = patch(original.decode('utf-8')).encode('utf-8')
    # Validate all source Python and XML/binary property lists, without executing
    # Python or invoking a compiler. Generated/cache/secret trees are not scanned.
    checked = {'python': [], 'plist': []}
    for path in collect_archive_files(project, archive_path):
        rel = path.relative_to(project).as_posix()
        payload = prepared.get(rel)
        if path.suffix not in ('.py', '.plist'):
            continue
        if payload is None:
            payload = path.read_bytes()
        if path.suffix == '.py':
            ast.parse(payload, filename=rel)
            checked['python'].append(rel)
        else:
            validate_plist(payload, rel)
            checked['plist'].append(rel)
    entries = []
    for rel, payload in sorted(prepared.items()):
        target = target_for(project, rel)
        if archive_path is not None and target.resolve(strict=False) == archive_path:
            raise ValueError('Archive collides with source target')
        before = target.read_bytes() if target.is_file() else None
        mode = stat.S_IMODE(target.stat().st_mode) if before is not None else (0o755 if rel.endswith('.sh') else 0o644)
        entries.append({'path': rel, 'target': target, 'before': before, 'after': payload, 'mode': mode})
    # Preflight backup path as well; no writes through a user-supplied symlink.
    backup_parent = project / '.leaf-upgrade-backup'
    no_symlinks(backup_parent)
    if backup_parent.exists() and not backup_parent.is_dir():
        raise ValueError('Backup root is not a directory')
    return entries, checked


def apply_upgrade(project, entries, checked):
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup_root = project / '.leaf-upgrade-backup' / (timestamp + '-' + uuid.uuid4().hex[:8])
    manifest = {
        'tool': 'LeafReader-v%s-upgrade' % INSTALLER_VERSION,
        'applied_at_utc': timestamp, 'file_count': len(FILES), 'status': 'prepared',
        'verification': checked, 'changes': [],
        'note': 'Only version scalars and release-approved missing material dependencies are patched in build configuration.',
        'material_dependencies': list(REQUIRED_MATERIAL_DEPENDENCIES),
    }
    # All originals are backed up before replacing even the first source.
    for entry in entries:
        rel, before, after = entry['path'], entry['before'], entry['after']
        if before is not None and before != after:
            destination = backup_root / 'files' / rel
            atomic_write(destination, before, entry['mode'])
        manifest['changes'].append({
            'path': rel, 'existed': before is not None, 'unchanged': before == after,
            'sha256_before': sha256_bytes(before) if before is not None else None,
            'sha256_after': sha256_bytes(after), 'bytes': len(after),
            'backup': 'files/' + rel if before is not None and before != after else None,
        })
    manifest_path = backup_root / 'change-manifest.json'
    write_json(manifest_path, manifest)
    payload_sha = {rel: sha256_bytes(text.encode('utf-8')) for rel, text in sorted(FILES.items())}
    write_json(backup_root / 'payload-sha256.json', payload_sha)
    applied = []
    try:
        for entry in entries:
            target = target_for(project, entry['path'])
            current = target.read_bytes() if target.is_file() else None
            if current != entry['before']:
                raise ValueError('Source changed since preflight: %s' % entry['path'])
            if current != entry['after']:
                atomic_write(target, entry['after'], entry['mode'])
                applied.append(entry)
            if target.read_bytes() != entry['after']:
                raise ValueError('Post-write verification failed: %s' % entry['path'])
        manifest['status'] = 'applied'
        write_json(manifest_path, manifest)
    except BaseException:
        failures = []
        for entry in reversed(applied):
            try:
                target = target_for(project, entry['path'])
                if entry['before'] is None:
                    target.unlink()
                else:
                    atomic_write(target, entry['before'], entry['mode'])
            except (OSError, ValueError) as error:
                failures.append('%s: %s' % (entry['path'], error))
        manifest['status'] = 'rollback-incomplete' if failures else 'rolled-back'
        manifest['rollback_errors'] = failures
        write_json(manifest_path, manifest)
        raise
    return backup_root


def main(argv=None):
    parser = argparse.ArgumentParser(description='Apply the offline LeafReader v%s source upgrade.' % INSTALLER_VERSION)
    parser.add_argument('--project', required=True, help='Existing LeafReader repository root')
    parser.add_argument('--archive', help='Optional ZIP path, relative to project unless absolute')
    args = parser.parse_args(argv)
    requested = Path(args.project).expanduser().absolute()
    no_symlinks(requested)
    project = requested.resolve()
    if not project.is_dir():
        raise ValueError('Project directory does not exist: %s' % project)
    archive_path = archive_destination(project, args.archive) if args.archive else None
    entries, checked = prepare_upgrade(project, archive_path)
    backup_root = apply_upgrade(project, entries, checked)
    print('Applied %d embedded files and two scoped configuration patches.' % len(FILES))
    print('Backup/change manifest/payload SHA: %s' % backup_root)
    if archive_path:
        written = write_archive(project, archive_path)
        print('Archive: %s (%d files)' % (archive_path, len(written)))
    print('Kotlin/Swift build, tests and device verification remain CI/device tasks.')
    return 0


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, SyntaxError, plistlib.InvalidFileException) as error:
        raise SystemExit('Upgrade stopped: %s' % error)
''',
    'validation-summary.json': r'''{
  "version": "0.5.0",
  "date": "2026-11-26",
  "shared_desktop_compilation": "passed: Gradle :shared:desktopTest on Linux/JDK 17",
  "kotlin_test_results": {"tests": 70, "failures": 0, "errors": 0, "skipped": 0, "note": "logic and source-structure tests; no simulated UI clicks"},
  "python_script_tests": {"tests": 34, "failures": 0},
  "apple_framework_and_swift": "not run; requires macOS/Xcode",
  "ipa_build": "not run for v0.5",
  "device_rendering_and_performance": "not tested: iOS 16:9, text blur, status bar, popup interaction, accessibility and performance",
  "github_workflow_dispatch": "not performed",
  "known_build_fixes_preserved": ["POSIX storage", "lipo -archs", "Xcode selection", "IPA upload before native tests"]
}
''',
}
EXPECTED_PAYLOAD_SHA256 = {
    ".github/workflows/upgrade-v02.yml": "30f785c663d91409e2ea26e536cc5596990dcd0fe26b2fda58a8db671999cdc8",
    ".github/workflows/upgrade-v03.yml": "2bfec4dc32c6a2cc453c279d575a7d32d0a79623dc86e7dd206f9e39f301da54",
    ".github/workflows/upgrade-v04.yml": "257c958c4c80e3bcfe3997fdec91e588c08dbe723197658d8c5683432b6dd9c9",
    ".github/workflows/upgrade-v05.yml": "fabf802bad7fcd54d9e47ec776cec77d117781205a4c3f05038267af5d2b8389",
    "README.md": "6d900d67f5529b9e3ef225c1c27aa9acfac6250b07de75fc683dd68ea968db60",
    "UPGRADE-v0.2.md": "d8e7883dcb9b2bd1ccc296cdfb31a42fd9a903894b2c46b142d669eb3c8b4693",
    "UPGRADE-v0.3.md": "59cf7f11f76f41f2e9b19eab8a6ed24d9b0b2be66371cd495f7386accc2b6693",
    "UPGRADE-v0.4.md": "34d0b39fd07e91a9f3d6df3d485b9c8a4bd8368c3239781e7b89b6cb762ae219",
    "UPGRADE-v0.5.md": "2e323e45bae7a2ec44b0254ae6eccfce233a422e993de31abb2f24db72efd376",
    "VALIDATION.md": "45a59f9b67a1728c37d3edc18d96a6d99927731af54150a9ab5d3f0bdb21e53b",
    "iosApp/README.md": "a5b4a90024de6d749782a0dca6a925b06ac46864fdeaae66840b4e2058334def",
    "iosApp/Sources/Host/DocumentPicker.swift": "63283ecfe0d97893d1241f0e93c89853ed4888f7d240a5520d1a17290f7d631d",
    "iosApp/Sources/Host/LeafReaderApp.swift": "93949eace93fa72929eee6d942b90bdb8f398c0ddd95f218aa5bd4d1b9555a31",
    "iosApp/Sources/Parser/BookParser.swift": "19aba14dcfb045b111e58c839406a8c2badfe52f3e0d2db9183224ae0888e2f3",
    "iosApp/Sources/Parser/EPUBParser.swift": "c5ba5bb56f363bb55c42fed86b27a7ffcdc80a2176a6d79c6431269d88db2697",
    "iosApp/Sources/Parser/STREAMING_IMPORT.md": "08bd4019bc1b49847233bfdfbbcb5df4a4104eabdbba072da580452788623b0c",
    "iosApp/Sources/Parser/StreamingImport.swift": "aa0f17ed69dc4a05301372c11a93d93566c13af4f9dcfe7fe2ad97ab9b222d90",
    "iosApp/Sources/Parser/ZIPPreflight.swift": "a3548a1aad1bcf1cc58a6484cc79d979c087e6e666affbf6e5eab9b6f8887256",
    "iosApp/Tests/BookParserTests.swift": "e713df918f048a0fb8afbd9040adc6c26d20766db70a15023f0e0947174b211d",
    "iosApp/Tests/StreamingImportTests.swift": "ddde123aaffe0914b2b3ea50dd39c89d9134882abc76571f7804c39710b72012",
    "scripts/build-ios.sh": "728aac569242d3ed0141a4fffb84f4b8bd111f9ce22f322154c9207091a513b1",
    "scripts/tests/test_upgrade_v04.py": "83c243271b3da7d60ecb5068c1670eddd23b8e28a5ba8d1b86ef423b4a490c23",
    "scripts/tests/test_upgrade_v05.py": "5727bedb86d22b8673ab93e1f1ac8c41fc4797eaa0e5a455c6a70bdb6e3c3c85",
    "shared/src/commonMain/kotlin/dev/leaf/reader/Models.kt": "8ab531191ef8e70f3f9943333d75bd6b6fcc3aeb4a9a3e9c86bbdc72cac8bd9f",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ReaderFiles.kt": "bc772d23e8c26f656d9b399e88faffc34a118bfc123e29d5beb26c8f89fafef3",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ReaderStore.kt": "c485139ef4b4a02efe2216e3696aa344f3a258072666184c6748067b9a9d6071",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/ContentsScreen.kt": "d1411f26ce5f306f251951f0391d1e2a9ee58c863481eb3a6d6381604abcbe8a",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/MiuixAtoms.kt": "d259c5c473861d116494acd481de84293e1fe678476a041cfc18f7836be32582",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/MiuixGlyphs.kt": "a23952767b0d67cd74b03d09eb932e53e9509115d02ec23bb56318c017fa2a35",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/Pagination.kt": "d537012b6dd12fc640df0450621b84cf0bb8a15eae1f4b8eac437fb682315e47",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderApp.kt": "dd56a9b27ce96ecf1c623cfc5daa6ae78d675e490e843ab85856cb57fc673acf",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderChrome.kt": "ce7e6de0dfb0b35fe9959d0f3468a2c40200d5810283399ede8a4023546ac93d",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReadingScreen.kt": "638c99774006ad673788d2eb029d897c5d66f5d37326bedd547213f639d98db6",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReadingSettings.kt": "4dacd6fc30bde451d0380f1e369cc3febeaf943ffb747e67ab1f695412d4824c",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/ShelfScreen.kt": "2fa2a23b213435ec31d2e966b1d151d71a4d214043a25ee1831abe9f28ae6399",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/ShelfWidgets.kt": "94401b018ffaf45e5192f3678915688d0cedc277f46eba88b51fe72daa2a56d0",
    "shared/src/commonMain/kotlin/dev/leaf/reader/ui/TocSheet.kt": "88a3cab5884b9de6a3bc5d1fe8c7cd5f595cbf1880876f173b0c5d3fc27cacef",
    "shared/src/commonTest/kotlin/dev/leaf/reader/ManifestStorageTest.kt": "d867f79e055d70483ae5f6f26c3694903bdf4fb39943a5d7e03f9e35edb158ad",
    "shared/src/commonTest/kotlin/dev/leaf/reader/ReaderStoreTest.kt": "3efcbe98c16f447af00e8a432293b9007ad94b7e0d3f98319938fc8e704d8821",
    "shared/src/commonTest/kotlin/dev/leaf/reader/ui/ContentsNavigationTest.kt": "c06abe10028133f3cff36a14cf3869c6b83974df4f42140029acfe405450c96d",
    "shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderChromeTest.kt": "48d4293d12a74aee28b3c1625a7b64e893b5997954f8448fff06639aba6f7875",
    "shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderOverlayRegressionTest.kt": "eb4c89dd0055863ee860cec51935da294b3967ae115497572862f1287a5928ab",
    "shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderPaginationTest.kt": "9138b7ecf6a8046dcad5226c36d069be221c87f15e03eb4badb85a87a74aa445",
    "shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReadingItemsTest.kt": "af18c8d791c8c351f547dbace4fd2f3998130a39744cc7b8816f7be1164b49cb",
    "shared/src/desktopTest/kotlin/dev/leaf/reader/ui/ReaderHostStructureTest.kt": "334d6f5dea671e726d43c6f8eb232e44098a4af2a5052db4d286a3c077141be2",
    "shared/src/iosMain/kotlin/dev/leaf/reader/MainViewController.kt": "9aad96c263beb2ec38f1da1c4f4aee8bb5fd787058848365e3c7a43772eed233",
    "shared/src/iosMain/kotlin/dev/leaf/reader/ReaderFiles.ios.kt": "a0242483ff8c961b8dae99d346ef4809c538ef2e5692fc2879c264525fbd6270",
    "tools/make_upgrade.py": "5dc32920c8bf610db9aff9d9055cfc7643c62e66d08664937deb00621550d23e",
    "tools/upgrade_runner.py": "c2a78e7816a54861ee11d3f1cdfd61ce19bcc13d8e8b7c3078c1bd2b921f353e",
    "validation-summary.json": "e2ee9eb7b1aaa2ec62daae488a02465a0039d7b6082c42117d38aa914e0bd3a9"
}

#!/usr/bin/env python3
"""Offline LeafReader installer runtime; importable for temporary-project tests.

The packer prepends a literal FILES dictionary and its expected SHA256 map.
Preflight reads/validates EVERY replacement and patch before creating backups or
writing sources. Atomicity is per file; caught apply failures trigger a best-
effort rollback. No network, subprocess, credentials or Git operations are used.
"""
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import stat
import tempfile
import uuid
import zipfile

INSTALLER_VERSION = globals().get('INSTALLER_VERSION', '0.4')
VERSION_PATCHES = globals().get('VERSION_PATCHES', {
    'MARKETING_VERSION': '0.4.0',
    'CURRENT_PROJECT_VERSION': '4',
})
FILES = globals().get('FILES', {})
EXPECTED_PAYLOAD_SHA256 = globals().get('EXPECTED_PAYLOAD_SHA256', {})
PROJECT_MARKERS = ('settings.gradle.kts', 'iosApp/project.yml')
PATCH_TARGETS = ('iosApp/project.yml', 'shared/build.gradle.kts')
ARCHIVE_DIRS = (
    '.github', 'gradle', 'shared', 'iosApp', 'scripts', 'samples', 'licenses',
    'build-logic', 'tools', 'docs',
)
ARCHIVE_ROOT_FILES = (
    'gradlew', 'gradlew.bat', 'gradle.properties', 'settings.gradle.kts',
    'build.gradle.kts', '.gitignore', '.gitattributes', '.editorconfig',
    'LICENSE', 'NOTICE', 'validation-summary.json',
)
EXCLUDED_DIR_NAMES = {
    'build', '.gradle', '.kotlin', '.git', '__pycache__', '.leaf-upgrade-backup',
    'dist', 'xcuserdata', '.swiftpm', 'DerivedData', '.build', '.idea',
    '.cache', 'cache', 'caches', 'node_modules', '.venv', 'venv',
    'secrets', 'credentials', '.ssh', '.aws', 'backups',
}
EXCLUDED_SUFFIXES = (
    '.ipa', '.pyc', '.pyo', '.zip', '.tmp', '.bak', '.p12', '.pfx', '.pem',
    '.key', '.keystore', '.jks', '.mobileprovision', '.xcuserstate',
)
MIUIX_COORDINATE = 'top.yukonga.miuix.kmp:'
# The packer injects the release-approved coordinates. This legacy default keeps
# the v0.4 runtime/test contract; v0.5 coordinates are confirmed by the Lead.
REQUIRED_MATERIAL_DEPENDENCIES = globals().get('REQUIRED_MATERIAL_DEPENDENCIES', (
    'top.yukonga.miuix.kmp:miuix-blur:0.9.4',
))


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def validate_relative(rel):
    if (not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel or
            any(ord(char) < 32 or ord(char) == 127 for char in rel)):
        raise ValueError('Unsafe source path: %r' % (rel,))
    parts = rel.split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise ValueError('Unsafe source path: %r' % (rel,))
    pure = PurePosixPath(rel)
    if pure.is_absolute():
        raise ValueError('Absolute source path: %r' % (rel,))
    return pure


def no_symlinks(path):
    """Check the leaf too, including dangling symlinks, without following them."""
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError('Symlink in output/source path: %s' % candidate)


def target_for(project, rel):
    pure = validate_relative(rel)
    target = project.joinpath(*pure.parts)
    no_symlinks(target)
    try:
        target.resolve(strict=False).relative_to(project)
    except ValueError:
        raise ValueError('Target escapes project: %s' % rel)
    if target.exists() and not target.is_file():
        raise ValueError('Expected regular file at %s' % rel)
    for parent in target.parents:
        if parent == project:
            break
        if parent.exists() and not parent.is_dir():
            raise ValueError('Expected source directory at %s' % parent)
    return target


def validate_plist(payload, rel):
    try:
        plistlib.loads(payload)
    except Exception as error:
        raise ValueError('Invalid property list %s: %s' % (rel, error)) from error


def preflight(rel, content):
    data = content.encode('utf-8')
    if rel.endswith('.py'):
        ast.parse(data, filename=rel)
    elif rel.endswith('.json'):
        json.loads(content)
    elif rel.endswith('.plist'):
        validate_plist(data, rel)
    return data


def patch_project_yml(text):
    """Replace exactly two scalar values; preserve ID, comments and line endings."""
    for key, value in VERSION_PATCHES.items():
        pattern = re.compile(
            r'(?m)^([ \t]*' + re.escape(key) + r':[ \t]*)'
            r'("[^"\r\n]*"|\'[^\'\r\n]*\'|[^#\r\n \t]+)'
            r'([ \t]*(?:#[^\r\n]*)?)(\r?)$'
        )
        matches = list(pattern.finditer(text))
        if len(matches) != 1:
            raise ValueError('Expected exactly one %s scalar in iosApp/project.yml' % key)
        text = pattern.sub(lambda match: match.group(1) + '"' + value + '"' +
                           match.group(3) + match.group(4), text, count=1)
    return text


def mask_gradle_comments(text):
    """Keep character offsets/newlines while hiding // and nested /* comments.

    Ordinary quoted coordinates retain contents. Raw multiline strings are masked
    so example dependency lines inside them never become real patch anchors;
    comment markers in literals do not swallow later dependency declarations.
    """
    out = list(text)
    index = 0
    state = 'code'
    depth = 0
    while index < len(text):
        if state == 'line':
            if text[index] in '\r\n':
                state = 'code'
            else:
                out[index] = ' '
            index += 1
        elif state == 'block':
            if text.startswith('/*', index):
                out[index:index + 2] = '  '
                depth += 1
                index += 2
            elif text.startswith('*/', index):
                out[index:index + 2] = '  '
                depth -= 1
                index += 2
                if depth == 0:
                    state = 'code'
            else:
                if text[index] not in '\r\n':
                    out[index] = ' '
                index += 1
        elif state == 'triple':
            if text.startswith('"""', index):
                out[index:index + 3] = '   '
                state = 'code'
                index += 3
            else:
                if text[index] not in '\r\n':
                    out[index] = ' '
                index += 1
        elif state in ('"', "'"):
            if text[index] == '\\':
                index += 2
            elif text[index] == state:
                state = 'code'
                index += 1
            else:
                index += 1
        elif text.startswith('//', index):
            state = 'line'
            out[index:index + 2] = '  '
            index += 2
        elif text.startswith('/*', index):
            state = 'block'
            depth = 1
            out[index:index + 2] = '  '
            index += 2
        elif text.startswith('"""', index):
            out[index:index + 3] = '   '
            state = 'triple'
            index += 3
        elif text[index] in ('"', "'"):
            state = text[index]
            index += 1
        else:
            index += 1
    return ''.join(out)


def patch_shared_gradle(text, requirements=None):
    """Insert only approved missing coordinates beside miuix-ui, never replace.

    Existing exact dependencies are satisfied. Every required version and the
    insertion anchor are checked before returning any patch. Different groups
    are supported without assuming a material API or choosing release versions.
    """
    requirements = REQUIRED_MATERIAL_DEPENDENCIES if requirements is None else requirements
    required = {}
    for coordinate in requirements:
        if not isinstance(coordinate, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+', coordinate):
            raise ValueError('Expected an exact group:artifact:version material coordinate')
        group, artifact, version = coordinate.split(':')
        key = group + ':' + artifact
        if key in required:
            raise ValueError('Duplicate material requirement: %s' % key)
        required[key] = (version, coordinate)
    active = mask_gradle_comments(text)
    dependency = re.compile(
        r'(?m)^([ \t]*)implementation[ \t]*\([ \t]*"'
        r'([^":\r\n]+:[^":\r\n]+):([^"\r\n]+)"[ \t]*\)'
        r'[ \t]*;?[ \t]*(\r?\n|$)'
    )
    declarations = list(dependency.finditer(active))
    missing = []
    for key, (version, coordinate) in required.items():
        found = [match for match in declarations if match.group(2) == key]
        if found:
            if len(found) != 1 or found[0].group(3) != version:
                raise ValueError('Existing %s must be one implementation pinned to %s' % (key, version))
        elif key + ':' in active:
            raise ValueError('Unrecognized dependency %s; review shared/build.gradle.kts' % key)
        else:
            missing.append(coordinate)
    if not missing:
        return text
    anchors = [match for match in declarations if match.group(2) == MIUIX_COORDINATE + 'miuix-ui' and match.group(3) == '0.9.4']
    if len(anchors) != 1:
        raise ValueError('Expected exactly one implementation("%smiuix-ui:0.9.4") anchor' % MIUIX_COORDINATE)
    anchor = anchors[0]
    newline = anchor.group(4) or ('\r\n' if '\r\n' in text else '\n')
    addition = ''.join(anchor.group(1) + 'implementation("%s")' % coordinate + newline for coordinate in missing)
    prefix = text[:anchor.end()]
    if not anchor.group(4):
        prefix += newline
    return prefix + addition + text[anchor.end():]


def excluded_name(name):
    lower = name.lower()
    return (name in EXCLUDED_DIR_NAMES or lower in {'local.properties', '.ds_store'} or
            lower == '.env' or lower.startswith('.env.') or
            any(word in lower for word in ('secret', 'credential', 'signing-key')) or
            lower.endswith(EXCLUDED_SUFFIXES))


def collect_archive_files(project, archive_output=None):
    """Source allowlist only. Prune ignored/symlink directories before traversal."""
    result = set()
    for directory in ARCHIVE_DIRS:
        root = project / directory
        if root.is_symlink() or not root.is_dir():
            continue
        for current, directories, filenames in os.walk(str(root), followlinks=False):
            current = Path(current)
            directories[:] = sorted(name for name in directories if not excluded_name(name)
                                    and not (current / name).is_symlink()
                                    and not name.endswith(('.xcodeproj', '.xcworkspace')))
            for name in sorted(filenames):
                path = current / name
                if excluded_name(name) or path.is_symlink() or not path.is_file():
                    continue
                if archive_output is not None and path.resolve() == archive_output:
                    continue
                result.add(path)
    for path in project.iterdir():
        if path.is_symlink() or not path.is_file() or excluded_name(path.name):
            continue
        if (path.name in ARCHIVE_ROOT_FILES or path.suffix.lower() == '.md' or
                re.fullmatch(r'LeafReader-v[0-9.]+-upgrade\.py', path.name)):
            if archive_output is None or path.resolve() != archive_output:
                result.add(path)
    return sorted(result)


def atomic_write(target, payload, mode=0o644):
    no_symlinks(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(target.parent), prefix='.leaf-', suffix='.tmp')
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        no_symlinks(target)
        os.replace(temporary, str(target))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode('utf-8') + b'\n')


def archive_destination(project, argument):
    output = Path(argument).expanduser()
    if not output.is_absolute():
        output = project / output
    # Reject user traversal spellings too, before resolve normalizes them.
    if '..' in output.parts:
        raise ValueError('Archive path contains traversal')
    no_symlinks(output)
    output = output.resolve(strict=False)
    if output.suffix.lower() != '.zip':
        raise ValueError('--archive must end in .zip')
    if output.exists() and not output.is_file():
        raise ValueError('Archive output is not a regular file')
    for ancestor in output.parents:
        if ancestor.exists() and not ancestor.is_dir():
            raise ValueError('Archive parent is not a directory: %s' % ancestor)
    try:
        relative = output.relative_to(project)
    except ValueError:
        relative = None
    if relative and any(part in EXCLUDED_DIR_NAMES - {'dist'} for part in relative.parts[:-1]):
        raise ValueError('Archive output inside a cache/backup directory')
    return output


def write_archive(project, output):
    files = collect_archive_files(project, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(output.parent), prefix='.leaf-archive-', suffix='.tmp')
    os.close(handle)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in files:
                no_symlinks(path)
                archive.write(path, path.relative_to(project).as_posix())
        no_symlinks(output)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return files


def prepare_upgrade(project, archive_path=None):
    """Read-only phase. No mkdir, temporary file, backup or replacement here."""
    for marker in PROJECT_MARKERS:
        if not target_for(project, marker).is_file():
            raise ValueError('Missing LeafReader project marker: %s' % marker)
    if not FILES:
        raise ValueError('No embedded files; run tools/make_upgrade.py to create an installer')
    if any(rel in FILES for rel in PATCH_TARGETS):
        raise ValueError('Patch-only targets must not be embedded as full replacements')
    if EXPECTED_PAYLOAD_SHA256 and set(EXPECTED_PAYLOAD_SHA256) != set(FILES):
        raise ValueError('Payload SHA map does not match FILES')
    prepared = {}
    for rel, text in sorted(FILES.items()):
        target_for(project, rel)
        payload = preflight(rel, text)
        expected = EXPECTED_PAYLOAD_SHA256.get(rel)
        if expected and sha256_bytes(payload) != expected:
            raise ValueError('Embedded payload SHA mismatch: %s' % rel)
        prepared[rel] = payload
    patches = (
        ('iosApp/project.yml', patch_project_yml),
        ('shared/build.gradle.kts', patch_shared_gradle),
    )
    for rel, patch in patches:
        target = target_for(project, rel)
        if not target.is_file():
            raise ValueError('Missing patch target: %s' % rel)
        original = target.read_bytes()
        prepared[rel] = patch(original.decode('utf-8')).encode('utf-8')
    # Validate all source Python and XML/binary property lists, without executing
    # Python or invoking a compiler. Generated/cache/secret trees are not scanned.
    checked = {'python': [], 'plist': []}
    for path in collect_archive_files(project, archive_path):
        rel = path.relative_to(project).as_posix()
        payload = prepared.get(rel)
        if path.suffix not in ('.py', '.plist'):
            continue
        if payload is None:
            payload = path.read_bytes()
        if path.suffix == '.py':
            ast.parse(payload, filename=rel)
            checked['python'].append(rel)
        else:
            validate_plist(payload, rel)
            checked['plist'].append(rel)
    entries = []
    for rel, payload in sorted(prepared.items()):
        target = target_for(project, rel)
        if archive_path is not None and target.resolve(strict=False) == archive_path:
            raise ValueError('Archive collides with source target')
        before = target.read_bytes() if target.is_file() else None
        mode = stat.S_IMODE(target.stat().st_mode) if before is not None else (0o755 if rel.endswith('.sh') else 0o644)
        entries.append({'path': rel, 'target': target, 'before': before, 'after': payload, 'mode': mode})
    # Preflight backup path as well; no writes through a user-supplied symlink.
    backup_parent = project / '.leaf-upgrade-backup'
    no_symlinks(backup_parent)
    if backup_parent.exists() and not backup_parent.is_dir():
        raise ValueError('Backup root is not a directory')
    return entries, checked


def apply_upgrade(project, entries, checked):
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup_root = project / '.leaf-upgrade-backup' / (timestamp + '-' + uuid.uuid4().hex[:8])
    manifest = {
        'tool': 'LeafReader-v%s-upgrade' % INSTALLER_VERSION,
        'applied_at_utc': timestamp, 'file_count': len(FILES), 'status': 'prepared',
        'verification': checked, 'changes': [],
        'note': 'Only version scalars and release-approved missing material dependencies are patched in build configuration.',
        'material_dependencies': list(REQUIRED_MATERIAL_DEPENDENCIES),
    }
    # All originals are backed up before replacing even the first source.
    for entry in entries:
        rel, before, after = entry['path'], entry['before'], entry['after']
        if before is not None and before != after:
            destination = backup_root / 'files' / rel
            atomic_write(destination, before, entry['mode'])
        manifest['changes'].append({
            'path': rel, 'existed': before is not None, 'unchanged': before == after,
            'sha256_before': sha256_bytes(before) if before is not None else None,
            'sha256_after': sha256_bytes(after), 'bytes': len(after),
            'backup': 'files/' + rel if before is not None and before != after else None,
        })
    manifest_path = backup_root / 'change-manifest.json'
    write_json(manifest_path, manifest)
    payload_sha = {rel: sha256_bytes(text.encode('utf-8')) for rel, text in sorted(FILES.items())}
    write_json(backup_root / 'payload-sha256.json', payload_sha)
    applied = []
    try:
        for entry in entries:
            target = target_for(project, entry['path'])
            current = target.read_bytes() if target.is_file() else None
            if current != entry['before']:
                raise ValueError('Source changed since preflight: %s' % entry['path'])
            if current != entry['after']:
                atomic_write(target, entry['after'], entry['mode'])
                applied.append(entry)
            if target.read_bytes() != entry['after']:
                raise ValueError('Post-write verification failed: %s' % entry['path'])
        manifest['status'] = 'applied'
        write_json(manifest_path, manifest)
    except BaseException:
        failures = []
        for entry in reversed(applied):
            try:
                target = target_for(project, entry['path'])
                if entry['before'] is None:
                    target.unlink()
                else:
                    atomic_write(target, entry['before'], entry['mode'])
            except (OSError, ValueError) as error:
                failures.append('%s: %s' % (entry['path'], error))
        manifest['status'] = 'rollback-incomplete' if failures else 'rolled-back'
        manifest['rollback_errors'] = failures
        write_json(manifest_path, manifest)
        raise
    return backup_root


def main(argv=None):
    parser = argparse.ArgumentParser(description='Apply the offline LeafReader v%s source upgrade.' % INSTALLER_VERSION)
    parser.add_argument('--project', required=True, help='Existing LeafReader repository root')
    parser.add_argument('--archive', help='Optional ZIP path, relative to project unless absolute')
    args = parser.parse_args(argv)
    requested = Path(args.project).expanduser().absolute()
    no_symlinks(requested)
    project = requested.resolve()
    if not project.is_dir():
        raise ValueError('Project directory does not exist: %s' % project)
    archive_path = archive_destination(project, args.archive) if args.archive else None
    entries, checked = prepare_upgrade(project, archive_path)
    backup_root = apply_upgrade(project, entries, checked)
    print('Applied %d embedded files and two scoped configuration patches.' % len(FILES))
    print('Backup/change manifest/payload SHA: %s' % backup_root)
    if archive_path:
        written = write_archive(project, archive_path)
        print('Archive: %s (%d files)' % (archive_path, len(written)))
    print('Kotlin/Swift build, tests and device verification remain CI/device tasks.')
    return 0


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, SyntaxError, plistlib.InvalidFileException) as error:
        raise SystemExit('Upgrade stopped: %s' % error)
