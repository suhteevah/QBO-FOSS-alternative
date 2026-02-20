import SwiftUI

struct TransactionListView: View {
    @Environment(LedgerRepository.self) private var repo
    @State private var vm: TransactionListViewModel?

    var body: some View {
        Group {
            if let vm {
                if vm.isLoading {
                    LoadingIndicator()
                } else if let error = vm.error {
                    ErrorMessageView(message: error) { Task { await vm.load() } }
                } else if vm.transactions.isEmpty {
                    ContentUnavailableView(
                        "No Transactions",
                        systemImage: "list.bullet.rectangle",
                        description: Text("No bank transactions imported yet")
                    )
                } else {
                    List(vm.transactions, id: \.id) { txn in
                        TransactionRow(txn: txn)
                    }
                    .listStyle(.plain)
                }
            } else {
                LoadingIndicator()
            }
        }
        .navigationTitle("Transactions")
        .task {
            if vm == nil { vm = TransactionListViewModel(repo: repo) }
            await vm?.load()
        }
    }
}

private struct TransactionRow: View {
    let txn: BankTransactionResponse

    private var amount: Decimal? {
        Decimal(string: txn.amount)
    }

    private var isNegative: Bool {
        (amount ?? 0) < 0
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(txn.transactionDate)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                Text("$\(txn.amount)")
                    .font(.headline)
                    .foregroundStyle(isNegative ? OLColor.red : OLColor.green)
            }
            Text(txn.descriptionCleaned ?? txn.descriptionRaw)
                .font(.subheadline)
            HStack(spacing: 8) {
                if txn.isReconciled {
                    ChipView(text: "Reconciled", color: OLColor.green)
                }
                if let cat = txn.aiCategory {
                    ChipView(text: cat, color: OLColor.blue)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

private struct ChipView: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.caption2)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(color.opacity(0.12))
            .foregroundStyle(color)
            .clipShape(Capsule())
    }
}
