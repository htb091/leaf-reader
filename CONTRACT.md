# Implementation contract

Package: `dev.leaf.reader`. App name: 叶读 / Leaf Reader. First delivered host: iOS 16+, ARM64, unsigned IPA for TrollStore. Shared UI and domain remain suitable for adding Android later; this iteration does not claim an Android APK.

## Shared API (Lead owns)

`@Serializable data class BookChapter(val title: String, val paragraphs: List<String>)`
`@Serializable data class BookDocument(val id: String, val title: String, val author: String = "", val format: String = "TXT", val chapters: List<BookChapter>)`
`@Serializable data class ReadingProgress(val itemIndex: Int = 0, val scrollOffset: Int = 0)`
`@Serializable data class ShelfBook(val id: String, val title: String, val author: String, val format: String, val chapterCount: Int, val paragraphCount: Int, val addedAt: Long, val lastOpenedAt: Long = 0, val progress: ReadingProgress = ReadingProgress())`
`@Serializable enum class ReaderTheme { SYSTEM, LIGHT, DARK, SEPIA }`
`@Serializable data class ReaderSettings(val fontSize: Float = 20f, val lineHeight: Float = 1.7f, val theme: ReaderTheme = ReaderTheme.SYSTEM)`
`data class LibraryState(val books: List<ShelfBook> = emptyList(), val currentBook: BookDocument? = null, val currentProgress: ReadingProgress = ReadingProgress(), val settings: ReaderSettings = ReaderSettings(), val busy: Boolean = false, val error: String? = null)`

`class ReaderStore` exposes `val state: StateFlow<LibraryState>` and non-suspend public methods `openBook(id: String)`, `closeBook()`, `updateProgress(itemIndex: Int, scrollOffset: Int)`, `updateSettings(settings: ReaderSettings)`, `deleteBook(id: String)`, `dismissError()`, `importBookJson(json: String)`, `reportError(message: String)`, `flush()`.

`object ReaderRuntime { val store: ReaderStore; fun importBook(json: String); fun reportError(message: String); fun flush() }` available from Swift through `ReaderRuntime.shared`.

`fun MainViewController(onImportRequested: () -> Unit): UIViewController` (Lead owns iOS Kotlin entry) is exported as MainViewControllerKt.MainViewController(onImportRequested:).

Shared UI entry: `@Composable fun ReaderApp(store: ReaderStore, onImportRequested: () -> Unit)` in package `dev.leaf.reader.ui`.

## Flattened reading list

For each chapter: one title item, then one item for every paragraph. ReadingProgress.itemIndex indexes this flattened list, scrollOffset is a nonnegative pixel offset. UI must use exactly this ordering and must not persist stale scroll values while restoring/changing books. Change of font metrics can fall back to the same paragraph at offset zero.

## Swift import boundary

Swift parses local TXT or EPUB to JSON matching BookDocument; id is SHA-256 of original file bytes, format TXT or EPUB. Swift calls ReaderRuntime.shared.importBook(json:). UTF-8/UTF-16 BOM and GB18030 decoding for TXT. EPUB uses ZIPFoundation + SwiftSoup: OPF spine order, title/author metadata and basic readable body paragraphs. No image/CSS/script/fixed-layout/DRM support in v0.1. Reject encrypted/oversized archives; constrain paths and decompressed bytes. Never extract archive paths to arbitrary filesystem locations.

JSON top-level keys: id,title,author,format,chapters; chapter keys:title,paragraphs. No original book text in logs.

## Ownership

- Lead: Gradle/build/wrapper, shared models/store/files implementations, MainViewController, CI, docs/package.
- ui teammate: ONLY shared/src/commonMain/kotlin/dev/leaf/reader/ui/**.
- ios teammate: ONLY iosApp/** (Swift host/importer, project.yml, Info.plist, Swift tests). Scheme and target LeafReader; shared static framework name Shared; framework is prebuilt by CI and located ../shared/build/bin/iosArm64/releaseFramework/Shared.framework. project.yml has no Gradle script phase. iOS deployment target 16.0.

All teammates inspect the session skill catalog/tools first and load applicable skills; none of the available dsh-go-specific skills match this standalone app. Use read/glob/grep and coordinated disjoint edits; do not commit or push. Missing integration facts go to Lead via send_message.
