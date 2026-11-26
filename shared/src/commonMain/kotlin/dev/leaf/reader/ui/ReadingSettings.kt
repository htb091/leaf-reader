package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.selection.toggleable
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.overlay.OverlayBottomSheet
import top.yukonga.miuix.kmp.theme.MiuixTheme

/**
 * Scrollable typography sheet with a pinned close action, including on short landscape windows.
 * Every interactive row keeps at least a 48dp target and clearly separated groups.
 */
@Composable
internal fun ReadingSettings(
    show: Boolean,
    settings: ReaderSettings,
    onChange: (ReaderSettings) -> Unit,
    onDismiss: () -> Unit,
    maxHeight: Dp = 560.dp,
) {
    OverlayBottomSheet(
        show = show,
        title = null,
        onDismissRequest = onDismiss,
        cornerRadius = 28.dp,
    ) {
        Column(Modifier.fillMaxWidth().heightIn(max = maxHeight)
            .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Bottom + WindowInsetsSides.Horizontal))) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("排版设置", Modifier.weight(1f).semantics { heading() },
                    fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
                ReaderIconButton(Glyph.CLOSE, "关闭排版设置", onDismiss)
            }
            Column(Modifier.fillMaxWidth().weight(1f, fill = false)
                .verticalScroll(rememberScrollState())
                .padding(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 20.dp),
                verticalArrangement = Arrangement.spacedBy(22.dp)) {
            SettingsSection("翻页与分栏") {
                Choice("阅读方式", listOf("滑动", "无动画", "滚动"),
                    listOf(ReadingMode.SLIDE, ReadingMode.INSTANT, ReadingMode.SCROLL).indexOf(settings.readingMode)) {
                    onChange(settings.copy(readingMode = listOf(ReadingMode.SLIDE, ReadingMode.INSTANT, ReadingMode.SCROLL)[it]))
                }
                Choice("分栏", listOf("自动", "单栏", "双栏"),
                    listOf(ColumnMode.AUTO, ColumnMode.SINGLE, ColumnMode.DOUBLE).indexOf(settings.columnMode)) {
                    onChange(settings.copy(columnMode = listOf(ColumnMode.AUTO, ColumnMode.SINGLE, ColumnMode.DOUBLE)[it]))
                }
                SettingsNote("自动在宽度达到 840dp 时使用双栏。双栏从左至右阅读；滚动模式按双栏书页连续排列。")
            }
            SettingsSection("文字与留白") {
                Choice("字体", listOf("衬线", "无衬线", "等宽"),
                    listOf(ReaderFont.SERIF, ReaderFont.SANS, ReaderFont.MONO).indexOf(settings.fontFamily)) {
                    onChange(settings.copy(fontFamily = listOf(ReaderFont.SERIF, ReaderFont.SANS, ReaderFont.MONO)[it]))
                }
                StepSetting("字号", settings.fontSize, 14f, 40f, 1f, "sp") { onChange(settings.copy(fontSize = it)) }
                StepSetting("行距", settings.lineHeight, 1.2f, 2.4f, 0.1f, "倍") { onChange(settings.copy(lineHeight = it)) }
                StepSetting("页边距", settings.horizontalMargin, 8f, 56f, 4f, "dp") { onChange(settings.copy(horizontalMargin = it)) }
                StepSetting("段间距", settings.paragraphSpacing, 0f, 40f, 2f, "dp") { onChange(settings.copy(paragraphSpacing = it)) }
                StepSetting("字间距", settings.letterSpacing, -0.5f, 3f, 0.25f, "sp") { onChange(settings.copy(letterSpacing = it)) }
                ToggleSetting("首行缩进", settings.firstLineIndent) { onChange(settings.copy(firstLineIndent = it)) }
                ToggleSetting("加粗正文", settings.bold) { onChange(settings.copy(bold = it)) }
            }
            SettingsSection("阅读主题") {
                Choice("纸张", listOf("系统", "明亮", "纸色", "深色"),
                    listOf(ReaderTheme.SYSTEM, ReaderTheme.LIGHT, ReaderTheme.SEPIA, ReaderTheme.DARK).indexOf(settings.theme)) {
                    onChange(settings.copy(theme = listOf(ReaderTheme.SYSTEM, ReaderTheme.LIGHT, ReaderTheme.SEPIA, ReaderTheme.DARK)[it]))
                }
            }
            SettingsSection("阅读控制") {
                ToggleSetting("控制栏自动隐藏", settings.autoHideControls) { onChange(settings.copy(autoHideControls = it)) }
                ToggleSetting("显示阅读页脚", settings.showReadingFooter) { onChange(settings.copy(showReadingFooter = it)) }
                SettingsNote("轻点中央显示 / 隐藏控制栏；分页时轻点两侧翻页。字号、分栏或旋转后按文字位置恢复，不存储页码。")
            }
            PrimaryAction("完成", onDismiss, Modifier.fillMaxWidth())
            }
        }
    }
}

@Composable
private fun SettingsSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(title, fontSize = 14.sp, fontWeight = FontWeight.SemiBold,
            color = MiuixTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 4.dp).semantics { heading() })
        Card(Modifier.fillMaxWidth(), insideMargin = PaddingValues(18.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(16.dp), content = content)
        }
    }
}

@Composable
private fun Choice(label: String, labels: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, style = MiuixTheme.textStyles.body2)
        TabRowWithContour(tabs = labels, selectedTabIndex = selected.coerceAtLeast(0),
            onTabSelected = onSelect, modifier = Modifier.fillMaxWidth(), minWidth = 52.dp, height = 48.dp)
    }
}

@Composable
private fun StepSetting(label: String, value: Float, minimum: Float, maximum: Float,
    step: Float, unit: String, onChange: (Float) -> Unit) {
    val rounded = (value * 100).toInt() / 100f
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, Modifier.weight(1f), fontSize = 15.sp, maxLines = 1)
        Text("$rounded$unit", fontSize = 14.sp, maxLines = 1,
            color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
        StepButton("−", "减小$label", enabled = value > minimum) {
            onChange((value - step).coerceAtLeast(minimum))
        }
        StepButton("＋", "增大$label", enabled = value < maximum) {
            onChange((value + step).coerceAtMost(maximum))
        }
    }
}

/** 48dp square stepper button; the symbol is text, not an icon dependency. */
@Composable
private fun StepButton(symbol: String, description: String, enabled: Boolean, onClick: () -> Unit) {
    val container = MiuixTheme.colorScheme.surfaceContainerHigh
    Box(
        modifier = Modifier.size(SettingsTouchTarget)
            .clip(RoundedCornerShape(12.dp))
            .background(if (enabled) container else container.copy(alpha = 0.5f))
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics {
                role = Role.Button
                contentDescription = description
            },
        contentAlignment = Alignment.Center,
    ) {
        Text(symbol, fontSize = 18.sp, fontWeight = FontWeight.Medium,
            color = if (enabled) MiuixTheme.colorScheme.onSurface
            else MiuixTheme.colorScheme.onSurfaceVariantSummary)
    }
}

@Composable
private fun ToggleSetting(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 52.dp)
        .toggleable(value = checked, role = Role.Switch, onValueChange = onChange)
        .semantics { contentDescription = label }, verticalAlignment = Alignment.CenterVertically) {
        Text(label, Modifier.weight(1f), fontSize = 15.sp, maxLines = 1)
        Switch(checked = checked, onCheckedChange = null,
            modifier = Modifier.clearAndSetSemantics { })
    }
}

@Composable
private fun SettingsNote(text: String) {
    Text(text, fontSize = 12.sp, lineHeight = 18.sp,
        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f))
}

private val SettingsTouchTarget = 48.dp

@Composable
internal fun PrimaryAction(label: String, action: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) =
    TextButton(label, action, modifier, enabled = enabled, minHeight = 48.dp,
        colors = ButtonDefaults.textButtonColorsPrimary())

@Composable
internal fun MutedText(text: String, modifier: Modifier = Modifier, maxLines: Int = Int.MAX_VALUE) = Text(
    text, modifier, fontSize = 13.sp, lineHeight = 20.sp, maxLines = maxLines,
    overflow = TextOverflow.Ellipsis, color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
)

@Composable
internal fun ProgressTrack(progress: Float, modifier: Modifier = Modifier) {
    LinearProgressIndicator(modifier = modifier, progress = progress.coerceIn(0f, 1f), height = 3.dp)
}
