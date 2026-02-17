package com.openledger.android.ui.reports

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.openledger.android.data.remote.dto.ReportRequest
import com.openledger.android.data.remote.dto.ReportResponse
import com.openledger.android.data.repository.LedgerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ReportState(
    val reportType: String = "profit_loss",
    val startDate: String = "2026-01-01",
    val endDate: String = "2026-12-31",
    val isLoading: Boolean = false,
    val error: String? = null,
    val report: ReportResponse? = null,
)

@HiltViewModel
class ReportViewModel @Inject constructor(
    private val repo: LedgerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ReportState())
    val state: StateFlow<ReportState> = _state.asStateFlow()

    fun onTypeChanged(v: String) { _state.value = _state.value.copy(reportType = v, error = null, report = null) }
    fun onStartDateChanged(v: String) { _state.value = _state.value.copy(startDate = v) }
    fun onEndDateChanged(v: String) { _state.value = _state.value.copy(endDate = v) }

    fun generate() {
        val s = _state.value
        _state.value = s.copy(isLoading = true, error = null, report = null)
        viewModelScope.launch {
            repo.generateReport(ReportRequest(s.reportType, s.startDate, s.endDate))
                .onSuccess { _state.value = _state.value.copy(isLoading = false, report = it) }
                .onFailure { _state.value = _state.value.copy(isLoading = false, error = it.message) }
        }
    }
}
