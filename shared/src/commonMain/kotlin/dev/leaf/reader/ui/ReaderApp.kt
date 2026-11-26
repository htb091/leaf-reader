package dev.leaf.reader.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.unit.IntSize
import kotlinx.coroutines.launch
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.Card
import top.yukonga.miuix.kmp.basic.CircularProgressIndicator
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.basic.TextButton
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.theme.darkColorScheme
import top.yukonga.miuix.kmp.theme.lightColorScheme

/** Keep the shelf mounted under the reading layer. The same progress drives the
 * entire reader surface in both directions; book state survives until exit ends.
 */
@Composable
fun ReaderApp(store: ReaderStore, onImportRequested: () -> Unit) {
    val state by store.state.collectAsState()
    val systemDark = isSystemInDarkTheme()
    val colors = when (state.settings.theme) {
        ReaderTheme.SEPIA -> readerColorScheme(ReaderTheme.SEPIA)
        ReaderTheme.LIGHT -> lightColorScheme()
        ReaderTheme.DARK -> darkColorScheme()
        ReaderTheme.SYSTEM -> if (systemDark) darkColorScheme() else lightColorScheme()
    }
    MiuixTheme(colors = colors) {
        val shelfState = rememberSaveableStateHolder()
        val scope = rememberCoroutineScope()
        val entrance = remember { Animatable(0f) }
        var rootSize by remember { mutableStateOf(IntSize.Zero) }
        var origin by remember { mutableStateOf<Offset?>(null) }
        var originSize by remember { mutableStateOf(IntSize.Zero) }
        var frozenShelfBooks by remember { mutableStateOf(state.books) }
        var closing by remember { mutableStateOf(false) }
        val book = state.currentBook
        LaunchedEffect(book?.id) {
            closing = false
            if (book != null) {
                entrance.snapTo(0f)
                entrance.animateTo(1f, animationSpec = bookOpen())
            }
        }
        Box(Modifier.fillMaxSize().onSizeChanged { rootSize = it }.background(MiuixTheme.colorScheme.surface)) {
            // Hidden from both touch and accessibility while the reader is on top.
            val shelfBlocker = if (book != null) Modifier
                .clearAndSetSemantics { }
                .pointerInput(book.id) {
                    awaitPointerEventScope { while (true) awaitPointerEvent(PointerEventPass.Initial).changes.forEach { it.consume() } }
                } else Modifier
            Box(Modifier.fillMaxSize().then(shelfBlocker)) {
                shelfState.SaveableStateProvider("shelf") {
                    ShelfScreen(state = if (book == null) state else state.copy(books = frozenShelfBooks),
                        store = store, onImportRequested = onImportRequested,
                        onOpenBook = { id, center ->
                            frozenShelfBooks = state.books
                            origin = center
                            originSize = rootSize
                            store.openBook(id)
                        })
                }
            }
            if (book != null) {
                key(book.id) {
                    val target = origin?.takeIf {
                        originSize == rootSize && rootSize.width > 0 && rootSize.height > 0 &&
                            it.x in 0f..rootSize.width.toFloat() && it.y in 0f..rootSize.height.toFloat()
                    }
                    val progress = entrance.value
                    val startingScale = if (target != null) 0.28f else 0.94f
                    Box(Modifier.fillMaxSize().graphicsLayer {
                        val scale = startingScale + (1f - startingScale) * progress
                        scaleX = scale
                        scaleY = scale
                        alpha = progress
                        translationX = ((target?.x ?: size.width / 2f) - size.width / 2f) * (1f - progress)
                        translationY = ((target?.y ?: size.height / 2f) - size.height / 2f) * (1f - progress)
                    }) {
                        ReadingScreen(state = state, store = store, onRequestClose = {
                            if (!closing) {
                                closing = true
                                // The shelf book list stays frozen during reading, so an unchanged
                                // window can reverse toward the tapped item without a re-sort jump.
                                // A resized or rotated window uses the centered fallback above.
                                val closingBookId = book.id
                                scope.launch {
                                    entrance.animateTo(0f, animationSpec = bookClose())
                                    if (store.state.value.currentBook?.id == closingBookId) store.closeBook()
                                }
                            }
                        })
                    }
                }
                if (closing) {
                    Box(Modifier.fillMaxSize().pointerInput(Unit) {
                        awaitPointerEventScope { while (true) awaitPointerEvent(PointerEventPass.Initial).changes.forEach { it.consume() } }
                    })
                }
            }
            if (state.busy) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.22f))
                        .pointerInput(Unit) {
                            awaitPointerEventScope {
                                while (true) awaitPointerEvent().changes.forEach { it.consume() }
                            }
                        },
                    contentAlignment = Alignment.Center,
                ) {
                    Card(insideMargin = PaddingValues(28.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(16.dp),
                        ) {
                            CircularProgressIndicator(size = 26.dp)
                            Text(
                                "正在整理书页…",
                                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                            )
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
                TextButton(
                    text = "知道了", onClick = store::dismissError,
                    modifier = Modifier.fillMaxWidth(), minHeight = 48.dp,
                    colors = top.yukonga.miuix.kmp.basic.ButtonDefaults.textButtonColorsPrimary(),
                )
            }
        }
    }
}
