using System;
using UnityEngine;

namespace Game.Player
{
    /// <summary>
    /// Sudut pandang kamera orbit (yaw/pitch) yang murni, digerakkan input Look.
    /// Mouse menghasilkan delta piksel per frame (tidak dikali deltaTime), stik gamepad
    /// menghasilkan laju (dikali deltaTime) sehingga keduanya konsisten di semua frame rate.
    /// Semua method bebas alokasi.
    /// </summary>
    public sealed class PlayerLook
    {
        // Satu putaran penuh (bukan tuning): yaw dinormalisasi ke [0, 360).
        private const float FullTurnDegrees = 360f;

        private readonly PlayerCameraConfig _config;

        public PlayerLook(PlayerCameraConfig config, float initialYawDegrees)
        {
            _config = config != null ? config : throw new ArgumentNullException(nameof(config));
            Yaw = Mathf.Repeat(initialYawDegrees, FullTurnDegrees);
            Pitch = Mathf.Clamp(config.InitialPitch, config.MinPitch, config.MaxPitch);
        }

        /// <summary>Arah horizontal pandangan (derajat, 0 = utara/+Z, 90 = timur/+X).</summary>
        public float Yaw { get; private set; }

        /// <summary>Kemiringan pandangan (derajat, positif = menunduk).</summary>
        public float Pitch { get; private set; }

        /// <summary>Rotasi titik fokus kamera; diikuti CinemachineThirdPersonFollow.</summary>
        public Quaternion Rotation => Quaternion.Euler(Pitch, Yaw, 0f);

        /// <summary>Menerapkan satu frame input Look.</summary>
        /// <param name="lookInput">x = kanan, y = atas.</param>
        /// <param name="isPointerDelta">True bila input berupa delta mouse (piksel per frame).</param>
        public void Step(Vector2 lookInput, bool isPointerDelta, float deltaTime)
        {
            float yawDelta;
            float pitchDelta;
            if (isPointerDelta)
            {
                yawDelta = lookInput.x * _config.PointerSensitivity;
                pitchDelta = lookInput.y * _config.PointerSensitivity;
            }
            else
            {
                yawDelta = lookInput.x * _config.StickYawSpeed * deltaTime;
                pitchDelta = lookInput.y * _config.StickPitchSpeed * deltaTime;
            }

            // Input "atas" menengadah = pitch berkurang, kecuali sumbu dibalik.
            if (!_config.InvertPitch)
            {
                pitchDelta = -pitchDelta;
            }

            SetAngles(Yaw + yawDelta, Pitch + pitchDelta);
        }

        /// <summary>Mengatur sudut langsung (spawn, teleport, test), tetap dalam batas config.</summary>
        public void SetAngles(float yawDegrees, float pitchDegrees)
        {
            Yaw = Mathf.Repeat(yawDegrees, FullTurnDegrees);
            Pitch = Mathf.Clamp(pitchDegrees, _config.MinPitch, _config.MaxPitch);
        }
    }
}
