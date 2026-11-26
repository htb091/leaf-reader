package dev.leaf.reader

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse

class ReduceMotionDesktopTest {
    @Test fun portableDesktopFallbackIsExplicitlyFalseAndNeedsNoNativeObservers() {
        var callbacks = 0
        val release = DesktopReduceMotionSource.subscribe { callbacks++ }
        assertFalse(DesktopReduceMotionSource.isEnabled())
        release()
        release()
        assertFalse(DesktopReduceMotionSource.isEnabled())
        assertEquals(0, callbacks)
    }
}
