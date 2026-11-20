using Game.Core.Config;
using UnityEngine;

namespace Game.Player
{
    /// <summary>
    /// Tuning gerak karakter pemain berjalan kaki. Aset default:
    /// <c>Assets/_Project/Settings/player-movement-config.asset</c>.
    /// Satuan SI: meter, detik, derajat.
    /// </summary>
    [CreateAssetMenu(menuName = "Game/Config/Player Movement", fileName = "player-movement-config")]
    public sealed class PlayerMovementConfig : GameConfig
    {
        // Batas validasi (bukan tuning): gravitasi nol membuat lompatan tak pernah turun.
        private const float MinGravity = 0.01f;

        // Batas validasi: kecepatan jatuh maksimum nol membuat karakter melayang tanpa jatuh.
        private const float MinMaxFallSpeed = 0.1f;

        [Header("Kecepatan")]
        [Tooltip("Kecepatan jalan (m/s). Manusia rata-rata ±1.4–2 m/s.")]
        [SerializeField, Min(0f)] private float _walkSpeed = 2f;

        [Tooltip("Kecepatan lari (m/s). Tidak boleh lebih kecil dari kecepatan jalan.")]
        [SerializeField, Min(0f)] private float _runSpeed = 5f;

        [Tooltip("Percepatan menuju kecepatan target saat ada input (m/s²).")]
        [SerializeField, Min(0f)] private float _acceleration = 12f;

        [Tooltip("Perlambatan saat input dilepas (m/s²).")]
        [SerializeField, Min(0f)] private float _deceleration = 16f;

        [Tooltip("Pengali percepatan/perlambatan saat di udara (0 = tidak bisa dikendalikan, 1 = sama dengan di tanah).")]
        [SerializeField, Range(0f, 1f)] private float _airControl = 0.3f;

        [Header("Lompat & gravitasi")]
        [Tooltip("Tinggi puncak lompatan (m).")]
        [SerializeField, Min(0f)] private float _jumpHeight = 1.2f;

        [Tooltip("Besar percepatan gravitasi ke bawah (m/s²).")]
        [SerializeField, Min(MinGravity)] private float _gravity = 9.81f;

        [Tooltip("Batas kecepatan jatuh (m/s).")]
        [SerializeField, Min(MinMaxFallSpeed)] private float _maxFallSpeed = 50f;

        [Header("Rotasi")]
        [Tooltip("Kecepatan putar badan menghadap arah gerak (derajat/detik).")]
        [SerializeField, Min(0f)] private float _rotationSpeed = 720f;

        public float WalkSpeed => _walkSpeed;
        public float RunSpeed => _runSpeed;
        public float Acceleration => _acceleration;
        public float Deceleration => _deceleration;
        public float AirControl => _airControl;
        public float JumpHeight => _jumpHeight;
        public float Gravity => _gravity;
        public float MaxFallSpeed => _maxFallSpeed;
        public float RotationSpeed => _rotationSpeed;

        protected override void Validate()
        {
            _walkSpeed = Mathf.Max(0f, _walkSpeed);
            _runSpeed = Mathf.Max(_walkSpeed, _runSpeed);
            _acceleration = Mathf.Max(0f, _acceleration);
            _deceleration = Mathf.Max(0f, _deceleration);
            _airControl = Mathf.Clamp01(_airControl);
            _jumpHeight = Mathf.Max(0f, _jumpHeight);
            _gravity = Mathf.Max(MinGravity, _gravity);
            _maxFallSpeed = Mathf.Max(MinMaxFallSpeed, _maxFallSpeed);
            _rotationSpeed = Mathf.Max(0f, _rotationSpeed);
        }
    }
}
