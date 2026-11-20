using Game.Core.Config;
using UnityEngine;

namespace Game.Core.Flow
{
    /// <summary>
    /// Tuning alur game dan perpindahan scene. Aset default:
    /// <c>Assets/_Project/Settings/game-flow-config.asset</c>.
    /// </summary>
    [CreateAssetMenu(menuName = "Game/Config/Game Flow", fileName = "game-flow-config")]
    public sealed class GameFlowConfig : GameConfig
    {
        // Nama scene default; harus sama dengan Build Settings (dijaga test EditMode).
        private const string DefaultMenuSceneName = "Menu";
        private const string DefaultWorldSceneName = "World";

        [Header("Scene")]
        [Tooltip("Nama scene menu utama di Build Settings.")]
        [SerializeField] private string _menuSceneName = DefaultMenuSceneName;

        [Tooltip("Nama scene dunia di Build Settings.")]
        [SerializeField] private string _worldSceneName = DefaultWorldSceneName;

        [Header("Loading")]
        [Tooltip("Durasi minimum state Loading (detik, waktu nyata) agar indikator memuat tidak berkedip.")]
        [SerializeField, Min(0f)] private float _minimumLoadingSeconds = 0.5f;

        [Tooltip("Prioritas thread pemuatan latar. Low membatasi kerja integrasi aset per frame " +
                 "sehingga frame tidak membeku saat scene dimuat.")]
        [SerializeField] private ThreadPriority _backgroundLoadingPriority = ThreadPriority.Low;

        public string MenuSceneName => _menuSceneName;
        public string WorldSceneName => _worldSceneName;
        public float MinimumLoadingSeconds => _minimumLoadingSeconds;
        public ThreadPriority BackgroundLoadingPriority => _backgroundLoadingPriority;

        protected override void Validate()
        {
            if (string.IsNullOrWhiteSpace(_menuSceneName))
            {
                _menuSceneName = DefaultMenuSceneName;
            }

            if (string.IsNullOrWhiteSpace(_worldSceneName))
            {
                _worldSceneName = DefaultWorldSceneName;
            }

            _minimumLoadingSeconds = Mathf.Max(0f, _minimumLoadingSeconds);
        }
    }
}
