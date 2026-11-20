using System;
using UnityEngine;

namespace Game.Core.Events
{
    /// <summary>
    /// Helper langganan untuk MonoBehaviour: langganan dilepas otomatis saat komponen
    /// di-destroy (lewat <c>destroyCancellationToken</c>), jadi lupa unsubscribe tidak
    /// membuat leak atau handler dipanggil pada objek mati.
    /// </summary>
    public static class EventBusMonoBehaviourExtensions
    {
        /// <summary>
        /// Subscribe dan ikat masa hidup langganan ke <paramref name="owner"/>.
        /// Alokasi hanya terjadi sekali saat subscribe, bukan saat publish.
        /// Token yang dikembalikan boleh di-Dispose lebih awal (mis. di <c>OnDisable</c>);
        /// Dispose melepas langganan sekaligus registrasinya pada token destroy.
        /// </summary>
        /// <exception cref="ArgumentNullException"><paramref name="owner"/> atau <paramref name="handler"/> null.</exception>
        /// <exception cref="ObjectDisposedException"><paramref name="owner"/> sudah di-destroy.</exception>
        public static EventSubscription<T> SubscribeUntilDestroyed<T>(this MonoBehaviour owner, GameEventHandler<T> handler)
            where T : struct
        {
            if (ReferenceEquals(owner, null))
            {
                throw new ArgumentNullException(nameof(owner));
            }

            // Operator == Unity: referensi managed masih ada tetapi objek native sudah di-destroy.
            if (owner == null)
            {
                // Referensi managed tidak null (dicek di atas); analisis nullable tidak tahu operator Unity.
                throw new ObjectDisposedException(owner!.GetType().Name,
                    "Tidak bisa subscribe atas nama MonoBehaviour yang sudah di-destroy.");
            }

            if (handler == null)
            {
                throw new ArgumentNullException(nameof(handler));
            }

            var destroyToken = owner.destroyCancellationToken;
            var id = EventChannel<T>.Subscribe(handler);

            // Callback tanpa capture (di-cache compiler); id di-box sekali saat subscribe.
            var registration = destroyToken.Register(state => EventChannel<T>.UnsubscribeById((int)state!), id);
            return new EventSubscription<T>(id, registration);
        }
    }
}
