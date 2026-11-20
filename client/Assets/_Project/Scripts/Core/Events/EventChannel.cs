using System;
using UnityEngine;

namespace Game.Core.Events
{
    /// <summary>
    /// Penyimpanan subscriber untuk satu tipe event. Karena kelas ini generic statis,
    /// setiap <typeparamref name="T"/> punya daftar sendiri dan dispatch tidak butuh
    /// dictionary lookup. Hanya untuk main thread.
    /// </summary>
    /// <remarks>
    /// Publish tidak beralokasi: subscriber disimpan di array yang hanya tumbuh saat
    /// Subscribe. Unsubscribe saat publish berjalan hanya menandai slot kosong (null),
    /// lalu array dipadatkan setelah publish terluar selesai. Subscriber yang ditambah
    /// saat publish berjalan baru menerima event pada publish berikutnya.
    /// </remarks>
    internal static class EventChannel<T> where T : struct
    {
        private const int InitialCapacity = 4;

        private static GameEventHandler<T>?[] _handlers = new GameEventHandler<T>?[InitialCapacity];
        private static int[] _ids = new int[InitialCapacity];
        private static int _count;
        private static int _nextId;
        private static int _publishDepth;
        private static bool _needsCompaction;

        static EventChannel()
        {
            EventBus.RegisterChannelReset(Clear);
        }

        internal static int Capacity => _handlers.Length;

        internal static int SubscriberCount
        {
            get
            {
                var active = 0;
                for (var i = 0; i < _count; i++)
                {
                    if (_handlers[i] != null)
                    {
                        active++;
                    }
                }

                return active;
            }
        }

        internal static int Subscribe(GameEventHandler<T> handler)
        {
            if (handler == null)
            {
                throw new ArgumentNullException(nameof(handler));
            }

            if (_count == _handlers.Length)
            {
                var newCapacity = _handlers.Length * 2;
                Array.Resize(ref _handlers, newCapacity);
                Array.Resize(ref _ids, newCapacity);
            }

            // Id 0 dicadangkan untuk token kosong (default).
            _nextId = _nextId == int.MaxValue ? 1 : _nextId + 1;
            _handlers[_count] = handler;
            _ids[_count] = _nextId;
            _count++;
            return _nextId;
        }

        internal static bool Unsubscribe(GameEventHandler<T> handler)
        {
            for (var i = 0; i < _count; i++)
            {
                if (_handlers[i] == handler)
                {
                    RemoveAt(i);
                    return true;
                }
            }

            return false;
        }

        internal static bool UnsubscribeById(int id)
        {
            if (id == 0)
            {
                return false;
            }

            for (var i = 0; i < _count; i++)
            {
                if (_ids[i] == id && _handlers[i] != null)
                {
                    RemoveAt(i);
                    return true;
                }
            }

            return false;
        }

        internal static void Publish(in T evt)
        {
            // Snapshot jumlah: subscriber baru selama publish tidak ikut dipanggil.
            var count = _count;
            _publishDepth++;
            try
            {
                for (var i = 0; i < count; i++)
                {
                    var handler = _handlers[i];
                    if (handler == null)
                    {
                        continue;
                    }

                    if (IsDestroyedUnityTarget(handler))
                    {
                        RemoveAt(i);
                        Debug.LogWarning(
                            $"[EventBus] Subscriber {typeof(T).Name} milik objek yang sudah di-destroy dilepas otomatis. " +
                            "Gunakan token Dispose atau SubscribeUntilDestroyed.");
                        continue;
                    }

                    try
                    {
                        handler(in evt);
                    }
                    catch (Exception exception)
                    {
                        // Satu subscriber yang gagal tidak boleh menghentikan subscriber lain.
                        Debug.LogException(exception);
                    }
                }
            }
            finally
            {
                _publishDepth--;
                if (_publishDepth == 0 && _needsCompaction)
                {
                    Compact();
                }
            }
        }

        internal static void Clear()
        {
            Array.Clear(_handlers, 0, _handlers.Length);
            Array.Clear(_ids, 0, _ids.Length);
            if (_publishDepth > 0)
            {
                // Dipanggil dari dalam handler: biarkan publish yang berjalan selesai
                // membaca slot kosong, lalu padatkan setelahnya.
                _needsCompaction = true;
                return;
            }

            _count = 0;
            _needsCompaction = false;
        }

        private static bool IsDestroyedUnityTarget(GameEventHandler<T> handler)
        {
            // Operator == milik UnityEngine.Object mendeteksi objek native yang sudah di-destroy
            // walau referensi managed-nya masih ada. Tidak beralokasi.
            var target = handler.Target;
            return target is UnityEngine.Object unityObject && unityObject == null;
        }

        private static void RemoveAt(int index)
        {
            if (_publishDepth > 0)
            {
                _handlers[index] = null;
                _ids[index] = 0;
                _needsCompaction = true;
                return;
            }

            _count--;
            if (index < _count)
            {
                Array.Copy(_handlers, index + 1, _handlers, index, _count - index);
                Array.Copy(_ids, index + 1, _ids, index, _count - index);
            }

            _handlers[_count] = null;
            _ids[_count] = 0;
        }

        private static void Compact()
        {
            var write = 0;
            for (var read = 0; read < _count; read++)
            {
                if (_handlers[read] == null)
                {
                    continue;
                }

                _handlers[write] = _handlers[read];
                _ids[write] = _ids[read];
                write++;
            }

            for (var i = write; i < _count; i++)
            {
                _handlers[i] = null;
                _ids[i] = 0;
            }

            _count = write;
            _needsCompaction = false;
        }
    }
}
