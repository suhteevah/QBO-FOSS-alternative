import SwiftUI

struct MoreView: View {
    @Environment(AuthRepository.self) private var authRepo
    @Environment(KeychainManager.self) private var keychain

    var body: some View {
        List {
            Section("Features") {
                NavigationLink(value: AppRoute.reports) {
                    Label("Reports", systemImage: "chart.bar.doc.horizontal")
                }
                NavigationLink(value: AppRoute.reconciliation) {
                    Label("Reconciliation", systemImage: "arrow.left.arrow.right")
                }
                NavigationLink(value: AppRoute.aiQuery) {
                    Label("AI Query", systemImage: "brain")
                }
                NavigationLink(value: AppRoute.periods) {
                    Label("Periods", systemImage: "calendar")
                }
                NavigationLink(value: AppRoute.auditLog) {
                    Label("Audit Log", systemImage: "clock.arrow.circlepath")
                }
            }

            Section {
                Button(role: .destructive) {
                    authRepo.logout()
                } label: {
                    Label("Sign Out", systemImage: "rectangle.portrait.and.arrow.right")
                }
            }
        }
        .navigationTitle("More")
        .listStyle(.insetGrouped)
    }
}
