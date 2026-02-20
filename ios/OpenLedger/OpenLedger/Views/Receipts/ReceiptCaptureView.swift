import SwiftUI
import PhotosUI

struct ReceiptCaptureView: View {
    @Environment(APIClient.self) private var api

    @State private var selectedItem: PhotosPickerItem?
    @State private var imageData: Data?
    @State private var isUploading = false
    @State private var error: String?
    @State private var receipt: ReceiptResponse?

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                PhotosPicker(selection: $selectedItem, matching: .images) {
                    if let imageData, let uiImage = UIImage(data: imageData) {
                        Image(uiImage: uiImage)
                            .resizable()
                            .scaledToFit()
                            .frame(maxHeight: 300)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    } else {
                        VStack(spacing: 12) {
                            Image(systemName: "camera.fill")
                                .font(.system(size: 48))
                                .foregroundStyle(OLColor.green)
                            Text("Select Receipt Image")
                                .font(.headline)
                            Text("Tap to choose a photo from your library")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity)
                        .frame(height: 200)
                        .background(OLColor.cardBackground)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                }
                .onChange(of: selectedItem) { _, newItem in
                    Task {
                        if let data = try? await newItem?.loadTransferable(type: Data.self) {
                            imageData = data
                            receipt = nil
                            error = nil
                        }
                    }
                }

                if imageData != nil {
                    Button {
                        Task { await upload() }
                    } label: {
                        if isUploading {
                            ProgressView()
                                .frame(maxWidth: .infinity)
                        } else {
                            Label("Upload & Process", systemImage: "arrow.up.circle.fill")
                                .frame(maxWidth: .infinity)
                                .bold()
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(OLColor.green)
                    .disabled(isUploading)
                }

                if let error {
                    Text(error)
                        .foregroundStyle(.red)
                        .font(.caption)
                }

                if let receipt {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Receipt Processed")
                            .font(.headline)
                            .foregroundStyle(OLColor.green)

                        Group {
                            if let merchant = receipt.merchantName {
                                LabeledContent("Merchant", value: merchant)
                            }
                            if let date = receipt.transactionDate {
                                LabeledContent("Date", value: date)
                            }
                            if let total = receipt.totalAmount {
                                LabeledContent("Total", value: "$\(total)")
                            }
                            if let tax = receipt.taxAmount {
                                LabeledContent("Tax", value: "$\(tax)")
                            }
                            if let conf = receipt.ocrConfidence {
                                LabeledContent("OCR Confidence", value: conf)
                            }
                        }
                        .font(.subheadline)
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(OLColor.cardBackground)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
            .padding()
        }
        .navigationTitle("Capture Receipt")
    }

    private func upload() async {
        guard let imageData else { return }
        isUploading = true
        error = nil
        do {
            let result: ReceiptResponse = try await api.upload(
                path: "/api/receipts/upload",
                fileData: imageData,
                fileName: "receipt.jpg",
                mimeType: "image/jpeg"
            )
            receipt = result
        } catch {
            self.error = error.localizedDescription
        }
        isUploading = false
    }
}
