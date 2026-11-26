package dev.leaf.reader.ui

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class ContentsNavigationTest {
    @Test fun searchKeepsRealChapterIndicesAndIgnoresCase() {
        val titles = listOf("Alpha", "第二章", "ALPHA 续", "尾声")
        assertEquals(listOf(0, 2), contentsChapterIndices(titles, "  alpha  ", false))
        assertEquals(listOf(2, 0), contentsChapterIndices(titles, "alpha", true))
        assertEquals(listOf(1), contentsChapterIndices(titles, "第二", false))
    }

    @Test fun duplicatesAndBlankHeadingsAreNotMerged() {
        val titles = listOf("重复", "", "重复")
        assertEquals(listOf(0, 1, 2), contentsChapterIndices(titles, "", false))
        assertEquals(listOf(0, 2), contentsChapterIndices(titles, "重复", false))
        assertEquals(listOf(1), contentsChapterIndices(titles, "第 2 章", false))
    }

    @Test fun numericSearchUsesOneBasedChapterNumber() {
        val titles = listOf("序", "正文", "终")
        assertEquals(listOf(1), contentsChapterIndices(titles, "2", false))
        assertTrue(contentsChapterIndices(titles, "0", false).isEmpty())
        assertTrue(contentsChapterIndices(titles, "999999999999999999", false).isEmpty())
    }

    @Test fun locateUsesPositionInFilteredReversedListNotChapterNumber() {
        val titles = listOf("选中一", "其他", "选中二", "选中三")
        val matches = contentsChapterIndices(titles, "选中", true)
        assertEquals(listOf(3, 2, 0), matches)
        assertEquals(1, contentsChapterPosition(matches, 2))
        assertNull(contentsChapterPosition(matches, 1))
        assertNull(contentsChapterPosition(emptyList(), 0))
    }

    @Test fun fiftyThousandChapterMetadataRetainsLastChapter() {
        val titles = List(50_000) { "Chapter ${it + 1}" }
        val reversed = contentsChapterIndices(titles, "", true)
        assertEquals(50_000, reversed.size)
        assertEquals(49_999, reversed.first())
        assertEquals(0, contentsChapterPosition(reversed, 49_999))
        assertEquals(49_999, contentsChapterPosition(reversed, 0))
        assertEquals(listOf(49_999), contentsChapterIndices(titles, "50000", false))
    }

    @Test fun clearSearchRestoresCurrentChapterPositionForEitherOrder() {
        val titles = List(800) { "章节 $it" }
        assertEquals(405, contentsChapterPosition(contentsChapterIndices(titles, "", false), 405))
        assertEquals(394, contentsChapterPosition(contentsChapterIndices(titles, "", true), 405))
    }

    @Test fun shortWindowsKeyboardAndLargeFontsUseCompactContents() {
        assertTrue(compactContentsLayout(360f, 1f))
        assertTrue(compactContentsLayout(480f, 1f))
        assertTrue(compactContentsLayout(640f, 1.5f))
        assertFalse(compactContentsLayout(800f, 1f))
        assertFalse(compactContentsLayout(884f, 1.5f))
    }
}
