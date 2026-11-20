using System;
using System.Threading;

namespace Game.Core.Events
{
    /// <summary>
    /// Token langganan yang dikembalikan <see cref="EventBus.Subscribe{T}"/> dan
    /// <see cref="EventBusMonoBehaviourExtensions.SubscribeUntilDestroyed{T}"/>.
    /// Struct sehingga tidak beralokasi; <c>Dispose</c> aman dipanggil berkali-kali
    /// dan hanya melepas langganan miliknya sendiri. Untuk langganan yang terikat
    /// masa hidup MonoBehaviour, <c>Dispose</c> juga melepas registrasi pada
    /// <c>destroyCancellationToken</c> sehingga pola subscribe/Dispose berulang
    /// (OnEnable/OnDisable) tidak menumpuk registrasi.
    /// </summary>
    public readonly struct EventSubscription<T> : IDisposable where T : struct
    {
        private readonly int _id;
        private readonly CancellationTokenRegistration _destroyRegistration;

        internal EventSubscription(int id)
            : this(id, default)
        {
        }

        internal EventSubscription(int id, CancellationTokenRegistration destroyRegistration)
        {
            _id = id;
            _destroyRegistration = destroyRegistration;
        }

        /// <summary>True bila token berasal dari Subscribe (bukan default); tidak berubah setelah Dispose.</summary>
        public bool IsValid => _id != 0;

        public void Dispose()
        {
            EventChannel<T>.UnsubscribeById(_id);
            _destroyRegistration.Dispose();
        }
    }
}
