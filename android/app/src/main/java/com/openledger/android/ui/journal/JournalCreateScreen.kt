package com.openledger.android.ui.journal

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun JournalCreateScreen(
    onDone: () -> Unit,
    viewModel: JournalCreateViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = { TopAppBar(title = { Text("New Journal Entry") }) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            OutlinedTextField(
                value = state.entryDate,
                onValueChange = viewModel::onDateChanged,
                label = { Text("Date (YYYY-MM-DD)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(12.dp))
            OutlinedTextField(
                value = state.description,
                onValueChange = viewModel::onDescriptionChanged,
                label = { Text("Description") },
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(16.dp))

            Text("Line Items", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))

            state.lineItems.forEachIndexed { index, item ->
                Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            var expanded by remember { mutableStateOf(false) }
                            ExposedDropdownMenuBox(
                                expanded = expanded,
                                onExpandedChange = { expanded = it },
                            ) {
                                OutlinedTextField(
                                    value = state.accounts.find { it.id == item.accountId }?.let {
                                        "${it.accountNumber} — ${it.name}"
                                    } ?: "Select account",
                                    onValueChange = {},
                                    readOnly = true,
                                    modifier = Modifier.menuAnchor().weight(1f),
                                    label = { Text("Account") },
                                )
                                ExposedDropdownMenu(
                                    expanded = expanded,
                                    onDismissRequest = { expanded = false },
                                ) {
                                    state.accounts.forEach { acct ->
                                        DropdownMenuItem(
                                            text = { Text("${acct.accountNumber} — ${acct.name}") },
                                            onClick = {
                                                viewModel.onLineAccountChanged(index, acct.id)
                                                expanded = false
                                            },
                                        )
                                    }
                                }
                            }
                            IconButton(onClick = { viewModel.removeLine(index) }) {
                                Icon(Icons.Filled.Delete, contentDescription = "Remove")
                            }
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(
                                value = item.debit,
                                onValueChange = { viewModel.onLineDebitChanged(index, it) },
                                label = { Text("Debit") },
                                singleLine = true,
                                modifier = Modifier.weight(1f),
                            )
                            OutlinedTextField(
                                value = item.credit,
                                onValueChange = { viewModel.onLineCreditChanged(index, it) },
                                label = { Text("Credit") },
                                singleLine = true,
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                }
            }

            TextButton(onClick = viewModel::addLine) {
                Icon(Icons.Filled.Add, contentDescription = null)
                Spacer(modifier = Modifier.width(4.dp))
                Text("Add Line Item")
            }

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = { viewModel.submit(onDone) },
                enabled = !state.isSubmitting,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (state.isSubmitting) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                else Text("Create Entry")
            }

            state.error?.let {
                Spacer(modifier = Modifier.height(8.dp))
                Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
