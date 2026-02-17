package com.openledger.android.ui.accounts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.openledger.android.data.remote.dto.AccountResponse
import com.openledger.android.data.repository.LedgerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AccountListState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val accounts: List<AccountResponse> = emptyList(),
)

@HiltViewModel
class AccountListViewModel @Inject constructor(
    private val repo: LedgerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AccountListState())
    val state: StateFlow<AccountListState> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = AccountListState(isLoading = true)
        viewModelScope.launch {
            repo.getAccounts()
                .onSuccess { _state.value = AccountListState(isLoading = false, accounts = it) }
                .onFailure { _state.value = AccountListState(isLoading = false, error = it.message) }
        }
    }
}
