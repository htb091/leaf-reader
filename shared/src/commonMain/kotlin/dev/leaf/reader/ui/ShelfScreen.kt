package dev.leaf.reader.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.layout.*
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
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme

private enum class ShelfOrder(val label: String) {
    RECENT("最近阅读"), ADDED("最近导入"), TITLE("书名"), LENGTH("篇幅"),
}

/** Keeps the floating dock from covering the last row; >= 96dp by contract. */
private val ShelfDockClearance = 104.dp

/** Scroll distance over which the large title folds into the compact top bar. */
private val ShelfCollapseDistance = 72.dp

@Composable
internal fun ShelfScreen(state: LibraryState, store: ReaderStore, onImportRequested: () -> Unit) {
    var panel by rememberSaveable { mutableIntStateOf(0) }
    var query by rememberSaveable { mutableStateOf("") }
    var searching by rememberSaveable { mutableStateOf(false) }
    var orderIndex by rememberSaveable { mutableIntStateOf(0) }
    var deleting by remember { mutableStateOf<ShelfBook?>(null) }
    var headerHeightPx by remember { mutableIntStateOf(0) }
    val gridState = rememberLazyGridState()
    val settingsState = rememberLazyListState()
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
                it.author.contains(keyword, ignoreCase = true)
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
    val contentTopPadding = with(density) { headerHeightPx.toDp() } + 10.dp
    val shelfMode = panel == 0

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MiuixTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets.systemBars.union(WindowInsets.displayCutout),
        floatingToolbarPosition = ToolbarPosition.BottomCenter,
        floatingToolbar = {
            ShelfDock(panel) { next ->
                panel = next
                searching = false
                focusManager.clearFocus()
            }
        },
    ) { insets ->
        Box(Modifier.fillMaxSize().padding(insets).consumeWindowInsets(insets)) {
            if (shelfMode) {
                ShelfGridPane(
                    books = books,
                    continuing = continuing,
                    layout = layout,
                    order = order,
                    query = query,
                    enabled = enabled,
                    topPadding = contentTopPadding,
                    state = gridState,
                    onOpen = { store.openBook(it.id) },
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
            ShelfHeader(
                compactTitle = if (shelfMode) "书架" else "设置",
                largeTitle = if (shelfMode) "书架" else "设置",
                detail = if (shelfMode) "共 ${state.books.size} 本本地书籍" else "你的书架，你的阅读习惯",
                showActions = shelfMode,
                searching = searching,
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

/** Floating dock: Miuix Scaffold placement + FloatingToolbar pill with two dock tabs. */
@Composable
private fun ShelfDock(panel: Int, onSelect: (Int) -> Unit) {
    FloatingToolbar(
        color = MiuixTheme.colorScheme.surfaceContainerHigh,
        cornerRadius = 999.dp,
        outSidePadding = PaddingValues(horizontal = PageMargin, vertical = 12.dp),
        shadowElevation = 8.dp,
        showDivider = true,
    ) {
        MiuixDockPill {
            DockTab(Glyph.SHELVES, "书架", selected = panel == 0, onClick = { onSelect(0) })
            DockTab(Glyph.GEAR, "设置", selected = panel == 1, onClick = { onSelect(1) })
        }
    }
}

/**
 * Collapsing header laid over the list: gradient scrim (no divider), compact title fading in
 * while the large title scales and fades out, then the search row that expands underneath.
 */
@Composable
private fun ShelfHeader(
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
    GradientHeaderScrim {
        Column(Modifier.fillMaxWidth()) {
            Column(Modifier.fillMaxWidth().onSizeChanged { onHeaderHeight(it.height) }) {
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
        InputField(
            query = query,
            onQueryChange = onQueryChange,
            onSearch = { focusManager.clearFocus() },
            expanded = true,
            onExpandedChange = { },
            modifier = Modifier.weight(1f),
            label = "搜索书名或作者",
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
    onOpen: (ShelfBook) -> Unit,
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
                    ContinueReadingHero(hero, enabled) { onOpen(hero) }
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
                    ShelfEmptyCard(query.isBlank(), enabled, onImport, onClearSearch)
                }
            }
            items(books, key = { it.id }, contentType = { layout }) { book ->
                when (layout) {
                    ShelfLayout.GRID -> ShelfCoverTile(book, enabled, { onOpen(book) }, { onDelete(book) })
                    ShelfLayout.LIST -> ShelfListRow(book, enabled, false, { onOpen(book) }, { onDelete(book) })
                    ShelfLayout.COMPACT -> ShelfListRow(book, enabled, true, { onOpen(book) }, { onDelete(book) })
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
