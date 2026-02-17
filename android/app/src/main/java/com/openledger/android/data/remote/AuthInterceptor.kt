package com.openledger.android.data.remote

import com.openledger.android.data.local.EncryptedPrefsManager
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject

class AuthInterceptor @Inject constructor(
    private val prefs: EncryptedPrefsManager,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val builder = original.newBuilder()

        // Prefer API key (mobile auth), fall back to JWT
        val apiKey = prefs.apiKey
        val jwt = prefs.jwtToken

        when {
            !apiKey.isNullOrBlank() -> builder.header("X-API-Key", apiKey)
            !jwt.isNullOrBlank() -> builder.header("Authorization", "Bearer $jwt")
        }

        return chain.proceed(builder.build())
    }
}
