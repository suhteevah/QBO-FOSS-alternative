import SwiftUI

struct PeriodListView: View {
    @Environment(LedgerRepository.self) private var repo
    @State private var vm: PeriodListViewModel?

    var body: some View {
        Group {
            if let vm {
                if vm.isLoading {
                    LoadingIndicator()
                } else if let error = vm.error {
                    ErrorMessageView(message: error) { Task { await vm.load() } }
                } else if vm.periods.isEmpty {
                    ContentUnavailableView("No Periods", systemImage: "calendar", description: Text("No accounting periods configured"))
                } else {
                    List(vm.periods, id: \.id) { period in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(period.name)
                                    .font(.headline)
                                Spacer()
                                Text(period.status.capitalized)
                                    .font(.caption2.bold())
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(period.status.lowercased() == "open" ? OLColor.green.opacity(0.12) : Color.red.opacity(0.12))
                                    .foregroundStyle(period.status.lowercased() == "open" ? OLColor.green : .red)
                                    .clipShape(Capsule())
                            }
                            Text("\(period.startDate) — \(period.endDate)")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            if let closedBy = period.closedBy, let closedAt = period.closedAt {
                                Text("Closed by \(closedBy) on \(closedAt)")
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
        .navigationTitle("Periods")
        .task {
            if vm == nil { vm = PeriodListViewModel(repo: repo) }
            await vm?.load()
        }
    }
}
