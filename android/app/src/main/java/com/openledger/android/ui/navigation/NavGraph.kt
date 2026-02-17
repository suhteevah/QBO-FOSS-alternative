package com.openledger.android.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.openledger.android.data.local.EncryptedPrefsManager
import com.openledger.android.ui.accounts.AccountListScreen
import com.openledger.android.ui.ai.AiQueryScreen
import com.openledger.android.ui.audit.AuditLogScreen
import com.openledger.android.ui.auth.ApiKeySetupScreen
import com.openledger.android.ui.auth.LoginScreen
import com.openledger.android.ui.auth.ServerSetupScreen
import com.openledger.android.ui.dashboard.DashboardScreen
import com.openledger.android.ui.journal.JournalCreateScreen
import com.openledger.android.ui.journal.JournalListScreen
import com.openledger.android.ui.periods.PeriodListScreen
import com.openledger.android.ui.receipts.ReceiptCaptureScreen
import com.openledger.android.ui.reconciliation.ReconciliationScreen
import com.openledger.android.ui.reports.ReportScreen
import com.openledger.android.ui.transactions.TransactionListScreen

data class BottomNavItem(
    val screen: Screen,
    val label: String,
    val icon: ImageVector,
)

private val bottomNavItems = listOf(
    BottomNavItem(Screen.Dashboard, "Dashboard", Icons.Filled.Dashboard),
    BottomNavItem(Screen.Transactions, "Txns", Icons.Filled.Receipt),
    BottomNavItem(Screen.Journal, "Journal", Icons.Filled.MenuBook),
    BottomNavItem(Screen.ReceiptCapture, "Receipts", Icons.Filled.CameraAlt),
    BottomNavItem(Screen.Accounts, "More", Icons.Filled.MoreHoriz),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OpenLedgerNavHost(
    prefs: EncryptedPrefsManager = hiltViewModel<NavViewModel>().prefs,
) {
    val navController = rememberNavController()

    // Determine start destination
    val startDestination = when {
        !prefs.hasServerUrl() -> Screen.ServerSetup.route
        !prefs.isConfigured() -> Screen.Login.route
        else -> Screen.Dashboard.route
    }

    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    // Show bottom bar only on main screens
    val showBottomBar = currentDestination?.hierarchy?.any { dest ->
        bottomNavItems.any { it.screen.route == dest.route }
    } == true

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    bottomNavItems.forEach { item ->
                        NavigationBarItem(
                            icon = { Icon(item.icon, contentDescription = item.label) },
                            label = { Text(item.label) },
                            selected = currentDestination?.hierarchy?.any {
                                it.route == item.screen.route
                            } == true,
                            onClick = {
                                navController.navigate(item.screen.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                        )
                    }
                }
            }
        },
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = startDestination,
            modifier = Modifier.padding(innerPadding),
        ) {
            // Auth flow
            composable(Screen.ServerSetup.route) {
                ServerSetupScreen(onNext = { navController.navigate(Screen.Login.route) { popUpTo(0) } })
            }
            composable(Screen.Login.route) {
                LoginScreen(onNext = { navController.navigate(Screen.ApiKeySetup.route) { popUpTo(0) } })
            }
            composable(Screen.ApiKeySetup.route) {
                ApiKeySetupScreen(onNext = { navController.navigate(Screen.Dashboard.route) { popUpTo(0) } })
            }

            // P0 — Main tabs
            composable(Screen.Dashboard.route) {
                DashboardScreen(
                    onNavigate = { route -> navController.navigate(route) },
                )
            }
            composable(Screen.Transactions.route) { TransactionListScreen() }
            composable(Screen.Journal.route) {
                JournalListScreen(onCreateNew = { navController.navigate(Screen.JournalCreate.route) })
            }
            composable(Screen.Accounts.route) {
                AccountListScreen(
                    onNavigate = { route -> navController.navigate(route) },
                )
            }

            // P1 — Core features
            composable(Screen.JournalCreate.route) {
                JournalCreateScreen(onDone = { navController.popBackStack() })
            }
            composable(Screen.ReceiptCapture.route) { ReceiptCaptureScreen() }
            composable(Screen.Reports.route) { ReportScreen() }

            // P2 — Advanced
            composable(Screen.Reconciliation.route) { ReconciliationScreen() }
            composable(Screen.AiQuery.route) { AiQueryScreen() }
            composable(Screen.Periods.route) { PeriodListScreen() }
            composable(Screen.AuditLog.route) { AuditLogScreen() }
        }
    }
}
