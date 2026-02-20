import SwiftUI

struct ReportView: View {
    @Environment(LedgerRepository.self) private var repo
    @State private var vm: ReportViewModel?

    private let reportTypes = [
        ("profit_loss", "Profit & Loss"),
        ("balance_sheet", "Balance Sheet"),
        ("trial_balance", "Trial Balance"),
    ]

    var body: some View {
        Group {
            if let vm {
                ScrollView {
                    VStack(spacing: 16) {
                        // Controls
                        VStack(spacing: 12) {
                            Picker("Report Type", selection: Binding(get: { vm.reportType }, set: { vm.reportType = $0 })) {
                                ForEach(reportTypes, id: \.0) { type in
                                    Text(type.1).tag(type.0)
                                }
                            }
                            .pickerStyle(.segmented)

                            HStack {
                                DatePicker("From", selection: Binding(get: { vm.startDate }, set: { vm.startDate = $0 }), displayedComponents: .date)
                                    .labelsHidden()
                                Text("to")
                                    .foregroundStyle(.secondary)
                                DatePicker("To", selection: Binding(get: { vm.endDate }, set: { vm.endDate = $0 }), displayedComponents: .date)
                                    .labelsHidden()
                            }

                            Button {
                                Task { await vm.generate() }
                            } label: {
                                if vm.isLoading {
                                    ProgressView().frame(maxWidth: .infinity)
                                } else {
                                    Text("Generate Report").frame(maxWidth: .infinity).bold()
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(OLColor.green)
                            .disabled(vm.isLoading)
                        }
                        .padding()
                        .background(OLColor.cardBackground)
                        .clipShape(RoundedRectangle(cornerRadius: 12))

                        if let error = vm.error {
                            Text(error).foregroundStyle(.red).font(.caption)
                        }

                        // Report Output
                        if let report = vm.report {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(report.period)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Text("Basis: \(report.accountingBasis)")
                                    .font(.caption2)
                                    .foregroundStyle(.tertiary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)

                            ForEach(report.sections, id: \.title) { section in
                                ReportSectionView(section: section)
                            }

                            HStack {
                                Text("Net Total")
                                    .font(.headline)
                                Spacer()
                                Text("$\(report.netTotal)")
                                    .font(.headline.bold())
                            }
                            .padding()
                            .background(OLColor.green.opacity(0.1))
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                    }
                    .padding()
                }
            } else {
                LoadingIndicator()
            }
        }
        .navigationTitle("Reports")
        .task {
            if vm == nil { vm = ReportViewModel(repo: repo) }
        }
    }
}

private struct ReportSectionView: View {
    let section: ReportSection

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(section.title)
                .font(.subheadline.bold())
                .padding(.horizontal)
                .padding(.vertical, 8)

            Divider()

            ForEach(section.items, id: \.accountNumber) { item in
                HStack {
                    Text(item.accountNumber)
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                        .frame(width: 50, alignment: .leading)
                    Text(item.accountName)
                        .font(.subheadline)
                    Spacer()
                    Text("$\(item.amount)")
                        .font(.subheadline.monospaced())
                }
                .padding(.horizontal)
                .padding(.vertical, 6)
            }

            Divider()

            HStack {
                Text("Subtotal")
                    .font(.subheadline.bold())
                Spacer()
                Text("$\(section.subtotal)")
                    .font(.subheadline.bold().monospaced())
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
        }
        .background(OLColor.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
