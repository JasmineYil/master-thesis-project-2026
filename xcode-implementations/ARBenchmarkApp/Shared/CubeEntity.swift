import RealityKit
import UIKit

enum CubeEntity {
    static func create(size: Float = 0.1, color: UIColor = .systemBlue) -> ModelEntity {
        let mesh = MeshResource.generateBox(size: size)
        let material = SimpleMaterial(color: color, isMetallic: false)
        let cube = ModelEntity(mesh: mesh, materials: [material])
        
        cube.name = "ARCube"
        cube.collision = CollisionComponent(
            shapes: [.generateBox(size: [size, size, size])]
        )
        return cube
    }
}
