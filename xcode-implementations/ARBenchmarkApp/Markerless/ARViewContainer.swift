import SwiftUI
import RealityKit
import ARKit

struct ARViewContainer: UIViewRepresentable {
    func makeUIView(context: Context) -> ARView {
        let arView = ARView(frame: .zero)
        
        let config = ARWorldTrackingConfiguration()
        config.planeDetection = [.horizontal, .vertical]
        arView.session.run(config)
        
        arView.session.delegate = context.coordinator
        context.coordinator.arView = arView
        
        let tap = UITapGestureRecognizer(
            target: context.coordinator,
            action: #selector(Coordinator.handleTap(_:))
        )
        arView.addGestureRecognizer(tap)
        
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
        private var planeAnchors: [UUID: AnchorEntity] = [:]
        private var cubeAnchor: AnchorEntity?
        
        func session(_ session: ARSession, didAdd anchors: [ARAnchor]) {
            guard let arView else { return }
            
            for anchor in anchors {
                guard let planeAnchor = anchor as? ARPlaneAnchor else { continue }
                
                let planeEntity = PlaneEntity.create(for: planeAnchor)
                let anchorEntity = AnchorEntity(anchor: planeAnchor)
                anchorEntity.addChild(planeEntity)
                arView.scene.addAnchor(anchorEntity)
                
                planeAnchors[planeAnchor.identifier] = anchorEntity
            }
        }
        
        func session(_ session: ARSession, didUpdate anchors: [ARAnchor]) {
            for anchor in anchors {
                guard let planeAnchor = anchor as? ARPlaneAnchor,
                      let anchorEntity = planeAnchors[planeAnchor.identifier],
                      let planeEntity = anchorEntity.children.first as? ModelEntity
                else { continue }
                
                PlaneEntity.update(planeEntity, for: planeAnchor)
            }
        }
        
        func session(_ session: ARSession, didRemove anchors: [ARAnchor]) {
            guard let arView else { return }
            
            for anchor in anchors {
                guard let planeAnchor = anchor as? ARPlaneAnchor,
                      let anchorEntity = planeAnchors[planeAnchor.identifier]
                else { continue }
                
                arView.scene.removeAnchor(anchorEntity)
                planeAnchors.removeValue(forKey: planeAnchor.identifier)
            }
        }
        
        @objc func handleTap(_ recognizer: UITapGestureRecognizer) {
            guard let arView, cubeAnchor == nil else { return }
            
            let location = recognizer.location(in: arView)
            let results = arView.raycast(
                from: location,
                allowing: .estimatedPlane,
                alignment: .any
            )
            guard let firstResult = results.first else { return }
            
            let cube = CubeEntity.create()
            let anchor = AnchorEntity(world: firstResult.worldTransform)
            anchor.addChild(cube)
            arView.scene.addAnchor(anchor)
            arView.installGestures([.translation, .rotation, .scale], for: cube)
            
            cubeAnchor = anchor
        }
        
        @objc func handleLongPress(_ recognizer: UILongPressGestureRecognizer) {
            guard recognizer.state == .began, let arView else { return }
            
            let location = recognizer.location(in: arView)
            guard let hit = arView.hitTest(location).first(where: { $0.entity.name == "ARCube" }),
                  let anchor = hit.entity.anchor as? AnchorEntity
            else { return }
            
            arView.scene.removeAnchor(anchor)
            cubeAnchor = nil
        }
    }
}
