package com.openledger.android.ui.navigation

import androidx.lifecycle.ViewModel
import com.openledger.android.data.local.EncryptedPrefsManager
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class NavViewModel @Inject constructor(
    val prefs: EncryptedPrefsManager,
) : ViewModel()
