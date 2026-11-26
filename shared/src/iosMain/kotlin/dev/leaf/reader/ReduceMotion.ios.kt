@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package dev.leaf.reader

import androidx.compose.runtime.Composable
import androidx.compose.runtime.State
import androidx.compose.runtime.remember
import platform.Foundation.NSNotificationCenter
import platform.Foundation.NSOperationQueue
import platform.UIKit.UIAccessibilityIsReduceMotionEnabled
import platform.UIKit.UIAccessibilityReduceMotionStatusDidChangeNotification
import platform.UIKit.UIApplicationDidBecomeActiveNotification
import platform.darwin.NSObjectProtocol

/** Uses Objective-C/C UIKit declarations directly; no SwiftUI bridge is required. */
@Composable
internal actual fun rememberReduceMotion(): State<Boolean> {
    val source = remember { IosReduceMotionSource() }
    return rememberObservedReduceMotion(source)
}

/** Constructor seams let iosTest exercise real notification registration safely. */
internal class IosReduceMotionSource(
    private val center: NSNotificationCenter = NSNotificationCenter.defaultCenter,
    private val readEnabled: () -> Boolean = { UIAccessibilityIsReduceMotionEnabled() },
) : ReduceMotionSource {
    override fun isEnabled(): Boolean = readEnabled()

    override fun subscribe(onChange: () -> Unit): () -> Unit {
        val tokens = mutableListOf<NSObjectProtocol>()
        try {
            for (name in listOf(
                UIAccessibilityReduceMotionStatusDidChangeNotification,
                // Settings can change while the app is suspended. Re-query once
                // on activation even if the accessibility notification was missed.
                UIApplicationDidBecomeActiveNotification,
            )) {
                tokens += center.addObserverForName(
                    name = name,
                    `object` = null,
                    queue = NSOperationQueue.mainQueue,
                ) { onChange() }
            }
        } catch (error: Throwable) {
            tokens.forEach { center.removeObserver(it) }
            throw error
        }
        return {
            tokens.forEach { center.removeObserver(it) }
            tokens.clear()
        }
    }
}
