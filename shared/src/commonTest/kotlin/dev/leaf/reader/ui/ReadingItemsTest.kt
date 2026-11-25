package dev.leaf.reader.ui

import dev.leaf.reader.BookChapter
import dev.leaf.reader.BookDocument
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** Replaces legacy whole-book flattening tests with the chapter-local coordinate contract. */
class ReadingItemsTest {
    @Test fun headingAndParagraphsKeepExactLocalOrder() {
        val texts = chapterReadingTexts(BookChapter("第一章", listOf("甲", "乙")), 0)
        assertEquals(listOf("第一章", "甲", "乙"), texts)
        assertEquals("甲", texts[TextAnchor(paragraphIndex = 1).paragraphIndex])
    }

    @Test fun titleOnlyMetadataNeverSuppliesBodyText() {
        val metadata = BookDocument(id = "a".repeat(64), title = "测试书籍", chapters =
            listOf(BookChapter("第一章", emptyList()), BookChapter("第二章", emptyList())))
        val loaded = BookChapter("第二章", listOf("当前章正文"))
        val texts = chapterReadingTexts(loaded, 1)
        assertEquals(listOf("第二章", "当前章正文"), texts)
        assertTrue(metadata.chapters.all { it.paragraphs.isEmpty() })
        assertEquals(TextAnchor(1, 2), clampAnchor(texts, TextAnchor(1, 2)))
    }

    @Test fun emptyChapterStillOccupiesOneHeadingIndex() {
        assertEquals(listOf("序"), chapterReadingTexts(BookChapter("序", emptyList()), 0))
    }

    @Test fun blankTitlesGetReadableFallbackWithoutAddingItems() {
        val texts = chapterReadingTexts(BookChapter("  ", listOf("原文")), 7)
        assertEquals(listOf("第 8 章", "原文"), texts)
    }

    @Test fun blankAndDuplicateParagraphsAreNotDroppedOrMerged() {
        assertEquals(listOf("章", "", "重复", "重复"),
            chapterReadingTexts(BookChapter("章", listOf("", "重复", "重复")), 0))
    }

    @Test fun localAnchorStillAddressesSameTextAfterRecreatingChapter() {
        val chapter = BookChapter("第二章", listOf("甲乙", "丙丁😀"))
        val anchor = TextAnchor(paragraphIndex = 2, characterOffset = 2)
        val before = chapterReadingTexts(chapter, 1)
        val after = chapterReadingTexts(chapter.copy(paragraphs = chapter.paragraphs.toList()), 1)
        assertEquals(before[anchor.paragraphIndex].substring(anchor.characterOffset),
            after[anchor.paragraphIndex].substring(anchor.characterOffset))
        assertEquals("😀", after[anchor.paragraphIndex].substring(anchor.characterOffset))
    }

    @Test fun endOfChapterRequestClampsAfterBodyLoad() {
        val texts = chapterReadingTexts(BookChapter("章", listOf("尾😀")), 0)
        assertEquals(TextAnchor(1, 3), clampAnchor(texts, TextAnchor(Int.MAX_VALUE, Int.MAX_VALUE)))
    }
}
