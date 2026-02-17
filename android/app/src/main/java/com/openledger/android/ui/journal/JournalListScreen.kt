package com.openledger.android.ui.journal

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.openledger.android.data.remote.dto.JournalEntryResponse
import com.openledger.android.ui.common.ErrorMessage
import com.openledger.android.ui.common.LoadingIndicator

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun JournalListScreen(
    onCreateNew: () -> Unit,
    viewModel: JournalListViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Journal Entries") }) },
        floatingActionButton = {
            FloatingActionButton(onClick = onCreateNew) {
                Icon(Icons.Filled.Add, contentDescription = "New Entry")
            }
        },
    ) { padding ->
        when {
            state.isLoading -> LoadingIndicator()
            state.error != null -> ErrorMessage(state.error!!, onRetry = viewModel::load)
            state.entries.isEmpty() -> Box(Modifier.fillMaxSize().padding(padding)) {
                Text("No journal entries yet", modifier = Modifier.padding(24.dp))
            }
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.entries) { entry -> JournalEntryCard(entry) }
            }
        }
    }
}

@Composable
private fun JournalEntryCard(entry: JournalEntryResponse) {
    val totalDebits = entry.lineItems.sumOf {
        it.debitAmount.toBigDecimalOrNull() ?: java.math.BigDecimal.ZERO
    }
    val statusColor = when (entry.status) {
        "approved", "auto" -> MaterialTheme.colorScheme.primary
        "draft", "pending" -> MaterialTheme.colorScheme.tertiary
        "voided" -> MaterialTheme.colorScheme.error
        else -> MaterialTheme.colorScheme.outline
    }

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(entry.entryNumber ?: "—", style = MaterialTheme.typography.labelMedium)
                AssistChip(
                    onClick = {},
                    label = { Text(entry.status.uppercase()) },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = statusColor.copy(alpha = 0.12f),
                    ),
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(entry.description ?: "No description", style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(4.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(entry.entryDate, style = MaterialTheme.typography.bodySmall)
                Text("$$totalDebits", style = MaterialTheme.typography.titleSmall)
            }
        }
    }
}
