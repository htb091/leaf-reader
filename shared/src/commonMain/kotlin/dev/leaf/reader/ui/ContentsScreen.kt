package dev.leaf.reader.ui

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
                        verticalArrangement = Arrangement.spacedBy(4.dp)) {
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
        .clickable(role = Role.Button, onClick = onClick).heightIn(min = 56.dp).padding(12.dp)
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
        .clickable(role = Role.Button, onClick = onClick).heightIn(min = if (dense) 48.dp else 60.dp)
        .padding(horizontal = 12.dp, vertical = 8.dp)
        .semantics { if (current) stateDescription = "当前章节"; contentDescription = "第 ${index + 1} 项，$title" },
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Text((index + 1).toString(), Modifier.widthIn(min = 28.dp), fontSize = 12.sp,
            color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
        Text(title, Modifier.weight(1f), fontSize = 15.sp,
            fontWeight = if (current) FontWeight.SemiBold else FontWeight.Normal,
            maxLines = 2, overflow = TextOverflow.Ellipsis,
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
