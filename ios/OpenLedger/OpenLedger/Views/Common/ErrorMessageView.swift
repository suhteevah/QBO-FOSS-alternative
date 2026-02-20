import SwiftUI

struct ErrorMessageView: View {
    let message: String
    var onRetry: (() -> Void)? = nil

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 40))
                .foregroundStyle(.red)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
            if let onRetry {
                Button("Try Again", action: onRetry)
                    .buttonStyle(.borderedProminent)
                    .tint(OLColor.green)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
