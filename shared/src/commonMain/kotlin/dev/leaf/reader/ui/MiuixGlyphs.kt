package dev.leaf.reader.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Small Canvas glyphs used by the floating controls. Miuix 0.9.4 ships only a
 * narrow icon set, so these keep the controls dependency-free instead of pulling
 * an extra icon artifact into the Kotlin/Native framework.
 */
internal enum class Glyph {
    BACK, SEARCH, ADD, TOC, TUNE, CLOSE, SORT, REFRESH, TAG, MORE, BOOK, SHELVES, GEAR, CHEVRON_UP,
}

@Composable
internal fun MiuixGlyph(glyph: Glyph, tint: Color, size: Dp = 22.dp) {
    Canvas(Modifier.size(size)) {
        val unit = this.size.minDimension / 24f
        val stroke = 2f * unit
        fun at(x: Float, y: Float) = Offset(x * unit, y * unit)
        fun line(x1: Float, y1: Float, x2: Float, y2: Float) =
            drawLine(tint, at(x1, y1), at(x2, y2), strokeWidth = stroke, cap = StrokeCap.Round)
        fun dot(x: Float, y: Float, r: Float = 1.35f) = drawCircle(tint, r * unit, at(x, y))
        when (glyph) {
            Glyph.BACK -> {
                line(14.5f, 5f, 7.5f, 12f)
                line(7.5f, 12f, 14.5f, 19f)
            }
            Glyph.SEARCH -> {
                drawCircle(tint, 6.2f * unit, at(10.5f, 10.5f), style = Stroke(stroke))
                line(15.1f, 15.1f, 20f, 20f)
            }
            Glyph.ADD -> {
                line(12f, 6f, 12f, 18f)
                line(6f, 12f, 18f, 12f)
            }
            Glyph.TOC -> {
                dot(5.5f, 6.5f, 1.2f); line(9f, 6.5f, 19f, 6.5f)
                dot(5.5f, 12f, 1.2f); line(9f, 12f, 19f, 12f)
                dot(5.5f, 17.5f, 1.2f); line(9f, 17.5f, 19f, 17.5f)
            }
            Glyph.TUNE -> {
                line(4f, 7f, 20f, 7f); dot(9f, 7f, 2f)
                line(4f, 12f, 20f, 12f); dot(15f, 12f, 2f)
                line(4f, 17f, 20f, 17f); dot(11.5f, 17f, 2f)
            }
            Glyph.CLOSE -> {
                line(6.5f, 6.5f, 17.5f, 17.5f)
                line(17.5f, 6.5f, 6.5f, 17.5f)
            }
            Glyph.SORT -> {
                line(12f, 4.5f, 12f, 19.5f)
                line(8.5f, 8f, 12f, 4.5f)
                line(15.5f, 8f, 12f, 4.5f)
                line(8.5f, 16f, 12f, 19.5f)
                line(15.5f, 16f, 12f, 19.5f)
            }
            Glyph.REFRESH -> {
                drawArc(
                    color = tint, startAngle = -40f, sweepAngle = 280f, useCenter = false,
                    topLeft = at(4f, 4f), size = androidx.compose.ui.geometry.Size(16f * unit, 16f * unit),
                    style = Stroke(stroke, cap = StrokeCap.Round),
                )
                line(17.5f, 3f, 19.5f, 7f)
                line(19.5f, 7f, 15f, 7.5f)
            }
            Glyph.TAG -> {
                line(9f, 4.5f, 7.5f, 19.5f)
                line(16.5f, 4.5f, 15f, 19.5f)
                line(4.5f, 9.5f, 19.5f, 9.5f)
                line(4f, 15f, 19f, 15f)
            }
            Glyph.MORE -> {
                dot(12f, 5.5f); dot(12f, 12f); dot(12f, 18.5f)
            }
            Glyph.BOOK -> {
                val path = Path().apply {
                    moveTo(6f * unit, 4.5f * unit)
                    lineTo(6f * unit, 19.5f * unit)
                    lineTo(18f * unit, 19.5f * unit)
                    lineTo(18f * unit, 6.5f * unit)
                    lineTo(8.5f * unit, 6.5f * unit)
                }
                drawPath(path, tint, style = Stroke(stroke, cap = StrokeCap.Round))
                line(6f, 16.5f, 18f, 16.5f)
                line(9.5f, 10f, 15f, 10f)
            }
            Glyph.SHELVES -> {
                line(4.5f, 7f, 4.5f, 19f)
                line(11.5f, 5f, 11.5f, 19f)
                line(18.5f, 8f, 18.5f, 19f)
                line(3f, 19f, 21f, 19f)
            }
            Glyph.GEAR -> {
                drawCircle(tint, 3.2f * unit, at(12f, 12f), style = Stroke(stroke))
                for (index in 0 until 8) {
                    val angle = index * (Math.PI / 4).toFloat()
                    val inner = 6.2f
                    val outer = 9.2f
                    line(
                        12f + kotlin.math.cos(angle) * inner,
                        12f + kotlin.math.sin(angle) * inner,
                        12f + kotlin.math.cos(angle) * outer,
                        12f + kotlin.math.sin(angle) * outer,
                    )
                }
            }
            Glyph.CHEVRON_UP -> {
                line(7f, 14.5f, 12f, 9.5f)
                line(17f, 14.5f, 12f, 9.5f)
            }
        }
    }
}
