package dev.leaf.reader.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.border
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import top.yukonga.miuix.kmp.basic.IconButton
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.blur.LayerBackdrop
import top.yukonga.miuix.kmp.theme.MiuixTheme

/** Chrome is a sibling overlay: its visibility never changes the measured reading viewport. */
@Composable
internal fun BoxScope.ReaderChrome(
    visible: Boolean,
    title: String,
    progressText: String,
    backdrop: LayerBackdrop,
    onClose: () -> Unit,
    onDirectory: () -> Unit,
    onSettings: () -> Unit,
) {
    val reducedMotion = LocalReducedMotion.current
    AnimatedVisibility(
        visible = visible,
        enter = if (reducedMotion) EnterTransition.None else slideInVertically(tween(ReaderChromeEnterMillis, easing = MiuixEaseOut)) { -it } +
            fadeIn(tween(ReaderChromeEnterMillis)),
        exit = if (reducedMotion) ExitTransition.None else slideOutVertically(tween(ReaderChromeExitMillis, easing = MiuixEaseIn)) { -it } +
            fadeOut(tween(ReaderChromeExitMillis)),
        modifier = Modifier.align(Alignment.TopCenter),
    ) {
        // Shared scrim combines a transparent tint with real miuix-blur sampling of body only.
        GradientHeaderScrim(backdrop = backdrop) {
            Row(
                modifier = Modifier.fillMaxWidth()
                    .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Top + WindowInsetsSides.Horizontal))
                    .padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 20.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                ReaderIconButton(Glyph.BACK, "保存进度并返回书架", onClose)
                Text(title, Modifier.weight(1f), fontSize = 15.sp,
                    color = MiuixTheme.colorScheme.onSurfaceVariantSummary, maxLines = 1,
                    overflow = TextOverflow.Ellipsis)
            }
        }
    }
    AnimatedVisibility(
        visible = visible,
        enter = if (reducedMotion) EnterTransition.None else slideInVertically(tween(ReaderChromeEnterMillis, easing = MiuixEaseOut)) { it } +
            fadeIn(tween(ReaderChromeEnterMillis)),
        exit = if (reducedMotion) ExitTransition.None else slideOutVertically(tween(ReaderChromeExitMillis, easing = MiuixEaseIn)) { it } +
            fadeOut(tween(ReaderChromeExitMillis)),
        modifier = Modifier.align(Alignment.BottomCenter),
    ) {
        Box(
            Modifier.fillMaxWidth()
                .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Bottom + WindowInsetsSides.Horizontal))
                .padding(horizontal = 16.dp, vertical = 12.dp),
            contentAlignment = Alignment.Center,
        ) {
            MiuixDockPill(Modifier.widthIn(max = 640.dp).fillMaxWidth(), backdrop = backdrop,
                verticalPadding = ReaderDockVerticalPaddingDp.dp) {
                ReaderDockAction(Glyph.BOOK, "目录", onDirectory)
                Text(progressText, Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite },
                    fontSize = 12.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                    textAlign = TextAlign.Center, maxLines = 1, overflow = TextOverflow.Ellipsis)
                // Settings is deliberately the rightmost dock action, matching the reader template.
                ReaderDockAction(Glyph.TUNE, "设置", onSettings)
            }
        }
    }
}

/** The shelf's 40dp circle inside a separate 44dp Miuix IconButton touch target. */
@Composable
internal fun ReaderIconButton(
    glyph: Glyph,
    description: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    highlighted: Boolean = false,
    enabled: Boolean = true,
) {
    val colors = MiuixTheme.colorScheme
    IconButton(
        onClick = onClick,
        modifier = modifier.size(ReaderControlTouchDp.dp).semantics { contentDescription = description },
        enabled = enabled,
        minWidth = ReaderControlTouchDp.dp,
        minHeight = ReaderControlTouchDp.dp,
        cornerRadius = 22.dp,
        backgroundColor = Color.Transparent,
    ) {
        Box(Modifier.size(ReaderControlVisualDp.dp).shadow(2.dp, CircleShape)
            .border(1.dp, colors.onSurface.copy(alpha = 0.07f), CircleShape)
            .background(if (highlighted) colors.primaryContainer else colors.surfaceContainerHigh, CircleShape),
            contentAlignment = Alignment.Center) {
            MiuixGlyph(glyph, if (highlighted) colors.onPrimaryContainer else colors.onSurface, 20.dp)
        }
    }
}

@Composable
private fun ReaderDockAction(glyph: Glyph, label: String, onClick: () -> Unit) {
    IconButton(onClick = onClick, minHeight = ReaderControlTouchDp.dp, minWidth = 64.dp, cornerRadius = 24.dp,
        modifier = Modifier.semantics { contentDescription = label }) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            MiuixGlyph(glyph, MiuixTheme.colorScheme.onSurface, 20.dp)
            Text(label, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1)
        }
    }
}

internal enum class ReaderTapAction { TOGGLE_CHROME, PREVIOUS_PAGE, NEXT_PAGE, NONE }

/** Keep central chrome taps distinct from the page-turn zones, including in scroll mode. */
internal fun readerTapAction(horizontalFraction: Float, paged: Boolean): ReaderTapAction = when {
    !horizontalFraction.isFinite() || horizontalFraction !in 0f..1f -> ReaderTapAction.NONE
    horizontalFraction in 0.32f..0.68f -> ReaderTapAction.TOGGLE_CHROME
    !paged -> ReaderTapAction.NONE
    horizontalFraction < 0.32f -> ReaderTapAction.PREVIOUS_PAGE
    else -> ReaderTapAction.NEXT_PAGE
}

internal const val ReaderControlVisualDp = 40f
internal const val ReaderControlTouchDp = 44f
internal const val ReaderDockVerticalPaddingDp = 4f
// 44dp actions + 8dp padding = 52dp, versus the previous 48 + 20 = 68dp.
// Only minimums are specified; dynamic text can grow the dock instead of being clipped.
internal const val ReaderDockMinimumHeightDp = ReaderControlTouchDp + 2 * ReaderDockVerticalPaddingDp

internal const val ReaderChromeEnterMillis = 240
internal const val ReaderChromeExitMillis = 200
