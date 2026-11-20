using System;
using UnityEngine.InputSystem;

namespace Game.Tests.PlayMode
{
    /// <summary>
    /// Di editor batchmode Game view tidak pernah fokus sehingga input perangkat virtual dialihkan
    /// ke editor. Scope ini mengarahkan semua input ke game selama test, lalu mengembalikan nilai semula.
    /// (Mengganti objek InputSystem.settings tidak dipakai: setter menghancurkan settings lama.)
    /// </summary>
    internal sealed class InputTestSettingsScope : IDisposable
    {
        private readonly InputSettings.BackgroundBehavior _originalBackgroundBehavior;
#if UNITY_EDITOR
        private readonly InputSettings.EditorInputBehaviorInPlayMode _originalEditorBehavior;
#endif

        public InputTestSettingsScope()
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

        public void Dispose()
        {
            var settings = InputSystem.settings;
            settings.backgroundBehavior = _originalBackgroundBehavior;
#if UNITY_EDITOR
            settings.editorInputBehaviorInPlayMode = _originalEditorBehavior;
#endif
        }
    }
}
