package dev.leaf.reader.ui

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
