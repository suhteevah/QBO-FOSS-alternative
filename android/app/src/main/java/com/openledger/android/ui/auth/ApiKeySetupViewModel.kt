package com.openledger.android.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.openledger.android.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ApiKeySetupState(
    val keyName: String = "Android Phone",
    val isLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class ApiKeySetupViewModel @Inject constructor(
    private val authRepo: AuthRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ApiKeySetupState())
    val state: StateFlow<ApiKeySetupState> = _state.asStateFlow()

    fun onKeyNameChanged(name: String) {
        _state.value = _state.value.copy(keyName = name, error = null)
    }

    fun createKey(onSuccess: () -> Unit) {
        _state.value = _state.value.copy(isLoading = true, error = null)
        viewModelScope.launch {
            authRepo.createApiKey(_state.value.keyName)
                .onSuccess { onSuccess() }
                .onFailure { e ->
                    _state.value = _state.value.copy(
                        isLoading = false,
                        error = "Failed to create key: ${e.message}",
                    )
                }
        }
    }
}
