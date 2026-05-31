using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem.EnhancedTouch;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
using Touch = UnityEngine.InputSystem.EnhancedTouch.Touch;

public class PlaneTapSpawner : MonoBehaviour
{
    [SerializeField] ARRaycastManager raycastManager;
    [SerializeField] GameObject prefab;
    [SerializeField] bool singleInstance = true;

    GameObject current;
    static readonly List<ARRaycastHit> hits = new();

    void OnEnable()  => EnhancedTouchSupport.Enable();
    void OnDisable() => EnhancedTouchSupport.Disable();

    void Update()
    {
        if (Touch.activeTouches.Count == 0) return;

        var touch = Touch.activeTouches[0];
        if (touch.phase != UnityEngine.InputSystem.TouchPhase.Began) return;
        
        if (singleInstance && current != null)
        {
            return;
        }

        if (!raycastManager.Raycast(touch.screenPosition, hits,
                TrackableType.PlaneWithinPolygon))
        {
            return;
        }
        var pose = hits[0].pose;
        current = Instantiate(prefab, pose.position, pose.rotation);
    }
}