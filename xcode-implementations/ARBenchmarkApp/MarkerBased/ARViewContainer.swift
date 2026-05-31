import SwiftUI
import RealityKit
import ARKit

struct ARViewContainer: UIViewRepresentable {
    func makeUIView(context: Context) -> ARView {
        let arView = ARView(frame: .zero)
        
        if let referenceImages = ARReferenceImage.referenceImages(
            inGroupNamed: "ARReferenceImages",
            bundle: nil
        ) {
            let config = ARImageTrackingConfiguration()
            config.trackingImages = referenceImages
            config.maximumNumberOfTrackedImages = 1
            arView.session.run(config)
        } else {
            print("AR Resource Group 'ARReferenceImages' nicht gefunden")
        }
        
        arView.session.delegate = context.coordinator
        context.coordinator.arView = arView
        
        let longPress = UILongPressGestureRecognizer(
            target: context.coordinator,
            action: #selector(Coordinator.handleLongPress(_:))
        )
        longPress.minimumPressDuration = 1.0
        arView.addGestureRecognizer(longPress)
        
        return arView
    }
    
    func updateUIView(_ uiView: ARView, context: Context) {}
    
    func makeCoordinator() -> Coordinator { Coordinator() }
    
    class Coordinator: NSObject, ARSessionDelegate {
        var arView: ARView?
        private var anchors: [UUID: AnchorEntity] = [:]
        private var cooldownUntil: [UUID: Date] = [:]
        private let cooldownDuration: TimeInterval = 2.0
        
        func session(_ session: ARSession, didAdd anchors: [ARAnchor]) {
            for anchor in anchors {
                guard let imageAnchor = anchor as? ARImageAnchor else { continue }
                spawnCube(for: imageAnchor)
            }
        }
        
        func session(_ session: ARSession, didUpdate anchors: [ARAnchor]) {
            for anchor in anchors {
                guard let imageAnchor = anchor as? ARImageAnchor else { continue }
                
                if let anchorEntity = self.anchors[imageAnchor.identifier] {
                    anchorEntity.isEnabled = imageAnchor.isTracked
                } else if imageAnchor.isTracked, canRespawn(for: imageAnchor.identifier) {
                    spawnCube(for: imageAnchor)
                }
            }
        }
        
        private func canRespawn(for id: UUID) -> Bool {
            guard let until = cooldownUntil[id] else { return true }
            return Date() >= until
        }
        
        private func spawnCube(for imageAnchor: ARImageAnchor) {
            guard let arView else { return }
            
            let cube = CubeEntity.create()
            let anchorEntity = AnchorEntity(anchor: imageAnchor)
            anchorEntity.addChild(cube)
            arView.scene.addAnchor(anchorEntity)
            arView.installGestures([.rotation, .scale], for: cube)
            
            anchors[imageAnchor.identifier] = anchorEntity
            cooldownUntil.removeValue(forKey: imageAnchor.identifier)
        }
        
        @objc func handleLongPress(_ recognizer: UILongPressGestureRecognizer) {
            guard recognizer.state == .began, let arView else { return }
            
            let location = recognizer.location(in: arView)
            guard let hit = arView.hitTest(location).first(where: { $0.entity.name == "ARCube" }),
                  let anchorEntity = hit.entity.anchor as? AnchorEntity,
                  let id = anchorEntity.anchorIdentifier
            else { return }
            
            arView.scene.removeAnchor(anchorEntity)
            anchors.removeValue(forKey: id)
            cooldownUntil[id] = Date().addingTimeInterval(cooldownDuration)
        }
    }
}
