package dev.leaf.reader

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember

/**
 * Live system Reduce Motion preference, owned by this composition.
 *
 * iOS reads UIKit before the first frame and observes setting changes/foreground
 * activation on the main queue. Desktop currently has an explicit false fallback
 * (there is no portable JVM Reduce Motion setting). No preference is persisted.
 *
 * Read with `val reduceMotion by rememberReduceMotion()`. This reports a policy;
 * it does not itself alter animation specs or cancel running animations. Include
 * the value in an animation effect's keys when an in-flight animation must snap
 * immediately after the user enables Reduce Motion.
 *
 * Kept internal: Compose State/Composer signatures are not a new Swift/ObjC API.
 */
@Composable
internal expect fun rememberReduceMotion(): State<Boolean>

/** UI-thread-only platform seam; callbacks mean "re-read", not toggle. */
internal interface ReduceMotionSource {
    fun isEnabled(): Boolean
    fun subscribe(onChange: () -> Unit): () -> Unit
}

@Composable
internal fun rememberObservedReduceMotion(source: ReduceMotionSource): State<Boolean> {
    val observer = remember(source) { ReduceMotionObserver(source) }
    DisposableEffect(observer) {
        observer.start()
        onDispose { observer.stop() }
    }
    return observer.state
}

/**
 * Testable lifecycle behind the composable. Platform sources deliver callbacks
 * on the UI thread; no process-global observer or polling task outlives a screen.
 */
internal class ReduceMotionObserver(private val source: ReduceMotionSource) {
    private val value = mutableStateOf(source.isEnabled())
    val state: State<Boolean> get() = value
    private var subscription: Any? = null
    private var unsubscribe: (() -> Unit)? = null

    fun start() {
        if (subscription != null) return
        val token = Any()
        subscription = token
        try {
            val release = source.subscribe {
                // A queued callback from a disposed/older subscription is inert.
                if (subscription === token) value.value = source.isEnabled()
            }
            if (subscription !== token) {
                release()
                return
            }
            unsubscribe = release
            // Close the initial-read/registration race, including changes while
            // the composition was temporarily not observing the platform.
            value.value = source.isEnabled()
        } catch (error: Throwable) {
            if (subscription === token) stop()
            throw error
        }
    }

    fun stop() {
        subscription = null
        val release = unsubscribe
        unsubscribe = null
        // Invalidate before removing native tokens: already-enqueued notifications
        // may still run after removeObserver, but must not update this State.
        release?.invoke()
    }
}
