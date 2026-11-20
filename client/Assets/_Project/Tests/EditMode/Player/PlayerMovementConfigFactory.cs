using Game.Player;
using UnityEditor;
using UnityEngine;

namespace Game.Tests.EditMode.Player
{
    /// <summary>Membuat <see cref="PlayerMovementConfig"/> sementara dengan nilai tertentu untuk test.</summary>
    internal static class PlayerMovementConfigFactory
    {
        public static PlayerMovementConfig Create(
            float walkSpeed = 2f,
            float runSpeed = 5f,
            float acceleration = 12f,
            float deceleration = 16f,
            float airControl = 0.3f,
            float jumpHeight = 1.2f,
            float gravity = 9.81f,
            float maxFallSpeed = 50f,
            float rotationSpeed = 720f)
        {
            var config = ScriptableObject.CreateInstance<PlayerMovementConfig>();
            var serialized = new SerializedObject(config);
            serialized.FindProperty("_walkSpeed").floatValue = walkSpeed;
            serialized.FindProperty("_runSpeed").floatValue = runSpeed;
            serialized.FindProperty("_acceleration").floatValue = acceleration;
            serialized.FindProperty("_deceleration").floatValue = deceleration;
            serialized.FindProperty("_airControl").floatValue = airControl;
            serialized.FindProperty("_jumpHeight").floatValue = jumpHeight;
            serialized.FindProperty("_gravity").floatValue = gravity;
            serialized.FindProperty("_maxFallSpeed").floatValue = maxFallSpeed;
            serialized.FindProperty("_rotationSpeed").floatValue = rotationSpeed;
            serialized.ApplyModifiedPropertiesWithoutUndo();
            config.RunValidation();
            return config;
        }
    }
}
