package dev.leaf.reader.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme

@Composable
internal fun ReadingSettings(
    show: Boolean,
    settings: ReaderSettings,
    onChange: (ReaderSettings) -> Unit,
    onDismiss: () -> Unit,
) {
    OverlayDialog(show = show, title = "阅读设置", onDismissRequest = onDismiss) {
        Column(Modifier.fillMaxWidth().heightIn(max = 560.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)) {
            SettingsGroup("翻页与分栏") {
                Choice("阅读方式", listOf("滑动", "无动画", "滚动"),
                    listOf(ReadingMode.SLIDE, ReadingMode.INSTANT, ReadingMode.SCROLL).indexOf(settings.readingMode)) {
                    onChange(settings.copy(readingMode = listOf(ReadingMode.SLIDE, ReadingMode.INSTANT, ReadingMode.SCROLL)[it]))
                }
                Choice("分栏", listOf("自动", "单栏", "双栏"),
                    listOf(ColumnMode.AUTO, ColumnMode.SINGLE, ColumnMode.DOUBLE).indexOf(settings.columnMode)) {
                    onChange(settings.copy(columnMode = listOf(ColumnMode.AUTO, ColumnMode.SINGLE, ColumnMode.DOUBLE)[it]))
                }
                MutedText("自动在宽度达到 840dp 时使用双栏。双栏从左至右阅读；滚动模式按双栏书页连续排列。")
            }
            SettingsGroup("文字与留白") {
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
            SettingsGroup("阅读主题") {
                Choice("纸张", listOf("系统", "明亮", "纸色", "深色"),
                    listOf(ReaderTheme.SYSTEM, ReaderTheme.LIGHT, ReaderTheme.SEPIA, ReaderTheme.DARK).indexOf(settings.theme)) {
                    onChange(settings.copy(theme = listOf(ReaderTheme.SYSTEM, ReaderTheme.LIGHT, ReaderTheme.SEPIA, ReaderTheme.DARK)[it]))
                }
            }
            SettingsGroup("阅读控制") {
                ToggleSetting("控制栏自动隐藏", settings.autoHideControls) { onChange(settings.copy(autoHideControls = it)) }
                ToggleSetting("显示阅读页脚", settings.showReadingFooter) { onChange(settings.copy(showReadingFooter = it)) }
                MutedText("轻点中央显示 / 隐藏控制栏；分页时轻点两侧翻页。字号、分栏或旋转后按文字位置恢复，不存储页码。")
            }
            PrimaryAction("完成", onDismiss, Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun SettingsGroup(title: String, content: @Composable ColumnScope.() -> Unit) {
    Text(title, fontWeight = FontWeight.SemiBold, color = MiuixTheme.colorScheme.primary)
    Card(Modifier.fillMaxWidth(), insideMargin = PaddingValues(16.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
    }
}

@Composable
private fun Choice(label: String, labels: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    Text(label, style = MiuixTheme.textStyles.body2)
    TabRowWithContour(tabs = labels, selectedTabIndex = selected.coerceAtLeast(0),
        onTabSelected = onSelect, modifier = Modifier.fillMaxWidth(), minWidth = 52.dp)
}

@Composable
private fun StepSetting(label: String, value: Float, minimum: Float, maximum: Float,
    step: Float, unit: String, onChange: (Float) -> Unit) {
    val rounded = (value * 100).toInt() / 100f
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text("$label  $rounded$unit", Modifier.weight(1f), style = MiuixTheme.textStyles.body2)
        TextButton("−", { onChange((value - step).coerceAtLeast(minimum)) }, enabled = value > minimum,
            minHeight = 48.dp, modifier = Modifier.semantics { contentDescription = "减小$label" })
        Spacer(Modifier.width(4.dp))
        TextButton("＋", { onChange((value + step).coerceAtMost(maximum)) }, enabled = value < maximum,
            minHeight = 48.dp, modifier = Modifier.semantics { contentDescription = "增大$label" })
    }
}

@Composable
private fun ToggleSetting(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, Modifier.weight(1f), style = MiuixTheme.textStyles.body2)
        Switch(checked = checked, onCheckedChange = onChange,
            modifier = Modifier.semantics { contentDescription = label })
    }
}

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
