package com.openledger.android.di

import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
object RepositoryModule
// Repositories are @Singleton @Inject constructor — Hilt resolves them automatically.
// This module exists as a placeholder for any future manual bindings.
