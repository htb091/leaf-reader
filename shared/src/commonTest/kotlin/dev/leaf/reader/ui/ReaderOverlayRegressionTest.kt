package dev.leaf.reader.ui

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** Logic checks; actual popup rendering/touch delivery remains a device/UI-test responsibility. */
class ReaderOverlayRegressionTest {
    @Test fun settingsAlwaysReplacesThePreviousPanel() {
        ReaderPanel.entries.forEach { previous ->
            assertEquals(ReaderPanel.SETTINGS, reduceReaderPanel(previous, ReaderPanelAction.OPEN_SETTINGS))
        }
    }

    @Test fun directoryAlwaysReplacesSettingsWithoutLeavingBothOpen() {
        ReaderPanel.entries.forEach { previous ->
            assertEquals(ReaderPanel.CONTENTS, reduceReaderPanel(previous, ReaderPanelAction.OPEN_CONTENTS))
        }
    }

    @Test fun dismissClosesOnlyItsOwnPanel() {
        assertEquals(ReaderPanel.NONE, reduceReaderPanel(ReaderPanel.SETTINGS, ReaderPanelAction.CLOSE_SETTINGS))
        assertEquals(ReaderPanel.NONE, reduceReaderPanel(ReaderPanel.CONTENTS, ReaderPanelAction.CLOSE_CONTENTS))
        assertEquals(ReaderPanel.CONTENTS, reduceReaderPanel(ReaderPanel.CONTENTS, ReaderPanelAction.CLOSE_SETTINGS))
        assertEquals(ReaderPanel.SETTINGS, reduceReaderPanel(ReaderPanel.SETTINGS, ReaderPanelAction.CLOSE_CONTENTS))
    }

    @Test fun delayedOldDismissCannotUndoASecondSettingsOpen() {
        var panel = reduceReaderPanel(ReaderPanel.NONE, ReaderPanelAction.OPEN_CONTENTS)
        panel = reduceReaderPanel(panel, ReaderPanelAction.OPEN_SETTINGS)
        panel = reduceReaderPanel(panel, ReaderPanelAction.CLOSE_CONTENTS)
        assertEquals(ReaderPanel.SETTINGS, panel)
        panel = reduceReaderPanel(panel, ReaderPanelAction.CLOSE_SETTINGS)
        panel = reduceReaderPanel(panel, ReaderPanelAction.OPEN_SETTINGS)
        assertEquals(ReaderPanel.SETTINGS, panel)
    }

    @Test fun floatingCircleMatchesShelfButKeepsTheTouchTarget() {
        assertEquals(CircleControlSize.value, ReaderControlVisualDp)
        assertEquals(40f, ReaderControlVisualDp)
        assertTrue(ReaderControlTouchDp >= 44f)
        assertTrue(ReaderControlTouchDp > ReaderControlVisualDp)
    }

    @Test fun dockIsAboutThreeQuartersOfTheOldMinimumWithoutShrinkingTouchTargets() {
        val previousMinimum = 48f + 2 * 10f
        assertEquals(52f, ReaderDockMinimumHeightDp)
        assertTrue(ReaderDockMinimumHeightDp / previousMinimum in 0.70f..0.80f)
        assertTrue(ReaderDockMinimumHeightDp >= ReaderControlTouchDp)
    }

    @Test fun largeFontsAndNarrowSettingsMoveControlsToAnotherLine() {
        assertTrue(stackedReaderSetting(1.5f, 320f))
        assertTrue(stackedReaderSetting(1f, 220f))
        assertEquals(false, stackedReaderSetting(1f, 280f))
        assertEquals(false, stackedReaderSetting(1f, 560f))
    }

    @Test fun denserContentsKeepsAccessibleMinimumInsteadOfTheOldSixtyDp() {
        assertTrue(ContentsRowMinimumHeightDp >= 44f)
        assertTrue(ContentsRowMinimumHeightDp < 60f)
        assertTrue(ContentsRowMinimumHeightDp >= 60f * 2f / 3f)
    }
}
