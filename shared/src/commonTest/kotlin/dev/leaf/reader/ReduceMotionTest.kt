package dev.leaf.reader

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Deterministic preference/lifecycle tests; no display, real OS setting or UI tree required. */
class ReduceMotionTest {
    @Test fun initialPreferenceIsAvailableBeforeSubscription() {
        val source = FakeSource(enabled = true)
        val observer = ReduceMotionObserver(source)
        assertTrue(observer.state.value)
        assertEquals(0, source.registrations)
    }

    @Test fun enabledAndDisabledChangesAreReflectedWithoutRecreatingState() {
        val source = FakeSource()
        val observer = ReduceMotionObserver(source)
        val state = observer.state
        observer.start()
        source.enabled = true
        source.notifyChanged()
        assertTrue(state.value)
        source.enabled = false
        source.notifyChanged()
        assertFalse(state.value)
        observer.stop()
    }

    @Test fun notificationsReReadTheSettingRatherThanToggleIt() {
        val source = FakeSource(enabled = true)
        val observer = ReduceMotionObserver(source)
        observer.start()
        repeat(3) { source.notifyChanged() }
        assertTrue(observer.state.value)
        observer.stop()
    }

    @Test fun registrationRechecksChangesSinceTheInitialRead() {
        val source = FakeSource()
        val observer = ReduceMotionObserver(source)
        source.enabled = true // No notification while not subscribed.
        observer.start()
        assertTrue(observer.state.value)
        observer.stop()
    }

    @Test fun synchronousNotificationDuringRegistrationIsHandled() {
        val source = FakeSource()
        source.onRegister = { callback -> source.enabled = true; callback() }
        val observer = ReduceMotionObserver(source)
        observer.start()
        assertTrue(observer.state.value)
        observer.stop()
        assertEquals(1, source.removals)
    }

    @Test fun startAndStopAreIdempotentAndReleaseExactlyOneSubscription() {
        val source = FakeSource()
        val observer = ReduceMotionObserver(source)
        observer.start()
        observer.start()
        assertEquals(1, source.registrations)
        observer.stop()
        observer.stop()
        assertEquals(1, source.removals)
        assertTrue(source.callbacks.isEmpty())
    }

    @Test fun queuedNotificationAfterDisposeIsIgnored() {
        val source = FakeSource()
        val observer = ReduceMotionObserver(source)
        observer.start()
        val queued = source.callbacks.single()
        observer.stop()
        source.enabled = true
        val readsBefore = source.reads
        queued()
        assertFalse(observer.state.value)
        assertEquals(readsBefore, source.reads)
    }

    @Test fun anOldCallbackCannotActOnANewSubscription() {
        val source = FakeSource()
        val observer = ReduceMotionObserver(source)
        observer.start()
        val old = source.callbacks.single()
        observer.stop()
        source.enabled = true
        observer.start()
        assertTrue(observer.state.value)
        source.enabled = false
        old()
        assertTrue(observer.state.value) // Old token must not perform the re-read.
        source.notifyChanged()
        assertFalse(observer.state.value)
        observer.stop()
    }

    @Test fun restartRefreshesChangesMissedWhileNotObserving() {
        val source = FakeSource()
        val observer = ReduceMotionObserver(source)
        observer.start()
        observer.stop()
        source.enabled = true
        observer.start()
        assertTrue(observer.state.value)
        assertEquals(2, source.registrations)
        observer.stop()
        assertEquals(2, source.removals)
    }

    @Test fun aFailedPostRegistrationReadReleasesTheSubscriptionAndAllowsRetry() {
        val source = FakeSource()
        val observer = ReduceMotionObserver(source)
        source.failRead = true
        assertFailsWith<IllegalStateException> { observer.start() }
        assertEquals(1, source.removals)
        assertTrue(source.callbacks.isEmpty())
        source.failRead = false
        source.enabled = true
        observer.start()
        assertTrue(observer.state.value)
        observer.stop()
        assertEquals(2, source.removals)
    }

    @Test fun aFailedRegistrationDoesNotLockTheObserverInStartedState() {
        val source = FakeSource()
        val observer = ReduceMotionObserver(source)
        source.failSubscribe = true
        assertFailsWith<IllegalStateException> { observer.start() }
        source.failSubscribe = false
        source.enabled = true
        observer.start()
        assertTrue(observer.state.value)
        observer.stop()
        assertEquals(1, source.removals)
    }

    private class FakeSource(var enabled: Boolean = false) : ReduceMotionSource {
        val callbacks = mutableListOf<() -> Unit>()
        var registrations = 0
        var removals = 0
        var reads = 0
        var failRead = false
        var failSubscribe = false
        var onRegister: ((() -> Unit) -> Unit)? = null

        override fun isEnabled(): Boolean {
            reads++
            check(!failRead) { "Simulated read failure" }
            return enabled
        }

        override fun subscribe(onChange: () -> Unit): () -> Unit {
            check(!failSubscribe) { "Simulated registration failure" }
            registrations++
            callbacks += onChange
            onRegister?.invoke(onChange)
            return {
                callbacks.remove(onChange)
                removals++
            }
        }

        fun notifyChanged() { callbacks.toList().forEach { it() } }
    }
}
