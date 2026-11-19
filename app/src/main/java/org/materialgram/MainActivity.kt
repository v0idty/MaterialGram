package org.materialgram

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Chat
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.DarkMode
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialGramRoot() }
    }
}

private data class DemoChat(val title: String, val message: String, val time: String, val initials: String)

private val demoChats = listOf(
    DemoChat("MaterialGram", "Welcome — this is a local UI preview.", "now", "M"),
    DemoChat("Compose notes", "Material 3 layout preview", "12:40", "C"),
    DemoChat("Android ideas", "Sample conversation row", "Yesterday", "A")
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun MaterialGramRoot() {
    var tab by remember { mutableIntStateOf(0) }
    var darkTheme by remember { mutableStateOf(false) }
    MaterialGramTheme(dark = darkTheme) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text(if (tab == 0) "MaterialGram" else "Settings", fontWeight = FontWeight.SemiBold) },
                    actions = { if (tab == 0) IconButton(onClick = {}) { Icon(Icons.Outlined.Search, contentDescription = "Search preview") } }
                )
            },
            bottomBar = {
                NavigationBar {
                    NavigationBarItem(selected = tab == 0, onClick = { tab = 0 },
                        icon = { Icon(Icons.Outlined.Chat, contentDescription = null) }, label = { Text("Chats") })
                    NavigationBarItem(selected = tab == 1, onClick = { tab = 1 },
                        icon = { Icon(Icons.Outlined.Settings, contentDescription = null) }, label = { Text("Settings") })
                }
            }
        ) { padding ->
            if (tab == 0) ChatsPreview(Modifier.padding(padding))
            else SettingsPreview(darkTheme, { darkTheme = it }, Modifier.padding(padding))
        }
    }
}

@Composable
private fun ChatsPreview(modifier: Modifier = Modifier) {
    Column(modifier.fillMaxSize()) {
        Surface(color = MaterialTheme.colorScheme.secondaryContainer, modifier = Modifier.fillMaxWidth()) {
            Text("Preview only • sample chats • no Telegram connection", modifier = Modifier.padding(12.dp),
                style = MaterialTheme.typography.labelMedium)
        }
        LazyColumn(Modifier.fillMaxSize()) {
            items(demoChats) { chat ->
                Row(
                    Modifier.fillMaxWidth().clickable {}.padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(Modifier.size(52.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primaryContainer),
                        contentAlignment = Alignment.Center) {
                        Text(chat.initials, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onPrimaryContainer)
                    }
                    Column(Modifier.weight(1f).padding(start = 14.dp)) {
                        Text(chat.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Medium)
                        Text(chat.message, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1)
                    }
                    Text(chat.time, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
            }
        }
    }
}

@Composable
private fun SettingsPreview(dark: Boolean, onDarkChange: (Boolean) -> Unit, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Appearance", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
        ListItem(
            headlineContent = { Text("Dark theme") },
            supportingContent = { Text("Preview theme switch") },
            leadingContent = { Icon(Icons.Outlined.DarkMode, contentDescription = null) },
            trailingContent = { Switch(checked = dark, onCheckedChange = onDarkChange) }
        )
        HorizontalDivider()
        Text("About", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(top = 8.dp))
        ListItem(headlineContent = { Text("MaterialGram") }, supportingContent = { Text("Version 0.1.0 • UI prototype") })
        Text("This build has no Telegram login, chats, or messaging yet.", style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(horizontal = 16.dp))
    }
}
