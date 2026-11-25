# 叶读 · Leaf Reader v0.2

面向 iOS16+ 的本地小说阅读器，Kotlin Multiplatform / Compose Multiplatform / Miuix 0.9.4。使用 GitHub Actions 构建未签名 ARM64 IPA，交给兼容设备上的 TrollStore 安装。

## 与 v0.1 的区别

- 真正 Miuix 折叠大标题、搜索、分组设置、分段选项、Switch 和 Slider。
- 网格 / 列表 / 紧凑三种书架。
- 横向滑动分页 / 瞬翻 / 纵向滚动，单栏 / 双栏 / 自动分栏。
- 阅读顶底栏可点击收起、可自动隐藏；叠层不挤压分页尺寸。
- 字体、字号、行距、段距、字距、边距、首行缩进、粗体、主题。
- 实际字体行测量和文字锚点；不是固定字数分页或整章一页。
- 大书文件流导入、正文按章存储、按章读取。TXT 输入上限512MiB，EPUB输入上限1GiB；这些数值是校验上限，不是真机跑满的承诺。
- 兼容旧索引/正文的渐进迁移；保留已修好的 POSIX 存储和 lipo -archs 构建链。

详细范围与限制见 [升级说明](<UPGRADE-v0.2.md>)、[验证记录](<VALIDATION.md>)。

## GitHub Actions

已有工程：把下载的 `LeafReader-v0.2-upgrade.py` 放到仓库根目录，把 `upgrade-v02.yml` 放到 `.github/workflows/`，手动运行 **Build LeafReader v0.2**。升级器明文可审阅、标准库、自包含；备份被覆盖的源码，不读取凭据，不自动提交或推送。

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

本轮执行器启动 bash/ripgrep 失败，因此本地未执行新版本编译、测试、打包或安装。新增测试源码和 CI 门禁已提供。v0.1 的19项通过测试不是 v0.2 的通过证明。首轮 Actions 日志与 iOS16 真机行为才是下一步验收依据。

## 许可

本项目为独立实现，未复制 Legado 代码。源码使用 [MIT](<LICENSE>)，依赖保持各自许可，见 [第三方说明](<THIRD_PARTY_NOTICES.md>)。
