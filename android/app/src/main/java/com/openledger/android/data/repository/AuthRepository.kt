package com.openledger.android.data.repository

import android.os.Build
import com.openledger.android.data.local.EncryptedPrefsManager
import com.openledger.android.data.remote.OpenLedgerApi
import com.openledger.android.data.remote.dto.ApiKeyCreateRequest
import com.openledger.android.data.remote.dto.LoginRequest
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val api: OpenLedgerApi,
    private val prefs: EncryptedPrefsManager,
) {
    suspend fun checkHealth(): Result<String> = runCatching {
        val response = api.health()
        if (response.isSuccessful) response.body()!!.version
        else throw Exception("Server returned ${response.code()}")
    }

    suspend fun login(email: String, password: String): Result<String> = runCatching {
        val response = api.login(LoginRequest(email, password))
        if (!response.isSuccessful) throw Exception("Login failed: ${response.code()}")
        val token = response.body()!!.accessToken
        prefs.jwtToken = token
        token
    }

    suspend fun createApiKey(name: String): Result<String> = runCatching {
        val deviceModel = "${Build.MANUFACTURER} ${Build.MODEL}"
        val request = ApiKeyCreateRequest(
            name = name,
            platform = "android",
            deviceInfo = deviceModel,
        )
        val response = api.createApiKey(request)
        if (!response.isSuccessful) throw Exception("Failed to create API key: ${response.code()}")
        val rawKey = response.body()!!.rawKey
        prefs.apiKey = rawKey
        prefs.jwtToken = null  // No longer need JWT — API key is permanent
        rawKey
    }

    fun isConfigured(): Boolean = prefs.isConfigured()
    fun hasServerUrl(): Boolean = prefs.hasServerUrl()
    fun getServerUrl(): String? = prefs.serverUrl
    fun setServerUrl(url: String) { prefs.serverUrl = url }
    fun logout() { prefs.clear() }
}
