import SwiftUI

struct ContentView: View {

    @Environment(KeychainManager.self) private var keychain
    @Environment(AppNavigator.self) private var navigator

    @State private var selectedTab: MainTab = .dashboard

    var body: some View {
        if keychain.isConfigured() {
            mainTabView
        } else {
            authFlow
        }
    }

    // MARK: - Auth Flow

    @State private var authStep: AuthStep = .serverSetup

    private enum AuthStep {
        case serverSetup
        case login
        case apiKeySetup
    }

    private var authFlow: some View {
        NavigationStack {
            switch authStep {
            case .serverSetup:
                ServerSetupView {
                    authStep = .login
                }
            case .login:
                LoginView {
                    authStep = .apiKeySetup
                }
            case .apiKeySetup:
                ApiKeySetupView {
                    // Auth complete -- keychain.isConfigured() now true,
                    // SwiftUI will re-evaluate body and show mainTabView.
                }
            }
        }
    }

    // MARK: - Main Tab View

    private var mainTabView: some View {
        TabView(selection: $selectedTab) {
            ForEach(MainTab.allCases, id: \.self) { tab in
                tabContent(for: tab)
                    .tabItem {
                        Label(tab.title, systemImage: tab.icon)
                    }
                    .tag(tab)
            }
        }
    }

    @ViewBuilder
    private func tabContent(for tab: MainTab) -> some View {
        switch tab {
        case .dashboard:
            NavigationStack {
                DashboardView()
                    .navigationDestination(for: AppRoute.self) { route in
                        destinationView(for: route)
                    }
            }
        case .transactions:
            NavigationStack {
                TransactionListView()
            }
        case .journal:
            NavigationStack {
                JournalListView()
                    .navigationDestination(for: AppRoute.self) { route in
                        destinationView(for: route)
                    }
            }
        case .receipts:
            NavigationStack {
                ReceiptCaptureView()
            }
        case .more:
            NavigationStack {
                MoreView()
                    .navigationDestination(for: AppRoute.self) { route in
                        destinationView(for: route)
                    }
            }
        }
    }

    @ViewBuilder
    private func destinationView(for route: AppRoute) -> some View {
        switch route {
        case .reports:
            ReportView()
        case .reconciliation:
            ReconciliationView()
        case .aiQuery:
            AiQueryView()
        case .periods:
            PeriodListView()
        case .auditLog:
            AuditLogView()
        case .journalCreate:
            JournalCreateView()
        case .receiptCapture:
            ReceiptCaptureView()
        default:
            Text("Not implemented")
        }
    }
}
