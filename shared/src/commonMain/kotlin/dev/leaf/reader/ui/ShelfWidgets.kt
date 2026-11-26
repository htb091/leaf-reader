package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
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

/** Segmented choice with a visible caption, using the contour Miuix tab row. */
@Composable
internal fun ShelfChoice(label: String, options: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, style = MiuixTheme.textStyles.body1)
        TabRowWithContour(
            tabs = options,
            selectedTabIndex = selected.coerceIn(0, options.lastIndex.coerceAtLeast(0)),
            onTabSelected = onSelect,
            modifier = Modifier.fillMaxWidth(),
            minWidth = 56.dp,
            height = 44.dp,
        )
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
