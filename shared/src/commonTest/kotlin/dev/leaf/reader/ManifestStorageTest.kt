@file:OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)

package dev.leaf.reader

import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class ManifestStorageTest {
    private val id = "c".repeat(64)
    private val revision = "1".repeat(32)
    private fun canonical(bookId: String = id) = "book-$bookId.manifest.json"

    private data class Fixture(val manifest: BookManifest, val chapters: List<BookChapter>)

    private fun fixture(
        chapters: List<BookChapter> = List(5) { BookChapter("第 ${it + 1} 章", listOf("正文 $it 😀", "尾段 $it")) },
        revision: String = this.revision,
        title: String = "分章书籍",
    ): Fixture = Fixture(
        BookManifest(id = id, title = title, revision = revision, chapters = chapters.mapIndexed { index, chapter ->
            ChapterEntry(chapter.title, "book-$id-$revision-c$index.json", chapter.paragraphs.size,
                chapter.paragraphs.sumOf { it.length })
        }), chapters,
    )

    private fun ManifestFiles.install(fixture: Fixture) {
        fixture.chapters.forEachIndexed { index, chapter ->
            values[fixture.manifest.chapters[index].fileName] = Json.encodeToString(chapter)
        }
    }

    @Test fun chapterUtf16LimitAcceptsExact512KiAndRejectsOneMoreUnit() {
        assertEquals(512 * 1024, MAX_CHAPTER_UNITS)
        fun chapter(units: Int): BookChapter = BookChapter("边界", buildList {
            var remaining = units
            while (remaining > 0) {
                val size = minOf(remaining, 16000)
                add("字".repeat(size))
                remaining -= size
            }
        })
        val exact = chapter(512 * 1024)
        val entry = fixture(listOf(exact)).manifest.chapters.single()
        exact.validate(entry)
        assertEquals(512 * 1024, entry.characterCount)
        assertFailsWith<IllegalArgumentException> { chapter(512 * 1024 + 1).validate() }
        assertFailsWith<IllegalArgumentException> {
            fixture(listOf(exact)).manifest.copy(chapters = listOf(entry.copy(characterCount = 512 * 1024 + 1))).validate()
        }
        // UTF-16 units, not Unicode code points: each emoji occupies two units.
        assertEquals(16000, "😀".repeat(8000).length)
        assertFailsWith<IllegalArgumentException> { BookChapter("段落边界", listOf("😀".repeat(8001))).validate() }
    }

    @Test fun manifestRejectsTraversalAbsoluteAndWrongRevisionOrIndexNames() {
        val valid = fixture().manifest
        valid.validate()
        val name = valid.chapters.first().fileName
        val invalid = listOf(
            "../$name", "/$name", "folder/$name", "folder\\$name", "./$name",
            "book-${"d".repeat(64)}-$revision-c0.json",
            "book-$id-${"2".repeat(32)}-c0.json", "book-$id-$revision-c00.json",
            "book-$id-$revision-c1.json", "$name/..", "$name\u0000",
        )
        invalid.forEach { candidate ->
            assertFailsWith<IllegalArgumentException>(candidate) {
                valid.copy(chapters = valid.chapters.toMutableList().also {
                    it[0] = it[0].copy(fileName = candidate)
                }).validate()
            }
        }
        assertFailsWith<IllegalArgumentException> { valid.copy(schema = 1).validate() }
        assertFailsWith<IllegalArgumentException> { valid.copy(revision = "A".repeat(32)).validate() }
        assertFailsWith<IllegalArgumentException> { valid.copy(id = "../bad").validate() }
    }

    @Test fun invalidManifestPathIsRejectedBeforeAnyBodyReadOrPublication() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        files.values["unrelated.json"] = "keep"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.reads.clear()
        val invalid = draft.manifest.copy(chapters = draft.manifest.chapters.toMutableList().also {
            it[1] = it[1].copy(fileName = "../unrelated.json")
        })
        store.importManifestJson(Json.encodeToString(invalid)); advanceUntilIdle()
        assertTrue(files.reads.isEmpty())
        assertTrue(store.state.value.books.isEmpty())
        assertNull(files.values[canonical()])
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.busy)
        assertEquals("keep", files.values["unrelated.json"])
    }

    @Test fun paragraphLimitUsesLongArithmeticBeforeSummingManifestMetadata() {
        val counts = List(42949) { 100000 } + 67297 // 2^32 + 1, not one paragraph.
        val manifest = BookManifest(id = id, title = "溢出边界", revision = revision,
            chapters = counts.mapIndexed { index, count ->
                ChapterEntry("章", "book-$id-$revision-c$index.json", count, 1)
            })
        assertEquals(4_294_967_297L, counts.sumOf { it.toLong() })
        assertFailsWith<IllegalArgumentException> { manifest.validate() }
    }

    @Test fun schema1LibraryKeepsBackupAndMigratesSplitChapterProgressLazily() = runTest {
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "字".repeat(10000) }), BookChapter("后记", listOf("尾")),
        ))
        val original = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":2,"paragraphCount":41,"addedAt":10,"lastOpenedAt":20,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{"fontSize":23,"lineHeight":1.8,"theme":"SEPIA"}}"""
        val files = ManifestFiles()
        files.values["library.json"] = original
        val legacyRaw = Json.encodeToString(legacy)
        files.values["book-$id.json"] = legacyRaw
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertEquals(original, files.values["library.v1-backup.json"])
        assertEquals(original, files.values["library.json"])
        assertNull(files.values[canonical()]) // Startup does not decode every old book body.
        assertEquals(ReadingMode.SLIDE, store.state.value.settings.readingMode)
        assertEquals(ShelfLayout.GRID, store.state.value.settings.shelfLayout)
        store.openBook(id); advanceUntilIdle()
        val state = store.state.value
        val manifest = assertNotNull(state.manifest)
        assertEquals(3, manifest.chapters.size)
        assertTrue(manifest.chapters.all { it.characterCount <= 512 * 1024 })
        assertEquals(400001L, state.books.single().characterCount)
        assertTrue(state.currentBook!!.chapters.all { it.paragraphs.isEmpty() })
        assertEquals("长章（续）", state.chapter?.title)
        assertEquals(1, state.currentProgress.chapterIndex)
        assertEquals(5, state.currentProgress.paragraphIndex)
        assertEquals(32, state.currentProgress.itemIndex) // New split heading shifts the legacy global index.
        assertEquals(57, state.currentProgress.scrollOffset)
        assertEquals(0, state.currentProgress.characterOffset)
        assertEquals(legacyRaw, files.values["book-$id.json"])
        store.closeBook()
        assertEquals(2, Json.decodeFromString<LibrarySnapshot>(files.values.getValue("library.json")).schema)
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(1, restarted.state.value.currentProgress.chapterIndex)
        assertEquals(5, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(57, restarted.state.value.currentProgress.scrollOffset)
        assertEquals(original, files.values["library.v1-backup.json"])
        assertEquals(23f, restarted.state.value.settings.fontSize)
        assertEquals(ReaderTheme.SEPIA, restarted.state.value.settings.theme)
    }

    @Test fun canceledLegacyMigrationKeepsOriginalParagraphAnchor() = runTest {
        val files = ManifestFiles()
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "段${it.toString().padStart(2, '0')}" + "字".repeat(9997) }),
        ))
        files.values["book-$id.json"] = Json.encodeToString(legacy)
        files.values["library.json"] = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":1,"paragraphCount":40,"addedAt":10,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{}}"""
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.openBook(id)
        store.closeBook() // The queued migration can finish I/O but must not publish a wrong anchor.
        advanceUntilIdle()
        assertNull(store.state.value.currentBook)
        store.openBook(id); advanceUntilIdle()
        assertEquals(1, store.state.value.currentProgress.chapterIndex)
        assertEquals(5, store.state.value.currentProgress.paragraphIndex)
        assertEquals(32, store.state.value.currentProgress.itemIndex)
        assertEquals(57, store.state.value.currentProgress.scrollOffset)
        val state = store.state.value
        assertEquals(legacy.chapters.single().paragraphs[30],
            state.chapter?.paragraphs?.get(state.currentProgress.paragraphIndex - 1))
    }

    @Test fun migrationIndexWriteFailureRetainsOriginalParagraphAfterRestart() = runTest {
        val files = ManifestFiles()
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "段${it.toString().padStart(2, '0')}" + "字".repeat(9997) }),
        ))
        files.values["book-$id.json"] = Json.encodeToString(legacy)
        files.values["library.json"] = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":1,"paragraphCount":40,"addedAt":10,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{}}"""
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        // Initial flush may succeed; every later index write fails once the migrated manifest exists.
        files.blockWrites = { name -> name == "library.json" && canonical() in files.values }
        store.openBook(id); advanceUntilIdle()
        assertNotNull(store.state.value.error)
        val onDisk = Json.decodeFromString<LibrarySnapshot>(files.values.getValue("library.json"))
        assertEquals(-1, onDisk.books.single().progress.chapterIndex)
        assertEquals(31, onDisk.books.single().progress.itemIndex)
        files.blockWrites = { false }
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        val state = restarted.state.value
        assertEquals(1, state.currentProgress.chapterIndex)
        assertEquals(5, state.currentProgress.paragraphIndex)
        assertEquals(32, state.currentProgress.itemIndex)
        assertEquals(57, state.currentProgress.scrollOffset)
        assertEquals(legacy.chapters.single().paragraphs[30],
            state.chapter?.paragraphs?.get(state.currentProgress.paragraphIndex - 1))
    }

    @Test fun legacyReimportMapsUnmigratedShelfAnchorBeforeFirstOpen() = runTest {
        val files = ManifestFiles()
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "段${it.toString().padStart(2, '0')}" + "字".repeat(9997) }),
        ))
        files.values["library.json"] = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":1,"paragraphCount":40,"addedAt":10,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{}}"""
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(Json.encodeToString(legacy)); advanceUntilIdle()
        val saved = store.state.value.books.single().progress
        assertEquals(1, saved.chapterIndex)
        assertEquals(5, saved.paragraphIndex)
        assertEquals(32, saved.itemIndex)
        store.openBook(id); advanceUntilIdle()
        val state = store.state.value
        assertEquals(57, state.currentProgress.scrollOffset)
        assertEquals(legacy.chapters.single().paragraphs[30],
            state.chapter?.paragraphs?.get(state.currentProgress.paragraphIndex - 1))
    }

    @Test fun existingV1BackupIsNeverOverwritten() = runTest {
        val files = ManifestFiles()
        files.values["library.json"] = """{"schema":1,"books":[],"settings":{}}"""
        files.values["library.v1-backup.json"] = "earlier backup"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.flush()
        assertNull(store.state.value.error)
        assertEquals("earlier backup", files.values["library.v1-backup.json"])
    }

    @Test fun failedV1BackupPreventsOverwritingTheOnlyLegacyIndex() = runTest {
        val files = ManifestFiles()
        val original = """{"schema":1,"books":[],"settings":{"fontSize":22}}"""
        files.values["library.json"] = original
        files.failNextWrites["library.v1-backup.json"] = 1
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertNotNull(store.state.value.error)
        store.dismissError()
        store.updateSettings(ReaderSettings(fontSize = 30f))
        advanceUntilIdle()
        store.flush()
        assertEquals(original, files.values["library.json"])
        assertNull(files.values["library.v1-backup.json"])
    }

    @Test fun importSamplesEndpointsAndOpeningLoadsOnlyCurrentChapterBody() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.reads.clear()
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        val bodyNames = draft.manifest.chapters.map { it.fileName }.toSet()
        assertEquals(listOf(draft.manifest.chapters.first().fileName, draft.manifest.chapters.last().fileName),
            files.reads.filter { it in bodyNames })
        files.reads.clear()
        store.openBook(id); advanceUntilIdle()
        assertEquals(listOf(canonical(), draft.manifest.chapters[0].fileName), files.reads)
        assertEquals(draft.chapters[0], store.state.value.chapter)
        assertTrue(store.state.value.currentBook!!.chapters.all { it.paragraphs.isEmpty() })
        assertEquals(5, store.state.value.currentBook!!.chapters.size)
        assertFalse(files.reads.contains("book-$id.json"))
        files.reads.clear()
        store.selectChapter(2); advanceUntilIdle()
        assertEquals(listOf(draft.manifest.chapters[2].fileName), files.reads)
        assertEquals(draft.chapters[2], store.state.value.chapter)
    }

    @Test fun chapterCacheIsBoundedAndCloseDropsCachedBodies() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        store.openBook(id); advanceUntilIdle()
        files.reads.clear()
        store.selectChapter(0); advanceUntilIdle()
        assertTrue(files.reads.isEmpty())
        for (index in 1..3) { store.selectChapter(index); advanceUntilIdle() }
        files.reads.clear()
        store.selectChapter(0); advanceUntilIdle()
        assertEquals(listOf(draft.manifest.chapters[0].fileName), files.reads)
        store.closeBook()
        files.reads.clear()
        store.openBook(id); advanceUntilIdle()
        assertTrue(draft.manifest.chapters[0].fileName in files.reads)
    }

    @Test fun mismatchedMiddleChapterFailsOnDemandAndRetainsLastReadableShelfAnchor() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        files.values[draft.manifest.chapters[1].fileName] = Json.encodeToString(BookChapter("损坏", listOf("不匹配")))
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        assertNull(store.state.value.error) // Import validates bounded endpoints, not every chapter body.
        store.openBook(id); advanceUntilIdle()
        store.updateChapterProgress(1, 2, 17)
        store.selectChapter(1); advanceUntilIdle()
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.chapterBusy)
        assertNull(store.state.value.chapter)
        val saved = store.state.value.books.single().progress
        assertEquals(0, saved.chapterIndex)
        assertEquals(1, saved.paragraphIndex)
        assertEquals(2, saved.characterOffset)
        assertEquals(17, saved.scrollOffset)
        store.closeBook()
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(draft.chapters[0], restarted.state.value.chapter)
        assertEquals(0, restarted.state.value.currentProgress.chapterIndex)
        assertEquals(1, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(2, restarted.state.value.currentProgress.characterOffset)
    }

    @Test fun newManifestIndexFailureRemovesCanonicalAndAllowsRetry() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        val original = Json.encodeToString(LibrarySnapshot())
        files.values["library.json"] = original
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.failNextWrites["library.json"] = 1
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertEquals(original, files.values["library.json"])
        assertNull(files.values[canonical()])
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.busy)
        assertTrue(draft.manifest.chapters.all { it.fileName in files.values }) // Draft revision is recoverable.
        store.dismissError()
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        assertEquals(id, store.state.value.books.single().id)
        assertNotNull(files.values[canonical()])
        assertNull(store.state.value.error)
    }

    @Test fun replacementIndexFailureRestoresPriorManifestShelfAndAnchorThenRecovers() = runTest {
        val files = ManifestFiles()
        val old = fixture()
        val replacement = fixture(revision = "2".repeat(32), title = "新版书名")
        files.install(old); files.install(replacement)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(old.manifest)); advanceUntilIdle()
        store.openBook(id); advanceUntilIdle()
        store.updateChapterProgress(1, 2, 13)
        store.closeBook()
        val oldCanonical = files.values.getValue(canonical())
        val oldIndex = files.values.getValue("library.json")
        files.failNextWrites["library.json"] = 1
        store.importManifestJson(Json.encodeToString(replacement.manifest)); advanceUntilIdle()
        assertEquals(oldCanonical, files.values[canonical()])
        assertEquals(oldIndex, files.values["library.json"])
        assertEquals(old.manifest.title, store.state.value.books.single().title)
        assertNotNull(store.state.value.error)
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(old.manifest.revision, restarted.state.value.manifest?.revision)
        assertEquals(1, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(2, restarted.state.value.currentProgress.characterOffset)
        assertEquals(13, restarted.state.value.currentProgress.scrollOffset)
        restarted.closeBook()
        restarted.importManifestJson(Json.encodeToString(replacement.manifest)); advanceUntilIdle()
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(replacement.manifest.revision, restarted.state.value.manifest?.revision)
        assertEquals(replacement.manifest.title, restarted.state.value.books.single().title)
        assertEquals(1, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(2, restarted.state.value.currentProgress.characterOffset)
        assertNull(restarted.state.value.error)
    }

    @Test fun failedAtomicCanonicalWritePreservesPreviouslyPublishedRevision() = runTest {
        val files = ManifestFiles()
        val old = fixture()
        val replacement = fixture(revision = "2".repeat(32), title = "未发布副本")
        files.install(old); files.install(replacement)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(old.manifest)); advanceUntilIdle()
        val oldCanonical = files.values.getValue(canonical())
        val oldIndex = files.values.getValue("library.json")
        files.failNextWrites[canonical()] = 1
        store.importManifestJson(Json.encodeToString(replacement.manifest)); advanceUntilIdle()
        assertEquals(oldCanonical, files.values[canonical()])
        assertEquals(oldIndex, files.values["library.json"])
        assertEquals(old.manifest.title, store.state.value.books.single().title)
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.busy)
    }
}

/** Faults occur before commit, matching ReaderFiles' atomic-replacement contract. */
private class ManifestFiles : ReaderFiles {
    val values = mutableMapOf<String, String>()
    val reads = mutableListOf<String>()
    val failNextWrites = mutableMapOf<String, Int>()
    var blockWrites: (String) -> Boolean = { false }
    override fun readText(name: String): String? {
        reads += name
        return values[name]
    }
    override fun writeText(name: String, value: String) {
        if (blockWrites(name)) error("injected persistent pre-commit failure")
        val remaining = failNextWrites[name] ?: 0
        if (remaining > 0) {
            failNextWrites[name] = remaining - 1
            error("injected pre-commit write failure")
        }
        values[name] = value
    }
    override fun delete(name: String) { values.remove(name) }
    override fun nowMillis() = 2000L
}
