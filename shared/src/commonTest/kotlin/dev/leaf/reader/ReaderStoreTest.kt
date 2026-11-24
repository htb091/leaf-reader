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
        store.importBookJson(sample.encoded())
        advanceUntilIdle()
        assertEquals(1, store.state.value.books.size)
        assertEquals(ReadingProgress(3, 42), store.state.value.currentProgress)
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
        assertEquals(ReadingProgress(2, 75), restored.state.value.currentProgress)
    }

    @Test fun clampsInvalidProgressToExistingItems() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(9999, -3)
        assertEquals(ReadingProgress(4, 0), store.state.value.currentProgress)
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
        store.updateProgress(2, 7); store.closeBook()
        files.values.remove("book-${sample.id}.json")
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        assertNotNull(store.state.value.currentBook)
        assertEquals(ReadingProgress(2, 7), store.state.value.currentProgress)
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

    @Test fun settingsAndDocumentLimitsAreEnforced() {
        assertEquals(36f, ReaderSettings(fontSize = 100f).sanitized().fontSize)
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
