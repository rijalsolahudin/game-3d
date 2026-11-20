using System;
using UnityEngine;

namespace Game.Player
{
    /// <summary>
    /// Perhitungan gerak karakter yang murni (tanpa MonoBehaviour), semua nilai dibaca dari
    /// <see cref="PlayerMovementConfig"/> setiap pemanggilan sehingga perubahan config di
    /// Inspector langsung berlaku. Dipakai controller karakter (GAME-23) di Update/FixedUpdate;
    /// semua method bebas alokasi.
    /// </summary>
    public sealed class PlayerMovementCalculator
    {
        private readonly PlayerMovementConfig _config;

        public PlayerMovementCalculator(PlayerMovementConfig config)
        {
            _config = config != null ? config : throw new ArgumentNullException(nameof(config));
        }

        /// <summary>
        /// Kecepatan horizontal target (bidang XZ) dari input gerak.
        /// </summary>
        /// <param name="moveInput">Input stik/WASD, x = kanan, y = depan. Magnitudo &gt; 1 dipotong ke 1.</param>
        /// <param name="isRunning">True bila tombol lari ditahan.</param>
        /// <param name="viewYawDegrees">Yaw kamera (derajat) agar "depan" mengikuti arah pandang.</param>
        public Vector3 GetTargetHorizontalVelocity(Vector2 moveInput, bool isRunning, float viewYawDegrees)
        {
            var input = Vector2.ClampMagnitude(moveInput, 1f);
            var speed = isRunning ? _config.RunSpeed : _config.WalkSpeed;
            var local = new Vector3(input.x, 0f, input.y) * speed;
            return Quaternion.Euler(0f, viewYawDegrees, 0f) * local;
        }

        /// <summary>
        /// Satu langkah percepatan/perlambatan kecepatan horizontal menuju target.
        /// </summary>
        public Vector3 StepHorizontalVelocity(Vector3 current, Vector3 target, bool isGrounded, float deltaTime)
        {
            current.y = 0f;
            target.y = 0f;
            var rate = target.sqrMagnitude > current.sqrMagnitude ? _config.Acceleration : _config.Deceleration;
            if (!isGrounded)
            {
                rate *= _config.AirControl;
            }

            return Vector3.MoveTowards(current, target, rate * deltaTime);
        }

        /// <summary>Kecepatan vertikal awal agar puncak lompatan = <see cref="PlayerMovementConfig.JumpHeight"/>.</summary>
        public float GetJumpVelocity()
        {
            return Mathf.Sqrt(2f * _config.Gravity * _config.JumpHeight);
        }

        /// <summary>Menerapkan gravitasi satu langkah, dibatasi kecepatan jatuh maksimum.</summary>
        public float StepVerticalVelocity(float verticalVelocity, float deltaTime)
        {
            return Mathf.Max(verticalVelocity - _config.Gravity * deltaTime, -_config.MaxFallSpeed);
        }

        /// <summary>Memutar badan menghadap arah gerak horizontal dengan kecepatan putar dari config.</summary>
        public Quaternion StepRotation(Quaternion current, Vector3 moveDirection, float deltaTime)
        {
            moveDirection.y = 0f;
            // Arah yang nyaris nol (sisa perlambatan, noise stik) tidak boleh memutar badan.
            if (moveDirection.sqrMagnitude < Vector3.kEpsilon)
            {
                return current;
            }

            var target = Quaternion.LookRotation(moveDirection, Vector3.up);
            return Quaternion.RotateTowards(current, target, _config.RotationSpeed * deltaTime);
        }
    }
}
