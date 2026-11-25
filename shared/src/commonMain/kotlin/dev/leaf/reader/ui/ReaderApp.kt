package dev.leaf.reader.ui

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
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
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

/**
 * Root of the shared UI. The shelf owns its collapsing header and floating dock;
 * the reader owns an immersive viewport with slide-in chrome and its own
 * open/close spring, so this root only resolves theme + overlays.
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
        Box(Modifier.fillMaxSize().background(MiuixTheme.colorScheme.surface)) {
            val book = state.currentBook
            if (book == null) {
                shelfState.SaveableStateProvider("shelf") {
                    ShelfScreen(state = state, store = store, onImportRequested = onImportRequested)
                }
            } else {
                key(book.id) { ReadingScreen(state = state, store = store) }
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
