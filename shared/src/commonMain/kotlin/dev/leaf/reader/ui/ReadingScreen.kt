package dev.leaf.reader.ui

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
import top.yukonga.miuix.kmp.overlay.OverlayBottomSheet
import top.yukonga.miuix.kmp.theme.MiuixTheme
import kotlin.math.abs
import kotlin.math.roundToInt

/** Only the loaded chapter is measured. currentBook contains chapter titles, never body text. */
@Composable
internal fun ReadingScreen(state: LibraryState, store: ReaderStore) {
    val book = state.currentBook ?: return
    val scope = rememberCoroutineScope()
    var directory by remember(book.id) { mutableStateOf(false) }
    var settingsOpen by remember(book.id) { mutableStateOf(false) }
    var showHint by remember(book.id) { mutableStateOf(true) }
    var interaction by remember { mutableIntStateOf(0) }
    var closing by remember(book.id) { mutableStateOf(false) }
    // One Animatable drives the page entrance: scale 0.94 -> 1 and alpha 0 -> 1.
    // Closing runs it back to 0 for 280ms before the shelf takes over.
    val entry = remember(book.id) { Animatable(0f) }
    LaunchedEffect(book.id) { entry.animateTo(1f, animationSpec = bookOpen()) }
    LaunchedEffect(book.id, state.chapter != null) {
        if (state.chapter != null) {
            delay(4500)
            showHint = false
        }
    }
    LaunchedEffect(state.chromeVisible, state.settings.autoHideControls, directory, settingsOpen, interaction, closing) {
        if (state.chromeVisible && state.settings.autoHideControls && !directory && !settingsOpen && !closing) {
            delay(5000)
            store.setChromeVisible(false)
        }
    }
    val leave: () -> Unit = {
        if (!closing) {
            closing = true
            store.setChromeVisible(false)
            scope.launch {
                entry.animateTo(0f, animationSpec = bookClose())
                store.closeBook()
            }
        }
    }
    BoxWithConstraints(Modifier.fillMaxSize().background(MiuixTheme.colorScheme.surface)) {
        // Sheets never exceed a share of the real window height, so 16:9 phones keep the list scrollable.
        val tocMaxHeight = maxHeight * 0.72f
        val settingsMaxHeight = maxHeight * 0.82f
        Box(
            Modifier.fillMaxSize().graphicsLayer {
                val progress = entry.value
                val scale = 0.94f + 0.06f * progress
                scaleX = scale
                scaleY = scale
                alpha = progress
            },
        ) {
            val chapter = state.chapter
            if (chapter != null && !state.chapterBusy) {
                key(book.id, state.chapterIndex, chapter) {
                    ChapterReader(state, chapter, store, closing,
                        onToggleChrome = { interaction++; store.setChromeVisible(!store.state.value.chromeVisible) },
                        onInteraction = { interaction++ },
                        onDirectory = { directory = true },
                        onSettings = { settingsOpen = true },
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
                        TextButton("选择其他章节", { directory = true }, minHeight = 48.dp)
                    }
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
        // While the page animates out, swallow pointer input so no chrome action can fire twice.
        if (closing) {
            Box(Modifier.fillMaxSize().pointerInput(Unit) {
                awaitPointerEventScope {
                    while (true) awaitPointerEvent().changes.forEach { it.consume() }
                }
            })
        }
        OverlayBottomSheet(
            show = directory,
            title = null,
            onDismissRequest = { directory = false },
            cornerRadius = 28.dp,
        ) {
            TocSheet(
                book = book,
                manifest = state.manifest,
                currentChapter = state.chapterIndex,
                progressText = "${(state.chapterIndex + 1).coerceAtLeast(1)} / " +
                    "${(state.manifest?.chapters?.size ?: book.chapters.size).coerceAtLeast(1)}",
                maxHeight = tocMaxHeight,
                onSelectChapter = {
                    if (it != state.chapterIndex) store.selectChapter(it)
                    directory = false
                },
                onDismiss = { directory = false },
            )
        }
        ReadingSettings(settingsOpen, state.settings, store::updateSettings, { settingsOpen = false },
            maxHeight = settingsMaxHeight)
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
    closing: Boolean,
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

    BoxWithConstraints(Modifier.fillMaxSize()) {
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
                if (settings.readingMode == ReadingMode.SCROLL || position.x in size.width * 0.32f..size.width * 0.68f)
                    onToggleChrome()
                else move(if (position.x < size.width / 2f) -1 else 1)
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
        // Immersive chrome: a gradient-scrimmed floating header, never a solid bar or divider.
        AnimatedVisibility(
            visible = state.chromeVisible && !closing,
            enter = slideInVertically(animationSpec = tween(ChromeInMillis, easing = MiuixEaseOut)) { -it } +
                fadeIn(animationSpec = tween(ChromeInMillis)),
            exit = slideOutVertically(animationSpec = tween(ChromeOutMillis, easing = MiuixEaseIn)) { -it } +
                fadeOut(animationSpec = tween(ChromeOutMillis)),
            modifier = Modifier.align(Alignment.TopCenter),
        ) {
            GradientHeaderScrim {
                Row(
                    modifier = Modifier.fillMaxWidth()
                        .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Top + WindowInsetsSides.Horizontal))
                        .padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    MiuixCircleButton(Glyph.BACK, "返回书架", onClose, size = TouchTarget)
                    Text(chapter.title.ifBlank { "正文" }, Modifier.weight(1f), fontSize = 15.sp,
                        color = MiuixTheme.colorScheme.onSurfaceVariantSummary, maxLines = 1,
                        overflow = TextOverflow.Ellipsis)
                    MiuixCircleButton(Glyph.TOC, "打开目录", onDirectory, size = TouchTarget)
                }
            }
        }
        AnimatedVisibility(
            visible = state.chromeVisible && !closing,
            enter = slideInVertically(animationSpec = tween(ChromeInMillis, easing = MiuixEaseOut)) { it } +
                fadeIn(animationSpec = tween(ChromeInMillis)),
            exit = slideOutVertically(animationSpec = tween(ChromeOutMillis, easing = MiuixEaseIn)) { it } +
                fadeOut(animationSpec = tween(ChromeOutMillis)),
            modifier = Modifier.align(Alignment.BottomCenter),
        ) {
            Box(
                Modifier.fillMaxWidth()
                    .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Bottom + WindowInsetsSides.Horizontal))
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                contentAlignment = Alignment.Center,
            ) {
                MiuixDockPill(Modifier.fillMaxWidth()) {
                    DockAction(Glyph.BOOK, "目录", onDirectory)
                    Text(progressText, Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite },
                        fontSize = 13.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                        textAlign = TextAlign.Center, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    DockAction(Glyph.TUNE, "设置", onSettings)
                }
            }
        }
    }
}

/** 44dp minimum touch target; the visible glyph stays small inside it. */
private val TouchTarget = 44.dp
private const val ChromeInMillis = 240
private const val ChromeOutMillis = 200

/** Glyph + label action inside the floating reading dock. */
@Composable
private fun DockAction(glyph: Glyph, label: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .clickable(role = Role.Button, onClick = onClick)
            .heightIn(min = TouchTarget)
            .padding(horizontal = 8.dp)
            .semantics { contentDescription = label },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        MiuixGlyph(glyph, MiuixTheme.colorScheme.onSurface, 20.dp)
        Text(label, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1)
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
