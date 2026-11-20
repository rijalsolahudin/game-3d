using Game.Player;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Game.Tests.EditMode.Player
{
    public sealed class PlayerCameraConfigTests
    {
        private const string DefaultAssetPath = "Assets/_Project/Settings/player-camera-config.asset";

        [Test]
        public void DefaultAsset_ExistsWithPlausibleValues()
        {
            var config = AssetDatabase.LoadAssetAtPath<PlayerCameraConfig>(DefaultAssetPath);

            Assert.That(config, Is.Not.Null, $"Aset {DefaultAssetPath} tidak ditemukan.");
            Assert.That(config.PointerSensitivity, Is.GreaterThan(0f));
            Assert.That(config.StickYawSpeed, Is.GreaterThan(0f));
            Assert.That(config.StickPitchSpeed, Is.GreaterThan(0f));
            Assert.That(config.MinPitch, Is.LessThan(config.MaxPitch));
            Assert.That(config.CameraDistance, Is.InRange(1f, 10f));
            Assert.That(config.CollisionLayers.value, Is.Not.EqualTo(0), "Kamera harus mendeteksi tabrakan.");
            Assert.That(config.CameraRadius, Is.GreaterThan(0f));
        }

        [Test]
        public void Validation_KeepsPitchRangeOrdered()
        {
            var config = ScriptableObject.CreateInstance<PlayerCameraConfig>();
            try
            {
                var serialized = new SerializedObject(config);
                serialized.FindProperty("_minPitch").floatValue = 50f;
                serialized.FindProperty("_maxPitch").floatValue = 10f;
                serialized.FindProperty("_initialPitch").floatValue = -80f;
                serialized.FindProperty("_pointerSensitivity").floatValue = -1f;
                serialized.ApplyModifiedPropertiesWithoutUndo();
                config.RunValidation();

                Assert.That(config.MaxPitch, Is.GreaterThanOrEqualTo(config.MinPitch));
                Assert.That(config.InitialPitch, Is.InRange(config.MinPitch, config.MaxPitch));
                Assert.That(config.PointerSensitivity, Is.EqualTo(0f));
            }
            finally
            {
                Object.DestroyImmediate(config);
            }
        }
    }
}
