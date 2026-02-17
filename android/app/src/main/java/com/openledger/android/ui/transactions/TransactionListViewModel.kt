package com.openledger.android.ui.transactions

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.openledger.android.data.remote.dto.BankTransactionResponse
import com.openledger.android.data.repository.LedgerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class TransactionListState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val transactions: List<BankTransactionResponse> = emptyList(),
)

@HiltViewModel
class TransactionListViewModel @Inject constructor(
    private val repo: LedgerRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(TransactionListState())
    val state: StateFlow<TransactionListState> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = TransactionListState(isLoading = true)
        viewModelScope.launch {
            repo.getTransactions()
                .onSuccess { _state.value = TransactionListState(isLoading = false, transactions = it) }
                .onFailure { _state.value = TransactionListState(isLoading = false, error = it.message) }
        }
    }
}
