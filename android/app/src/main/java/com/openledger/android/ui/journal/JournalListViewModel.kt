package com.openledger.android.ui.journal

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.openledger.android.data.remote.dto.JournalEntryResponse
import com.openledger.android.data.repository.LedgerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class JournalListState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val entries: List<JournalEntryResponse> = emptyList(),
)

@HiltViewModel
class JournalListViewModel @Inject constructor(
    private val repo: LedgerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(JournalListState())
    val state: StateFlow<JournalListState> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = JournalListState(isLoading = true)
        viewModelScope.launch {
            repo.getJournalEntries()
                .onSuccess { _state.value = JournalListState(isLoading = false, entries = it) }
                .onFailure { _state.value = JournalListState(isLoading = false, error = it.message) }
        }
    }
}
