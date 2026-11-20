using System.Collections;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using Game.Core.Events;
using Game.Core.Flow;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Game.Tests.PlayMode.Flow
{
    /// <summary>
    /// Alur scene nyata: Boot → Menu otomatis, Mulai → Loading → Playing di World, pause/resume
    /// lewat tombol Escape, kembali ke menu, serta frame time terlama selama transisi.
    /// </summary>
    public sealed class GameFlowPlayModeTests
    {
        private const string BootSceneName = "Boot";
        private const string WorldSceneName = "World";
        private const string MenuSceneName = "Menu";
        private const float StateTimeoutSeconds = 20f;
        private const double MaxFrameSeconds = 0.1;

        private readonly List<GameStateChanged> _received = new();
        private EventSubscription<GameStateChanged> _subscription;
        private Keyboard _keyboard = null!;
        private GameFlowController _controller = null!;
        private double _longestFrameSeconds;
        private InputSettings.BackgroundBehavior _originalBackgroundBehavior;
#if UNITY_EDITOR
        private InputSettings.EditorInputBehaviorInPlayMode _originalEditorBehavior;
#endif

        [UnitySetUp]
        public IEnumerator SetUp()
        {
            _received.Clear();
            _controller = null!;
            UseTestInputSettings();
            _keyboard = InputSystem.AddDevice<Keyboard>();
            _subscription = EventBus.Subscribe<GameStateChanged>(OnGameStateChanged);

            SceneManager.LoadScene(BootSceneName, LoadSceneMode.Single);
            var start = Time.realtimeSinceStartupAsDouble;
            while (_controller == null && Time.realtimeSinceStartupAsDouble - start < StateTimeoutSeconds)
            {
                yield return null;
                _controller = Object.FindAnyObjectByType<GameFlowController>();
            }

            Assert.That(_controller, Is.Not.Null, "GameFlowController tidak ada di scene Boot.");
            yield return WaitForState(GameState.Menu);
        }

        [UnityTearDown]
        public IEnumerator TearDown()
        {
            _subscription.Dispose();
            if (_controller != null)
            {
                Object.Destroy(_controller.gameObject);
            }

            InputSystem.RemoveDevice(_keyboard);
            RestoreInputSettings();
            Time.timeScale = 1f;
            yield return null;
        }

        // Di editor batchmode Game view tidak pernah fokus, sehingga input perangkat dialihkan ke
        // editor. Selama test, arahkan semua input ke game, lalu kembalikan nilai semula.
        // (Mengganti objek InputSystem.settings tidak dipakai: setter menghancurkan settings lama.)
        private void UseTestInputSettings()
        {
            var settings = InputSystem.settings;
            _originalBackgroundBehavior = settings.backgroundBehavior;
            settings.backgroundBehavior = InputSettings.BackgroundBehavior.IgnoreFocus;
#if UNITY_EDITOR
            _originalEditorBehavior = settings.editorInputBehaviorInPlayMode;
            settings.editorInputBehaviorInPlayMode =
                InputSettings.EditorInputBehaviorInPlayMode.AllDeviceInputAlwaysGoesToGameView;
#endif
        }

        private void RestoreInputSettings()
        {
            var settings = InputSystem.settings;
            settings.backgroundBehavior = _originalBackgroundBehavior;
#if UNITY_EDITOR
            settings.editorInputBehaviorInPlayMode = _originalEditorBehavior;
#endif
        }

        private void OnGameStateChanged(in GameStateChanged evt)
        {
            _received.Add(evt);
        }

        [UnityTest]
        public IEnumerator Boot_AutomaticallyEntersMenu()
        {
            Assert.That(_controller.CurrentState, Is.EqualTo(GameState.Menu));
            Assert.That(SceneManager.GetActiveScene().name, Is.EqualTo(MenuSceneName));
            Assert.That(_received[0].Previous, Is.EqualTo(GameState.Boot));
            Assert.That(_received[0].Current, Is.EqualTo(GameState.Menu));
            yield break;
        }

        [UnityTest]
        public IEnumerator StartGame_GoesThroughLoadingToPlayingInWorld_WithoutFrameFreeze()
        {
            _received.Clear();
            EventBus.Publish(new GameFlowRequested(GameFlowCommand.StartGame));
            Assert.That(_controller.CurrentState, Is.EqualTo(GameState.Loading));

            yield return WaitForState(GameState.Playing);

            Assert.That(SceneManager.GetActiveScene().name, Is.EqualTo(WorldSceneName));
            Assert.That(_received.Count, Is.EqualTo(2));
            Assert.That(_received[0].Current, Is.EqualTo(GameState.Loading));
            Assert.That(_received[1].Current, Is.EqualTo(GameState.Playing));
            Debug.Log($"[GAME-12] Frame terlama Menu→World: {_longestFrameSeconds * 1000.0:F1} ms");
            Assert.That(_longestFrameSeconds, Is.LessThan(MaxFrameSeconds),
                $"Frame freeze {_longestFrameSeconds * 1000.0:F1} ms saat pindah ke World.");
        }

        [UnityTest]
        public IEnumerator PauseKey_PausesAndBlocksMoveInput_ThenResumes()
        {
            yield return EnterWorld();
            var move = InputSystem.actions.FindAction("Player/Move", true);
            Assert.That(move.enabled, Is.True, "Input gerak harus aktif saat Playing.");

            yield return Tap(Key.Escape);
            Assert.That(_controller.CurrentState, Is.EqualTo(GameState.Paused));
            Assert.That(Time.timeScale, Is.EqualTo(0f));
            Assert.That(move.enabled, Is.False, "Input gerak harus nonaktif saat Paused.");

            InputSystem.QueueStateEvent(_keyboard, new KeyboardState(Key.W));
            yield return null;
            Assert.That(move.ReadValue<Vector2>(), Is.EqualTo(Vector2.zero), "Gerak tidak boleh terbaca saat Paused.");
            InputSystem.QueueStateEvent(_keyboard, new KeyboardState());
            yield return null;

            yield return Tap(Key.Escape);
            Assert.That(_controller.CurrentState, Is.EqualTo(GameState.Playing));
            Assert.That(Time.timeScale, Is.EqualTo(1f));
            Assert.That(move.enabled, Is.True);

            InputSystem.QueueStateEvent(_keyboard, new KeyboardState(Key.W));
            yield return null;
            Assert.That(move.ReadValue<Vector2>().y, Is.GreaterThan(0f), "Gerak harus terbaca lagi setelah resume.");
            InputSystem.QueueStateEvent(_keyboard, new KeyboardState());
            yield return null;
        }

        [UnityTest]
        public IEnumerator ReturnToMenu_FromPause_LoadsMenuWithoutFrameFreeze()
        {
            yield return EnterWorld();
            EventBus.Publish(new GameFlowRequested(GameFlowCommand.Pause));
            Assert.That(_controller.CurrentState, Is.EqualTo(GameState.Paused));

            EventBus.Publish(new GameFlowRequested(GameFlowCommand.ReturnToMenu));
            Assert.That(_controller.CurrentState, Is.EqualTo(GameState.Loading));
            Assert.That(Time.timeScale, Is.EqualTo(1f));

            yield return WaitForState(GameState.Menu);
            Assert.That(SceneManager.GetActiveScene().name, Is.EqualTo(MenuSceneName));
            Debug.Log($"[GAME-12] Frame terlama World→Menu: {_longestFrameSeconds * 1000.0:F1} ms");
            Assert.That(_longestFrameSeconds, Is.LessThan(MaxFrameSeconds));
        }

        [UnityTest]
        public IEnumerator PauseRequestInMenu_IsRejectedWithWarning()
        {
            LogAssert.Expect(LogType.Warning, new Regex("Transisi tidak valid ditolak: Menu → Paused"));

            EventBus.Publish(new GameFlowRequested(GameFlowCommand.Pause));

            Assert.That(_controller.CurrentState, Is.EqualTo(GameState.Menu));
            Assert.That(Time.timeScale, Is.EqualTo(1f));
            yield return null;
        }

        [UnityTest]
        public IEnumerator PauseKeyInMenu_IsIgnored()
        {
            yield return Tap(Key.Escape);

            Assert.That(_controller.CurrentState, Is.EqualTo(GameState.Menu));
            LogAssert.NoUnexpectedReceived();
        }

        private IEnumerator EnterWorld()
        {
            EventBus.Publish(new GameFlowRequested(GameFlowCommand.StartGame));
            yield return WaitForState(GameState.Playing);
        }

        private IEnumerator Tap(Key key)
        {
            InputSystem.QueueStateEvent(_keyboard, new KeyboardState(key));
            yield return null;
            InputSystem.QueueStateEvent(_keyboard, new KeyboardState());
            yield return null;
        }

        /// <summary>Menunggu state tertentu sambil mencatat frame (waktu nyata) terlama.</summary>
        private IEnumerator WaitForState(GameState target)
        {
            _longestFrameSeconds = 0.0;
            var start = Time.realtimeSinceStartupAsDouble;
            var previous = start;
            while (_controller.CurrentState != target)
            {
                yield return null;
                var now = Time.realtimeSinceStartupAsDouble;
                if (now - previous > _longestFrameSeconds)
                {
                    _longestFrameSeconds = now - previous;
                }

                previous = now;
                if (now - start > StateTimeoutSeconds)
                {
                    Assert.Fail($"Timeout menunggu state {target}; state sekarang {_controller.CurrentState}.");
                }
            }
        }
    }
}
