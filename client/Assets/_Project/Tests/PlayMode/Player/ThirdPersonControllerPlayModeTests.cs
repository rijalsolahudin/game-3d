using System.Collections;
using Game.Player;
using NUnit.Framework;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;

namespace Game.Tests.PlayMode.Player
{
    /// <summary>
    /// GAME-23 di scene World nyata: jalan/lari/lompat dengan keyboard virtual dan gamepad virtual,
    /// arah gerak mengikuti kamera, tanjakan & undakan uji, tabrakan kamera dengan bangunan/tanah,
    /// kesamaan jarak di 30 vs 144 FPS, dan nol alokasi GC dari controller.
    /// </summary>
    public sealed class ThirdPersonControllerPlayModeTests
    {
        private const string WorldSceneName = "World";
        private const string GameplayMapName = "Player";
        private const float SceneTimeoutSeconds = 20f;
        private const float SettleSeconds = 0.5f;
        private const float SpeedTolerance = 0.05f;
        private const float DirectionToleranceDegrees = 3f;
        private const float JumpTimeoutSeconds = 3f;
        private const float ClimbTimeoutSeconds = 10f;

        // Area terbuka di selatan geometri uji.
        private static readonly Vector3 OpenArea = new(0f, 0.05f, -30f);

        private InputTestSettingsScope _inputScope = null!;
        private Keyboard _keyboard = null!;
        private Mouse _mouse = null!;
        private Gamepad _gamepad = null!;
        private ThirdPersonController _controller = null!;
        private float _lastApex;
        private InputActionMap? _gameplayMap;
        private bool _gameplayMapWasEnabled;
        private float _lastDistance;

        [UnitySetUp]
        public IEnumerator SetUp()
        {
            _inputScope = new InputTestSettingsScope();
            _gameplayMap = null;
            _keyboard = InputSystem.AddDevice<Keyboard>();
            _mouse = InputSystem.AddDevice<Mouse>();
            _gamepad = InputSystem.AddDevice<Gamepad>();

            SceneManager.LoadScene(WorldSceneName, LoadSceneMode.Single);
            var start = Time.realtimeSinceStartupAsDouble;
            _controller = null!;
            while (_controller == null && Time.realtimeSinceStartupAsDouble - start < SceneTimeoutSeconds)
            {
                yield return null;
                _controller = Object.FindAnyObjectByType<ThirdPersonController>();
            }

            Assert.That(_controller, Is.Not.Null, "ThirdPersonController tidak ada di scene World.");
            // Tanpa scene Boot, GameFlowController tidak ada; aktifkan map gameplay seperti saat Playing.
            _gameplayMap = InputSystem.actions.FindActionMap(GameplayMapName, true);
            _gameplayMapWasEnabled = _gameplayMap.enabled;
            _gameplayMap.Enable();
            yield return null;
        }

        [UnityTearDown]
        public IEnumerator TearDown()
        {
            Time.captureDeltaTime = 0f;
            if (_gameplayMap != null && !_gameplayMapWasEnabled)
            {
                _gameplayMap.Disable();
            }

            InputSystem.RemoveDevice(_keyboard);
            InputSystem.RemoveDevice(_mouse);
            InputSystem.RemoveDevice(_gamepad);
            _inputScope.Dispose();
            yield return null;
        }

        [UnityTest]
        public IEnumerator Keyboard_Walk_MovesAlongCameraYawAtWalkSpeed()
        {
            yield return TeleportAndSettle(OpenArea, 90f, 15f);
            var start = _controller.transform.position;

            yield return HoldKeys(1.5f, Key.W);

            AssertMovedAlongYaw(start, 90f);
            Assert.That(HorizontalSpeed(), Is.EqualTo(_controller.MovementConfig.WalkSpeed).Within(SpeedTolerance));
        }

        [UnityTest]
        public IEnumerator Keyboard_ShiftW_RunsAtRunSpeed()
        {
            yield return TeleportAndSettle(OpenArea, 210f, 15f);
            var start = _controller.transform.position;

            yield return HoldKeys(1.5f, Key.W, Key.LeftShift);

            AssertMovedAlongYaw(start, 210f);
            Assert.That(HorizontalSpeed(), Is.EqualTo(_controller.MovementConfig.RunSpeed).Within(SpeedTolerance));
        }

        [UnityTest]
        public IEnumerator Keyboard_Space_JumpsToConfiguredHeightAndLands()
        {
            yield return TeleportAndSettle(OpenArea, 0f, 15f);

            yield return MeasureJump(() => QueueKeys(Key.Space), () => QueueKeys());

            Assert.That(_lastApex, Is.EqualTo(_controller.MovementConfig.JumpHeight).Within(0.1f));
            Assert.That(_controller.IsGrounded, Is.True, "Pemain harus mendarat kembali.");
        }

        [UnityTest]
        public IEnumerator Gamepad_LeftStick_WalksAlongCameraYaw()
        {
            yield return TeleportAndSettle(OpenArea, 300f, 15f);
            var start = _controller.transform.position;

            yield return HoldGamepad(1.5f, new GamepadState { leftStick = Vector2.up });

            AssertMovedAlongYaw(start, 300f);
            Assert.That(HorizontalSpeed(), Is.EqualTo(_controller.MovementConfig.WalkSpeed).Within(SpeedTolerance));
        }

        [UnityTest]
        public IEnumerator Gamepad_LeftStickPress_Runs()
        {
            yield return TeleportAndSettle(OpenArea, 45f, 15f);
            var start = _controller.transform.position;

            yield return HoldGamepad(1.5f, new GamepadState { leftStick = Vector2.up }.WithButton(GamepadButton.LeftStick));

            AssertMovedAlongYaw(start, 45f);
            Assert.That(HorizontalSpeed(), Is.EqualTo(_controller.MovementConfig.RunSpeed).Within(SpeedTolerance));
        }

        [UnityTest]
        public IEnumerator Gamepad_South_Jumps()
        {
            yield return TeleportAndSettle(OpenArea, 0f, 15f);

            yield return MeasureJump(
                () => InputSystem.QueueStateEvent(_gamepad, new GamepadState().WithButton(GamepadButton.South)),
                () => InputSystem.QueueStateEvent(_gamepad, new GamepadState()));

            Assert.That(_lastApex, Is.EqualTo(_controller.MovementConfig.JumpHeight).Within(0.1f));
            Assert.That(_controller.IsGrounded, Is.True);
        }

        [UnityTest]
        public IEnumerator Mouse_Delta_RotatesCamera_AndMovementFollowsNewYaw()
        {
            yield return TeleportAndSettle(OpenArea, 0f, 15f);
            var config = _controller.CameraConfig;
            const float pixelsPerFrame = 50f;
            const int frames = 10;

            for (var i = 0; i < frames; i++)
            {
                InputSystem.QueueStateEvent(_mouse, new MouseState { delta = new Vector2(pixelsPerFrame, 0f) });
                yield return null;
            }

            InputSystem.QueueStateEvent(_mouse, new MouseState());
            yield return null;
            var expectedYaw = frames * pixelsPerFrame * config.PointerSensitivity;
            Assert.That(_controller.Look.Yaw, Is.EqualTo(expectedYaw).Within(0.5f));

            var start = _controller.transform.position;
            yield return HoldKeys(1f, Key.W);
            AssertMovedAlongYaw(start, _controller.Look.Yaw);

            // Kamera Cinemachine benar-benar menghadap yaw baru.
            var cameraForward = Camera.main!.transform.forward;
            cameraForward.y = 0f;
            Assert.That(Vector3.Angle(cameraForward, Quaternion.Euler(0f, _controller.Look.Yaw, 0f) * Vector3.forward),
                Is.LessThan(DirectionToleranceDegrees));
        }

        [UnityTest]
        public IEnumerator Gamepad_RightStick_RotatesCameraAtConfiguredRate()
        {
            yield return TeleportAndSettle(OpenArea, 0f, 15f);
            Time.captureDeltaTime = 1f / 60f;
            const int frames = 30;

            InputSystem.QueueStateEvent(_gamepad, new GamepadState { rightStick = Vector2.right });
            for (var i = 0; i < frames; i++)
            {
                yield return null;
            }

            InputSystem.QueueStateEvent(_gamepad, new GamepadState());
            yield return null;
            var expectedYaw = _controller.CameraConfig.StickYawSpeed * frames / 60f;
            Assert.That(_controller.Look.Yaw, Is.EqualTo(expectedYaw).Within(expectedYaw * 0.05f));
        }

        [UnityTest]
        public IEnumerator Movement_SameDistanceAt30And144Fps()
        {
            yield return WalkFixedFrames(30f);
            var low = _lastDistance;
            yield return WalkFixedFrames(144f);
            var high = _lastDistance;

            Debug.Log($"[GAME-23] Jarak 1 detik jalan: 30 FPS = {low:F4} m, 144 FPS = {high:F4} m");
            Assert.That(low, Is.EqualTo(high).Within(0.03f));
            Assert.That(high, Is.GreaterThan(_controller.MovementConfig.WalkSpeed * 0.8f));
        }

        [UnityTest]
        public IEnumerator Ramp30Degrees_CanBeClimbedToPlatform()
        {
            var ramp = GameObject.Find("Test Ramp 30deg");
            var platform = GameObject.Find("Test Ramp Platform");
            Assert.That(ramp, Is.Not.Null);
            Assert.That(platform, Is.Not.Null);
            var rampBounds = ramp.GetComponent<Collider>().bounds;
            var platformTop = platform.GetComponent<Collider>().bounds.max.y;

            yield return TeleportAndSettle(new Vector3(rampBounds.center.x, 0.05f, rampBounds.min.z - 2f), 0f, 15f);
            yield return WalkNorthUntil(rampBounds.max.z + 0.5f, ClimbTimeoutSeconds);

            var position = _controller.transform.position;
            Assert.That(position.y, Is.EqualTo(platformTop).Within(0.1f), "Pemain harus sampai di atas tanjakan.");
            Assert.That(position.z, Is.GreaterThan(rampBounds.max.z));
        }

        [UnityTest]
        public IEnumerator Steps_LowerThanStepOffset_CanBeClimbedWithoutJumping()
        {
            var landing = GameObject.Find("Test Step Landing");
            var firstStep = GameObject.Find("Test Step 1");
            Assert.That(landing, Is.Not.Null);
            Assert.That(firstStep, Is.Not.Null);
            var stepBounds = firstStep.GetComponent<Collider>().bounds;
            Assert.That(stepBounds.size.y, Is.LessThan(_controller.MovementConfig.StepOffset));
            var landingBounds = landing.GetComponent<Collider>().bounds;

            yield return TeleportAndSettle(new Vector3(stepBounds.center.x, 0.05f, stepBounds.min.z - 2f), 0f, 15f);
            yield return WalkNorthUntil(landingBounds.min.z + 0.5f, ClimbTimeoutSeconds);

            var position = _controller.transform.position;
            Assert.That(position.y, Is.EqualTo(landingBounds.max.y).Within(0.1f), "Pemain harus sampai di puncak undakan.");
            Assert.That(position.z, Is.GreaterThan(landingBounds.min.z));
        }

        [UnityTest]
        public IEnumerator Camera_BackingIntoBuilding_PullsInSmoothly_WithoutPenetrating()
        {
            var building = GameObject.Find("Test Building");
            Assert.That(building, Is.Not.Null);
            var bounds = building.GetComponent<Collider>().bounds;
            var config = _controller.CameraConfig;

            // Menghadap selatan, membelakangi dinding selatan bangunan; kamera di antara pemain dan dinding.
            var start = new Vector3(bounds.center.x, 0.05f, bounds.min.z - config.CameraDistance - 3f);
            yield return TeleportAndSettle(start, 180f, 10f);
            var camera = Camera.main!.transform;
            var initialDistance = CameraDistance(camera);
            Assert.That(initialDistance, Is.GreaterThan(config.CameraDistance * 0.9f), "Awalnya kamera tidak terhalang.");

            // Mundur (S) ke arah dinding sambil memantau kamera tiap frame (60 FPS tetap agar
            // "langkah per frame" bermakna; batchmode tanpa vsync bisa ribuan FPS).
            Time.captureDeltaTime = 1f / 60f;
            var largestStep = 0f;
            var previous = initialDistance;
            QueueKeys(Key.S);
            var end = Time.time + 3.5f;
            while (Time.time < end)
            {
                yield return null;
                var distance = CameraDistance(camera);
                largestStep = Mathf.Max(largestStep, previous - distance);
                previous = distance;
                Assert.That(bounds.Contains(camera.position), Is.False,
                    $"Kamera menembus bangunan di {camera.position}.");
            }

            QueueKeys();
            yield return null;
            Debug.Log($"[GAME-23] Kamera terhalang: jarak akhir {previous:F2} m, langkah maju terbesar {largestStep:F3} m/frame @60 FPS");
            Assert.That(previous, Is.LessThan(config.CameraDistance * 0.75f), "Kamera harus mendekat saat terhalang.");
            Assert.That(largestStep, Is.LessThan(0.25f), "Kamera harus mendekat dengan halus, bukan melompat.");
        }

        [UnityTest]
        public IEnumerator Camera_LookingUp_StaysAboveGround()
        {
            yield return TeleportAndSettle(OpenArea, 0f, _controller.CameraConfig.MinPitch);
            var camera = Camera.main!.transform;
            var ground = GameObject.Find("Ground");
            Assert.That(ground, Is.Not.Null);
            var groundY = ground.GetComponent<Collider>().bounds.max.y;

            Assert.That(camera.position.y, Is.GreaterThan(groundY + _controller.CameraConfig.CameraRadius * 0.5f),
                "Kamera tidak boleh menembus tanah.");
        }

        [UnityTest]
        public IEnumerator ControllerTick_WithAllInputsActive_DoesNotAllocate()
        {
            yield return TeleportAndSettle(OpenArea, 0f, 15f);
            QueueKeys(Key.W, Key.LeftShift, Key.Space);
            InputSystem.QueueStateEvent(_gamepad, new GamepadState { leftStick = Vector2.right, rightStick = Vector2.up });
            InputSystem.QueueStateEvent(_mouse, new MouseState { delta = new Vector2(3f, 2f) });
            yield return null;
            _controller.Tick(1f / 60f);

            Assert.That(() =>
            {
                for (var i = 0; i < 60; i++)
                {
                    _controller.Tick(1f / 60f);
                }
            }, Is.Not.AllocatingGCMemory());

            // Informasi: total GC.Alloc main thread per frame (termasuk runner test & editor).
            using var recorder = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC.Alloc", 30);
            for (var i = 0; i < 30; i++)
            {
                yield return null;
            }

            Debug.Log($"[GAME-23] GC.Alloc frame terakhir (semua sistem, editor): {recorder.LastValue} B");
            QueueKeys();
            InputSystem.QueueStateEvent(_gamepad, new GamepadState());
            yield return null;
        }

        /// <summary>Menekan lompat satu frame, lalu mencatat tinggi puncak sampai mendarat ke <see cref="_lastApex"/>.</summary>
        private IEnumerator MeasureJump(System.Action press, System.Action release)
        {
            var groundY = _controller.transform.position.y;
            _lastApex = 0f;
            press();
            yield return null;
            release();
            var end = Time.time + JumpTimeoutSeconds;
            var leftGround = false;
            while (Time.time < end)
            {
                yield return null;
                _lastApex = Mathf.Max(_lastApex, _controller.transform.position.y - groundY);
                leftGround |= !_controller.IsGrounded;
                if (leftGround && _controller.IsGrounded)
                {
                    break;
                }
            }

            yield return null;
        }

        /// <summary>Jalan maju tepat satu detik simulasi dengan deltaTime tetap; jarak ke <see cref="_lastDistance"/>.</summary>
        private IEnumerator WalkFixedFrames(float fps)
        {
            yield return TeleportAndSettle(OpenArea, 0f, 15f);
            Time.captureDeltaTime = 1f / fps;
            yield return null;
            var start = _controller.transform.position;
            QueueKeys(Key.W);
            var frames = Mathf.RoundToInt(fps);
            for (var i = 0; i < frames; i++)
            {
                yield return null;
            }

            var delta = _controller.transform.position - start;
            delta.y = 0f;
            _lastDistance = delta.magnitude;
            QueueKeys();
            Time.captureDeltaTime = 0f;
            yield return null;
        }

        private float HorizontalSpeed()
        {
            var v = _controller.Locomotion.HorizontalVelocity;
            v.y = 0f;
            return v.magnitude;
        }

        private float CameraDistance(Transform camera)
        {
            return Vector3.Distance(camera.position, _controller.CameraTarget.position);
        }

        private void AssertMovedAlongYaw(Vector3 start, float yawDegrees)
        {
            var delta = _controller.transform.position - start;
            delta.y = 0f;
            Assert.That(delta.magnitude, Is.GreaterThan(0.5f), "Pemain tidak bergerak.");
            var expected = Quaternion.Euler(0f, yawDegrees, 0f) * Vector3.forward;
            Assert.That(Vector3.Angle(delta, expected), Is.LessThan(DirectionToleranceDegrees),
                $"Arah gerak {delta} tidak mengikuti yaw kamera {yawDegrees}°.");
        }

        private IEnumerator TeleportAndSettle(Vector3 position, float yaw, float pitch)
        {
            QueueKeys();
            InputSystem.QueueStateEvent(_gamepad, new GamepadState());
            yield return null;
            _controller.Teleport(position, yaw, pitch);
            var end = Time.time + SettleSeconds;
            while (Time.time < end)
            {
                yield return null;
            }

            Assert.That(_controller.IsGrounded, Is.True,
                $"Pemain harus menapak setelah teleport (posisi {_controller.transform.position}, " +
                $"vy {_controller.Locomotion.VerticalVelocity}, enabled {_controller.enabled}, t {Time.time}).");
        }

        /// <summary>Tahan W (yaw 0 = utara) sampai melewati z tertentu atau timeout (tersangkut).</summary>
        private IEnumerator WalkNorthUntil(float targetZ, float timeoutSeconds)
        {
            QueueKeys(Key.W);
            var end = Time.time + timeoutSeconds;
            while (Time.time < end && _controller.transform.position.z < targetZ)
            {
                yield return null;
            }

            QueueKeys();
            var settle = Time.time + SettleSeconds;
            while (Time.time < settle)
            {
                yield return null;
            }
        }

        private IEnumerator HoldKeys(float seconds, params Key[] keys)
        {
            QueueKeys(keys);
            var end = Time.time + seconds;
            while (Time.time < end)
            {
                yield return null;
            }
        }

        private IEnumerator HoldGamepad(float seconds, GamepadState state)
        {
            InputSystem.QueueStateEvent(_gamepad, state);
            var end = Time.time + seconds;
            while (Time.time < end)
            {
                yield return null;
            }
        }

        private void QueueKeys(params Key[] keys)
        {
            InputSystem.QueueStateEvent(_keyboard, new KeyboardState(keys));
        }
    }
}
