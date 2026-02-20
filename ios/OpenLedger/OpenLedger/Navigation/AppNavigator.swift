import Foundation
import SwiftUI

@Observable
final class AppNavigator {

    private let keychain: KeychainManager

    var path = NavigationPath()

    init(keychain: KeychainManager) {
        self.keychain = keychain
    }

    /// Determines the first screen based on keychain state.
    var startRoute: AppRoute {
        if !keychain.hasServerUrl() {
            return .serverSetup
        } else if !keychain.isConfigured() {
            return .login
        } else {
            return .dashboard
        }
    }

    func navigate(to route: AppRoute) {
        path.append(route)
    }

    func pop() {
        if !path.isEmpty {
            path.removeLast()
        }
    }

    func popToRoot() {
        path = NavigationPath()
    }
}
