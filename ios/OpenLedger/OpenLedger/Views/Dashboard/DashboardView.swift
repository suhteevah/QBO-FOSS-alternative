import SwiftUI

struct DashboardView: View {
    @Environment(LedgerRepository.self) private var repo
    @State private var vm: DashboardViewModel?

    var body: some View {
        Group {
            if let vm {
                if vm.isLoading {
                    LoadingIndicator()
                } else if let error = vm.error {
                    ErrorMessageView(message: error) { Task { await vm.load() } }
                } else {
                    dashboardContent(vm)
                }
            } else {
                LoadingIndicator()
            }
        }
        .navigationTitle("OpenLedger")
        .task {
            if vm == nil { vm = DashboardViewModel(repo: repo) }
            await vm?.load()
        }
    }

    private func dashboardContent(_ vm: DashboardViewModel) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Welcome, \(vm.userName ?? "User")")
                    .font(.title2.bold())
                    .padding(.horizontal)

                // KPI Grid
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    KpiCard(title: "Accounts", value: "\(vm.accountCount)", icon: "building.columns")
                    KpiCard(title: "Entries", value: "\(vm.entryCount)", icon: "book")
                    KpiCard(title: "Transactions", value: "\(vm.txnCount)", icon: "list.bullet.rectangle")
                    KpiCard(title: "Role", value: vm.userRole ?? "\u{2014}", icon: "person.badge.shield.checkmark")
                }
                .padding(.horizontal)

                Text("Quick Access")
                    .font(.title3.bold())
                    .padding(.horizontal)
                    .padding(.top, 8)

                VStack(spacing: 8) {
                    QuickNavRow(label: "Reports", icon: "chart.bar.doc.horizontal", route: .reports)
                    QuickNavRow(label: "Reconciliation", icon: "arrow.left.arrow.right", route: .reconciliation)
                    QuickNavRow(label: "AI Query", icon: "brain", route: .aiQuery)
                    QuickNavRow(label: "Periods", icon: "calendar", route: .periods)
                    QuickNavRow(label: "Audit Log", icon: "clock.arrow.circlepath", route: .auditLog)
                }
                .padding(.horizontal)
            }
            .padding(.vertical)
        }
    }
}

// MARK: - Sub-components

private struct KpiCard: View {
    let title: String
    let value: String
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Image(systemName: icon)
                .foregroundStyle(OLColor.green)
                .font(.title3)
            Text(value)
                .font(.title2.bold())
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(OLColor.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

private struct QuickNavRow: View {
    let label: String
    let icon: String
    let route: AppRoute

    var body: some View {
        NavigationLink(value: route) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(OLColor.green)
                    .frame(width: 24)
                Text(label)
                    .foregroundStyle(.primary)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .padding()
            .background(OLColor.cardBackground)
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
    }
}
