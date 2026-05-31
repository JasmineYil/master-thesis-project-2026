using UnityEngine;
using Touch = UnityEngine.InputSystem.EnhancedTouch.Touch;

[RequireComponent(typeof(Collider))]
public class LongPressToDelete : MonoBehaviour
{
    [SerializeField] float holdDuration = 1.0f;
    [SerializeField] float maxScreenMovement = 30f;

    Camera cam;
    Collider myCollider;
    float holdTimer;
    bool tracking;
    Vector2 startScreenPos;

    void Awake()
    {
        cam = Camera.main;
        myCollider = GetComponent<Collider>();
    }
    
    void Update()
    {
        if (Touch.activeTouches.Count != 1)
        {
            tracking = false;
            return;
        }
        var touch = Touch.activeTouches[0];

        if (touch.phase == UnityEngine.InputSystem.TouchPhase.Began)
        {
            Ray ray = cam.ScreenPointToRay(touch.screenPosition);
            if (Physics.Raycast(ray, out RaycastHit hit) && hit.collider == myCollider)
            {
                tracking = true;
                holdTimer = 0f;
                startScreenPos = touch.screenPosition;
            }
            return;
        }
        if (!tracking) return;

        if (touch.phase == UnityEngine.InputSystem.TouchPhase.Ended ||
            touch.phase == UnityEngine.InputSystem.TouchPhase.Canceled)
        {
            tracking = false;
            return;
        }

        if (Vector2.Distance(touch.screenPosition, startScreenPos) > maxScreenMovement)
        {
            tracking = false;
            return;
        }

        holdTimer += Time.deltaTime;
        if (holdTimer >= holdDuration)
        {
            Destroy(gameObject);
        }
    }
}