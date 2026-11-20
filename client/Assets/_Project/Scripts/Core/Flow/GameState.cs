namespace Game.Core.Flow
{
    /// <summary>
    /// Tahap game secara keseluruhan (ARC §2.3). Alur normal:
    /// Boot → Menu → Loading → Playing ⇄ Paused. Transisi sah dijaga <see cref="GameStateMachine"/>.
    /// </summary>
    public enum GameState
    {
        /// <summary>Baru dinyalakan: inisialisasi service di scene Boot.</summary>
        Boot = 0,

        /// <summary>Di menu utama.</summary>
        Menu = 1,

        /// <summary>Sedang memuat scene (dunia, atau menu saat keluar dari permainan).</summary>
        Loading = 2,

        /// <summary>Bermain di dunia; satu-satunya state yang menerima input gameplay.</summary>
        Playing = 3,

        /// <summary>Permainan dijeda; waktu berhenti dan input gameplay diabaikan.</summary>
        Paused = 4,
    }
}
