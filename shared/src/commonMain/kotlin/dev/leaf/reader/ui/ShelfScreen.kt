package dev.leaf.reader.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme

private enum class ShelfOrder(val label: String) {
    RECENT("最近阅读"), ADDED("最近导入"), TITLE("书名"), LENGTH("篇幅"),
}

/** Real shelf layouts share the same data and persistence path; no screenshot-only presets. */
@Composable
internal fun ShelfScreen(state: LibraryState, store: ReaderStore, onImportRequested: () -> Unit) {
    var panel by rememberSaveable { mutableIntStateOf(0) }
    var query by rememberSaveable { mutableStateOf("") }
    var searching by rememberSaveable { mutableStateOf(false) }
    var orderIndex by rememberSaveable { mutableIntStateOf(0) }
    var deleting by remember { mutableStateOf<ShelfBook?>(null) }
    val focusManager = LocalFocusManager.current
    val behavior = MiuixScrollBehavior()
    val gridState = rememberLazyGridState()
    val enabled = !state.busy
    val layout = state.settings.shelfLayout
    val order = ShelfOrder.entries[orderIndex]
    val books = remember(state.books, query, order) {
        val keyword = query.trim()
        val filtered = state.books.filter {
            it.title.contains(keyword, ignoreCase = true) || it.author.contains(keyword, ignoreCase = true)
        }
        when (order) {
            ShelfOrder.RECENT -> filtered.sortedWith(
                compareByDescending<ShelfBook> { it.lastOpenedAt }.thenByDescending { it.addedAt }.thenBy { it.id },
            )
            ShelfOrder.ADDED -> filtered.sortedWith(compareByDescending<ShelfBook> { it.addedAt }.thenBy { it.id })
            ShelfOrder.TITLE -> filtered.sortedWith(compareBy<ShelfBook> { it.title.lowercase() }.thenBy { it.id })
            ShelfOrder.LENGTH -> filtered.sortedWith(
                compareByDescending<ShelfBook> { it.characterCount }.thenByDescending { it.paragraphCount }.thenBy { it.id },
            )
        }
    }
    val continuing = remember(state.books) {
        state.books.filter { it.lastOpenedAt > 0 }.maxByOrNull { it.lastOpenedAt }
    }
    Scaffold(
        modifier = Modifier.fillMaxSize().nestedScroll(behavior.nestedScrollConnection),
        topBar = {
            TopAppBar(
                title = if (panel == 0) "书架" else "设置",
                largeTitle = if (panel == 0) "叶读" else "阅读，随你",
                subtitle = if (panel == 0) "${state.books.size} 本藏书 · 把片刻留给阅读" else "你的书架，你的阅读习惯",
                scrollBehavior = behavior,
                actions = {
                    TextButton("导入", onImportRequested, enabled = enabled, minHeight = 48.dp,
                        colors = ButtonDefaults.textButtonColorsPrimary(),
                        modifier = Modifier.semantics { contentDescription = "导入本地 TXT 或 EPUB 书籍" })
                },
                bottomContent = {
                    Column(Modifier.fillMaxWidth().padding(bottom = 12.dp)) {
                        TabRowWithContour(
                            tabs = listOf("书架", "设置"), selectedTabIndex = panel,
                            onTabSelected = {
                                panel = it
                                focusManager.clearFocus()
                                searching = false
                            },
                            modifier = Modifier.padding(horizontal = 24.dp), height = 48.dp,
                        )
                        if (panel == 0) {
                            SearchBar(
                                modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 12.dp),
                                expanded = searching,
                                onExpandedChange = { searching = it },
                                outsideEndAction = {
                                    TextButton("取消", {
                                        query = ""
                                        searching = false
                                        focusManager.clearFocus()
                                    }, minHeight = 48.dp)
                                },
                                inputField = {
                                    InputField(
                                        query = query, onQueryChange = { query = it },
                                        onSearch = { focusManager.clearFocus() },
                                        expanded = searching, onExpandedChange = { searching = it },
                                        label = "搜索书名或作者",
                                        modifier = Modifier.semantics { contentDescription = "搜索书名或作者" },
                                        trailingIcon = {
                                            if (query.isNotEmpty()) {
                                                TextButton("清空", { query = "" }, minHeight = 48.dp,
                                                    insideMargin = PaddingValues(horizontal = 10.dp),
                                                    modifier = Modifier.semantics { contentDescription = "清空搜索" })
                                            }
                                        },
                                    )
                                },
                            ) { /* Results are in the lazy shelf, not an unbounded search popup. */ }
                        }
                    }
                },
            )
        },
    ) { insets ->
        if (panel == 1) {
            ShelfSettings(state, store, onImportRequested,
                Modifier.fillMaxSize().padding(insets).consumeWindowInsets(insets))
        } else {
            LazyVerticalGrid(
                columns = if (layout == ShelfLayout.GRID) GridCells.Adaptive(148.dp) else GridCells.Fixed(1),
                state = gridState,
                modifier = Modifier.fillMaxSize().padding(insets).consumeWindowInsets(insets).imePadding(),
                contentPadding = PaddingValues(start = 24.dp, end = 24.dp, top = 4.dp, bottom = 28.dp),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
                verticalArrangement = Arrangement.spacedBy(if (layout == ShelfLayout.COMPACT) 2.dp else 16.dp),
            ) {
                if (query.isBlank() && continuing != null) {
                    item(key = "continue", span = { GridItemSpan(maxLineSpan) }) {
                        ContinueReadingHero(continuing, enabled) { store.openBook(continuing.id) }
                    }
                }
                item(key = "organization", span = { GridItemSpan(maxLineSpan) }) {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Text(if (query.isBlank()) "我的藏书" else "搜索结果",
                                modifier = Modifier.weight(1f).semantics { heading() })
                            ShelfMuted("${books.size} 本", Modifier.semantics { liveRegion = LiveRegionMode.Polite })
                        }
                        TabRowWithContour(
                            tabs = listOf("封面", "列表", "紧凑"), selectedTabIndex = layout.ordinal,
                            onTabSelected = { store.updateSettings(state.settings.copy(shelfLayout = ShelfLayout.entries[it])) },
                            height = 48.dp, modifier = Modifier.semantics { contentDescription = "书架布局" },
                        )
                        TabRow(
                            tabs = ShelfOrder.entries.map { it.label }, selectedTabIndex = orderIndex,
                            onTabSelected = { orderIndex = it }, minWidth = 74.dp, height = 48.dp,
                            modifier = Modifier.semantics { contentDescription = "书架排序" },
                        )
                    }
                }
                if (books.isEmpty()) {
                    item(key = "empty", span = { GridItemSpan(maxLineSpan) }) {
                        Card {
                            BasicComponent(
                                title = if (query.isBlank()) "让第一本书，住进来" else "还没有找到这本书",
                                summary = if (query.isBlank()) "导入本地 TXT 或 EPUB，下次从上次的位置接着读。" else "换一个书名或作者试试。",
                                bottomAction = {
                                    TextButton(if (query.isBlank()) "选择本地书籍" else "清空搜索", {
                                        if (query.isBlank()) onImportRequested() else query = ""
                                    }, enabled = enabled, minHeight = 48.dp,
                                        modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.textButtonColorsPrimary())
                                },
                            )
                        }
                    }
                }
                items(books, key = { it.id }, contentType = { layout }) { book ->
                    when (layout) {
                        ShelfLayout.GRID -> ShelfCoverTile(book, enabled, { store.openBook(book.id) }, { deleting = book })
                        ShelfLayout.LIST -> ShelfListRow(book, enabled, false, { store.openBook(book.id) }, { deleting = book })
                        ShelfLayout.COMPACT -> ShelfListRow(book, enabled, true, { store.openBook(book.id) }, { deleting = book })
                    }
                }
                item(key = "local-note", span = { GridItemSpan(maxLineSpan) }) {
                    ShelfMuted("本地存储 · 无需联网阅读\nTXT / 基础 EPUB 纯文本；不还原 EPUB 图片、CSS、脚本、固定版式或 DRM 内容。",
                        Modifier.padding(top = 12.dp))
                }
            }
        }
        OverlayDialog(
            show = deleting != null, title = "移出书架？",
            summary = "将移除《${deleting?.title.orEmpty()}》及阅读进度，原始文件保留。",
            onDismissRequest = { deleting = null },
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                TextButton("保留", { deleting = null }, Modifier.weight(1f), minHeight = 48.dp)
                TextButton("移除书籍", {
                    deleting?.let { store.deleteBook(it.id) }
                    deleting = null
                }, Modifier.weight(1f), enabled = enabled, minHeight = 48.dp,
                    colors = ButtonDefaults.textButtonColorsPrimary(color = MiuixTheme.colorScheme.error))
            }
        }
    }
}

@Composable
private fun ShelfSettings(
    state: LibraryState, store: ReaderStore, onImportRequested: () -> Unit, modifier: Modifier,
) {
    val settings = state.settings
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(start = 24.dp, end = 24.dp, top = 4.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp),
    ) {
        item {
            ShelfSettingGroup("外观与书架") {
                BasicComponent(title = "书架布局", summary = "立即切换，重启后保留", bottomAction = {
                    TabRowWithContour(listOf("封面", "列表", "紧凑"), settings.shelfLayout.ordinal,
                        { store.updateSettings(settings.copy(shelfLayout = ShelfLayout.entries[it])) }, height = 48.dp)
                })
                BasicComponent(title = "主题", bottomAction = {
                    TabRowWithContour(listOf("跟随系统", "浅色", "深色", "纸色"), settings.theme.ordinal,
                        { store.updateSettings(settings.copy(theme = ReaderTheme.entries[it])) }, minWidth = 64.dp, height = 48.dp)
                })
            }
        }
        item {
            ShelfSettingGroup("默认阅读方式") {
                BasicComponent(title = "翻页方式", summary = "横向滑动、即时切页或上下滚动", bottomAction = {
                    TabRowWithContour(listOf("滚动", "滑动", "即时"), settings.readingMode.ordinal,
                        { store.updateSettings(settings.copy(readingMode = ReadingMode.entries[it])) }, height = 48.dp)
                })
                BasicComponent(title = "分栏", summary = "自动仅在宽屏采用双栏", bottomAction = {
                    TabRowWithContour(listOf("自动", "单栏", "双栏"), settings.columnMode.ordinal,
                        { store.updateSettings(settings.copy(columnMode = ColumnMode.entries[it])) }, height = 48.dp)
                })
                BasicComponent(title = "字体", bottomAction = {
                    TabRowWithContour(listOf("衬线", "无衬线", "等宽"), settings.fontFamily.ordinal,
                        { store.updateSettings(settings.copy(fontFamily = ReaderFont.entries[it])) }, height = 48.dp)
                })
                BasicComponent(title = "字号 · ${settings.fontSize.toInt()}", bottomAction = {
                    Slider(settings.fontSize, { store.updateSettings(settings.copy(fontSize = it)) },
                        valueRange = 14f..40f, steps = 25,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).semantics { contentDescription = "阅读字号" })
                })
            }
        }
        item {
            ShelfSettingGroup("沉浸阅读") {
                ShelfSwitchSetting("自动收起工具栏", "阅读时自动隐藏；轻点正文中央再次显示", settings.autoHideControls) {
                    store.updateSettings(settings.copy(autoHideControls = it))
                }
                ShelfSwitchSetting("阅读页脚", "显示当前章节与阅读进度", settings.showReadingFooter) {
                    store.updateSettings(settings.copy(showReadingFooter = it))
                }
                BasicComponent(title = "更多排版选项", summary = "在阅读页打开「设置」，调整行距、页边距、段距、首行缩进与字重。")
            }
        }
        item {
            ShelfSettingGroup("本地书库") {
                BasicComponent(title = "导入书籍", summary = "从「文件」选择 TXT 或 EPUB", onClick = onImportRequested,
                    onClickLabel = "选择本地书籍", enabled = !state.busy,
                    endActions = { Text("＋", color = MiuixTheme.colorScheme.primary) })
                BasicComponent(title = "${state.books.size} 本藏书", summary = "正文按章节存储，阅读按需加载；进度与偏好保存在本机。")
                BasicComponent(title = "格式兼容", summary = "支持 TXT 与基础 EPUB 纯文本。EPUB 图片、CSS 排版、脚本、固定版式与 DRM 内容不在当前纯文本引擎内。")
                BasicComponent(title = "移除与原文件", summary = "移除书籍前始终确认。只清理应用内副本和阅读进度，原始文件保留。")
            }
        }
    }
}
