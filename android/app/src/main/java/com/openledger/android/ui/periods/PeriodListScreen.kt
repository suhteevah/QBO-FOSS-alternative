package com.openledger.android.ui.periods

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.openledger.android.ui.common.ErrorMessage
import com.openledger.android.ui.common.LoadingIndicator

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PeriodListScreen(viewModel: PeriodListViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Accounting Periods") }) },
    ) { padding ->
        when {
            state.isLoading -> LoadingIndicator()
            state.error != null -> ErrorMessage(state.error!!, onRetry = viewModel::load)
            state.periods.isEmpty() -> Box(Modifier.fillMaxSize().padding(padding)) {
                Text("No periods configured", modifier = Modifier.padding(24.dp))
            }
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.periods) { period ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text(period.name, style = MaterialTheme.typography.titleSmall)
                                val color = when (period.status.lowercase()) {
                                    "open" -> MaterialTheme.colorScheme.primary
                                    "closed" -> MaterialTheme.colorScheme.outline
                                    else -> MaterialTheme.colorScheme.onSurface
                                }
                                AssistChip(
                                    onClick = {},
                                    label = {
                                        Text(
                                            period.status.replaceFirstChar { it.uppercase() },
                                            style = MaterialTheme.typography.labelSmall,
                                        )
                                    },
                                    colors = AssistChipDefaults.assistChipColors(labelColor = color),
                                )
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                "${period.startDate} — ${period.endDate}",
                                style = MaterialTheme.typography.bodyMedium,
                            )
                            period.closedAt?.let { closedAt ->
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    "Closed: $closedAt",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.outline,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
