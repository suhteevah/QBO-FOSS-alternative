package com.openledger.android.ui.audit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.openledger.android.data.remote.dto.AuditLogResponse
import com.openledger.android.data.repository.LedgerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuditLogState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val logs: List<AuditLogResponse> = emptyList(),
)

@HiltViewModel
class AuditLogViewModel @Inject constructor(
    private val repo: LedgerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AuditLogState())
    val state: StateFlow<AuditLogState> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = AuditLogState(isLoading = true)
        viewModelScope.launch {
            repo.getAuditLogs()
                .onSuccess { _state.value = AuditLogState(isLoading = false, logs = it) }
                .onFailure { _state.value = AuditLogState(isLoading = false, error = it.message) }
        }
    }
}
