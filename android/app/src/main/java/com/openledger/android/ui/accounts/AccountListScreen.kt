package com.openledger.android.ui.accounts

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.openledger.android.data.remote.dto.AccountResponse
import com.openledger.android.ui.common.ErrorMessage
import com.openledger.android.ui.common.LoadingIndicator
import com.openledger.android.ui.navigation.Screen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AccountListScreen(
    onNavigate: (String) -> Unit,
    viewModel: AccountListViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    var showAccounts by remember { mutableStateOf(false) }

    Scaffold(
        topBar = { TopAppBar(title = { Text("More") }) },
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            item {
                Text("Navigation", style = MaterialTheme.typography.titleMedium)
                Spacer(modifier = Modifier.height(8.dp))
            }
            val navItems = listOf(
                Triple("Reports", Icons.Filled.Assessment, Screen.Reports.route),
                Triple("Reconciliation", Icons.Filled.CompareArrows, Screen.Reconciliation.route),
                Triple("AI Query", Icons.Filled.Psychology, Screen.AiQuery.route),
                Triple("Periods", Icons.Filled.CalendarMonth, Screen.Periods.route),
                Triple("Audit Log", Icons.Filled.History, Screen.AuditLog.route),
            )
            items(navItems) { (label, icon, route) ->
                OutlinedCard(onClick = { onNavigate(route) }, modifier = Modifier.fillMaxWidth()) {
                    Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(label, style = MaterialTheme.typography.bodyLarge)
                        Spacer(modifier = Modifier.weight(1f))
                        Icon(Icons.Filled.ChevronRight, contentDescription = null)
                    }
                }
            }

            item {
                Spacer(modifier = Modifier.height(16.dp))
                OutlinedCard(
                    onClick = { showAccounts = !showAccounts },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.AccountBalance, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("Chart of Accounts (${state.accounts.size})", style = MaterialTheme.typography.bodyLarge)
                        Spacer(modifier = Modifier.weight(1f))
                        Icon(
                            if (showAccounts) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                            contentDescription = null,
                        )
                    }
                }
            }

            if (showAccounts) {
                when {
                    state.isLoading -> item { LoadingIndicator("Loading accounts...") }
                    state.error != null -> item { ErrorMessage(state.error!!, onRetry = viewModel::load) }
                    else -> {
                        val grouped = state.accounts.groupBy { it.accountType }
                        grouped.forEach { (type, accounts) ->
                            item {
                                Text(
                                    type.replace("_", " ").uppercase(),
                                    style = MaterialTheme.typography.labelLarge,
                                    modifier = Modifier.padding(top = 8.dp),
                                )
                            }
                            items(accounts) { account ->
                                Row(
                                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp, horizontal = 8.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Text("${account.accountNumber} — ${account.name}", style = MaterialTheme.typography.bodyMedium)
                                    Text(account.normalBalance, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
