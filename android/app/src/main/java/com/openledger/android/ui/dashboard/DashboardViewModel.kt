package com.openledger.android.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.openledger.android.data.repository.LedgerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val userName: String? = null,
    val userRole: String? = null,
    val accountCount: Int = 0,
    val entryCount: Int = 0,
    val txnCount: Int = 0,
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val repo: LedgerRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(DashboardState())
    val state: StateFlow<DashboardState> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = DashboardState(isLoading = true)
        viewModelScope.launch {
            try {
                val meDeferred = async { repo.getMe() }
                val accountsDeferred = async { repo.getAccounts() }
                val entriesDeferred = async { repo.getJournalEntries() }
                val txnsDeferred = async { repo.getTransactions() }

                val me = meDeferred.await().getOrNull()
                val accounts = accountsDeferred.await().getOrDefault(emptyList())
                val entries = entriesDeferred.await().getOrDefault(emptyList())
                val txns = txnsDeferred.await().getOrDefault(emptyList())

                _state.value = DashboardState(
                    isLoading = false,
                    userName = me?.fullName ?: me?.email,
                    userRole = me?.role,
                    accountCount = accounts.size,
                    entryCount = entries.size,
                    txnCount = txns.size,
                )
            } catch (e: Exception) {
                _state.value = DashboardState(isLoading = false, error = e.message)
            }
        }
    }
}
