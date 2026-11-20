namespace Game.Tests.EditMode.Events
{
    public readonly struct OtherTestEvent
    {
        public readonly float Amount;

        public OtherTestEvent(float amount)
        {
            Amount = amount;
        }
    }
}
