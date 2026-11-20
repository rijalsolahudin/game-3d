using Game.Core.Config;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Game.Tests.EditMode.Config
{
    /// <summary>Semua aset config di Settings/ harus sudah konsisten: validasi tidak boleh mengubah nilainya.</summary>
    public sealed class GameConfigAssetTests
    {
        private const string SettingsFolder = "Assets/_Project/Settings";

        [Test]
        public void AllConfigAssets_AreAlreadyValid()
        {
            var checkedCount = 0;
            foreach (var guid in AssetDatabase.FindAssets("t:ScriptableObject", new[] { SettingsFolder }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (AssetDatabase.LoadAssetAtPath<ScriptableObject>(path) is not GameConfig asset)
                {
                    continue;
                }

                // Validasi salinan agar aset di disk tidak ikut termodifikasi.
                var copy = Object.Instantiate(asset);
                try
                {
                    var before = EditorJsonUtility.ToJson(copy);
                    copy.RunValidation();
                    var after = EditorJsonUtility.ToJson(copy);

                    Assert.That(after, Is.EqualTo(before), $"Aset {path} tidak konsisten dengan Validate().");
                }
                finally
                {
                    Object.DestroyImmediate(copy);
                }

                checkedCount++;
            }

            Assert.That(checkedCount, Is.GreaterThan(0), $"Tidak ada aset GameConfig di {SettingsFolder}.");
        }
    }
}
