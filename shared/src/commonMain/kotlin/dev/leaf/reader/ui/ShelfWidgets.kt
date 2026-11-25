package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.*
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.ShelfBook
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.theme.MiuixTheme

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

@Composable
internal fun ContinueReadingHero(book: ShelfBook, enabled: Boolean, onOpen: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.defaultColors(
            color = MiuixTheme.colorScheme.primary.copy(alpha = 0.10f),
            contentColor = MiuixTheme.colorScheme.onSurface,
        ),
    ) {
        BasicComponent(
            title = "接着上次读",
            summary = "你的故事，还在这里",
            startAction = { BookCover(book, Modifier.width(64.dp).height(88.dp), small = true) },
            insideMargin = PaddingValues(18.dp),
        )
        Column(Modifier.fillMaxWidth().padding(start = 18.dp, end = 18.dp, bottom = 18.dp)) {
            Text(book.title, fontSize = 24.sp, fontWeight = FontWeight.SemiBold,
                maxLines = 2, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.semantics { heading() })
            ShelfMuted("${book.author.ifBlank { "佚名" }} · ${readingLabel(book)}",
                Modifier.padding(top = 6.dp, bottom = 12.dp))
            LinearProgressIndicator(
                progress = shelfPercent(book) / 100f, height = 4.dp,
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = readingLabel(book) },
            )
            TextButton("继续阅读", onOpen,
                modifier = Modifier.fillMaxWidth().padding(top = 16.dp).semantics {
                    contentDescription = "继续阅读《${book.title}》"
                },
                enabled = enabled, minHeight = 48.dp, colors = ButtonDefaults.textButtonColorsPrimary())
        }
    }
}

@Composable
internal fun ShelfCoverTile(book: ShelfBook, enabled: Boolean, onOpen: () -> Unit, onDelete: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth(), insideMargin = PaddingValues(12.dp)) {
        // The cover and title are one accessible reading target. Delete is a separate explicit action.
        BasicComponent(
            modifier = Modifier.semantics { stateDescription = readingLabel(book) },
            insideMargin = PaddingValues(0.dp), onClick = onOpen,
            onClickLabel = "阅读《${book.title}》", role = Role.Button, enabled = enabled,
        ) {
            BookCover(book, Modifier.fillMaxWidth().aspectRatio(0.74f))
            Text(book.title, fontSize = 17.sp, fontWeight = FontWeight.Medium,
                maxLines = 2, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).padding(top = 10.dp))
            ShelfMuted(book.author.ifBlank { "佚名" }, maxLines = 1)
            ShelfMuted("${book.chapterCount} 章 · ${lengthLabel(book)}", Modifier.padding(top = 4.dp), maxLines = 1)
        }
        Row(Modifier.fillMaxWidth().padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            ShelfMuted(if (book.lastOpenedAt > 0) "${shelfPercent(book)}%" else "未读", Modifier.weight(1f), maxLines = 1)
            ShelfRemoveAction(book, enabled, onDelete)
        }
    }
}

@Composable
internal fun ShelfListRow(
    book: ShelfBook, enabled: Boolean, compact: Boolean, onOpen: () -> Unit, onDelete: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        BasicComponent(
            modifier = Modifier.semantics { stateDescription = readingLabel(book) },
            onClick = onOpen, onClickLabel = "阅读《${book.title}》", role = Role.Button, enabled = enabled,
            insideMargin = PaddingValues(horizontal = 16.dp, vertical = if (compact) 8.dp else 16.dp),
            startAction = {
                if (compact) {
                    Box(Modifier.width(4.dp).height(38.dp)
                        .background(MiuixTheme.colorScheme.primary.copy(alpha = 0.55f), RoundedCornerShape(2.dp)))
                } else {
                    BookCover(book, Modifier.width(62.dp).height(88.dp), small = true)
                }
            },
            endActions = { ShelfRemoveAction(book, enabled, onDelete) },
        ) {
            Text(book.title, fontSize = if (compact) 16.sp else 19.sp,
                fontWeight = FontWeight.Medium, maxLines = if (compact) 1 else 2, overflow = TextOverflow.Ellipsis)
            ShelfMuted(
                if (compact) "${book.author.ifBlank { "佚名" }} · ${readingLabel(book)}"
                else "${book.author.ifBlank { "佚名" }} · ${book.format}",
                Modifier.padding(top = 4.dp), maxLines = 1,
            )
            if (!compact) {
                ShelfMuted("${book.chapterCount} 章 · ${lengthLabel(book)} · ${readingLabel(book)}",
                    Modifier.padding(top = 4.dp), maxLines = 2)
            }
        }
        if (!compact && book.lastOpenedAt > 0) {
            LinearProgressIndicator(progress = shelfPercent(book) / 100f, height = 3.dp,
                modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, bottom = 12.dp))
        }
    }
}

@Composable
private fun ShelfRemoveAction(book: ShelfBook, enabled: Boolean, onDelete: () -> Unit) {
    TextButton("移除", onDelete, enabled = enabled, minHeight = 48.dp, minWidth = 48.dp,
        insideMargin = PaddingValues(horizontal = 10.dp, vertical = 10.dp),
        colors = ButtonDefaults.textButtonColors(color = Color.Transparent),
        modifier = Modifier.semantics { contentDescription = "移除《${book.title}》，打开确认" })
}

/** Typographic covers are generated locally; they do not pretend to be fetched cover artwork. */
@Composable
private fun BookCover(book: ShelfBook, modifier: Modifier, small: Boolean = false) {
    val palette = listOf(
        Color(0xFF355E50), Color(0xFF465B73), Color(0xFF745749),
        Color(0xFF635774), Color(0xFF61613F), Color(0xFF6E4C58),
    )
    val color = palette[(book.id.hashCode() and Int.MAX_VALUE) % palette.size]
    Box(
        modifier = modifier.clip(RoundedCornerShape(10.dp))
            .background(Brush.linearGradient(listOf(color, color.copy(alpha = 0.78f))))
            .clearAndSetSemantics { },
    ) {
        Box(Modifier.fillMaxHeight().width(if (small) 5.dp else 8.dp).background(Color.Black.copy(alpha = 0.12f)))
        Column(
            Modifier.fillMaxSize().padding(if (small) 9.dp else 16.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(book.format, fontSize = if (small) 8.sp else 10.sp,
                color = Color.White.copy(alpha = 0.72f), letterSpacing = 1.sp)
            Text(if (small) book.title.take(4) else book.title,
                fontSize = if (small) 17.sp else 24.sp, lineHeight = if (small) 22.sp else 32.sp,
                color = Color.White, fontWeight = FontWeight.SemiBold,
                maxLines = if (small) 2 else 4, overflow = TextOverflow.Ellipsis)
            if (!small) Text(book.author.ifBlank { "叶读 · 本地藏书" }, fontSize = 10.sp,
                color = Color.White.copy(alpha = 0.8f), maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
internal fun ShelfMuted(text: String, modifier: Modifier = Modifier, maxLines: Int = Int.MAX_VALUE) {
    Text(text, modifier = modifier, fontSize = 13.sp, lineHeight = 20.sp,
        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.65f),
        maxLines = maxLines, overflow = TextOverflow.Ellipsis)
}

@Composable
internal fun ShelfSettingGroup(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, fontSize = 14.sp, color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.65f),
            modifier = Modifier.padding(start = 16.dp).semantics { heading() })
        Card(modifier = Modifier.fillMaxWidth(), content = content)
    }
}

@Composable
internal fun ShelfSwitchSetting(title: String, summary: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    BasicComponent(
        title = title, summary = summary,
        endActions = {
            Switch(checked = checked, onCheckedChange = onChange,
                modifier = Modifier.heightIn(min = 48.dp).semantics { contentDescription = title })
        },
    )
}
