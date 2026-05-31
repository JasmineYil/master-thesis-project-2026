using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
public class MarkerContentController : MonoBehaviour
{
    [SerializeField] GameObject contentPrefab;

    ARTrackedImage trackedImage;
    GameObject content;
    bool wasLostAfterDestroy;

    void Start()
    {
        trackedImage = GetComponent<ARTrackedImage>();
        SpawnContent();
    }

    void Update()
    {
        if (content != null) return;

        if (trackedImage.trackingState != TrackingState.Tracking)
        {
            wasLostAfterDestroy = true;
            return;
        }

        if (wasLostAfterDestroy)
        {
            SpawnContent();
            wasLostAfterDestroy = false;
        }
    }

    void SpawnContent()
    {
        content = Instantiate(contentPrefab, transform.position, transform.rotation, transform);
    }
}