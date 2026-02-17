package com.openledger.android.ui.journal

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.openledger.android.data.remote.dto.AccountResponse
import com.openledger.android.data.remote.dto.JournalEntryCreate
import com.openledger.android.data.remote.dto.LineItemCreate
import com.openledger.android.data.repository.LedgerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LineItemForm(
    val accountId: String = "",
    val debit: String = "",
    val credit: String = "",
)

data class JournalCreateState(
    val entryDate: String = "",
    val description: String = "",
    val lineItems: List<LineItemForm> = listOf(LineItemForm(), LineItemForm()),
    val accounts: List<AccountResponse> = emptyList(),
    val isSubmitting: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class JournalCreateViewModel @Inject constructor(
    private val repo: LedgerRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(JournalCreateState())
    val state: StateFlow<JournalCreateState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            repo.getAccounts().onSuccess { accounts ->
                _state.value = _state.value.copy(accounts = accounts)
            }
        }
    }

    fun onDateChanged(v: String) { _state.value = _state.value.copy(entryDate = v, error = null) }
    fun onDescriptionChanged(v: String) { _state.value = _state.value.copy(description = v, error = null) }

    fun onLineAccountChanged(index: Int, accountId: String) {
        val items = _state.value.lineItems.toMutableList()
        items[index] = items[index].copy(accountId = accountId)
        _state.value = _state.value.copy(lineItems = items)
    }

    fun onLineDebitChanged(index: Int, v: String) {
        val items = _state.value.lineItems.toMutableList()
        items[index] = items[index].copy(debit = v, credit = if (v.isNotBlank()) "" else items[index].credit)
        _state.value = _state.value.copy(lineItems = items)
    }

    fun onLineCreditChanged(index: Int, v: String) {
        val items = _state.value.lineItems.toMutableList()
        items[index] = items[index].copy(credit = v, debit = if (v.isNotBlank()) "" else items[index].debit)
        _state.value = _state.value.copy(lineItems = items)
    }

    fun addLine() {
        _state.value = _state.value.copy(lineItems = _state.value.lineItems + LineItemForm())
    }

    fun removeLine(index: Int) {
        if (_state.value.lineItems.size <= 2) return
        _state.value = _state.value.copy(
            lineItems = _state.value.lineItems.toMutableList().also { it.removeAt(index) },
        )
    }

    fun submit(onDone: () -> Unit) {
        val s = _state.value
        val lineItems = s.lineItems.map {
            LineItemCreate(
                accountId = it.accountId,
                debitAmount = it.debit.ifBlank { "0.00" },
                creditAmount = it.credit.ifBlank { "0.00" },
            )
        }
        val entry = JournalEntryCreate(
            entryDate = s.entryDate,
            description = s.description,
            lineItems = lineItems,
        )
        _state.value = s.copy(isSubmitting = true, error = null)
        viewModelScope.launch {
            repo.createJournalEntry(entry)
                .onSuccess { onDone() }
                .onFailure { _state.value = _state.value.copy(isSubmitting = false, error = it.message) }
        }
    }
}
