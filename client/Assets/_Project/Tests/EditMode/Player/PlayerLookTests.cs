using System;
using Game.Player;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace Game.Tests.EditMode.Player
{
    /// <summary>Orbit kamera: sensitivitas dari config, batas pitch, mouse vs stik terhadap deltaTime.</summary>
    public sealed class PlayerLookTests
    {
        private const float Tolerance = 1e-3f;

        private PlayerCameraConfig _config = null!;

        [SetUp]
        public void SetUp()
        {
            _config = CreateConfig(pointerSensitivity: 0.5f, stickYawSpeed: 180f, stickPitchSpeed: 90f,
                minPitch: -30f, maxPitch: 60f, initialPitch: 10f, invertPitch: false);
        }

        [TearDown]
        public void TearDown()
        {
            Object.DestroyImmediate(_config);
        }

        [Test]
        public void Constructor_NullConfig_Throws()
        {
            Assert.Throws<ArgumentNullException>(() => _ = new PlayerLook(null!, 0f));
        }

        [Test]
        public void Constructor_UsesInitialYawAndConfigPitch()
        {
            var look = new PlayerLook(_config, 450f);

            Assert.That(look.Yaw, Is.EqualTo(90f).Within(Tolerance));
            Assert.That(look.Pitch, Is.EqualTo(10f).Within(Tolerance));
        }

        [Test]
        public void PointerDelta_UsesSensitivity_AndIgnoresDeltaTime()
        {
            var a = new PlayerLook(_config, 0f);
            var b = new PlayerLook(_config, 0f);

            a.Step(new Vector2(20f, 0f), true, 1f / 30f);
            b.Step(new Vector2(20f, 0f), true, 1f / 144f);

            Assert.That(a.Yaw, Is.EqualTo(10f).Within(Tolerance));
            Assert.That(b.Yaw, Is.EqualTo(a.Yaw).Within(Tolerance));
        }

        [Test]
        public void Stick_RotatesAtConfiguredRate_SameAt30And144Fps()
        {
            var low = new PlayerLook(_config, 0f);
            var high = new PlayerLook(_config, 0f);
            for (var i = 0; i < 15; i++)
            {
                low.Step(Vector2.right, false, 1f / 30f);
            }

            for (var i = 0; i < 72; i++)
            {
                high.Step(Vector2.right, false, 1f / 144f);
            }

            Assert.That(low.Yaw, Is.EqualTo(90f).Within(Tolerance));
            Assert.That(high.Yaw, Is.EqualTo(low.Yaw).Within(Tolerance));
        }

        [Test]
        public void LookUp_DecreasesPitch_UnlessInverted()
        {
            var look = new PlayerLook(_config, 0f);
            look.Step(new Vector2(0f, 10f), true, 0.016f);
            Assert.That(look.Pitch, Is.EqualTo(5f).Within(Tolerance));

            var inverted = CreateConfig(0.5f, 180f, 90f, -30f, 60f, 10f, invertPitch: true);
            try
            {
                var invertedLook = new PlayerLook(inverted, 0f);
                invertedLook.Step(new Vector2(0f, 10f), true, 0.016f);
                Assert.That(invertedLook.Pitch, Is.EqualTo(15f).Within(Tolerance));
            }
            finally
            {
                Object.DestroyImmediate(inverted);
            }
        }

        [Test]
        public void Pitch_IsClampedToConfigLimits()
        {
            var look = new PlayerLook(_config, 0f);

            look.Step(new Vector2(0f, -1000f), true, 0.016f);
            Assert.That(look.Pitch, Is.EqualTo(60f).Within(Tolerance));

            look.Step(new Vector2(0f, 1000f), true, 0.016f);
            Assert.That(look.Pitch, Is.EqualTo(-30f).Within(Tolerance));
        }

        [Test]
        public void Yaw_WrapsAround()
        {
            var look = new PlayerLook(_config, 350f);

            look.Step(new Vector2(40f, 0f), true, 0.016f);

            Assert.That(look.Yaw, Is.EqualTo(10f).Within(Tolerance));
        }

        [Test]
        public void Rotation_MatchesYawAndPitch()
        {
            var look = new PlayerLook(_config, 90f);

            var forward = look.Rotation * Vector3.forward;

            Assert.That(forward.x, Is.GreaterThan(0.9f));
            Assert.That(forward.y, Is.LessThan(0f), "Pitch positif = menunduk.");
        }

        [Test]
        public void Step_DoesNotAllocate()
        {
            var look = new PlayerLook(_config, 0f);
            look.Step(Vector2.one, false, 0.016f);

            Assert.That(() => look.Step(Vector2.one, false, 0.016f), Is.Not.AllocatingGCMemory());
        }

        private static PlayerCameraConfig CreateConfig(float pointerSensitivity, float stickYawSpeed, float stickPitchSpeed,
            float minPitch, float maxPitch, float initialPitch, bool invertPitch)
        {
            var config = ScriptableObject.CreateInstance<PlayerCameraConfig>();
            var serialized = new SerializedObject(config);
            serialized.FindProperty("_pointerSensitivity").floatValue = pointerSensitivity;
            serialized.FindProperty("_stickYawSpeed").floatValue = stickYawSpeed;
            serialized.FindProperty("_stickPitchSpeed").floatValue = stickPitchSpeed;
            serialized.FindProperty("_minPitch").floatValue = minPitch;
            serialized.FindProperty("_maxPitch").floatValue = maxPitch;
            serialized.FindProperty("_initialPitch").floatValue = initialPitch;
            serialized.FindProperty("_invertPitch").boolValue = invertPitch;
            serialized.ApplyModifiedPropertiesWithoutUndo();
            config.RunValidation();
            return config;
        }
    }
}
