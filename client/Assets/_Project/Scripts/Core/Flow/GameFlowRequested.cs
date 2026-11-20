namespace Game.Core.Flow
{
    /// <summary>
    /// Permintaan dari UI (tombol "Mulai", "Lanjut", dst.) ke <see cref="GameFlowController"/>.
    /// UI tidak memutasi state langsung; controller yang memutuskan apakah permintaan sah.
    /// </summary>
    public readonly struct GameFlowRequested
    {
        public readonly GameFlowCommand Command;

        public GameFlowRequested(GameFlowCommand command)
        {
            Command = command;
        }
    }
}
