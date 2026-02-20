import Foundation

enum MainTab: String, CaseIterable, Hashable {
    case dashboard
    case transactions
    case journal
    case receipts
    case more

    var title: String {
        switch self {
        case .dashboard:    return "Dashboard"
        case .transactions: return "Transactions"
        case .journal:      return "Journal"
        case .receipts:     return "Receipts"
        case .more:         return "More"
        }
    }

    var icon: String {
        switch self {
        case .dashboard:    return "chart.bar"
        case .transactions: return "list.bullet.rectangle"
        case .journal:      return "book"
        case .receipts:     return "camera"
        case .more:         return "ellipsis"
        }
    }
}
