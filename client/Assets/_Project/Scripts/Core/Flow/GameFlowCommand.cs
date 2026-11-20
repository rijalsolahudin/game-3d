namespace Game.Core.Flow
{
    /// <summary>Permintaan perpindahan alur game yang dikirim UI lewat <see cref="GameFlowRequested"/>.</summary>
    public enum GameFlowCommand
    {
        /// <summary>Menu → Loading → Playing di scene dunia.</summary>
        StartGame = 0,

        /// <summary>Playing → Paused.</summary>
        Pause = 1,

        /// <summary>Paused → Playing.</summary>
        Resume = 2,

        /// <summary>Paused → Loading → Menu.</summary>
        ReturnToMenu = 3,

        /// <summary>Keluar dari aplikasi (hanya dari menu).</summary>
        Quit = 4,
    }
}
