import Foundation

struct EditableLineItem: Identifiable {
    let id = UUID()
    var accountId: String = ""
    var description: String = ""
    var debitAmount: String = ""
    var creditAmount: String = ""
}

@Observable
final class JournalCreateViewModel {
    var entryDate = Date.now
    var description = ""
    var lineItems: [EditableLineItem] = [EditableLineItem(), EditableLineItem()]
    var accounts: [AccountResponse] = []
    var isLoading = false
    var error: String?
    var isSaved = false

    var isBalanced: Bool {
        let debits = lineItems.compactMap { Decimal(string: $0.debitAmount) }.reduce(0, +)
        let credits = lineItems.compactMap { Decimal(string: $0.creditAmount) }.reduce(0, +)
        return debits > 0 && debits == credits
    }

    private let repo: LedgerRepository

    init(repo: LedgerRepository) {
        self.repo = repo
    }

    func loadAccounts() async {
        do {
            accounts = try await repo.getAccounts()
        } catch {
            self.error = error.localizedDescription
        }
    }

    func addLineItem() {
        lineItems.append(EditableLineItem())
    }

    func removeLineItem(id: UUID) {
        lineItems.removeAll { $0.id == id }
    }

    func save() async {
        guard isBalanced else {
            error = "Debits and credits must balance"
            return
        }
        isLoading = true
        error = nil
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let items = lineItems.map {
            LineItemCreate(
                accountId: $0.accountId,
                description: $0.description.isEmpty ? nil : $0.description,
                debitAmount: $0.debitAmount.isEmpty ? "0.00" : $0.debitAmount,
                creditAmount: $0.creditAmount.isEmpty ? "0.00" : $0.creditAmount
            )
        }
        let entry = JournalEntryCreate(
            entryDate: formatter.string(from: entryDate),
            description: description,
            source: "manual",
            lineItems: items
        )
        do {
            _ = try await repo.createJournalEntry(entry)
            isSaved = true
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
