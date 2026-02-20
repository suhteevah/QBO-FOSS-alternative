import SwiftUI

struct JournalListView: View {
    @Environment(LedgerRepository.self) private var repo
    @State private var vm: JournalListViewModel?

    var body: some View {
        Group {
            if let vm {
                if vm.isLoading {
                    LoadingIndicator()
                } else if let error = vm.error {
                    ErrorMessageView(message: error) { Task { await vm.load() } }
                } else if vm.entries.isEmpty {
                    ContentUnavailableView(
                        "No Journal Entries",
                        systemImage: "book",
                        description: Text("Create your first journal entry")
                    )
                } else {
                    List(vm.entries, id: \.id) { entry in
                        JournalEntryRow(entry: entry)
                    }
                    .listStyle(.plain)
                }
            } else {
                LoadingIndicator()
            }
        }
        .navigationTitle("Journal Entries")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                NavigationLink(value: AppRoute.journalCreate) {
                    Image(systemName: "plus")
                }
            }
        }
        .task {
            if vm == nil { vm = JournalListViewModel(repo: repo) }
            await vm?.load()
        }
    }
}

private struct JournalEntryRow: View {
    let entry: JournalEntryResponse

    private var statusColor: Color {
        switch entry.status.lowercased() {
        case "posted": return OLColor.green
        case "draft": return .gray
        case "pending": return .orange
        default: return .gray
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                if let num = entry.entryNumber {
                    Text("#\(num)")
                        .font(.caption.bold())
                        .foregroundStyle(.secondary)
                }
                Text(entry.entryDate)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                Text(entry.status.capitalized)
                    .font(.caption2.bold())
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(statusColor.opacity(0.12))
                    .foregroundStyle(statusColor)
                    .clipShape(Capsule())
            }
            if let desc = entry.description {
                Text(desc)
                    .font(.subheadline)
            }
            HStack {
                Text("Source: \(entry.source)")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                if let conf = entry.aiConfidence {
                    Text("AI: \(conf)")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
            // Line items summary
            if !entry.lineItems.isEmpty {
                let totalDebit = entry.lineItems
                    .compactMap { Decimal(string: $0.debitAmount) }
                    .reduce(Decimal.zero, +)
                let totalCredit = entry.lineItems
                    .compactMap { Decimal(string: $0.creditAmount) }
                    .reduce(Decimal.zero, +)
                Text("\(entry.lineItems.count) lines \u{00B7} DR \(totalDebit) / CR \(totalCredit)")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}
