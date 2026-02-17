package com.openledger.android.ui.reconciliation

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CompareArrows
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.openledger.android.ui.common.ErrorMessage
import com.openledger.android.ui.common.LoadingIndicator

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReconciliationScreen(viewModel: ReconciliationViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Reconciliation") }) },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
        ) {
            Button(
                onClick = viewModel::autoMatch,
                enabled = !state.isMatching,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Filled.CompareArrows, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(if (state.isMatching) "Matching..." else "Auto-Match")
            }
            Spacer(modifier = Modifier.height(16.dp))

            when {
                state.isLoading -> LoadingIndicator()
                state.error != null -> ErrorMessage(state.error!!, onRetry = viewModel::load)
                else -> {
                    Text(
                        "${state.unmatchedCount} unmatched transactions",
                        style = MaterialTheme.typography.titleMedium,
                    )
                    if (state.matchedCount > 0) {
                        Text(
                            "${state.matchedCount} matches found",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                    Spacer(modifier = Modifier.height(12.dp))
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(state.unmatched) { txn ->
                            Card(modifier = Modifier.fillMaxWidth()) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                        Text(txn.transactionDate, style = MaterialTheme.typography.bodySmall)
                                        Text("$${txn.amount}", style = MaterialTheme.typography.titleSmall)
                                    }
                                    Text(txn.descriptionRaw, style = MaterialTheme.typography.bodyMedium)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
