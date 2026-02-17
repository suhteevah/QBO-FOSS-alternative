package com.openledger.android.ui.periods

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.openledger.android.data.remote.dto.PeriodResponse
import com.openledger.android.data.repository.LedgerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PeriodListState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val periods: List<PeriodResponse> = emptyList(),
)

@HiltViewModel
class PeriodListViewModel @Inject constructor(
    private val repo: LedgerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(PeriodListState())
    val state: StateFlow<PeriodListState> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = PeriodListState(isLoading = true)
        viewModelScope.launch {
            repo.getPeriods()
                .onSuccess { _state.value = PeriodListState(isLoading = false, periods = it) }
                .onFailure { _state.value = PeriodListState(isLoading = false, error = it.message) }
        }
    }
}
