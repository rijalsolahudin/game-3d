namespace Game.Tests.EditMode.Events
{
    public readonly struct TestEvent
    {
        public readonly int Value;

        public TestEvent(int value)
        {
            Value = value;
        }
    }
}
