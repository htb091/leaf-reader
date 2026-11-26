package dev.leaf.reader.ui

import java.io.File
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * No DISPLAY/Skiko window required. These are source-structure guards, NOT simulated UI clicks.
 * They protect the real v0.4 regression: OverlayBottomSheet registered a dialog but no ancestor
 * Miuix Scaffold/MiuixPopupHost ever rendered that registration in the reading branch.
 */
class ReaderHostStructureTest {
    private fun source(name: String): String {
        val relative = "src/commonMain/kotlin/dev/leaf/reader/ui/$name"
        val module = File(System.getProperty("user.dir"))
        val candidates = listOf(File(module, relative), File(module, "shared/$relative"),
            File(module.parentFile, "shared/$relative"))
        val file = candidates.firstOrNull { it.isFile }
            ?: error("Run this source-structure test from the repository root or shared module: $name")
        return file.readText()
    }

    @Test fun readerSettingsIsComposedInsideItsOwnZeroInsetScaffold() {
        val screen = source("ReadingScreen.kt")
        val host = screen.indexOf("Scaffold(modifier = Modifier.fillMaxSize()")
        val settings = screen.indexOf("ReadingSettings(settingsOpen")
        assertTrue(host >= 0 && settings > host, "Reader settings requires an ancestor Miuix Scaffold popup host")
        assertTrue(screen.contains("contentWindowInsets = WindowInsets(0, 0, 0, 0)"),
            "The local popup host must not add a second safe area to measured chapter content")
    }

    @Test fun sheetAndRealDropdownUseTheReadersLocalHost() {
        val settings = source("ReadingSettings.kt")
        assertTrue(settings.contains("OverlayBottomSheet("))
        assertTrue(settings.contains("OverlayListPopup("))
        assertTrue(settings.contains("ListPopupColumn {"))
        assertTrue(settings.contains("DropdownImpl("))
        assertTrue(Regex("renderInRootScaffold\\s*=\\s*false").findAll(settings).count() >= 2,
            "Both sheet and option list must render through the local reader host")
        assertFalse(settings.contains("TabRowWithContour("), "Preferences now use an actual Miuix popup list")
    }

    @Test fun blurCaptureIncludesPaperAndExcludesTheChrome() {
        val screen = source("ReadingScreen.kt")
        assertTrue(screen.contains("rememberLayerBackdrop { drawRect(paper); drawContent() }"))
        val capture = screen.indexOf(".layerBackdrop(backdrop)")
        val header = screen.indexOf("ReaderChrome(visible = state.chromeVisible")
        assertTrue(capture >= 0 && header > capture)
        assertTrue(screen.contains("SideEffect { chromeProgress = progressText }"),
            "Chrome must be emitted outside the chapter safe-area metrics container")
    }

    @Test fun chromeHasNoTopContentsShortcutOrFixedDockHeight() {
        val chrome = source("ReaderChrome.kt")
        assertFalse(chrome.contains("ReaderIconButton(Glyph.TOC"))
        assertTrue(chrome.contains("ReaderDockAction(Glyph.BOOK, \"目录\", onDirectory)"))
        assertTrue(chrome.contains("ReaderDockAction(Glyph.TUNE, \"设置\", onSettings)"))
        assertTrue(chrome.contains("backdrop = backdrop"))
        assertFalse(chrome.contains(".height(ReaderDockMinimumHeightDp.dp)"),
            "Large Dynamic Type must be allowed to grow the dock rather than be clipped")
    }
}
