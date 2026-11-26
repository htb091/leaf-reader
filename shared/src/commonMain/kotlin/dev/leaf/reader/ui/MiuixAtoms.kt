package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.sizeIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import top.yukonga.miuix.kmp.blur.Backdrop
import top.yukonga.miuix.kmp.blur.progressiveTextureBlur
import top.yukonga.miuix.kmp.blur.textureBlur
import top.yukonga.miuix.kmp.blur.isRuntimeShaderSupported
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.theme.lightColorScheme
import top.yukonga.miuix.kmp.theme.darkColorScheme

/** Same curves the reference sheets use: open 360ms ease-out, close 280ms ease-in. */
internal val MiuixEaseOut = CubicBezierEasing(0.22f, 1f, 0.36f, 1f)
internal val MiuixEaseIn = CubicBezierEasing(0.4f, 0f, 0.2f, 1f)
internal const val BookOpenMillis = 360
internal const val BookCloseMillis = 280

internal fun <T> bookOpen() = tween<T>(BookOpenMillis, easing = MiuixEaseOut)
internal fun <T> bookClose() = tween<T>(BookCloseMillis, easing = MiuixEaseIn)

/** Touch target spacing from the reference: 12dp between floating controls. */
internal val ControlGap = 12.dp
internal val PageMargin = 20.dp
internal val CircleControlSize = 40.dp

/** A captured sibling content layer is progressively blurred behind the header.
 * The translucent surface wash is also the fallback where runtime shaders are unavailable.
 * Capture must exclude this header to avoid sampling the effect into itself.
 */
@Composable
internal fun GradientHeaderScrim(backdrop: Backdrop? = null, content: @Composable BoxScope.() -> Unit) {
    val surface = MiuixTheme.colorScheme.surface
    val useBlur = backdrop != null && isRuntimeShaderSupported()
    val blur = if (useBlur) {
        Modifier.progressiveTextureBlur(backdrop = backdrop, shape = RectangleShape, blurRadius = 22f)
    } else Modifier
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .then(blur)
            .background(
                Brush.verticalGradient(
                    0f to surface.copy(alpha = if (useBlur) 0.84f else 1f),
                    0.55f to surface.copy(alpha = if (useBlur) 0.72f else 0.94f),
                    0.82f to surface.copy(alpha = 0.42f),
                    1f to Color.Transparent,
                ),
            ),
    ) {
        content()
    }
}

/** Circular visual control with a separate minimum 44dp interactive target. */
@Composable
internal fun MiuixCircleButton(
    glyph: Glyph,
    description: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    size: Dp = CircleControlSize,
    container: Color = MiuixTheme.colorScheme.surfaceContainerHigh,
    tint: Color = MiuixTheme.colorScheme.onSurface,
) {
    Box(
        modifier = modifier
            .sizeIn(minWidth = 44.dp, minHeight = 44.dp)
            .size(size.coerceAtLeast(44.dp))
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics {
                role = Role.Button
                contentDescription = description
            },
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier.size(size)
                .clip(RoundedCornerShape(size / 2))
                .background(container),
            contentAlignment = Alignment.Center,
        ) {
            MiuixGlyph(glyph, if (enabled) tint else tint.copy(alpha = 0.4f), size * 0.55f)
        }
    }
}

/** Pill used by the floating dock rows. */
@Composable
internal fun MiuixDockPill(
    modifier: Modifier = Modifier,
    backdrop: Backdrop? = null,
    verticalPadding: Dp = 10.dp,
    horizontalPadding: Dp = 16.dp,
    content: @Composable RowScope.() -> Unit,
) {
    val shape = RoundedCornerShape(999.dp)
    val useBlur = backdrop != null && isRuntimeShaderSupported()
    val material = if (useBlur) Modifier.textureBlur(backdrop, shape, blurRadius = 18f, noiseCoefficient = 0f) else Modifier
    Row(
        modifier = modifier
            .clip(shape)
            .then(material)
            .background(MiuixTheme.colorScheme.surfaceContainerHigh.copy(alpha = if (useBlur) 0.78f else 1f))
            .padding(horizontal = horizontalPadding, vertical = verticalPadding),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        content = content,
    )
}

/** Selected/unselected pill tab for the bottom dock. */
@Composable
internal fun DockTab(
    glyph: Glyph,
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val container = if (selected) MiuixTheme.colorScheme.primary else Color.Transparent
    val content = if (selected) MiuixTheme.colorScheme.onPrimary else MiuixTheme.colorScheme.onSurfaceVariantSummary
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(999.dp))
            .background(container)
            .clickable(onClick = onClick)
            .padding(horizontal = 20.dp, vertical = 10.dp)
            .semantics { contentDescription = label },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        MiuixGlyph(glyph, content, 20.dp)
        Text(label, color = content, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1)
    }
}

/** Small rounded count badge (chapter word counts, progress). */
@Composable
internal fun CountPill(
    text: String,
    modifier: Modifier = Modifier,
    container: Color = MiuixTheme.colorScheme.surfaceContainerHighest,
    content: Color = MiuixTheme.colorScheme.onSurfaceVariantSummary,
) {
    Text(
        text = text,
        modifier = modifier
            .clip(RoundedCornerShape(999.dp))
            .background(container)
            .padding(horizontal = 10.dp, vertical = 3.dp),
        color = content,
        fontSize = 12.sp,
        fontWeight = FontWeight.Medium,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
    )
}

/** Miuix-coloured reader themes; sepia keeps a warm paper wash over the light scheme. */
@Composable
internal fun readerColorScheme(theme: dev.leaf.reader.ReaderTheme): top.yukonga.miuix.kmp.theme.Colors = when (theme) {
    dev.leaf.reader.ReaderTheme.SEPIA -> lightColorScheme(
        primary = Color(0xFF706044),
        onPrimary = Color(0xFFFFFFFF),
        surface = Color(0xFFF3ECD9),
        onSurface = Color(0xFF473E30),
        surfaceContainer = Color(0xFFFBF5E7),
        surfaceContainerHigh = Color(0xFFEFE5CE),
        surfaceContainerHighest = Color(0xFFE6DAC0),
        onSurfaceVariantSummary = Color(0xFF6B5F4B),
        background = Color(0xFFF3ECD9),
        onBackground = Color(0xFF473E30),
    )
    dev.leaf.reader.ReaderTheme.LIGHT -> lightColorScheme()
    else -> darkColorScheme()
}
