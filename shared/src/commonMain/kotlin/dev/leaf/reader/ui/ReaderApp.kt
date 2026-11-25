package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
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
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.theme.darkColorScheme
import top.yukonga.miuix.kmp.theme.lightColorScheme

/** Shared iOS / desktop entry. The host owns file selection, not this composable. */
@Composable
fun ReaderApp(store: ReaderStore, onImportRequested: () -> Unit) {
    val state by store.state.collectAsState()
    val dark = state.settings.theme == ReaderTheme.DARK ||
        (state.settings.theme == ReaderTheme.SYSTEM && isSystemInDarkTheme())
    val colors = when {
        dark -> darkColorScheme()
        state.settings.theme == ReaderTheme.SEPIA -> lightColorScheme(
            primary = Color(0xFF706044), surface = Color(0xFFF3ECD9),
            surfaceContainer = Color(0xFFFBF5E7), onSurface = Color(0xFF473E30),
            onBackground = Color(0xFF473E30), onSurfaceContainer = Color(0xFF473E30),
        )
        else -> lightColorScheme()
    }
    MiuixTheme(colors = colors) {
        val shelfState = rememberSaveableStateHolder()
        // Root Scaffold is only an overlay host. ShelfScreen owns its own collapsible bar.
        // In reading there is NO shelf toolbar or toolbar-sized padding in the viewport.
        Scaffold(contentWindowInsets = WindowInsets(0, 0, 0, 0)) {
            Box(Modifier.fillMaxSize()) {
                val book = state.currentBook
                if (book == null) {
                    shelfState.SaveableStateProvider("shelf") {
                        ShelfScreen(state = state, store = store, onImportRequested = onImportRequested)
                    }
                } else {
                    // Constant system-safe viewport, independent of reading chrome visibility.
                    // windowInsetsPadding consumes the insets for nested reading overlays.
                    Box(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing)) {
                        key(book.id) { ReadingScreen(state = state, store = store) }
                    }
                }
                if (state.busy) {
                    Box(
                        modifier = Modifier.fillMaxSize()
                            .background(Color.Black.copy(alpha = 0.25f))
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
                    TextButton(
                        text = "知道了", onClick = store::dismissError,
                        modifier = Modifier.fillMaxWidth(), minHeight = 48.dp,
                        colors = ButtonDefaults.textButtonColorsPrimary(),
                    )
                }
            }
        }
    }
}
