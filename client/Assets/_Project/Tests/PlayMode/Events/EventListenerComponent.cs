using Game.Core.Events;
using UnityEngine;

namespace Game.Tests.PlayMode.Events
{
    /// <summary>Subscriber MonoBehaviour yang memakai <c>SubscribeUntilDestroyed</c> dan tidak pernah unsubscribe manual.</summary>
    public sealed class EventListenerComponent : MonoBehaviour
    {
        public int ReceivedCount { get; private set; }

        private void Awake()
        {
            this.SubscribeUntilDestroyed<PlayModeTestEvent>(OnTestEvent);
        }

        private void OnTestEvent(in PlayModeTestEvent evt)
        {
            ReceivedCount++;
        }
    }
}
