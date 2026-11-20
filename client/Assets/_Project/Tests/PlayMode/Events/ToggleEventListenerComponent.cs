using Game.Core.Events;
using UnityEngine;

namespace Game.Tests.PlayMode.Events
{
    /// <summary>Subscriber dengan pola yang direkomendasikan: subscribe di OnEnable, Dispose di OnDisable.</summary>
    public sealed class ToggleEventListenerComponent : MonoBehaviour
    {
        private EventSubscription<PlayModeTestEvent> _subscription;

        public int ReceivedCount { get; private set; }

        private void OnEnable()
        {
            _subscription = this.SubscribeUntilDestroyed<PlayModeTestEvent>(OnTestEvent);
        }

        private void OnDisable()
        {
            _subscription.Dispose();
        }

        private void OnTestEvent(in PlayModeTestEvent evt)
        {
            ReceivedCount++;
        }
    }
}
