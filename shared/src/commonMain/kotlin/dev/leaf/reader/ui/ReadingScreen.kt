package dev.leaf.reader.ui

import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import top.yukonga.miuix.kmp.basic.ButtonDefaults
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.basic.TextButton
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme

internal data class ReadingItem(val text: String, val chapterIndex: Int, val isHeading: Boolean)

/** The persisted index is exactly: chapter heading, then each paragraph, in spine order. */
internal fun readingItems(book: BookDocument): List<ReadingItem> = buildList {
    book.chapters.forEachIndexed { index, chapter ->
        add(ReadingItem(chapter.title.ifBlank { "第 ${index + 1} 章" }, index, true))
        chapter.paragraphs.forEach { add(ReadingItem(it, index, false)) }
    }
}

@Composable
internal fun ReadingScreen(
    book: BookDocument,
    initialProgress: ReadingProgress,
    settings: ReaderSettings,
    isLoading: Boolean,
    store: ReaderStore,
) {
    val items = remember(book) { readingItems(book) }
    val restored = remember {
        ReadingProgress(initialProgress.itemIndex.coerceIn(0, (items.size - 1).coerceAtLeast(0)),
            initialProgress.scrollOffset.coerceAtLeast(0))
    }
    val list = rememberLazyListState(restored.itemIndex, restored.scrollOffset)
    val scope = rememberCoroutineScope()
    var directory by remember { mutableStateOf(false) }
    var typography by remember { mutableStateOf(false) }
    var ready by remember { mutableStateOf(false) }
    var hasRestored by remember { mutableStateOf(false) }
    var stable by remember { mutableStateOf(restored) }
    val metrics = settings.fontSize to settings.lineHeight
    var appliedMetrics by remember { mutableStateOf<Pair<Float, Float>?>(null) }

    // Never persist default/unmeasured positions. A metrics change keeps the paragraph,
    // discards its old pixel offset, and re-enables saving only after the new layout settles.
    LaunchedEffect(metrics) {
        ready = false
        if (items.isEmpty()) return@LaunchedEffect
        snapshotFlow { list.layoutInfo.totalItemsCount }.first { it == items.size }
        val target = if (hasRestored) stable.copy(scrollOffset = 0) else restored
        list.scrollToItem(target.itemIndex, target.scrollOffset)
        withFrameNanos { }
        stable = ReadingProgress(list.firstVisibleItemIndex, list.firstVisibleItemScrollOffset)
        hasRestored = true
        appliedMetrics = metrics
        ready = true
    }
    LaunchedEffect(metrics, isLoading) {
        snapshotFlow {
            if (ready && appliedMetrics == metrics && !isLoading)
                ReadingProgress(list.firstVisibleItemIndex, list.firstVisibleItemScrollOffset)
            else null
        }.filterNotNull().distinctUntilChanged().collect { position ->
            stable = position
            val live = store.state.value
            if (live.currentBook?.id == book.id && !live.busy) {
                store.updateProgress(position.itemIndex, position.scrollOffset)
            }
        }
    }
    val close: () -> Unit = {
        val live = store.state.value
        if (live.currentBook?.id == book.id) {
            if (ready && appliedMetrics == metrics && !live.busy) {
                store.updateProgress(list.firstVisibleItemIndex, list.firstVisibleItemScrollOffset)
            }
            ready = false
            store.closeBook()
        }
    }
    val changeMetrics: (ReaderSettings) -> Unit = { next ->
        stable = ReadingProgress(list.firstVisibleItemIndex, 0)
        ready = false
        store.updateSettings(next)
    }
    val index by remember { derivedStateOf { list.firstVisibleItemIndex.coerceIn(0, (items.size - 1).coerceAtLeast(0)) } }
    val chapterIndex = items.getOrNull(index)?.chapterIndex ?: 0
    val percent = if (items.size <= 1) 0 else ((index.toLong() * 100) / (items.size - 1)).toInt()
    val chapterStarts = remember(book) {
        var start = 0
        book.chapters.map { chapter -> start.also { start += chapter.paragraphs.size + 1 } }
    }

    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            TextButton("书架", close, minHeight = 48.dp,
                modifier = Modifier.semantics { contentDescription = "保存进度并返回书架" })
            Text(book.title, Modifier.weight(1f), fontSize = 15.sp,
                maxLines = 1, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.SemiBold)
            TextButton("目录", { directory = true }, enabled = ready && items.isNotEmpty(), minHeight = 48.dp)
            TextButton("排版", { typography = true }, minHeight = 48.dp)
        }
        if (items.isEmpty()) {
            Box(Modifier.weight(1f).fillMaxWidth().padding(28.dp), contentAlignment = Alignment.Center) {
                Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    Text("这本书暂时没有可读正文", fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
                    MutedText("EPUB 仅提取基础文本；图片、固定版式与加密内容不属于本版支持范围。")
                    PrimaryAction("返回书架", close)
                }
            }
        } else {
            Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.TopCenter) {
                LazyColumn(
                    state = list,
                    userScrollEnabled = ready && !isLoading,
                    modifier = Modifier.widthIn(max = 760.dp).fillMaxSize(),
                    contentPadding = PaddingValues(start = 26.dp, end = 26.dp, top = 22.dp, bottom = 60.dp),
                ) {
                    itemsIndexed(items, key = { itemIndex, _ -> itemIndex },
                        contentType = { _, item -> item.isHeading }) { _, item ->
                        if (item.isHeading) {
                            Column(Modifier.padding(top = 18.dp, bottom = 30.dp)) {
                                Text("${(item.chapterIndex + 1).toString().padStart(2, '0')} / ${book.chapters.size}",
                                    fontSize = 12.sp, color = MiuixTheme.colorScheme.primary,
                                    letterSpacing = 2.sp)
                                Text(item.text, fontSize = (settings.fontSize + 7).sp,
                                    lineHeight = ((settings.fontSize + 7) * 1.45f).sp,
                                    fontWeight = FontWeight.SemiBold,
                                    modifier = Modifier.padding(top = 12.dp).semantics { heading() })
                            }
                        } else {
                            Text(item.text,
                                modifier = Modifier.fillMaxWidth().padding(bottom = 18.dp),
                                fontSize = settings.fontSize.sp,
                                lineHeight = (settings.fontSize * settings.lineHeight).sp,
                                color = MiuixTheme.colorScheme.onSurface)
                        }
                    }
                }
            }
        }
        Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 12.dp)) {
            ProgressTrack(percent / 100f, Modifier.fillMaxWidth())
            Row(Modifier.fillMaxWidth().padding(top = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                MutedText(book.chapters.getOrNull(chapterIndex)?.title?.ifBlank { "正文" } ?: "正文",
                    Modifier.weight(1f), maxLines = 1)
                MutedText("$percent%",  Modifier.semantics { stateDescription = "阅读进度百分之$percent" })
            }
        }
    }
    OverlayDialog(show = directory, title = "目录", summary = "${book.chapters.size} 章 · 点击跳转",
        onDismissRequest = { directory = false }) {
        Column {
            val directoryList = rememberLazyListState(chapterIndex)
            LazyColumn(Modifier.fillMaxWidth().heightIn(max = 360.dp).weight(1f, fill = false), state = directoryList,
                verticalArrangement = Arrangement.spacedBy(6.dp)) {
                itemsIndexed(book.chapters) { number, chapter ->
                    TextButton(
                        "${number + 1}  ${chapter.title.ifBlank { "正文" }}",
                        {
                            directory = false
                            ready = false
                            scope.launch {
                                list.scrollToItem(chapterStarts[number])
                                withFrameNanos { }
                                stable = ReadingProgress(list.firstVisibleItemIndex, list.firstVisibleItemScrollOffset)
                                ready = true
                            }
                        }, Modifier.fillMaxWidth(), minHeight = 48.dp,
                        colors = if (number == chapterIndex) ButtonDefaults.textButtonColorsPrimary()
                            else ButtonDefaults.textButtonColors(),
                    )
                }
            }
            TextButton("关闭目录", { directory = false }, Modifier.fillMaxWidth().padding(top = 12.dp), minHeight = 48.dp)
        }
    }
    OverlayDialog(show = typography, title = "阅读排版", onDismissRequest = { typography = false }) {
        Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(18.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("字号 ${settings.fontSize.toInt()}", Modifier.weight(1f))
                TextButton("减小", { changeMetrics(settings.copy(fontSize = (settings.fontSize - 1).coerceAtLeast(14f))) },
                    enabled = ready && settings.fontSize > 14f, minHeight = 48.dp,
                    modifier = Modifier.semantics { contentDescription = "减小正文字号" })
                TextButton("增大", { changeMetrics(settings.copy(fontSize = (settings.fontSize + 1).coerceAtMost(32f))) },
                    enabled = ready && settings.fontSize < 32f, minHeight = 48.dp,
                    modifier = Modifier.semantics { contentDescription = "增大正文字号" })
            }
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("行距", Modifier.weight(1f))
                TextButton("紧凑", { changeMetrics(settings.copy(lineHeight = 1.5f)) },
                    enabled = ready && settings.lineHeight != 1.5f, minHeight = 48.dp)
                TextButton("舒展", { changeMetrics(settings.copy(lineHeight = 1.9f)) },
                    enabled = ready && settings.lineHeight != 1.9f, minHeight = 48.dp)
            }
            Text("阅读主题", fontWeight = FontWeight.SemiBold)
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf(ReaderTheme.SYSTEM to "跟随系统", ReaderTheme.LIGHT to "明亮",
                    ReaderTheme.SEPIA to "纸色", ReaderTheme.DARK to "深色").chunked(2).forEach { pair ->
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        pair.forEach { (theme, label) ->
                            TextButton(label, { store.updateSettings(settings.copy(theme = theme)) },
                                Modifier.weight(1f).semantics { stateDescription = if (settings.theme == theme) "已选中" else "未选中" },
                                minHeight = 48.dp,
                                colors = if (settings.theme == theme) ButtonDefaults.textButtonColorsPrimary()
                                    else ButtonDefaults.textButtonColors())
                        }
                    }
                }
            }
            MutedText("调整字号或行距后，保留当前段落，从段首继续阅读。")
            PrimaryAction("完成", { typography = false }, Modifier.fillMaxWidth())
        }
    }
}
