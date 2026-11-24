import SwiftUI
import UIKit
import Shared

@main
@MainActor
struct LeafReaderApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var importer = ImportCoordinator()

    var body: some Scene {
        WindowGroup {
            ReaderController(onImportRequested: { importer.presentPicker() })
                .ignoresSafeArea()
                .sheet(isPresented: $importer.pickerPresented) {
                    VStack(spacing: 0) {
                        Text("导入 TXT / EPUB · 仅正文\n图像、CSS 和固定版式暂不支持；不运行脚本。")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                            .padding()
                        DocumentPicker(onSelection: importer.importFiles, onCancel: { importer.pickerPresented = false })
                    }
                }
                .overlay(alignment: .bottom) {
                    if importer.pending > 0 {
                        HStack {
                            ProgressView()
                            Text("正在导入，剩余 \(importer.pending) 本")
                        }
                        .font(.footnote)
                        .padding(12)
                        .background(.regularMaterial, in: Capsule())
                        .padding(.bottom, 24)
                        .accessibilityElement(children: .combine)
                    }
                }
                .onOpenURL { importer.importFiles([$0]) }
        }
        .onChange(of: scenePhase) { phase in
            if phase != .active { ReaderRuntime.shared.flush() }
        }
    }
}

private struct ReaderController: UIViewControllerRepresentable {
    let onImportRequested: () -> Void

    func makeUIViewController(context: Context) -> UIViewController {
        MainViewControllerKt.MainViewController(onImportRequested: onImportRequested)
    }
    func updateUIViewController(_ controller: UIViewController, context: Context) {}
}
