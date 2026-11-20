using UnityEngine;

namespace Game.Player
{
    /// <summary>Input gerak satu frame untuk <see cref="PlayerLocomotion"/>.</summary>
    public readonly struct PlayerLocomotionInput
    {
        /// <summary>x = kanan, y = depan relatif arah pandang.</summary>
        public readonly Vector2 Move;
        public readonly bool IsRunning;

        /// <summary>True hanya pada frame tombol lompat ditekan.</summary>
        public readonly bool JumpPressed;

        /// <summary>Yaw kamera (derajat) agar "depan" mengikuti arah pandang.</summary>
        public readonly float ViewYawDegrees;

        public PlayerLocomotionInput(Vector2 move, bool isRunning, bool jumpPressed, float viewYawDegrees)
        {
            Move = move;
            IsRunning = isRunning;
            JumpPressed = jumpPressed;
            ViewYawDegrees = viewYawDegrees;
        }
    }
}
