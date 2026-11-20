using System;
using Game.Player;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace Game.Tests.EditMode.Player
{
    /// <summary>
    /// AC4 (GAME-23): gerak berbasis deltaTime menghasilkan jarak, kecepatan, dan tinggi lompatan
    /// yang sama di 30 FPS dan 144 FPS. Simulasi memakai lantai datar di y = 0.
    /// </summary>
    public sealed class PlayerLocomotionTests
    {
        private const float LowFps = 30f;
        private const float HighFps = 144f;
        private const float DistanceTolerance = 0.02f;
        private const float HeightTolerance = 0.01f;

        private PlayerMovementConfig _config = null!;

        [SetUp]
        public void SetUp()
        {
            _config = PlayerMovementConfigFactory.Create();
        }

        [TearDown]
        public void TearDown()
        {
            Object.DestroyImmediate(_config);
        }

        [Test]
        public void Constructor_NullConfig_Throws()
        {
            Assert.Throws<ArgumentNullException>(() => _ = new PlayerLocomotion(null!));
        }

        [TestCase(false)]
        [TestCase(true)]
        public void WalkOrRunDistance_IsFrameRateIndependent(bool isRunning)
        {
            var low = SimulateFlat(LowFps, 2f, Vector2.up, isRunning, jumpAtStart: false, out _, out var lowSpeed);
            var high = SimulateFlat(HighFps, 2f, Vector2.up, isRunning, jumpAtStart: false, out _, out var highSpeed);

            Assert.That(low.z, Is.EqualTo(high.z).Within(DistanceTolerance));
            Assert.That(lowSpeed, Is.EqualTo(highSpeed).Within(1e-3f));
            var expectedSpeed = isRunning ? _config.RunSpeed : _config.WalkSpeed;
            Assert.That(highSpeed, Is.EqualTo(expectedSpeed).Within(1e-3f));
        }

        [Test]
        public void JumpApex_IsFrameRateIndependent_AndMatchesConfig()
        {
            SimulateFlat(LowFps, 2f, Vector2.zero, false, jumpAtStart: true, out var lowApex, out _);
            SimulateFlat(HighFps, 2f, Vector2.zero, false, jumpAtStart: true, out var highApex, out _);

            Assert.That(lowApex, Is.EqualTo(_config.JumpHeight).Within(HeightTolerance));
            Assert.That(highApex, Is.EqualTo(_config.JumpHeight).Within(HeightTolerance));
        }

        [Test]
        public void Jump_RequiresGroundOrCoyoteTime()
        {
            var locomotion = new PlayerLocomotion(_config);
            var dt = 1f / HighFps;

            // Jatuh lama tanpa pernah menapak: tidak boleh lompat di udara.
            for (var i = 0; i < 60; i++)
            {
                locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, false, 0f), false, dt);
            }

            locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, true, 0f), false, dt);
            Assert.That(locomotion.JumpedThisStep, Is.False);
            Assert.That(locomotion.VerticalVelocity, Is.LessThan(0f));
        }

        [Test]
        public void Jump_WithinCoyoteTime_AfterLeavingLedge_Succeeds()
        {
            var locomotion = new PlayerLocomotion(_config);
            var dt = _config.CoyoteTime * 0.5f;
            locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, false, 0f), true, dt);

            locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, true, 0f), false, dt);

            Assert.That(locomotion.JumpedThisStep, Is.True);
            Assert.That(locomotion.VerticalVelocity, Is.GreaterThan(0f));
        }

        [Test]
        public void Jump_PressedShortlyBeforeLanding_IsBuffered()
        {
            var locomotion = new PlayerLocomotion(_config);
            var dt = _config.JumpBufferTime * 0.5f;
            locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, true, 0f), false, dt);
            Assert.That(locomotion.JumpedThisStep, Is.False);

            locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, false, 0f), true, dt);

            Assert.That(locomotion.JumpedThisStep, Is.True);
        }

        [Test]
        public void Jump_HeldButton_DoesNotDoubleJump()
        {
            var locomotion = new PlayerLocomotion(_config);
            var dt = 1f / HighFps;
            locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, true, 0f), true, dt);
            Assert.That(locomotion.JumpedThisStep, Is.True);

            locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, false, 0f), false, dt);
            locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, true, 0f), false, dt);

            Assert.That(locomotion.JumpedThisStep, Is.False);
        }

        [Test]
        public void Grounded_KeepsSmallDownwardVelocity_WithoutAccumulating()
        {
            var locomotion = new PlayerLocomotion(_config);
            var dt = 1f / LowFps;
            for (var i = 0; i < 120; i++)
            {
                locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, false, 0f), true, dt);
            }

            Assert.That(locomotion.VerticalVelocity,
                Is.EqualTo(-_config.GroundStickSpeed - _config.Gravity * dt).Within(1e-4f));
        }

        [Test]
        public void CancelUpwardVelocity_StopsRising()
        {
            var locomotion = new PlayerLocomotion(_config);
            locomotion.Step(new PlayerLocomotionInput(Vector2.zero, false, true, 0f), true, 1f / HighFps);

            locomotion.CancelUpwardVelocity();

            Assert.That(locomotion.VerticalVelocity, Is.EqualTo(0f));
        }

        [Test]
        public void Move_FollowsViewYaw()
        {
            var locomotion = new PlayerLocomotion(_config);
            var displacement = Vector3.zero;
            for (var i = 0; i < 60; i++)
            {
                displacement += locomotion.Step(new PlayerLocomotionInput(Vector2.up, false, false, 90f), true, 1f / 60f);
            }

            Assert.That(displacement.x, Is.GreaterThan(0.5f));
            Assert.That(Mathf.Abs(displacement.z), Is.LessThan(1e-3f));
        }

        [Test]
        public void ZeroDeltaTime_DoesNotMove()
        {
            var locomotion = new PlayerLocomotion(_config);

            var displacement = locomotion.Step(new PlayerLocomotionInput(Vector2.up, true, true, 0f), true, 0f);

            Assert.That(displacement, Is.EqualTo(Vector3.zero));
            Assert.That(locomotion.JumpedThisStep, Is.False);
        }

        [Test]
        public void Step_DoesNotAllocate()
        {
            var locomotion = new PlayerLocomotion(_config);
            var input = new PlayerLocomotionInput(Vector2.one, true, true, 45f);
            locomotion.Step(input, true, 0.016f);

            Assert.That(() => { locomotion.Step(input, true, 0.016f); }, Is.Not.AllocatingGCMemory());
        }

        /// <summary>Simulasi lantai datar: posisi y dijepit di 0, menapak bila y ≤ 0.</summary>
        private Vector3 SimulateFlat(float fps, float seconds, Vector2 move, bool isRunning, bool jumpAtStart,
            out float apex, out float finalSpeed)
        {
            var locomotion = new PlayerLocomotion(_config);
            var dt = 1f / fps;
            var steps = Mathf.RoundToInt(seconds * fps);
            var position = Vector3.zero;
            apex = 0f;
            var grounded = true;
            for (var i = 0; i < steps; i++)
            {
                var input = new PlayerLocomotionInput(move, isRunning, jumpAtStart && i == 0, 0f);
                position += locomotion.Step(input, grounded, dt);
                if (position.y <= 0f)
                {
                    position.y = 0f;
                    grounded = true;
                }
                else
                {
                    grounded = false;
                }

                apex = Mathf.Max(apex, position.y);
            }

            finalSpeed = locomotion.HorizontalVelocity.magnitude;
            return position;
        }
    }
}
