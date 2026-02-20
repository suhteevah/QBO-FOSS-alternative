import SwiftUI

struct ApiKeySetupView: View {

    @Environment(AuthRepository.self) private var authRepo

    var onNext: () -> Void

    @State private var viewModel = ApiKeySetupViewModel()

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            Image(systemName: "key")
                .font(.system(size: 64))
                .foregroundStyle(.tint)

            Spacer().frame(height: 16)

            Text("Create API Key")
                .font(.title2.bold())

            Spacer().frame(height: 8)

            Text("This device will use a secure API key for all future access. You won't need to sign in again.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            Spacer().frame(height: 32)

            TextField("Device Name", text: $viewModel.keyName, prompt: Text("My iPhone"))
                .textFieldStyle(.roundedBorder)
                .disableAutocorrection(true)

            Spacer().frame(height: 20)

            Button {
                viewModel.createKey(authRepo: authRepo, onSuccess: onNext)
            } label: {
                HStack {
                    if viewModel.isLoading {
                        ProgressView()
                            .tint(.white)
                    }
                    Text("Create & Connect")
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(viewModel.isLoading || viewModel.keyName.trimmingCharacters(in: .whitespaces).isEmpty)

            if let error = viewModel.error {
                Spacer().frame(height: 12)
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
            }

            Spacer()
        }
        .padding(24)
    }
}
