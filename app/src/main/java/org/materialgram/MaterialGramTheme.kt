package org.materialgram

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val GramLight = lightColorScheme(
    primary = Color(0xFF6750A4),
    secondary = Color(0xFF52616B),
    background = Color(0xFFF7F5FA),
    surface = Color(0xFFF7F5FA)
)
private val GramDark = darkColorScheme(
    primary = Color(0xFFD0BCFF),
    secondary = Color(0xFFB8C8D5)
)

@Composable
fun MaterialGramTheme(dark: Boolean, content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (dark) GramDark else GramLight, content = content)
}
