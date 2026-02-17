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

data class ServerSetupState(
    val serverUrl: String = "http://10.0.2.2:8000",
    val isLoading: Boolean = false,
    val error: String? = null,
    val success: String? = null,
)

@HiltViewModel
class ServerSetupViewModel @Inject constructor(
    private val authRepo: AuthRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ServerSetupState(
        serverUrl = authRepo.getServerUrl() ?: "http://10.0.2.2:8000"
    ))
    val state: StateFlow<ServerSetupState> = _state.asStateFlow()

    fun onUrlChanged(url: String) {
        _state.value = _state.value.copy(serverUrl = url, error = null, success = null)
    }

    fun testConnection(onSuccess: () -> Unit) {
        val url = _state.value.serverUrl.trimEnd('/')
        _state.value = _state.value.copy(isLoading = true, error = null, success = null)

        authRepo.setServerUrl(url)

        viewModelScope.launch {
            authRepo.checkHealth()
                .onSuccess { version ->
                    _state.value = _state.value.copy(isLoading = false, success = version)
                    onSuccess()
                }
                .onFailure { e ->
                    _state.value = _state.value.copy(
                        isLoading = false,
                        error = "Connection failed: ${e.message}",
                    )
                }
        }
    }
}
