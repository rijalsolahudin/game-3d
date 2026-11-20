using Game.Core.Events;
using UnityEngine;

namespace Game.Core.Flow
{
    /// <summary>
    /// State machine game yang murni (tanpa MonoBehaviour, tanpa scene) sehingga bisa diuji EditMode.
    /// Hanya menjaga transisi yang sah dan mengumumkannya lewat <see cref="GameStateChanged"/>;
    /// efek samping (memuat scene, menghentikan waktu, menonaktifkan input) dikerjakan driver
    /// <see cref="GameFlowController"/>.
    /// </summary>
    /// <remarks>
    /// Transisi sah:
    /// <list type="bullet">
    /// <item>Boot → Menu (service siap, scene menu termuat)</item>
    /// <item>Menu → Loading (pemain menekan "Mulai")</item>
    /// <item>Loading → Playing (scene dunia selesai dimuat)</item>
    /// <item>Loading → Menu (scene menu selesai dimuat, atau pemuatan dunia gagal)</item>
    /// <item>Playing → Paused, Paused → Playing</item>
    /// <item>Paused → Loading (pemain memilih "Ke Menu")</item>
    /// </list>
    /// Transisi lain, termasuk ke state yang sama, ditolak dan dicatat sebagai warning.
    /// </remarks>
    public sealed class GameStateMachine
    {
        public GameStateMachine(GameState initial = GameState.Boot)
        {
            Current = initial;
        }

        public GameState Current { get; private set; }

        /// <summary>True bila perpindahan <paramref name="from"/> → <paramref name="to"/> diizinkan.</summary>
        public static bool IsValidTransition(GameState from, GameState to)
        {
            switch (from)
            {
                case GameState.Boot:
                    return to == GameState.Menu;
                case GameState.Menu:
                    return to == GameState.Loading;
                case GameState.Loading:
                    return to == GameState.Playing || to == GameState.Menu;
                case GameState.Playing:
                    return to == GameState.Paused;
                case GameState.Paused:
                    return to == GameState.Playing || to == GameState.Loading;
                default:
                    return false;
            }
        }

        /// <summary>True bila <paramref name="state"/> boleh memproses input gameplay.</summary>
        public static bool AllowsGameplayInput(GameState state)
        {
            return state == GameState.Playing;
        }

        /// <summary>
        /// Berpindah ke <paramref name="next"/> bila sah, lalu publish <see cref="GameStateChanged"/>.
        /// Transisi tidak sah ditolak (state tidak berubah, tidak ada event) dan dicatat sebagai warning.
        /// </summary>
        /// <returns>True bila transisi dilakukan.</returns>
        public bool TryTransitionTo(GameState next)
        {
            var previous = Current;
            if (!IsValidTransition(previous, next))
            {
                // Jalur ini bukan per frame; alokasi string hanya terjadi saat ada bug alur.
                Debug.LogWarning($"[GameState] Transisi tidak valid ditolak: {previous} → {next}.");
                return false;
            }

            Current = next;
            EventBus.Publish(new GameStateChanged(previous, next));
            return true;
        }
    }
}
