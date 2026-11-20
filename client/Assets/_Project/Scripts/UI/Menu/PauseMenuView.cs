using Game.Core.Events;
using Game.Core.Flow;
using UnityEngine;
using UnityEngine.UIElements;

namespace Game.UI.Menu
{
    /// <summary>
    /// Overlay pause (UI Toolkit, <c>UI/Menu/pause-menu.uxml</c>) di scene World. Tampil hanya saat
    /// <see cref="GameState.Paused"/>; tombol mengirim <see cref="GameFlowRequested"/>.
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public sealed class PauseMenuView : MonoBehaviour
    {
        private const string OverlayName = "pause-overlay";
        private const string ResumeButtonName = "resume-button";
        private const string MenuButtonName = "menu-button";

        private UIDocument _document = null!;
        private VisualElement? _overlay;
        private Button? _resumeButton;
        private Button? _menuButton;
        private EventSubscription<GameStateChanged> _stateSubscription;

        private void Awake()
        {
            _document = GetComponent<UIDocument>();
        }

        private void OnEnable()
        {
            var root = _document.rootVisualElement;
            _overlay = root.Q<VisualElement>(OverlayName);
            _resumeButton = root.Q<Button>(ResumeButtonName);
            _menuButton = root.Q<Button>(MenuButtonName);

            if (_resumeButton != null)
            {
                _resumeButton.clicked += OnResumeClicked;
            }

            if (_menuButton != null)
            {
                _menuButton.clicked += OnMenuClicked;
            }

            SetVisible(false);
            _stateSubscription = this.SubscribeUntilDestroyed<GameStateChanged>(OnGameStateChanged);
        }

        private void OnDisable()
        {
            _stateSubscription.Dispose();
            if (_resumeButton != null)
            {
                _resumeButton.clicked -= OnResumeClicked;
            }

            if (_menuButton != null)
            {
                _menuButton.clicked -= OnMenuClicked;
            }
        }

        private static void OnResumeClicked()
        {
            EventBus.Publish(new GameFlowRequested(GameFlowCommand.Resume));
        }

        private static void OnMenuClicked()
        {
            EventBus.Publish(new GameFlowRequested(GameFlowCommand.ReturnToMenu));
        }

        private void OnGameStateChanged(in GameStateChanged evt)
        {
            SetVisible(evt.Current == GameState.Paused);
        }

        private void SetVisible(bool isVisible)
        {
            if (_overlay != null)
            {
                _overlay.style.display = isVisible ? DisplayStyle.Flex : DisplayStyle.None;
            }
        }
    }
}
