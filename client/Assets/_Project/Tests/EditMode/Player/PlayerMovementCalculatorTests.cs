using System;
using Game.Player;
using NUnit.Framework;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Game.Tests.EditMode.Player
{
    /// <summary>AC4: nilai gerak berasal dari <see cref="PlayerMovementConfig"/>, bukan konstanta kode.</summary>
    public sealed class PlayerMovementCalculatorTests
    {
        private const float Tolerance = 1e-4f;

        private PlayerMovementConfig _config = null!;
        private PlayerMovementCalculator _calculator = null!;

        [SetUp]
        public void SetUp()
        {
            _config = PlayerMovementConfigFactory.Create(
                walkSpeed: 1.7f, runSpeed: 4.3f, acceleration: 10f, deceleration: 20f,
                airControl: 0.5f, jumpHeight: 0.8f, gravity: 12f, maxFallSpeed: 30f, rotationSpeed: 90f);
            _calculator = new PlayerMovementCalculator(_config);
        }

        [TearDown]
        public void TearDown()
        {
            Object.DestroyImmediate(_config);
        }

        [Test]
        public void Constructor_NullConfig_Throws()
        {
            Assert.Throws<ArgumentNullException>(() => _ = new PlayerMovementCalculator(null!));
        }

        [Test]
        public void TargetVelocity_UsesWalkAndRunSpeedFromConfig()
        {
            var walk = _calculator.GetTargetHorizontalVelocity(Vector2.up, false, 0f);
            var run = _calculator.GetTargetHorizontalVelocity(Vector2.up, true, 0f);

            Assert.That(walk.z, Is.EqualTo(1.7f).Within(Tolerance));
            Assert.That(run.z, Is.EqualTo(4.3f).Within(Tolerance));
            Assert.That(walk.y, Is.EqualTo(0f));
        }

        [Test]
        public void TargetVelocity_FollowsConfigChanges()
        {
            var otherConfig = PlayerMovementConfigFactory.Create(walkSpeed: 2.5f, runSpeed: 6f);
            try
            {
                var other = new PlayerMovementCalculator(otherConfig);

                Assert.That(other.GetTargetHorizontalVelocity(Vector2.up, false, 0f).magnitude,
                    Is.EqualTo(2.5f).Within(Tolerance));
            }
            finally
            {
                Object.DestroyImmediate(otherConfig);
            }
        }

        [Test]
        public void TargetVelocity_DiagonalInputIsClampedToSpeed()
        {
            var velocity = _calculator.GetTargetHorizontalVelocity(new Vector2(1f, 1f), false, 0f);

            Assert.That(velocity.magnitude, Is.EqualTo(1.7f).Within(Tolerance));
        }

        [Test]
        public void TargetVelocity_RotatesWithViewYaw()
        {
            var velocity = _calculator.GetTargetHorizontalVelocity(Vector2.up, false, 90f);

            Assert.That(velocity.x, Is.EqualTo(1.7f).Within(Tolerance));
            Assert.That(velocity.z, Is.EqualTo(0f).Within(Tolerance));
        }

        [Test]
        public void StepHorizontal_AcceleratesWithConfigRate()
        {
            var next = _calculator.StepHorizontalVelocity(Vector3.zero, new Vector3(0f, 0f, 4f), true, 0.1f);

            Assert.That(next.z, Is.EqualTo(1f).Within(Tolerance));
        }

        [Test]
        public void StepHorizontal_DeceleratesWithConfigRate()
        {
            var next = _calculator.StepHorizontalVelocity(new Vector3(0f, 0f, 4f), Vector3.zero, true, 0.1f);

            Assert.That(next.z, Is.EqualTo(2f).Within(Tolerance));
        }

        [Test]
        public void StepHorizontal_InAir_ScaledByAirControl()
        {
            var next = _calculator.StepHorizontalVelocity(Vector3.zero, new Vector3(0f, 0f, 4f), false, 0.1f);

            Assert.That(next.z, Is.EqualTo(0.5f).Within(Tolerance));
        }

        [Test]
        public void JumpVelocity_ReachesConfiguredHeight()
        {
            var v = _calculator.GetJumpVelocity();
            var apex = v * v / (2f * _config.Gravity);

            Assert.That(apex, Is.EqualTo(0.8f).Within(Tolerance));
        }

        [Test]
        public void StepVertical_AppliesGravityAndClampsFallSpeed()
        {
            Assert.That(_calculator.StepVerticalVelocity(0f, 0.5f), Is.EqualTo(-6f).Within(Tolerance));
            Assert.That(_calculator.StepVerticalVelocity(-29f, 1f), Is.EqualTo(-30f).Within(Tolerance));
        }

        [Test]
        public void StepRotation_UsesConfiguredRotationSpeed()
        {
            var next = _calculator.StepRotation(Quaternion.identity, Vector3.right, 0.5f);

            Assert.That(Quaternion.Angle(Quaternion.identity, next), Is.EqualTo(45f).Within(0.01f));
        }

        [Test]
        public void StepRotation_TinyDirection_KeepsRotation()
        {
            var current = Quaternion.Euler(0f, 30f, 0f);

            Assert.That(_calculator.StepRotation(current, Vector3.right * 1e-4f, 1f), Is.EqualTo(current));
        }

        [Test]
        public void StepRotation_NoDirection_KeepsRotation()
        {
            var current = Quaternion.Euler(0f, 30f, 0f);

            Assert.That(_calculator.StepRotation(current, Vector3.zero, 1f), Is.EqualTo(current));
        }
    }
}
