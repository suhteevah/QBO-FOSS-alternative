package com.openledger.android.ui.reconciliation

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

data class ReconciliationState(
    val isLoading: Boolean = true,
    val isMatching: Boolean = false,
    val error: String? = null,
    val unmatched: List<BankTransactionResponse> = emptyList(),
    val unmatchedCount: Int = 0,
    val matchedCount: Int = 0,
)

@HiltViewModel
class ReconciliationViewModel @Inject constructor(
    private val repo: LedgerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ReconciliationState())
    val state: StateFlow<ReconciliationState> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = ReconciliationState(isLoading = true)
        viewModelScope.launch {
            repo.getUnmatched()
                .onSuccess {
                    _state.value = ReconciliationState(
                        isLoading = false,
                        unmatched = it,
                        unmatchedCount = it.size,
                    )
                }
                .onFailure { _state.value = ReconciliationState(isLoading = false, error = it.message) }
        }
    }

    fun autoMatch() {
        _state.value = _state.value.copy(isMatching = true)
        viewModelScope.launch {
            repo.autoMatch()
                .onSuccess { matches ->
                    _state.value = _state.value.copy(isMatching = false, matchedCount = matches.size)
                    load() // Refresh unmatched list
                }
                .onFailure { _state.value = _state.value.copy(isMatching = false, error = it.message) }
        }
    }
}
