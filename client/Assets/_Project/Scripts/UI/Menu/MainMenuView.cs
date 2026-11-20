using Game.Core.Events;
using Game.Core.Flow;
using UnityEngine;
using UnityEngine.UIElements;

namespace Game.UI.Menu
{
    /// <summary>
    /// Menu utama (UI Toolkit, <c>UI/Menu/main-menu.uxml</c>). Tombol hanya mengirim
    /// <see cref="GameFlowRequested"/>; tampilan "Memuat..." mengikuti <see cref="GameStateChanged"/>.
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public sealed class MainMenuView : MonoBehaviour
    {
        private const string StartButtonName = "start-button";
        private const string QuitButtonName = "quit-button";
        private const string LoadingLabelName = "loading-label";

        private UIDocument _document = null!;
        private Button? _startButton;
        private Button? _quitButton;
        private VisualElement? _loadingLabel;
        private EventSubscription<GameStateChanged> _stateSubscription;

        private void Awake()
        {
            _document = GetComponent<UIDocument>();
        }

        private void OnEnable()
        {
            var root = _document.rootVisualElement;
            _startButton = root.Q<Button>(StartButtonName);
            _quitButton = root.Q<Button>(QuitButtonName);
            _loadingLabel = root.Q<VisualElement>(LoadingLabelName);

            if (_startButton != null)
            {
                _startButton.clicked += OnStartClicked;
            }

            if (_quitButton != null)
            {
                _quitButton.clicked += OnQuitClicked;
            }

            SetLoading(false);
            _stateSubscription = this.SubscribeUntilDestroyed<GameStateChanged>(OnGameStateChanged);
        }

        private void OnDisable()
        {
            _stateSubscription.Dispose();
            if (_startButton != null)
            {
                _startButton.clicked -= OnStartClicked;
            }

            if (_quitButton != null)
            {
                _quitButton.clicked -= OnQuitClicked;
            }
        }

        private static void OnStartClicked()
        {
            EventBus.Publish(new GameFlowRequested(GameFlowCommand.StartGame));
        }

        private static void OnQuitClicked()
        {
            EventBus.Publish(new GameFlowRequested(GameFlowCommand.Quit));
        }

        private void OnGameStateChanged(in GameStateChanged evt)
        {
            SetLoading(evt.Current == GameState.Loading);
        }

        private void SetLoading(bool isLoading)
        {
            _startButton?.SetEnabled(!isLoading);
            _quitButton?.SetEnabled(!isLoading);
            if (_loadingLabel != null)
            {
                _loadingLabel.style.display = isLoading ? DisplayStyle.Flex : DisplayStyle.None;
            }
        }
    }
}
