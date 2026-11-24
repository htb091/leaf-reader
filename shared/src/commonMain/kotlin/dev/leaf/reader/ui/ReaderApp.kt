package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.theme.darkColorScheme
import top.yukonga.miuix.kmp.theme.lightColorScheme

/** Shared iOS / desktop entry. File selection belongs to the host. */
@Composable
fun ReaderApp(store: ReaderStore, onImportRequested: () -> Unit) {
    val state by store.state.collectAsState()
    val dark = state.settings.theme == ReaderTheme.DARK ||
        (state.settings.theme == ReaderTheme.SYSTEM && isSystemInDarkTheme())
    val sepia = state.settings.theme == ReaderTheme.SEPIA
    val colors = when {
        dark -> darkColorScheme(primary = Color(0xFF9BD0B5), onPrimary = Color(0xFF15392B))
        sepia -> lightColorScheme(
            primary = Color(0xFF706044), surface = Color(0xFFF3ECD9),
            surfaceContainer = Color(0xFFFBF5E7), onSurface = Color(0xFF473E30),
            onBackground = Color(0xFF473E30), onSurfaceContainer = Color(0xFF473E30),
        )
        else -> lightColorScheme(primary = Color(0xFF28634B), surface = Color(0xFFF3F6F3))
    }
    MiuixTheme(colors = colors) {
        Scaffold { insets ->
            Box(Modifier.fillMaxSize().padding(insets).consumeWindowInsets(insets)) {
                val book = state.currentBook
                if (book == null) {
                    ShelfScreen(state, store, onImportRequested)
                } else {
                    key(book.id) { ReadingScreen(book, state.currentProgress, state.settings, state.busy, store) }
                }
                if (state.busy) {
                    Box(
                        Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.25f))
                            .pointerInput(Unit) {
                                awaitPointerEventScope {
                                    while (true) awaitPointerEvent().changes.forEach { it.consume() }
                                }
                            },
                        contentAlignment = Alignment.Center,
                    ) {
                        Card(insideMargin = PaddingValues(28.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                                CircularProgressIndicator(size = 26.dp)
                                Text("正在整理书页…", modifier = Modifier.semantics {
                                    liveRegion = LiveRegionMode.Polite
                                })
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
                    PrimaryAction("知道了", store::dismissError, Modifier.fillMaxWidth())
                }
            }
        }
    }
}

@Composable
private fun ShelfScreen(state: LibraryState, store: ReaderStore, onImportRequested: () -> Unit) {
    var query by remember { mutableStateOf("") }
    var deleting by remember { mutableStateOf<ShelfBook?>(null) }
    val books = remember(state.books, query) {
        val keyword = query.trim()
        state.books.filter { it.title.contains(keyword, true) || it.author.contains(keyword, true) }
            .sortedByDescending { maxOf(it.lastOpenedAt, it.addedAt) }
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(22.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("叶读", fontSize = 34.sp, fontWeight = FontWeight.Bold,
                        modifier = Modifier.semantics { heading() })
                    MutedText("把片刻，留给阅读", Modifier.padding(top = 4.dp))
                }
                PrimaryAction("导入书籍", onImportRequested, enabled = !state.busy)
            }
        }
        item {
            BasicTextField(
                value = query,
                onValueChange = { query = it },
                singleLine = true,
                textStyle = TextStyle(color = MiuixTheme.colorScheme.onSurface, fontSize = 16.sp),
                cursorBrush = SolidColor(MiuixTheme.colorScheme.primary),
                modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)
                    .background(MiuixTheme.colorScheme.surfaceContainer, RoundedCornerShape(18.dp))
                    .padding(horizontal = 18.dp, vertical = 16.dp)
                    .semantics { contentDescription = "搜索书名或作者" },
                decorationBox = { input ->
                    Box {
                        if (query.isEmpty()) MutedText("搜索书名或作者")
                        input()
                    }
                },
            )
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(if (query.isBlank()) "我的书架" else "搜索结果", fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.semantics { heading() })
                MutedText("${books.size} 本")
            }
        }
        if (books.isEmpty()) {
            item {
                Card(Modifier.fillMaxWidth(), insideMargin = PaddingValues(26.dp)) {
                    Text(if (query.isBlank()) "让第一本书，住进来" else "还没有找到这本书",
                        fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
                    MutedText(
                        if (query.isBlank()) "导入本地 TXT 或 EPUB，随时接着上次的位置读。"
                        else "试试其他书名、作者，或清空搜索。",
                        Modifier.padding(top = 12.dp, bottom = 20.dp),
                    )
                    if (query.isBlank()) PrimaryAction("选择本地书籍", onImportRequested, enabled = !state.busy)
                    else TextButton("清空搜索", { query = "" }, minHeight = 48.dp)
                }
            }
        }
        items(books, key = { it.id }) { book ->
            ShelfCard(book, !state.busy, { store.openBook(book.id) }, { deleting = book })
        }
        item {
            MutedText(
                "只属于你的本地书架\n支持 TXT 与基础 EPUB 纯文本。EPUB 图片、CSS 排版、脚本、固定版式及 DRM 内容暂不支持。",
                Modifier.padding(vertical = 10.dp),
            )
        }
    }
    OverlayDialog(
        show = deleting != null,
        title = "移出书架？",
        summary = "将移除《${deleting?.title.orEmpty()}》及其阅读进度，原始文件保留。",
        onDismissRequest = { deleting = null },
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            TextButton("保留", { deleting = null }, Modifier.weight(1f), minHeight = 48.dp)
            TextButton("移除书籍", {
                deleting?.let { store.deleteBook(it.id) }
                deleting = null
            }, Modifier.weight(1f), minHeight = 48.dp,
                colors = ButtonDefaults.textButtonColorsPrimary(color = MiuixTheme.colorScheme.error))
        }
    }
}

@Composable
private fun ShelfCard(book: ShelfBook, enabled: Boolean, onOpen: () -> Unit, onDelete: () -> Unit) {
    val lastIndex = (book.chapterCount + book.paragraphCount - 1).coerceAtLeast(1)
    val percent = ((book.progress.itemIndex.toLong() * 100) / lastIndex).coerceIn(0, 100).toInt()
    Card(Modifier.fillMaxWidth(), insideMargin = PaddingValues(18.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Box(
                Modifier.width(62.dp).height(84.dp)
                    .background(MiuixTheme.colorScheme.primary.copy(alpha = 0.12f), RoundedCornerShape(9.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text(book.title.take(1).ifBlank { "书" }, fontSize = 30.sp,
                    color = MiuixTheme.colorScheme.primary, fontWeight = FontWeight.SemiBold)
            }
            Column(Modifier.weight(1f)) {
                Text(book.title, fontSize = 20.sp, fontWeight = FontWeight.SemiBold,
                    maxLines = 2, overflow = TextOverflow.Ellipsis)
                MutedText(book.author.ifBlank { "佚名" }, Modifier.padding(top = 5.dp), maxLines = 1)
                MutedText("${book.format} · ${book.chapterCount} 章 · ${book.paragraphCount} 段",
                    Modifier.padding(top = 6.dp))
            }
        }
        Row(Modifier.fillMaxWidth().padding(top = 16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(if (book.lastOpenedAt > 0) "上次读到 $percent%" else "尚未开始",
                    fontSize = 13.sp, color = MiuixTheme.colorScheme.primary)
                ProgressTrack(percent / 100f, Modifier.fillMaxWidth().padding(top = 7.dp, end = 16.dp))
            }
            TextButton("移除", onDelete, enabled = enabled, minHeight = 48.dp,
                modifier = Modifier.semantics { contentDescription = "移除《${book.title}》" })
            Spacer(Modifier.width(8.dp))
            TextButton(if (book.lastOpenedAt > 0) "继续读" else "开始读", onOpen,
                enabled = enabled, minHeight = 48.dp,
                colors = ButtonDefaults.textButtonColorsPrimary(),
                modifier = Modifier.semantics { contentDescription = "阅读《${book.title}》" })
        }
    }
}

@Composable
internal fun PrimaryAction(
    label: String, action: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true,
) = TextButton(label, action, modifier, enabled = enabled, minHeight = 48.dp,
    colors = ButtonDefaults.textButtonColorsPrimary())

@Composable
internal fun MutedText(text: String, modifier: Modifier = Modifier, maxLines: Int = Int.MAX_VALUE) = Text(
    text, modifier, fontSize = 13.sp, lineHeight = 20.sp, maxLines = maxLines,
    overflow = TextOverflow.Ellipsis,
    color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
)

@Composable
internal fun ProgressTrack(progress: Float, modifier: Modifier = Modifier) {
    LinearProgressIndicator(modifier = modifier, progress = progress, height = 3.dp)
}
