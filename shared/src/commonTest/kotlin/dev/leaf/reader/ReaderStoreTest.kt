@file:OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)

package dev.leaf.reader

import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlin.test.assertFailsWith

class ReaderStoreTest {
    private val sample = BookDocument(
        id = "a".repeat(64), title = "测试书", author = "作者", format = "TXT",
        chapters = listOf(BookChapter("第一章", listOf("第一段。", "第二段 😀。")), BookChapter("第二章", listOf("结束。"))),
    )
    private fun BookDocument.encoded() = Json.encodeToString(this)

    @Test fun importsAndReopensWithoutDuplicating() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded())
        advanceUntilIdle()
        assertEquals(1, store.state.value.books.size)
        store.openBook(sample.id)
        advanceUntilIdle()
        store.updateProgress(3, 42)
        advanceUntilIdle() // The legacy adapter loads a different chapter asynchronously.
        store.importBookJson(sample.encoded())
        advanceUntilIdle()
        assertEquals(1, store.state.value.books.size)
        assertProgress(store.state.value.currentProgress, item = 3, scroll = 42, chapter = 1, paragraph = 0)
    }

    @Test fun positionAndSettingsSurviveRestart() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(2, 75)
        store.updateSettings(ReaderSettings(fontSize = 25f, theme = ReaderTheme.SEPIA))
        store.flush()
        val restored = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertEquals(25f, restored.state.value.settings.fontSize)
        assertEquals(ReaderTheme.SEPIA, restored.state.value.settings.theme)
        restored.openBook(sample.id); advanceUntilIdle()
        assertProgress(restored.state.value.currentProgress, item = 2, scroll = 75, chapter = 0, paragraph = 2)
    }

    @Test fun clampsInvalidProgressToExistingItems() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(9999, -3)
        advanceUntilIdle()
        assertProgress(store.state.value.currentProgress, item = 4, scroll = 0, chapter = 1, paragraph = 1)
    }

    @Test fun closingBeforeOpenFinishesDoesNotReopen() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id)
        store.closeBook()
        advanceUntilIdle()
        assertNull(store.state.value.currentBook)
        assertFalse(store.state.value.busy)
    }

    @Test fun deletingDuringOpenDoesNotLeaveLoadingOverlay() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id)
        store.deleteBook(sample.id)
        advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertNull(store.state.value.currentBook)
        assertFalse(store.state.value.busy)
    }

    @Test fun removesShelfAndDerivedBookButNotOtherFiles() = runTest {
        val files = MemoryFiles()
        files.values["unrelated"] = "keep"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.deleteBook(sample.id); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertNull(files.values["book-${sample.id}.json"])
        assertNull(files.values["book-${sample.id}.manifest.json"])
        assertTrue(files.values.keys.none { it.startsWith("book-${sample.id}-") })
        assertEquals("keep", files.values["unrelated"])
    }

    @Test fun rejectedDocumentDoesNotReachShelf() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.copy(id = "../escape").encoded()); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertNotNull(store.state.value.error)
        assertTrue(files.values.keys.none { it.contains("escape") })
    }

    @Test fun failedIndexWriteRollsBackShelfAndPreservesOldIndex() = runTest {
        val files = MemoryFiles()
        val original = "{\"schema\":1,\"books\":[],\"settings\":{}}"
        files.values["library.json"] = original
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.failIndexWrite = true
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertEquals(original, files.values["library.json"])
        assertNotNull(store.state.value.error)
    }

    @Test fun corruptIndexIsNeverSilentlyOverwritten() = runTest {
        val files = MemoryFiles()
        files.values["library.json"] = "corrupt original"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.dismissError()
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.flush()
        assertEquals("corrupt original", files.values["library.json"])
        assertTrue(store.state.value.books.isEmpty())
        assertNotNull(store.state.value.error)
    }

    @Test fun reimportRepairsMissingDerivedFileWithoutLosingProgress() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(2, 7)
        val missingChapter = store.state.value.manifest!!.chapters[0].fileName
        store.closeBook()
        files.values.remove(missingChapter)
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        assertNotNull(store.state.value.currentBook)
        assertProgress(store.state.value.currentProgress, item = 2, scroll = 7, chapter = 0, paragraph = 2)
        assertNotNull(store.state.value.chapter)
    }

    @Test fun rapidOpeningKeepsLatestBook() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        val second = sample.copy(id = "b".repeat(64), title = "另一本")
        store.importBookJson(sample.encoded()); store.importBookJson(second.encoded()); advanceUntilIdle()
        store.openBook(sample.id)
        store.openBook(second.id)
        advanceUntilIdle()
        assertEquals(second.id, store.state.value.currentBook?.id)
    }

    @Test fun debounceSavesAndDismissErrorDoesNotLoseBook() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(1, 3)
        runCurrent(); advanceUntilIdle()
        assertTrue(files.values.getValue("library.json").contains("\"scrollOffset\":3"))
        store.reportError("测试提示"); store.dismissError()
        assertNull(store.state.value.error)
        assertEquals(sample.id, store.state.value.currentBook?.id)
    }

    @Test fun chapterAnchorsPersistAcrossAsyncNavigationAndRestart() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateChapterProgress(paragraphIndex = 2, characterOffset = 5, scrollOffset = 11)
        // UTF-16 index 5 bisects the emoji and must move back to the high surrogate.
        assertProgress(store.state.value.currentProgress, 2, 11, 0, 2, character = 4)
        store.selectChapter(1)
        assertTrue(store.state.value.chapterBusy)
        assertNull(store.state.value.chapter)
        store.updateChapterProgress(0, 0, 0) // Initial/unmeasured UI saves must be ignored.
        assertProgress(store.state.value.books.single().progress, 2, 11, 0, 2, character = 4)
        advanceUntilIdle()
        assertEquals("第二章", store.state.value.chapter?.title)
        store.updateChapterProgress(1, 2, 9)
        store.flush()
        val restored = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restored.openBook(sample.id); advanceUntilIdle()
        assertEquals(1, restored.state.value.chapterIndex)
        assertFalse(restored.state.value.chapterBusy)
        assertProgress(restored.state.value.currentProgress, 4, 9, 1, 1, character = 2)
        assertProgress(restored.state.value.books.single().progress, 4, 9, 1, 1, character = 2)
    }

    @Test fun previousChapterAtEndClampsSentinelAfterBodyLoads() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.selectChapter(1); advanceUntilIdle()
        store.selectChapter(0, atEnd = true)
        assertTrue(store.state.value.chapterBusy)
        assertEquals(Int.MAX_VALUE, store.state.value.currentProgress.characterOffset)
        advanceUntilIdle()
        assertProgress(store.state.value.currentProgress, 2, 0, 0, 2,
            character = sample.chapters[0].paragraphs.last().length)
    }

    @Test fun rapidChapterSelectionAndCloseDiscardObsoleteLoads() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.selectChapter(1)
        store.selectChapter(0)
        advanceUntilIdle()
        assertEquals("第一章", store.state.value.chapter?.title)
        assertProgress(store.state.value.currentProgress, 0, 0, 0, 0)
        store.selectChapter(1)
        store.closeBook()
        advanceUntilIdle()
        assertNull(store.state.value.currentBook)
        assertNull(store.state.value.manifest)
        assertNull(store.state.value.chapter)
        assertFalse(store.state.value.chapterBusy)
        assertFalse(store.state.value.busy)
    }

    @Test fun allReadingAndShelfOptionsSurviveRestart() = runTest {
        val files = MemoryFiles()
        val settings = ReaderSettings(
            fontSize = 27f, lineHeight = 2f, theme = ReaderTheme.DARK,
            readingMode = ReadingMode.INSTANT, columnMode = ColumnMode.DOUBLE,
            shelfLayout = ShelfLayout.COMPACT, fontFamily = ReaderFont.MONO,
            horizontalMargin = 32f, paragraphSpacing = 18f, letterSpacing = 1.5f,
            firstLineIndent = false, bold = true, autoHideControls = false, showReadingFooter = false,
        )
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.updateSettings(settings)
        advanceUntilIdle()
        val restored = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertEquals(settings, restored.state.value.settings)
    }

    private fun assertProgress(
        actual: ReadingProgress, item: Int, scroll: Int, chapter: Int, paragraph: Int, character: Int = 0,
    ) {
        assertEquals(item, actual.itemIndex, "global item")
        assertEquals(scroll, actual.scrollOffset, "pixel offset")
        assertEquals(chapter, actual.chapterIndex, "chapter anchor")
        assertEquals(paragraph, actual.paragraphIndex, "chapter-local heading/paragraph")
        assertEquals(character, actual.characterOffset, "UTF-16 text anchor")
    }

    @Test fun settingsAndDocumentLimitsAreEnforced() {
        assertEquals(40f, ReaderSettings(fontSize = 100f).sanitized().fontSize)
        assertEquals(20f, ReaderSettings(fontSize = Float.NaN).sanitized().fontSize)
        assertFailsWith<IllegalArgumentException> { sample.copy(chapters = emptyList()).validate() }
        assertFailsWith<IllegalArgumentException> { sample.copy(format = "PDF").validate() }
        assertFailsWith<IllegalArgumentException> { sample.copy(chapters = listOf(BookChapter("", listOf(" ")))).validate() }
        assertFailsWith<IllegalArgumentException> { sample.copy(chapters = listOf(BookChapter("", listOf("x".repeat(16001))))).validate() }
        sample.validate()
    }
}

private class MemoryFiles : ReaderFiles {
    val values = mutableMapOf<String, String>()
    var failIndexWrite = false
    override fun readText(name: String) = values[name]
    override fun writeText(name: String, value: String) {
        if (failIndexWrite && name == "library.json") error("disk full")
        values[name] = value
    }
    override fun delete(name: String) { values.remove(name) }
    override fun nowMillis() = 1000L
}
