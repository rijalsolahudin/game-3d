using UnityEngine;

namespace Game.Core.Config
{
    /// <summary>
    /// Basis semua config tuning (kecepatan, radius, interval, batas). Nilai disetel desainer
    /// lewat aset di <c>Assets/_Project/Settings/</c>, bukan konstanta di kode.
    /// </summary>
    /// <remarks>
    /// Cara pakai:
    /// <list type="number">
    /// <item>Turunkan kelas <c>sealed</c> di modul pemiliknya, beri <c>[CreateAssetMenu]</c>.</item>
    /// <item>Field <c>[SerializeField] private</c> + <c>[Tooltip]</c> + <c>[Min]</c>/<c>[Range]</c>; expose lewat property read-only.</item>
    /// <item>Override <see cref="Validate"/> untuk aturan antar-field (mis. lari ≥ jalan).</item>
    /// <item>Sistem menerima config lewat <c>[SerializeField]</c> atau konstruktor dan membacanya saat runtime.</item>
    /// </list>
    /// </remarks>
    public abstract class GameConfig : ScriptableObject
    {
        /// <summary>
        /// Memperbaiki nilai yang tidak konsisten. Dipanggil otomatis tiap nilai diubah di Inspector.
        /// </summary>
        protected abstract void Validate();

        internal void RunValidation()
        {
            Validate();
        }

        protected virtual void OnValidate()
        {
            Validate();
        }
    }
}
