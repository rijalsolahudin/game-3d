using Game.Core.Events;
using Game.Core.Flow;
using UnityEngine;

namespace Game.Player
{
    /// <summary>
    /// Mengunci dan menyembunyikan kursor selama Playing (mouse memutar kamera), dan melepasnya
    /// di state lain (Paused, Menu, Loading) agar menu bisa diklik. Kursor juga dilepas saat
    /// objek dihancurkan (keluar dari scene World).
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class PlayerCursorLock : MonoBehaviour
    {
        [Tooltip("Kunci kursor sejak awal walau GameFlowController tidak ada (scene World dibuka langsung di editor).")]
        [SerializeField] private bool _lockWithoutGameFlow = true;

        private bool _receivedState;

        private void Awake()
        {
            this.SubscribeUntilDestroyed<GameStateChanged>(OnGameStateChanged);
        }

        private void Start()
        {
            // Alur normal: World dimuat saat Loading, lalu GameStateChanged(Playing) mengunci kursor.
            if (!_receivedState && _lockWithoutGameFlow && FindAnyObjectByType<GameFlowController>() == null)
            {
                Apply(true);
            }
        }

        private void OnDestroy()
        {
            Apply(false);
        }

        private void OnGameStateChanged(in GameStateChanged evt)
        {
            _receivedState = true;
            Apply(evt.Current == GameState.Playing);
        }

        private static void Apply(bool locked)
        {
            Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !locked;
        }
    }
}
