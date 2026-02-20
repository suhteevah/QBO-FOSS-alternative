import SwiftUI

struct AccountListView: View {
    @Environment(LedgerRepository.self) private var repo
    @State private var vm: AccountListViewModel?

    var body: some View {
        Group {
            if let vm {
                if vm.isLoading {
                    LoadingIndicator()
                } else if let error = vm.error {
                    ErrorMessageView(message: error) { Task { await vm.load() } }
                } else if vm.accounts.isEmpty {
                    ContentUnavailableView(
                        "No Accounts",
                        systemImage: "building.columns",
                        description: Text("No chart of accounts configured")
                    )
                } else {
                    List {
                        ForEach(vm.groupedAccounts, id: \.type) { group in
                            Section(group.type.replacingOccurrences(of: "_", with: " ").capitalized) {
                                ForEach(group.accounts, id: \.id) { account in
                                    AccountRow(account: account)
                                }
                            }
                        }
                    }
                    .listStyle(.insetGrouped)
                }
            } else {
                LoadingIndicator()
            }
        }
        .navigationTitle("Accounts")
        .task {
            if vm == nil { vm = AccountListViewModel(repo: repo) }
            await vm?.load()
        }
    }
}

private struct AccountRow: View {
    let account: AccountResponse

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(account.accountNumber)
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                    Text(account.name)
                        .font(.subheadline.bold())
                }
                HStack(spacing: 8) {
                    if let sub = account.accountSubtype {
                        Text(sub.replacingOccurrences(of: "_", with: " ").capitalized)
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                    }
                    Text(account.normalBalance.uppercased())
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
            Spacer()
            if !account.isActive {
                Text("Inactive")
                    .font(.caption2)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.gray.opacity(0.12))
                    .foregroundStyle(.gray)
                    .clipShape(Capsule())
            }
        }
    }
}
