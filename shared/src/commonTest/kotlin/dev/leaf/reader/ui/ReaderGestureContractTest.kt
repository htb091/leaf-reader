package dev.leaf.reader.ui

import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.input.pointer.AwaitPointerEventScope
import androidx.compose.ui.input.pointer.PointerEvent
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.PointerId
import androidx.compose.ui.input.pointer.PointerInputChange
import androidx.compose.ui.input.pointer.PointerInputScope
import androidx.compose.ui.platform.ViewConfiguration
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.IntSize
import dev.leaf.reader.ReadingMode
import kotlinx.coroutines.test.runTest
import kotlin.coroutines.Continuation
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.coroutines.startCoroutine
import kotlin.coroutines.suspendCoroutine
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

/**
 * Runs the real Compose foundation detectors against scripted Main/Final events without a window.
 * This verifies their consumption/cancellation contract, NOT OS hit testing, a Pager fling, or
 * device gesture ergonomics. Pinning framework behaviour is stronger than reimplementing a fake
 * tap classifier; the application still uses the same foundation detectors unchanged.
 */
class ReaderGestureContractTest {
    @Test fun normalUpRoutesSideAndCenterTapsForAllReadingModes() = runTest {
        for (mode in ReadingMode.entries) {
            for (fraction in listOf(0.1f, 0.5f, 0.9f)) {
                val point = Offset(fraction * 1000f, 400f)
                val actions = mutableListOf<ReaderTapAction>()
                val scope = ScriptedPointerScope(listOf(main(down(point)), main(up(point))))
                assertFailsWith<EndOfPointerScript> {
                    scope.detectTapGestures { position ->
                        actions += readerTapAction(position.x / scope.size.width,
                            paged = mode != ReadingMode.SCROLL)
                    }
                }
                val expected = when {
                    fraction == 0.5f -> ReaderTapAction.TOGGLE_CHROME
                    mode == ReadingMode.SCROLL -> ReaderTapAction.NONE
                    fraction < 0.5f -> ReaderTapAction.PREVIOUS_PAGE
                    else -> ReaderTapAction.NEXT_PAGE
                }
                assertEquals(listOf(expected), actions, "$mode at $fraction")
            }
        }
    }

    @Test fun horizontalChildConsumptionCancelsParentTapBeforeReleaseInEitherDirection() = runTest {
        for (endX in listOf(260f, 740f)) {
            var taps = 0
            val start = Offset(500f, 400f)
            val end = Offset(endX, 400f)
            val claimedMove = move(start, end).also { it.consume() }
            val scope = ScriptedPointerScope(listOf(main(down(start)), main(claimedMove), final(up(end))))
            assertFailsWith<EndOfPointerScript> { scope.detectTapGestures { taps++ } }
            assertEquals(0, taps)
        }
    }

    @Test fun scrollChildConsumptionAlsoCancelsParentCenterTap() = runTest {
        var taps = 0
        val start = Offset(500f, 500f)
        val end = Offset(500f, 280f)
        val claimedScroll = move(start, end).also { it.consume() }
        val scope = ScriptedPointerScope(listOf(main(down(start)), main(claimedScroll), final(up(end))))
        assertFailsWith<EndOfPointerScript> { scope.detectTapGestures { taps++ } }
        assertEquals(0, taps)
    }

    @Test fun consumptionDuringFinalPassCancelsTapToo() = runTest {
        var taps = 0
        val start = Offset(500f, 400f)
        val end = Offset(620f, 400f)
        val movement = PointerEvent(listOf(move(start, end)))
        val scope = ScriptedPointerScope(listOf(main(down(start)),
            Delivery(PointerEventPass.Main, movement),
            Delivery(PointerEventPass.Final, movement) { it.changes.single().consume() }, final(up(end))))
        assertFailsWith<EndOfPointerScript> { scope.detectTapGestures { taps++ } }
        assertEquals(0, taps)
    }

    @Test fun unclaimedSmallJitterIsStillExactlyOneTap() = runTest {
        var taps = 0
        val start = Offset(500f, 400f)
        val end = Offset(503f, 402f)
        val jitter = PointerEvent(listOf(move(start, end)))
        val scope = ScriptedPointerScope(listOf(main(down(start)),
            Delivery(PointerEventPass.Main, jitter), Delivery(PointerEventPass.Final, jitter), main(up(end))))
        assertFailsWith<EndOfPointerScript> { scope.detectTapGestures { taps++ } }
        assertEquals(1, taps)
    }

    @Test fun consumedInitialDownSkipsTapEntirely() = runTest {
        var taps = 0
        val point = Offset(500f, 400f)
        val claimedDown = down(point).also { it.consume() }
        val scope = ScriptedPointerScope(listOf(main(claimedDown), main(up(point))))
        assertFailsWith<EndOfPointerScript> { scope.detectTapGestures { taps++ } }
        assertEquals(0, taps)
    }

    @Test fun instantDetectorAcceptsParentConsumedDownAndClaimsMovement() = runTest {
        val start = Offset(500f, 400f)
        val end = Offset(350f, 400f)
        val parentConsumedDown = down(start).also { it.consume() }
        val movement = move(start, end)
        var starts = 0
        var completions = 0
        var distance = 0f
        val scope = ScriptedPointerScope(listOf(main(parentConsumedDown), main(movement), main(up(end))))
        assertFailsWith<EndOfPointerScript> {
            scope.detectHorizontalDragGestures(onDragStart = { starts++; distance = 0f },
                onDragEnd = { completions++ },
                onHorizontalDrag = { change, amount -> change.consume(); distance += amount })
        }
        assertEquals(1, starts)
        assertEquals(1, completions)
        assertTrue(movement.isConsumed)
        assertTrue(distance < -48f, "Real detector reports post-slop delta for the instant turn threshold")
    }

    @Test fun cancelledHorizontalDragDoesNotCompleteAnInstantTurn() = runTest {
        val start = Offset(500f, 400f)
        val middle = Offset(430f, 400f)
        val end = Offset(350f, 400f)
        val cancelledMove = move(middle, end).also { it.consume() }
        var completions = 0
        var cancellations = 0
        val scope = ScriptedPointerScope(listOf(main(down(start)), main(move(start, middle)),
            main(cancelledMove), final(up(end))))
        assertFailsWith<EndOfPointerScript> {
            scope.detectHorizontalDragGestures(onDragEnd = { completions++ },
                onDragCancel = { cancellations++ }, onHorizontalDrag = { change, _ -> change.consume() })
        }
        assertEquals(0, completions)
        assertEquals(1, cancellations)
    }

    private fun down(point: Offset) = change(point, point, true, false, 0L)
    private fun move(from: Offset, to: Offset) = change(from, to, true, true, 16L)
    private fun up(point: Offset) = change(point, point, false, true, 32L)
    private fun change(from: Offset, to: Offset, pressed: Boolean, wasPressed: Boolean, time: Long) =
        PointerInputChange(id = PointerId(1), uptimeMillis = time, position = to, pressed = pressed,
            previousUptimeMillis = (time - 16L).coerceAtLeast(0L), previousPosition = from,
            previousPressed = wasPressed, isInitiallyConsumed = false)
    private fun main(change: PointerInputChange) = Delivery(PointerEventPass.Main, PointerEvent(listOf(change)))
    private fun final(change: PointerInputChange) = Delivery(PointerEventPass.Final, PointerEvent(listOf(change)))

    private class EndOfPointerScript : RuntimeException()
    private data class Delivery(val pass: PointerEventPass, val event: PointerEvent,
        val beforeDelivery: (PointerEvent) -> Unit = {})

    private class ScriptedPointerScope(private val deliveries: List<Delivery>) :
        PointerInputScope, Density by Density(1f) {
        override val size = IntSize(1000, 1600)
        override val extendedTouchPadding = Size.Zero
        override val viewConfiguration = object : ViewConfiguration {
            override val longPressTimeoutMillis = 500L
            override val doubleTapTimeoutMillis = 300L
            override val doubleTapMinTimeMillis = 40L
            override val touchSlop = 8f
        }
        private var position = 0
        // AwaitPointerEventScope is @RestrictsSuspension. Keep that receiver separate from the
        // public PointerInputScope so normal detector coroutines are not themselves restricted.
        private val eventScope = object : AwaitPointerEventScope, Density by Density(1f) {
            override val size get() = this@ScriptedPointerScope.size
            override val extendedTouchPadding = Size.Zero
            override val viewConfiguration get() = this@ScriptedPointerScope.viewConfiguration
            override var currentEvent = PointerEvent(emptyList())
                private set
            override suspend fun awaitPointerEvent(pass: PointerEventPass): PointerEvent {
                val delivery = deliveries.getOrNull(position++) ?: throw EndOfPointerScript()
                assertEquals(delivery.pass, pass, "Unexpected event phase requested by the real detector")
                delivery.beforeDelivery(delivery.event)
                currentEvent = delivery.event
                return currentEvent
            }
        }
        override suspend fun <R> awaitPointerEventScope(block: suspend AwaitPointerEventScope.() -> R): R =
            suspendCoroutine { continuation ->
                // A restricted suspend lambda requires EmptyCoroutineContext at runtime too.
                // Bridge its result back to runTest rather than inheriting runTest's dispatcher.
                block.startCoroutine(eventScope, object : Continuation<R> {
                    override val context = EmptyCoroutineContext
                    override fun resumeWith(result: Result<R>) = continuation.resumeWith(result)
                })
            }
    }
}
