@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package dev.leaf.reader

import platform.Foundation.NSNotificationCenter
import platform.Foundation.NSThread
import platform.UIKit.UIAccessibilityIsReduceMotionEnabled
import platform.UIKit.UIAccessibilityReduceMotionStatusDidChangeNotification
import platform.UIKit.UIApplicationDidBecomeActiveNotification
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Apple runner only. Notifications use a private center and never modify OS preferences. */
class ReduceMotionIosTest {
    @Test fun nativeReaderMatchesUIKitGetter() {
        assertTrue(NSThread.isMainThread, "UIKit test must run on the main thread")
        assertEquals(UIAccessibilityIsReduceMotionEnabled(), IosReduceMotionSource().isEnabled())
    }

    @Test fun preferenceNotificationsAndForegroundRefreshReachTheSameLiveState() {
        assertTrue(NSThread.isMainThread, "Notification test must run on the main thread")
        val center = NSNotificationCenter()
        var enabled = false
        val observer = ReduceMotionObserver(IosReduceMotionSource(center) { enabled })
        observer.start()
        assertFalse(observer.state.value)
        enabled = true
        center.postNotificationName(UIAccessibilityReduceMotionStatusDidChangeNotification, `object` = null)
        assertTrue(observer.state.value)
        enabled = false // Simulates changing Settings while the app was suspended.
        center.postNotificationName(UIApplicationDidBecomeActiveNotification, `object` = null)
        assertFalse(observer.state.value)
        observer.stop()
        enabled = true
        center.postNotificationName(UIAccessibilityReduceMotionStatusDidChangeNotification, `object` = null)
        center.postNotificationName(UIApplicationDidBecomeActiveNotification, `object` = null)
        assertFalse(observer.state.value)
    }

    @Test fun removingNativeSubscriptionStopsBothNotificationKinds() {
        assertTrue(NSThread.isMainThread, "Notification test must run on the main thread")
        val center = NSNotificationCenter()
        var calls = 0
        val release = IosReduceMotionSource(center) { false }.subscribe { calls++ }
        center.postNotificationName(UIAccessibilityReduceMotionStatusDidChangeNotification, `object` = null)
        center.postNotificationName(UIApplicationDidBecomeActiveNotification, `object` = null)
        assertEquals(2, calls)
        release()
        release()
        center.postNotificationName(UIAccessibilityReduceMotionStatusDidChangeNotification, `object` = null)
        center.postNotificationName(UIApplicationDidBecomeActiveNotification, `object` = null)
        assertEquals(2, calls)
    }
}
