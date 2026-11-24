package dev.leaf.reader

import androidx.compose.ui.window.ComposeUIViewController
import dev.leaf.reader.ui.ReaderApp
import platform.UIKit.UIViewController

fun MainViewController(onImportRequested: () -> Unit): UIViewController = ComposeUIViewController {
    ReaderApp(store = ReaderRuntime.store, onImportRequested = onImportRequested)
}
