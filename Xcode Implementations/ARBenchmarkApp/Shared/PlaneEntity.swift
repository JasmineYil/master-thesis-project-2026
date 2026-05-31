import RealityKit
import ARKit
import UIKit

enum PlaneEntity {
    static func create(for anchor: ARPlaneAnchor) -> ModelEntity {
        let mesh = makeMesh(for: anchor)
        var material = SimpleMaterial()
        material.color = .init(
            tint: UIColor.systemCyan.withAlphaComponent(0.3),
            texture: nil
        )
        let entity = ModelEntity(mesh: mesh, materials: [material])
        entity.name = "DetectedPlane"
        return entity
    }
    
    static func update(_ entity: ModelEntity, for anchor: ARPlaneAnchor) {
        entity.model?.mesh = makeMesh(for: anchor)
    }
    
    private static func makeMesh(for anchor: ARPlaneAnchor) -> MeshResource {
        MeshResource.generateBox(
            width: anchor.planeExtent.width,
            height: 0.001,
            depth: anchor.planeExtent.height
        )
    }
}
