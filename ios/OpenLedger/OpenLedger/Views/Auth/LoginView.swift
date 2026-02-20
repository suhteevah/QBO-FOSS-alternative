import SwiftUI

struct LoginView: View {

    @Environment(AuthRepository.self) private var authRepo

    var onNext: () -> Void

    @State private var viewModel = LoginViewModel()
    @State private var showPassword = false

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            Image(systemName: "lock")
                .font(.system(size: 64))
                .foregroundStyle(.tint)

            Spacer().frame(height: 16)

            Text("Sign In")
                .font(.title2.bold())

            Spacer().frame(height: 8)

            Text("Use your OpenLedger account credentials")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Spacer().frame(height: 32)

            TextField("Email", text: $viewModel.email)
                .textFieldStyle(.roundedBorder)
                .keyboardType(.emailAddress)
                .textContentType(.emailAddress)
                .autocapitalization(.none)
                .disableAutocorrection(true)

            Spacer().frame(height: 12)

            HStack {
                Group {
                    if showPassword {
                        TextField("Password", text: $viewModel.password)
                    } else {
                        SecureField("Password", text: $viewModel.password)
                    }
                }
                .textFieldStyle(.roundedBorder)
                .textContentType(.password)

                Button {
                    showPassword.toggle()
                } label: {
                    Image(systemName: showPassword ? "eye.slash" : "eye")
                        .foregroundStyle(.secondary)
                }
            }

            Spacer().frame(height: 20)

            Button {
                viewModel.login(authRepo: authRepo, onSuccess: onNext)
            } label: {
                HStack {
                    if viewModel.isLoading {
                        ProgressView()
                            .tint(.white)
                    }
                    Text("Sign In")
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(
                viewModel.isLoading
                || viewModel.email.trimmingCharacters(in: .whitespaces).isEmpty
                || viewModel.password.isEmpty
            )

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
