namespace Game.Core.Flow
{
    /// <summary>
    /// Dipublish lewat <see cref="Game.Core.Events.EventBus"/> setiap kali <see cref="GameStateMachine"/>
    /// berpindah state. Controller gameplay (mis. karakter GAME-23) mendengarkan event ini dan
    /// hanya memproses input gerak bila <see cref="AllowsGameplayInput"/> true.
    /// </summary>
    public readonly struct GameStateChanged
    {
        public readonly GameState Previous;
        public readonly GameState Current;

        public GameStateChanged(GameState previous, GameState current)
        {
            Previous = previous;
            Current = current;
        }

        /// <summary>True bila input gameplay (gerak, lompat, kendaraan) boleh diproses.</summary>
        public bool AllowsGameplayInput => GameStateMachine.AllowsGameplayInput(Current);
    }
}
