package com.openledger.android.ui.transactions

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.openledger.android.data.remote.dto.BankTransactionResponse
import com.openledger.android.ui.common.ErrorMessage
import com.openledger.android.ui.common.LoadingIndicator

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TransactionListScreen(viewModel: TransactionListViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Transactions") }) },
    ) { padding ->
        when {
            state.isLoading -> LoadingIndicator()
            state.error != null -> ErrorMessage(state.error!!, onRetry = viewModel::load)
            state.transactions.isEmpty() -> Box(Modifier.fillMaxSize().padding(padding)) {
                Text("No transactions yet", modifier = Modifier.padding(24.dp))
            }
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.transactions) { txn -> TransactionCard(txn) }
            }
        }
    }
}

@Composable
private fun TransactionCard(txn: BankTransactionResponse) {
    val amount = txn.amount.toBigDecimalOrNull()
    val isNegative = amount != null && amount < java.math.BigDecimal.ZERO

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(txn.transactionDate, style = MaterialTheme.typography.bodySmall)
                Text(
                    text = "$${txn.amount}",
                    style = MaterialTheme.typography.titleMedium,
                    color = if (isNegative) MaterialTheme.colorScheme.error else Color(0xFF2E7D32),
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(txn.descriptionCleaned ?: txn.descriptionRaw, style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (txn.isReconciled) {
                    AssistChip(onClick = {}, label = { Text("Reconciled") })
                }
                txn.aiCategory?.let { cat ->
                    AssistChip(onClick = {}, label = { Text(cat) })
                }
            }
        }
    }
}
