package com.openledger.android.ui.ai

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.openledger.android.data.remote.dto.AiQueryResponse
import com.openledger.android.data.repository.LedgerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AiQueryState(
    val query: String = "",
    val isLoading: Boolean = false,
    val error: String? = null,
    val response: AiQueryResponse? = null,
)

@HiltViewModel
class AiQueryViewModel @Inject constructor(
    private val repo: LedgerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AiQueryState())
    val state: StateFlow<AiQueryState> = _state.asStateFlow()

    fun onQueryChanged(v: String) {
        _state.value = _state.value.copy(query = v, error = null)
    }

    fun submit() {
        val q = _state.value.query.trim()
        if (q.isBlank()) return
        _state.value = _state.value.copy(isLoading = true, error = null, response = null)
        viewModelScope.launch {
            repo.aiQuery(q)
                .onSuccess { _state.value = _state.value.copy(isLoading = false, response = it) }
                .onFailure { _state.value = _state.value.copy(isLoading = false, error = it.message) }
        }
    }
}
