package com.openledger.android.ui.ai

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.openledger.android.ui.common.ErrorMessage
import com.openledger.android.ui.common.LoadingIndicator

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AiQueryScreen(viewModel: AiQueryViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = { TopAppBar(title = { Text("AI Query") }) },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
        ) {
            OutlinedTextField(
                value = state.query,
                onValueChange = viewModel::onQueryChanged,
                label = { Text("Ask a question about your books...") },
                modifier = Modifier.fillMaxWidth(),
                maxLines = 3,
                trailingIcon = {
                    IconButton(
                        onClick = viewModel::submit,
                        enabled = !state.isLoading && state.query.isNotBlank(),
                    ) {
                        Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Submit")
                    }
                },
            )
            Spacer(modifier = Modifier.height(16.dp))

            when {
                state.isLoading -> LoadingIndicator("Thinking...")
                state.error != null -> ErrorMessage(state.error!!)
                state.response != null -> {
                    val resp = state.response!!
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Interpreted as:", style = MaterialTheme.typography.labelSmall)
                            Text(resp.interpretedAs, style = MaterialTheme.typography.bodyMedium)
                            if (resp.cached) {
                                Spacer(modifier = Modifier.height(4.dp))
                                Text("(cached)", style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(12.dp))

                    if (resp.results.isNotEmpty()) {
                        Text(
                            "${resp.results.size} results",
                            style = MaterialTheme.typography.titleSmall,
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        val keys = resp.results.firstOrNull()?.keys?.toList() ?: emptyList()
                        LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            items(resp.results) { row ->
                                Card(modifier = Modifier.fillMaxWidth()) {
                                    Row(
                                        modifier = Modifier
                                            .padding(12.dp)
                                            .horizontalScroll(rememberScrollState()),
                                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                                    ) {
                                        keys.forEach { key ->
                                            Column {
                                                Text(key, style = MaterialTheme.typography.labelSmall)
                                                Text(
                                                    row[key] ?: "—",
                                                    style = MaterialTheme.typography.bodyMedium,
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        Text("No results returned.", style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
    }
}
