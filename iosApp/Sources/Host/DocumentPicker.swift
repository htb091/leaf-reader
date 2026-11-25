import SwiftUI
import UIKit
import UniformTypeIdentifiers
import Shared

@MainActor
struct DocumentPicker: UIViewControllerRepresentable {
    let onSelection: ([URL]) -> Void
    let onCancel: () -> Void

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }
    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let epub = UTType(filenameExtension: "epub") ?? UTType(importedAs: "org.idpf.epub-container")
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: [.plainText, epub], asCopy: true)
        picker.allowsMultipleSelection = true
        picker.delegate = context.coordinator
        return picker
    }
    func updateUIViewController(_ controller: UIDocumentPickerViewController, context: Context) {}

    final class Coordinator: NSObject, UIDocumentPickerDelegate {
        let parent: DocumentPicker
        init(parent: DocumentPicker) { self.parent = parent }
        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            parent.onSelection(urls)
        }
        func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) { parent.onCancel() }
    }
}

@MainActor
final class ImportCoordinator: ObservableObject {
    @Published var pickerPresented = false
    @Published private(set) var pending = 0
    private let queue = DispatchQueue(label: "dev.leaf.reader.import", qos: .userInitiated)
    private let batchLimit = 16

    func presentPicker() {
        guard pending == 0 else { return }
        pickerPresented = true
    }

    func importFiles(_ urls: [URL]) {
        pickerPresented = false
        guard !urls.isEmpty else { return }
        guard pending + urls.count <= batchLimit else {
            ReaderRuntime.shared.reportError(message: "每批最多导入 16 本，请等待当前任务结束。")
            return
        }
        pending += urls.count
        for url in urls {
            // Obtain the scope while the document-picker callback is active.
            // asCopy URLs inside our container commonly return false, which is fine.
            let scoped = url.startAccessingSecurityScopedResource()
            queue.async { [weak self] in
                let result: Result<String, Error> = autoreleasepool {
                    defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                    return Result { try BookParser().parseFileToManifest(at: url) }
                }
                DispatchQueue.main.async {
                    switch result {
                    case .success(let json): ReaderRuntime.shared.importManifest(json: json)
                    case .failure(let error):
                        // Never send OS errors, archive paths, or book text to logs/UI.
                        let message = (error as? ImportFailure)?.errorDescription ?? "导入失败：文件结构异常或读取中断。"
                        ReaderRuntime.shared.reportError(message: message)
                    }
                    self?.pending -= 1
                }
            }
        }
    }
}
