using System;
using UnityEngine;

namespace Game.Player
{
    /// <summary>
    /// State gerak karakter berjalan kaki (kecepatan, timer lompat) tanpa MonoBehaviour.
    /// <see cref="Step"/> menghasilkan perpindahan satu frame yang diteruskan ke
    /// <c>CharacterController.Move</c>. Perpindahan dihitung dari rata-rata kecepatan awal dan
    /// akhir langkah (trapesium), yang eksak untuk percepatan konstan, sehingga jarak tempuh dan
    /// tinggi lompatan sama di 30 maupun 144 FPS. Semua method bebas alokasi.
    /// </summary>
    public sealed class PlayerLocomotion
    {
        private readonly PlayerMovementConfig _config;
        private readonly PlayerMovementCalculator _calculator;

        private float _timeSinceGrounded = float.PositiveInfinity;
        private float _timeSinceJumpPressed = float.PositiveInfinity;

        public PlayerLocomotion(PlayerMovementConfig config)
        {
            _config = config != null ? config : throw new ArgumentNullException(nameof(config));
            _calculator = new PlayerMovementCalculator(config);
        }

        /// <summary>Kecepatan horizontal (bidang XZ, m/s).</summary>
        public Vector3 HorizontalVelocity { get; private set; }

        /// <summary>Kecepatan vertikal (m/s, positif = naik).</summary>
        public float VerticalVelocity { get; private set; }

        /// <summary>True pada langkah terakhir yang memulai lompatan.</summary>
        public bool JumpedThisStep { get; private set; }

        /// <summary>Menghitung perpindahan satu frame.</summary>
        /// <param name="isGrounded">Status menapak dari hasil <c>Move</c> frame sebelumnya.</param>
        public Vector3 Step(in PlayerLocomotionInput input, bool isGrounded, float deltaTime)
        {
            JumpedThisStep = false;
            if (deltaTime <= 0f)
            {
                return Vector3.zero;
            }

            _timeSinceGrounded = isGrounded ? 0f : _timeSinceGrounded + deltaTime;
            _timeSinceJumpPressed = input.JumpPressed ? 0f : _timeSinceJumpPressed + deltaTime;

            var previousHorizontal = HorizontalVelocity;
            var target = _calculator.GetTargetHorizontalVelocity(input.Move, input.IsRunning, input.ViewYawDegrees);
            HorizontalVelocity = _calculator.StepHorizontalVelocity(previousHorizontal, target, isGrounded, deltaTime);

            var vertical = VerticalVelocity;
            if (isGrounded && vertical < 0f)
            {
                // Tetap menekan ke bawah agar menempel di tanjakan menurun, tanpa menumpuk kecepatan jatuh.
                vertical = -_config.GroundStickSpeed;
            }

            if (_timeSinceJumpPressed <= _config.JumpBufferTime && _timeSinceGrounded <= _config.CoyoteTime)
            {
                vertical = _calculator.GetJumpVelocity();
                _timeSinceJumpPressed = float.PositiveInfinity;
                _timeSinceGrounded = float.PositiveInfinity;
                JumpedThisStep = true;
            }

            VerticalVelocity = _calculator.StepVerticalVelocity(vertical, deltaTime);

            var averageHorizontal = (previousHorizontal + HorizontalVelocity) * 0.5f;
            var averageVertical = (vertical + VerticalVelocity) * 0.5f;
            return new Vector3(averageHorizontal.x, averageVertical, averageHorizontal.z) * deltaTime;
        }

        /// <summary>Kepala membentur langit-langit: hentikan gerak naik.</summary>
        public void CancelUpwardVelocity()
        {
            VerticalVelocity = Mathf.Min(VerticalVelocity, 0f);
        }

        /// <summary>Hentikan semua gerak (spawn ulang, teleport).</summary>
        public void ResetMotion()
        {
            HorizontalVelocity = Vector3.zero;
            VerticalVelocity = 0f;
            _timeSinceGrounded = float.PositiveInfinity;
            _timeSinceJumpPressed = float.PositiveInfinity;
            JumpedThisStep = false;
        }
    }
}
