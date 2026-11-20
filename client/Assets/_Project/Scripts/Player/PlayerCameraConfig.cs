using Game.Core.Config;
using UnityEngine;

namespace Game.Player
{
    /// <summary>
    /// Tuning kamera third-person pemain berjalan kaki (orbit, sensitivitas, rig Cinemachine, tabrakan).
    /// Aset default: <c>Assets/_Project/Settings/player-camera-config.asset</c>.
    /// Satuan SI: meter, detik, derajat.
    /// </summary>
    [CreateAssetMenu(menuName = "Game/Config/Player Camera", fileName = "player-camera-config")]
    public sealed class PlayerCameraConfig : GameConfig
    {
        // Batas validasi (bukan tuning): pitch di ±90° membuat arah "depan" kamera tidak terdefinisi.
        private const float PitchLimit = 89f;

        // Batas validasi: rentang field CinemachineThirdPersonFollow / lensa kamera.
        private const float MinCameraRadius = 0.001f;
        private const float MaxCameraRadius = 1f;
        private const float MaxCollisionDamping = 10f;
        private const float MinFieldOfView = 1f;
        private const float MaxFieldOfView = 179f;
        private const float MinNearClipPlane = 0.01f;

        [Header("Sensitivitas")]
        [Tooltip("Putaran kamera per piksel gerak mouse (derajat/piksel).")]
        [SerializeField, Min(0f)] private float _pointerSensitivity = 0.12f;

        [Tooltip("Kecepatan putar horizontal saat stik kanan gamepad didorong penuh (derajat/detik).")]
        [SerializeField, Min(0f)] private float _stickYawSpeed = 200f;

        [Tooltip("Kecepatan putar vertikal saat stik kanan gamepad didorong penuh (derajat/detik).")]
        [SerializeField, Min(0f)] private float _stickPitchSpeed = 120f;

        [Tooltip("Balik sumbu vertikal (dorong ke atas = kamera menunduk).")]
        [SerializeField] private bool _invertPitch;

        [Header("Orbit")]
        [Tooltip("Pitch minimum (derajat, negatif = kamera di bawah, menengadah).")]
        [SerializeField, Range(-PitchLimit, PitchLimit)] private float _minPitch = -35f;

        [Tooltip("Pitch maksimum (derajat, positif = kamera di atas, menunduk).")]
        [SerializeField, Range(-PitchLimit, PitchLimit)] private float _maxPitch = 70f;

        [Tooltip("Pitch awal saat pemain muncul (derajat).")]
        [SerializeField, Range(-PitchLimit, PitchLimit)] private float _initialPitch = 15f;

        [Header("Rig (CinemachineThirdPersonFollow)")]
        [Tooltip("Tinggi titik fokus kamera dari kaki karakter (m).")]
        [SerializeField, Min(0f)] private float _targetHeight = 1.5f;

        [Tooltip("Offset bahu dari titik fokus (m). X = geser samping, Y = naik.")]
        [SerializeField] private Vector3 _shoulderOffset = new(0.4f, 0.2f, 0f);

        [Tooltip("Panjang lengan vertikal dari bahu ke 'tangan' kamera (m).")]
        [SerializeField] private float _verticalArmLength = 0.3f;

        [Tooltip("Jarak kamera di belakang titik fokus saat tidak terhalang (m).")]
        [SerializeField, Min(0f)] private float _cameraDistance = 4f;

        [Tooltip("Redaman ikut target per sumbu kamera (detik). Kecil = lebih responsif.")]
        [SerializeField] private Vector3 _followDamping = new(0.1f, 0.25f, 0.15f);

        [Tooltip("Field of view vertikal (derajat).")]
        [SerializeField, Range(MinFieldOfView, MaxFieldOfView)] private float _fieldOfView = 60f;

        [Tooltip("Near clip plane (m). Kecil agar kamera yang mepet dinding tidak memotong geometri.")]
        [SerializeField, Min(MinNearClipPlane)] private float _nearClipPlane = 0.1f;

        [Header("Tabrakan kamera")]
        [Tooltip("Layer yang menghalangi kamera (bangunan, terrain).")]
        [SerializeField] private LayerMask _collisionLayers = ~0;

        [Tooltip("Jarak minimum kamera ke penghalang (m).")]
        [SerializeField, Range(MinCameraRadius, MaxCameraRadius)] private float _cameraRadius = 0.25f;

        [Tooltip("Redaman saat kamera maju karena terhalang (detik). Kecil agar tidak sempat menembus dinding.")]
        [SerializeField, Range(0f, MaxCollisionDamping)] private float _dampingIntoCollision = 0.05f;

        [Tooltip("Redaman saat kamera kembali ke jarak normal setelah tidak terhalang (detik).")]
        [SerializeField, Range(0f, MaxCollisionDamping)] private float _dampingFromCollision = 0.4f;

        public float PointerSensitivity => _pointerSensitivity;
        public float StickYawSpeed => _stickYawSpeed;
        public float StickPitchSpeed => _stickPitchSpeed;
        public bool InvertPitch => _invertPitch;
        public float MinPitch => _minPitch;
        public float MaxPitch => _maxPitch;
        public float InitialPitch => _initialPitch;
        public float TargetHeight => _targetHeight;
        public Vector3 ShoulderOffset => _shoulderOffset;
        public float VerticalArmLength => _verticalArmLength;
        public float CameraDistance => _cameraDistance;
        public Vector3 FollowDamping => _followDamping;
        public float FieldOfView => _fieldOfView;
        public float NearClipPlane => _nearClipPlane;
        public LayerMask CollisionLayers => _collisionLayers;
        public float CameraRadius => _cameraRadius;
        public float DampingIntoCollision => _dampingIntoCollision;
        public float DampingFromCollision => _dampingFromCollision;

        protected override void Validate()
        {
            _pointerSensitivity = Mathf.Max(0f, _pointerSensitivity);
            _stickYawSpeed = Mathf.Max(0f, _stickYawSpeed);
            _stickPitchSpeed = Mathf.Max(0f, _stickPitchSpeed);
            _minPitch = Mathf.Clamp(_minPitch, -PitchLimit, PitchLimit);
            _maxPitch = Mathf.Clamp(_maxPitch, _minPitch, PitchLimit);
            _initialPitch = Mathf.Clamp(_initialPitch, _minPitch, _maxPitch);
            _targetHeight = Mathf.Max(0f, _targetHeight);
            _cameraDistance = Mathf.Max(0f, _cameraDistance);
            _followDamping = Vector3.Max(Vector3.zero, _followDamping);
            _fieldOfView = Mathf.Clamp(_fieldOfView, MinFieldOfView, MaxFieldOfView);
            _nearClipPlane = Mathf.Max(MinNearClipPlane, _nearClipPlane);
            _cameraRadius = Mathf.Clamp(_cameraRadius, MinCameraRadius, MaxCameraRadius);
            _dampingIntoCollision = Mathf.Clamp(_dampingIntoCollision, 0f, MaxCollisionDamping);
            _dampingFromCollision = Mathf.Clamp(_dampingFromCollision, 0f, MaxCollisionDamping);
        }
    }
}
