import SwiftUI

struct ServerSetupView: View {

    @Environment(AuthRepository.self) private var authRepo

    var onNext: () -> Void

    @State private var viewModel = ServerSetupViewModel()

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            Image(systemName: "cloud")
                .font(.system(size: 64))
                .foregroundStyle(.tint)

            Spacer().frame(height: 16)

            Text("Connect to OpenLedger")
                .font(.title2.bold())

            Spacer().frame(height: 8)

            Text("Enter your server URL to get started")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Spacer().frame(height: 32)

            TextField("Server URL", text: $viewModel.serverUrl, prompt: Text("http://192.168.1.5:8000"))
                .textFieldStyle(.roundedBorder)
                .keyboardType(.URL)
                .textContentType(.URL)
                .autocapitalization(.none)
                .disableAutocorrection(true)

            Spacer().frame(height: 16)

            Button {
                viewModel.testConnection(authRepo: authRepo, onSuccess: onNext)
            } label: {
                HStack {
                    if viewModel.isLoading {
                        ProgressView()
                            .tint(.white)
                    }
                    Text("Test Connection")
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(viewModel.isLoading || viewModel.serverUrl.trimmingCharacters(in: .whitespaces).isEmpty)

            if let error = viewModel.error {
                Spacer().frame(height: 12)
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
            }

            if let version = viewModel.successVersion {
                Spacer().frame(height: 12)
                Text("Connected -- OpenLedger v\(version)")
                    .font(.caption)
                    .foregroundStyle(.tint)
            }

            Spacer()
        }
        .padding(24)
    }
}
