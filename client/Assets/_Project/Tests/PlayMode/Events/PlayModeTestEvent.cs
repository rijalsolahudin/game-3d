namespace Game.Tests.PlayMode.Events
{
    public readonly struct PlayModeTestEvent
    {
        public readonly int Value;

        public PlayModeTestEvent(int value)
        {
            Value = value;
        }
    }
}
