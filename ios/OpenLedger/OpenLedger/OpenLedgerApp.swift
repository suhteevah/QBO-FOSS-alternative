import SwiftUI

@main
struct OpenLedgerApp: App {

    private let keychain = KeychainManager()
    private let apiClient: APIClient
    private let authRepository: AuthRepository
    private let ledgerRepository: LedgerRepository
    private let navigator: AppNavigator

    init() {
        let kc = keychain
        let client = APIClient(keychain: kc)
        apiClient = client
        authRepository = AuthRepository(api: client, keychain: kc)
        ledgerRepository = LedgerRepository(api: client)
        navigator = AppNavigator(keychain: kc)
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(keychain)
                .environment(navigator)
                .environment(apiClient)
                .environment(authRepository)
                .environment(ledgerRepository)
        }
    }
}
