import SwiftUI

struct ReconciliationView: View {
    @Environment(LedgerRepository.self) private var repo
    @State private var vm: ReconciliationViewModel?

    var body: some View {
        Group {
            if let vm {
                if vm.isLoading {
                    LoadingIndicator()
                } else if let error = vm.error {
                    ErrorMessageView(message: error) { Task { await vm.load() } }
                } else {
                    List {
                        Section {
                            Button {
                                Task { await vm.autoMatch() }
                            } label: {
                                Label("Run Auto-Match", systemImage: "arrow.left.arrow.right")
                                    .frame(maxWidth: .infinity)
                                    .bold()
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(OLColor.green)
                            .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                        }

                        if !vm.suggestions.isEmpty {
                            Section("Match Suggestions") {
                                ForEach(vm.suggestions, id: \.transactionId) { s in
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("Txn: \(s.transactionId.prefix(8))...")
                                            .font(.caption.monospaced())
                                        Text("Entry: \(s.journalEntryId.prefix(8))...")
                                            .font(.caption.monospaced())
                                        HStack {
                                            Text("Score")
                                            Spacer()
                                            Text(s.matchScore)
                                                .bold()
                                                .foregroundStyle(OLColor.green)
                                        }
                                        .font(.subheadline)
                                    }
                                    .padding(.vertical, 4)
                                }
                            }
                        }

                        Section("Unmatched Transactions (\(vm.unmatched.count))") {
                            if vm.unmatched.isEmpty {
                                Text("All transactions matched!")
                                    .foregroundStyle(.secondary)
                            } else {
                                ForEach(vm.unmatched, id: \.id) { txn in
                                    HStack {
                                        VStack(alignment: .leading) {
                                            Text(txn.descriptionCleaned ?? txn.descriptionRaw)
                                                .font(.subheadline)
                                            Text(txn.transactionDate)
                                                .font(.caption)
                                                .foregroundStyle(.secondary)
                                        }
                                        Spacer()
                                        Text("$\(txn.amount)")
                                            .font(.subheadline.bold())
                                    }
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
        .navigationTitle("Reconciliation")
        .task {
            if vm == nil { vm = ReconciliationViewModel(repo: repo) }
            await vm?.load()
        }
    }
}
