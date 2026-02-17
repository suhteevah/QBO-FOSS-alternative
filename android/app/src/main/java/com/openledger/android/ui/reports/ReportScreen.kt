package com.openledger.android.ui.reports

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
fun ReportScreen(viewModel: ReportViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Reports") }) },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
        ) {
            var expanded by remember { mutableStateOf(false) }
            ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
                OutlinedTextField(
                    value = state.reportType.replace("_", " ").replaceFirstChar { it.uppercase() },
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Report Type") },
                    modifier = Modifier.menuAnchor().fillMaxWidth(),
                )
                ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                    listOf("profit_loss", "balance_sheet", "trial_balance").forEach { type ->
                        DropdownMenuItem(
                            text = { Text(type.replace("_", " ").replaceFirstChar { it.uppercase() }) },
                            onClick = { viewModel.onTypeChanged(type); expanded = false },
                        )
                    }
                }
            }
            Spacer(modifier = Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = state.startDate,
                    onValueChange = viewModel::onStartDateChanged,
                    label = { Text("Start Date") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                OutlinedTextField(
                    value = state.endDate,
                    onValueChange = viewModel::onEndDateChanged,
                    label = { Text("End Date") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            Button(
                onClick = viewModel::generate,
                enabled = !state.isLoading,
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Generate Report") }
            Spacer(modifier = Modifier.height(16.dp))

            when {
                state.isLoading -> LoadingIndicator("Generating...")
                state.error != null -> ErrorMessage(state.error!!)
                state.report != null -> {
                    val report = state.report!!
                    Text(
                        "${report.reportType.replace("_", " ").uppercase()} — ${report.period}",
                        style = MaterialTheme.typography.titleMedium,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        report.sections.forEach { section ->
                            item { Text(section.title, style = MaterialTheme.typography.titleSmall) }
                            items(section.items) { item ->
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("${item.accountNumber} ${item.accountName}", style = MaterialTheme.typography.bodyMedium)
                                    Text("$${item.amount}", style = MaterialTheme.typography.bodyMedium)
                                }
                            }
                            item {
                                HorizontalDivider()
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("Subtotal", style = MaterialTheme.typography.bodyMedium)
                                    Text("$${section.subtotal}", style = MaterialTheme.typography.titleSmall)
                                }
                            }
                        }
                        item {
                            Spacer(modifier = Modifier.height(8.dp))
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("NET TOTAL", style = MaterialTheme.typography.titleMedium)
                                Text("$${report.netTotal}", style = MaterialTheme.typography.titleMedium)
                            }
                        }
                    }
                }
            }
        }
    }
}
