using UnityEngine;

namespace Game.Tests.EditMode.Events
{
    /// <summary>Subscriber berbasis UnityEngine.Object untuk menguji pelepasan otomatis saat di-destroy.</summary>
    public sealed class UnityObjectSubscriber : ScriptableObject
    {
        public int ReceivedCount { get; private set; }

        public void OnTestEvent(in TestEvent evt)
        {
            ReceivedCount++;
        }
    }
}
