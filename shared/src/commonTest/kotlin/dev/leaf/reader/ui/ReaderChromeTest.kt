package dev.leaf.reader.ui

import kotlin.test.Test
import kotlin.test.assertEquals

class ReaderChromeTest {
    @Test fun centralTapTogglesChromeInEveryReadingMode() {
        for (paged in listOf(false, true)) {
            for (fraction in listOf(0.32f, 0.5f, 0.68f)) {
                assertEquals(ReaderTapAction.TOGGLE_CHROME, readerTapAction(fraction, paged))
            }
        }
    }

    @Test fun pageTurnZonesDoNotToggleChrome() {
        assertEquals(ReaderTapAction.PREVIOUS_PAGE, readerTapAction(0f, true))
        assertEquals(ReaderTapAction.PREVIOUS_PAGE, readerTapAction(0.31f, true))
        assertEquals(ReaderTapAction.NEXT_PAGE, readerTapAction(0.69f, true))
        assertEquals(ReaderTapAction.NEXT_PAGE, readerTapAction(1f, true))
    }

    @Test fun scrollSideTapsHaveNoPageTurnOrChromeSideEffect() {
        assertEquals(ReaderTapAction.NONE, readerTapAction(0.2f, false))
        assertEquals(ReaderTapAction.NONE, readerTapAction(0.8f, false))
    }

    @Test fun invalidPointerCoordinatesProduceNoAction() {
        for (fraction in listOf(Float.NaN, Float.POSITIVE_INFINITY, -0.1f, 1.1f)) {
            assertEquals(ReaderTapAction.NONE, readerTapAction(fraction, true))
        }
    }
}
