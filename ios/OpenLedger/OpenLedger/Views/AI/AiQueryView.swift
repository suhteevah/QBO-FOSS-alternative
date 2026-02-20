import SwiftUI

struct AiQueryView: View {
    @Environment(LedgerRepository.self) private var repo
    @State private var vm: AiQueryViewModel?

    var body: some View {
        Group {
            if let vm {
                ScrollView {
                    VStack(spacing: 16) {
                        HStack {
                            TextField("Ask about your books...", text: Binding(get: { vm.query }, set: { vm.query = $0 }))
                                .textFieldStyle(.roundedBorder)

                            Button {
                                Task { await vm.submit() }
                            } label: {
                                if vm.isLoading {
                                    ProgressView()
                                } else {
                                    Image(systemName: "paperplane.fill")
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(OLColor.green)
                            .disabled(vm.query.trimmingCharacters(in: .whitespaces).isEmpty || vm.isLoading)
                        }

                        if let error = vm.error {
                            Text(error).foregroundStyle(.red).font(.caption)
                        }

                        if let resp = vm.response {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Interpreted as:")
                                    .font(.caption.bold())
                                    .foregroundStyle(.secondary)
                                Text(resp.interpretedAs)
                                    .font(.subheadline)

                                if let sql = resp.sqlGenerated {
                                    Text("SQL:")
                                        .font(.caption.bold())
                                        .foregroundStyle(.secondary)
                                    Text(sql)
                                        .font(.caption.monospaced())
                                        .padding(8)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(Color.gray.opacity(0.1))
                                        .clipShape(RoundedRectangle(cornerRadius: 8))
                                }

                                if resp.cached {
                                    Text("(cached result)")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .padding()
                            .background(OLColor.cardBackground)
                            .clipShape(RoundedRectangle(cornerRadius: 12))

                            // Results table
                            if let firstRow = resp.results.first {
                                let columns = Array(firstRow.keys).sorted()
                                VStack(alignment: .leading, spacing: 0) {
                                    // Header
                                    HStack {
                                        ForEach(columns, id: \.self) { col in
                                            Text(col)
                                                .font(.caption.bold())
                                                .frame(maxWidth: .infinity, alignment: .leading)
                                        }
                                    }
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 6)
                                    .background(OLColor.green.opacity(0.1))

                                    // Rows
                                    ForEach(Array(resp.results.enumerated()), id: \.offset) { _, row in
                                        HStack {
                                            ForEach(columns, id: \.self) { col in
                                                Text(row[col] ?? "—")
                                                    .font(.caption)
                                                    .frame(maxWidth: .infinity, alignment: .leading)
                                            }
                                        }
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 4)
                                    }
                                }
                                .background(OLColor.cardBackground)
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                            } else {
                                Text("No results")
                                    .foregroundStyle(.secondary)
                                    .font(.subheadline)
                            }
                        }
                    }
                    .padding()
                }
            } else {
                LoadingIndicator()
            }
        }
        .navigationTitle("AI Query")
        .task {
            if vm == nil { vm = AiQueryViewModel(repo: repo) }
        }
    }
}
