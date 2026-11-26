package dev.leaf.reader

import androidx.compose.runtime.Composable
import androidx.compose.runtime.State
import androidx.compose.runtime.remember

@Composable
internal actual fun rememberReduceMotion(): State<Boolean> {
    val source = remember { DesktopReduceMotionSource }
    return rememberObservedReduceMotion(source)
}

/** Explicit fallback, not a claim to read Windows/macOS/Linux native settings. */
internal object DesktopReduceMotionSource : ReduceMotionSource {
    override fun isEnabled(): Boolean = false
    override fun subscribe(onChange: () -> Unit): () -> Unit = {}
}
