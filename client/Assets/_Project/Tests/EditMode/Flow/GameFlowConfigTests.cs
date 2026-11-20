using Game.Core.Flow;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Game.Tests.EditMode.Flow
{
    public sealed class GameFlowConfigTests
    {
        private const string ConfigPath = "Assets/_Project/Settings/game-flow-config.asset";

        [Test]
        public void Validate_FixesNegativeLoadingDurationAndEmptySceneNames()
        {
            var config = ScriptableObject.CreateInstance<GameFlowConfig>();
            try
            {
                var serialized = new SerializedObject(config);
                serialized.FindProperty("_minimumLoadingSeconds").floatValue = -1f;
                serialized.FindProperty("_menuSceneName").stringValue = " ";
                serialized.FindProperty("_worldSceneName").stringValue = string.Empty;
                serialized.ApplyModifiedPropertiesWithoutUndo();

                config.RunValidation();

                Assert.That(config.MinimumLoadingSeconds, Is.EqualTo(0f));
                Assert.That(config.MenuSceneName, Is.EqualTo("Menu"));
                Assert.That(config.WorldSceneName, Is.EqualTo("World"));
            }
            finally
            {
                Object.DestroyImmediate(config);
            }
        }

        [Test]
        public void BuildSettings_StartWithBoot_AndContainConfiguredScenes()
        {
            var config = AssetDatabase.LoadAssetAtPath<GameFlowConfig>(ConfigPath);
            Assert.That(config, Is.Not.Null, $"Aset {ConfigPath} tidak ditemukan.");

            var scenes = EditorBuildSettings.scenes;
            Assert.That(scenes.Length, Is.GreaterThanOrEqualTo(3));
            Assert.That(scenes[0].path, Does.EndWith("/Boot.unity"), "Scene index 0 harus Boot.");

            Assert.That(ContainsEnabledScene(scenes, config.MenuSceneName), Is.True, "Scene menu tidak ada di Build Settings.");
            Assert.That(ContainsEnabledScene(scenes, config.WorldSceneName), Is.True, "Scene dunia tidak ada di Build Settings.");
        }

        private static bool ContainsEnabledScene(EditorBuildSettingsScene[] scenes, string sceneName)
        {
            foreach (var scene in scenes)
            {
                if (scene.enabled && scene.path.EndsWith("/" + sceneName + ".unity"))
                {
                    return true;
                }
            }

            return false;
        }
    }
}
