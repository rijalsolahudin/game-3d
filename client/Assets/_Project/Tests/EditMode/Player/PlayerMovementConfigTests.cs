using Game.Player;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Game.Tests.EditMode.Player
{
    public sealed class PlayerMovementConfigTests
    {
        private const string DefaultAssetPath = "Assets/_Project/Settings/player-movement-config.asset";

        [Test]
        public void DefaultAsset_ExistsWithHumanPlausibleValues()
        {
            var config = AssetDatabase.LoadAssetAtPath<PlayerMovementConfig>(DefaultAssetPath);

            Assert.That(config, Is.Not.Null, $"Aset {DefaultAssetPath} tidak ditemukan.");
            Assert.That(config.WalkSpeed, Is.InRange(1f, 3f));
            Assert.That(config.RunSpeed, Is.InRange(3f, 8f));
            Assert.That(config.RunSpeed, Is.GreaterThanOrEqualTo(config.WalkSpeed));
            Assert.That(config.JumpHeight, Is.InRange(0.5f, 2f));
            Assert.That(config.Gravity, Is.GreaterThan(0f));
            Assert.That(config.RotationSpeed, Is.GreaterThan(0f));
        }

        [Test]
        public void Validation_ClampsRunSpeedToAtLeastWalkSpeed()
        {
            var config = PlayerMovementConfigFactory.Create(walkSpeed: 3f, runSpeed: 1f);
            try
            {
                Assert.That(config.RunSpeed, Is.EqualTo(3f));
            }
            finally
            {
                Object.DestroyImmediate(config);
            }
        }

        [Test]
        public void Validation_KeepsMaxFallSpeedPositive()
        {
            var config = PlayerMovementConfigFactory.Create(maxFallSpeed: 0f);
            try
            {
                Assert.That(config.MaxFallSpeed, Is.GreaterThan(0f));
            }
            finally
            {
                Object.DestroyImmediate(config);
            }
        }

        [Test]
        public void Validation_ClampsNegativeValues()
        {
            var config = ScriptableObject.CreateInstance<PlayerMovementConfig>();
            try
            {
                var serialized = new SerializedObject(config);
                serialized.FindProperty("_walkSpeed").floatValue = -1f;
                serialized.FindProperty("_gravity").floatValue = -5f;
                serialized.FindProperty("_airControl").floatValue = 2f;
                serialized.ApplyModifiedPropertiesWithoutUndo();
                config.RunValidation();

                Assert.That(config.WalkSpeed, Is.EqualTo(0f));
                Assert.That(config.Gravity, Is.GreaterThan(0f));
                Assert.That(config.AirControl, Is.EqualTo(1f));
            }
            finally
            {
                Object.DestroyImmediate(config);
            }
        }
    }
}
