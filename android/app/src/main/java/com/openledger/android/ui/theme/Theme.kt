package com.openledger.android.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

// OpenLedger brand colors — professional accounting aesthetic
private val OlGreen = Color(0xFF2E7D32)
private val OlGreenLight = Color(0xFF60AD5E)
private val OlGreenDark = Color(0xFF005005)
private val OlBlue = Color(0xFF1565C0)

private val LightColors = lightColorScheme(
    primary = OlGreen,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFC8E6C9),
    onPrimaryContainer = OlGreenDark,
    secondary = OlBlue,
    onSecondary = Color.White,
    background = Color(0xFFFAFAFA),
    surface = Color.White,
    onBackground = Color(0xFF1C1B1F),
    onSurface = Color(0xFF1C1B1F),
    error = Color(0xFFBA1A1A),
)

private val DarkColors = darkColorScheme(
    primary = OlGreenLight,
    onPrimary = OlGreenDark,
    primaryContainer = OlGreen,
    onPrimaryContainer = Color(0xFFC8E6C9),
    secondary = Color(0xFF90CAF9),
    onSecondary = Color(0xFF003258),
    background = Color(0xFF1C1B1F),
    surface = Color(0xFF2B2B2B),
    onBackground = Color(0xFFE6E1E5),
    onSurface = Color(0xFFE6E1E5),
    error = Color(0xFFFFB4AB),
)

@Composable
fun OpenLedgerTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit,
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColors
        else -> LightColors
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography(),
        content = content,
    )
}
