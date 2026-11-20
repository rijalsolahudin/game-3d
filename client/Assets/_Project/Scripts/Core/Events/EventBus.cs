using System;
using System.Collections.Generic;
using UnityEngine;

namespace Game.Core.Events
{
    /// <summary>
    /// Event bus bertipe untuk komunikasi antar sistem tanpa saling mereferensikan
    /// (mis. gameplay → UI). Event adalah <c>struct</c>, sehingga Publish tidak boxing
    /// dan tidak beralokasi. Hanya untuk main thread.
    /// </summary>
    /// <example>
    /// <code>
    /// public readonly struct LocationDiscovered { public readonly int PoiId; ... }
    ///
    /// // Subscriber (simpan token, Dispose saat selesai):
    /// _subscription = EventBus.Subscribe&lt;LocationDiscovered&gt;(OnLocationDiscovered);
    /// private void OnLocationDiscovered(in LocationDiscovered evt) { ... }
    ///
    /// // Atau di MonoBehaviour, lepas otomatis saat objek di-destroy:
    /// this.SubscribeUntilDestroyed&lt;LocationDiscovered&gt;(OnLocationDiscovered);
    ///
    /// // Publisher:
    /// EventBus.Publish(new LocationDiscovered(poiId));
    /// </code>
    /// </example>
    public static class EventBus
    {
        private static readonly List<Action> ChannelResets = new();

        /// <summary>Mendaftarkan handler. Kembalikan token; panggil <c>Dispose</c> untuk berhenti.</summary>
        public static EventSubscription<T> Subscribe<T>(GameEventHandler<T> handler) where T : struct
        {
            return new EventSubscription<T>(EventChannel<T>.Subscribe(handler));
        }

        /// <summary>Melepas satu langganan <paramref name="handler"/>. True bila ditemukan.</summary>
        public static bool Unsubscribe<T>(GameEventHandler<T> handler) where T : struct
        {
            return handler != null && EventChannel<T>.Unsubscribe(handler);
        }

        /// <summary>Mengirim event ke semua subscriber tipe <typeparamref name="T"/>. Tanpa alokasi GC.</summary>
        public static void Publish<T>(in T evt) where T : struct
        {
            EventChannel<T>.Publish(in evt);
        }

        /// <summary>Jumlah subscriber aktif untuk tipe <typeparamref name="T"/> (diagnostik/test).</summary>
        public static int SubscriberCount<T>() where T : struct
        {
            return EventChannel<T>.SubscriberCount;
        }

        /// <summary>Melepas semua subscriber dari semua tipe event.</summary>
        public static void ClearAll()
        {
            for (var i = 0; i < ChannelResets.Count; i++)
            {
                ChannelResets[i]();
            }
        }

        internal static void RegisterChannelReset(Action reset)
        {
            ChannelResets.Add(reset);
        }

        // Saat "Enter Play Mode Options" mematikan domain reload, state statis bertahan
        // antar sesi Play. Reset di awal setiap sesi agar subscriber lama tidak bocor.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetOnPlayModeEnter()
        {
            ClearAll();
        }
    }
}
