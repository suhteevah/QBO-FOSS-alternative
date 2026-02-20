import SwiftUI

struct AuditLogView: View {
    @Environment(LedgerRepository.self) private var repo
    @State private var vm: AuditLogViewModel?

    var body: some View {
        Group {
            if let vm {
                if vm.isLoading {
                    LoadingIndicator()
                } else if let error = vm.error {
                    ErrorMessageView(message: error) { Task { await vm.load() } }
                } else if vm.logs.isEmpty {
                    ContentUnavailableView("No Audit Logs", systemImage: "clock.arrow.circlepath", description: Text("No audit activity recorded yet"))
                } else {
                    List(vm.logs, id: \.id) { log in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(log.action)
                                    .font(.subheadline.bold())
                                Spacer()
                                Text(log.createdAt)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            HStack(spacing: 8) {
                                Text(log.entityType)
                                    .font(.caption)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(OLColor.blue.opacity(0.12))
                                    .foregroundStyle(OLColor.blue)
                                    .clipShape(Capsule())
                                Text(log.entityId.prefix(8) + "...")
                                    .font(.caption.monospaced())
                                    .foregroundStyle(.tertiary)
                            }
                            if let userId = log.userId {
                                Text("User: \(userId.prefix(8))...")
                                    .font(.caption2)
                                    .foregroundStyle(.tertiary)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                    .listStyle(.plain)
                }
            } else {
                LoadingIndicator()
            }
        }
        .navigationTitle("Audit Log")
        .task {
            if vm == nil { vm = AuditLogViewModel(repo: repo) }
            await vm?.load()
        }
    }
}
