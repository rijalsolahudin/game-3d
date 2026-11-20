namespace Game.Core.Events
{
    /// <summary>
    /// Handler event bertipe. Event dikirim lewat referensi read-only (<c>in</c>)
    /// sehingga struct besar tidak disalin saat dispatch.
    /// </summary>
    /// <typeparam name="T">Tipe event (struct).</typeparam>
    public delegate void GameEventHandler<T>(in T evt) where T : struct;
}
