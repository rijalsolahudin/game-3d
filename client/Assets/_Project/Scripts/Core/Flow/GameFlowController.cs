using System;
using Game.Core.Events;
using UnityEngine;
using UnityEngine.InputSystem;

namespace Game.Core.Flow
{
    /// <summary>
    /// Driver tipis <see cref="GameStateMachine"/> di scene Boot. Hidup sepanjang sesi
    /// (<c>DontDestroyOnLoad</c>) dan mengerjakan efek samping tiap state:
    /// memuat scene secara async, menghentikan waktu saat Paused, serta mengaktifkan action map
    /// gameplay hanya saat Playing.
    /// </summary>
    /// <remarks>
    /// UI tidak memanggil class ini; UI mengirim <see cref="GameFlowRequested"/> lewat event bus.
    /// Perubahan state diumumkan lewat <see cref="GameStateChanged"/>.
    /// </remarks>
    [DisallowMultipleComponent]
    public sealed class GameFlowController : MonoBehaviour
    {
        // Identitas action di input-actions.inputactions (bukan tuning).
        private const string GameplayActionMapName = "Player";
        private const string PauseActionName = "System/Pause";

        // Skala waktu per state (bukan tuning): Paused menghentikan simulasi, selain itu normal.
        private const float PausedTimeScale = 0f;
        private const float NormalTimeScale = 1f;

        private static GameFlowController? _instance;

        [SerializeField] private GameFlowConfig _config = null!;

        private readonly GameStateMachine _stateMachine = new();
        private InputActionMap? _gameplayActionMap;
        private InputAction? _pauseAction;
        private bool _isPrimary;

        /// <summary>State game saat ini. Untuk mendengarkan perubahan, pakai <see cref="GameStateChanged"/>.</summary>
        public GameState CurrentState => _stateMachine.Current;

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                // Scene Boot dimuat ulang: pertahankan controller yang sudah berjalan.
                Destroy(gameObject);
                return;
            }

            if (_config == null)
            {
                Debug.LogError("[GameFlow] GameFlowConfig belum di-assign di scene Boot.", this);
                enabled = false;
                return;
            }

            _instance = this;
            _isPrimary = true;
            DontDestroyOnLoad(gameObject);
            Application.backgroundLoadingPriority = _config.BackgroundLoadingPriority;

            ResolveInputActions();
            this.SubscribeUntilDestroyed<GameStateChanged>(OnGameStateChanged);
            this.SubscribeUntilDestroyed<GameFlowRequested>(OnGameFlowRequested);
            ApplyStateEffects(_stateMachine.Current);
        }

        private void OnEnable()
        {
            if (_pauseAction != null)
            {
                _pauseAction.performed += OnPausePerformed;
            }
        }

        private void OnDisable()
        {
            if (_pauseAction != null)
            {
                _pauseAction.performed -= OnPausePerformed;
            }
        }

        private void Start()
        {
            if (_isPrimary)
            {
                _ = LoadSceneThenEnterAsync(_config.MenuSceneName, GameState.Menu);
            }
        }

        private void OnDestroy()
        {
            if (!_isPrimary)
            {
                return;
            }

            _instance = null;
            Time.timeScale = NormalTimeScale;
            _gameplayActionMap?.Enable();
        }

        private void ResolveInputActions()
        {
            var actions = InputSystem.actions;
            if (actions == null)
            {
                Debug.LogWarning("[GameFlow] Project-wide input actions tidak ditemukan; pause dan gating input nonaktif.", this);
                return;
            }

            _gameplayActionMap = actions.FindActionMap(GameplayActionMapName);
            _pauseAction = actions.FindAction(PauseActionName);
            if (_gameplayActionMap == null || _pauseAction == null)
            {
                Debug.LogWarning($"[GameFlow] Action map '{GameplayActionMapName}' atau action '{PauseActionName}' tidak ada.", this);
            }

            _pauseAction?.Enable();
        }

        private void OnPausePerformed(InputAction.CallbackContext context)
        {
            // Tombol pause di luar permainan (menu, loading) diabaikan tanpa warning.
            switch (_stateMachine.Current)
            {
                case GameState.Playing:
                    _stateMachine.TryTransitionTo(GameState.Paused);
                    break;
                case GameState.Paused:
                    _stateMachine.TryTransitionTo(GameState.Playing);
                    break;
            }
        }

        private void OnGameFlowRequested(in GameFlowRequested request)
        {
            switch (request.Command)
            {
                case GameFlowCommand.StartGame:
                    if (RequireState(GameState.Menu, request.Command) && _stateMachine.TryTransitionTo(GameState.Loading))
                    {
                        _ = LoadSceneThenEnterAsync(_config.WorldSceneName, GameState.Playing);
                    }

                    break;
                case GameFlowCommand.Pause:
                    _stateMachine.TryTransitionTo(GameState.Paused);
                    break;
                case GameFlowCommand.Resume:
                    if (RequireState(GameState.Paused, request.Command))
                    {
                        _stateMachine.TryTransitionTo(GameState.Playing);
                    }

                    break;
                case GameFlowCommand.ReturnToMenu:
                    if (RequireState(GameState.Paused, request.Command) && _stateMachine.TryTransitionTo(GameState.Loading))
                    {
                        _ = LoadSceneThenEnterAsync(_config.MenuSceneName, GameState.Menu);
                    }

                    break;
                case GameFlowCommand.Quit:
                    if (RequireState(GameState.Menu, request.Command))
                    {
                        Application.Quit();
                    }

                    break;
                default:
                    Debug.LogWarning($"[GameFlow] Perintah tidak dikenal: {request.Command}.", this);
                    break;
            }
        }

        private bool RequireState(GameState expected, GameFlowCommand command)
        {
            if (_stateMachine.Current == expected)
            {
                return true;
            }

            Debug.LogWarning($"[GameFlow] Perintah {command} ditolak di state {_stateMachine.Current}.", this);
            return false;
        }

        private void OnGameStateChanged(in GameStateChanged evt)
        {
            ApplyStateEffects(evt.Current);
        }

        private void ApplyStateEffects(GameState state)
        {
            Time.timeScale = state == GameState.Paused ? PausedTimeScale : NormalTimeScale;
            if (_gameplayActionMap == null)
            {
                return;
            }

            if (GameStateMachine.AllowsGameplayInput(state))
            {
                _gameplayActionMap.Enable();
            }
            else
            {
                _gameplayActionMap.Disable();
            }
        }

        private async Awaitable LoadSceneThenEnterAsync(string sceneName, GameState stateAfterLoad)
        {
            try
            {
                await SceneLoader.LoadSingleAsync(sceneName, _config.MinimumLoadingSeconds, destroyCancellationToken);
            }
            catch (OperationCanceledException)
            {
                return;
            }
            catch (Exception exception)
            {
                Debug.LogException(exception, this);
                if (stateAfterLoad == GameState.Playing)
                {
                    // Dunia gagal dimuat: kembali ke menu agar pemain tidak terjebak di Loading.
                    _ = LoadSceneThenEnterAsync(_config.MenuSceneName, GameState.Menu);
                }

                return;
            }

            _stateMachine.TryTransitionTo(stateAfterLoad);
        }
    }
}
