import SwiftUI

struct JournalCreateView: View {
    @Environment(LedgerRepository.self) private var repo
    @Environment(\.dismiss) private var dismiss
    @State private var vm: JournalCreateViewModel?

    var body: some View {
        Group {
            if let vm {
                Form {
                    Section("Entry Details") {
                        DatePicker("Date", selection: Binding(get: { vm.entryDate }, set: { vm.entryDate = $0 }), displayedComponents: .date)
                        TextField("Description", text: Binding(get: { vm.description }, set: { vm.description = $0 }))
                    }

                    ForEach(Array(vm.lineItems.enumerated()), id: \.element.id) { index, item in
                        Section("Line \(index + 1)") {
                            Picker("Account", selection: Binding(
                                get: { vm.lineItems[index].accountId },
                                set: { vm.lineItems[index].accountId = $0 }
                            )) {
                                Text("Select Account").tag("")
                                ForEach(vm.accounts, id: \.id) { acct in
                                    Text("\(acct.accountNumber) — \(acct.name)").tag(acct.id)
                                }
                            }
                            TextField("Description", text: Binding(
                                get: { vm.lineItems[index].description },
                                set: { vm.lineItems[index].description = $0 }
                            ))
                            HStack {
                                TextField("Debit", text: Binding(
                                    get: { vm.lineItems[index].debitAmount },
                                    set: { vm.lineItems[index].debitAmount = $0 }
                                ))
                                .keyboardType(.decimalPad)
                                TextField("Credit", text: Binding(
                                    get: { vm.lineItems[index].creditAmount },
                                    set: { vm.lineItems[index].creditAmount = $0 }
                                ))
                                .keyboardType(.decimalPad)
                            }
                            if vm.lineItems.count > 2 {
                                Button("Remove", role: .destructive) {
                                    vm.removeLineItem(id: item.id)
                                }
                            }
                        }
                    }

                    Section {
                        Button("Add Line Item") { vm.addLineItem() }
                    }

                    Section {
                        HStack {
                            Text("Balanced")
                            Spacer()
                            Image(systemName: vm.isBalanced ? "checkmark.circle.fill" : "xmark.circle.fill")
                                .foregroundStyle(vm.isBalanced ? OLColor.green : OLColor.red)
                        }
                    }

                    if let error = vm.error {
                        Section {
                            Text(error).foregroundStyle(.red).font(.caption)
                        }
                    }

                    Section {
                        Button {
                            Task { await vm.save() }
                        } label: {
                            if vm.isLoading {
                                ProgressView()
                                    .frame(maxWidth: .infinity)
                            } else {
                                Text("Save Entry")
                                    .frame(maxWidth: .infinity)
                                    .bold()
                            }
                        }
                        .disabled(!vm.isBalanced || vm.isLoading || vm.description.isEmpty)
                    }
                }
                .onChange(of: vm.isSaved) { _, saved in
                    if saved { dismiss() }
                }
            } else {
                LoadingIndicator()
            }
        }
        .navigationTitle("New Journal Entry")
        .task {
            if vm == nil { vm = JournalCreateViewModel(repo: repo) }
            await vm?.loadAccounts()
        }
    }
}
