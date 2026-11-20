using UnityEngine;
using UnityEngine.InputSystem;

namespace Game.Player
{
    /// <summary>
    /// Controller karakter third-person berjalan kaki: jalan, lari, lompat, dan orbit kamera.
    /// Input dari action map <c>Player</c> project-wide (ter-gate otomatis saat Paused); gerak lewat
    /// <see cref="CharacterController"/> dengan arah mengikuti yaw kamera. Titik fokus kamera
    /// (child <c>CameraTarget</c>) diputar sesuai yaw/pitch dan diikuti
    /// <c>CinemachineThirdPersonFollow</c> (lihat <see cref="PlayerCameraRig"/>).
    /// Nol alokasi GC per frame.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(CharacterController))]
    public sealed class ThirdPersonController : MonoBehaviour
    {
        // Pivot CharacterController di tengah kapsul; pivot objek di kaki (aturan aset).
        private const float CapsuleCenterFraction = 0.5f;

        // Bukan tuning: nilai bawaan CharacterController (0.001 m) mengabaikan perpindahan kecil per
        // frame di FPS tinggi sehingga karakter "membeku" dan status menapak berkedip. 0 = selalu bergerak.
        private const float MinMoveDistance = 0f;

        [SerializeField] private PlayerMovementConfig _movementConfig = null!;
        [SerializeField] private PlayerCameraConfig _cameraConfig = null!;

        [Tooltip("Titik fokus kamera (child karakter). Rotasinya dikendalikan controller ini.")]
        [SerializeField] private Transform _cameraTarget = null!;

        private CharacterController _characterController = null!;
        private PlayerInputReader? _input;
        private PlayerLocomotion _locomotion = null!;
        private PlayerMovementCalculator _calculator = null!;
        private PlayerLook _look = null!;

        /// <summary>Sudut pandang kamera saat ini.</summary>
        internal PlayerLook Look => _look;

        /// <summary>State gerak saat ini (kecepatan, lompat).</summary>
        internal PlayerLocomotion Locomotion => _locomotion;

        internal PlayerMovementConfig MovementConfig => _movementConfig;

        internal PlayerCameraConfig CameraConfig => _cameraConfig;

        internal Transform CameraTarget => _cameraTarget;

        /// <summary>True bila kapsul menapak setelah langkah terakhir.</summary>
        public bool IsGrounded => _characterController.isGrounded;

        private void Awake()
        {
            _characterController = GetComponent<CharacterController>();
            if (_movementConfig == null || _cameraConfig == null || _cameraTarget == null)
            {
                Debug.LogError("[Player] Config atau camera target belum di-assign di ThirdPersonController.", this);
                enabled = false;
                return;
            }

            ApplyCapsuleSettings();
            _locomotion = new PlayerLocomotion(_movementConfig);
            _calculator = new PlayerMovementCalculator(_movementConfig);
            _look = new PlayerLook(_cameraConfig, transform.eulerAngles.y);
            _cameraTarget.localPosition = new Vector3(0f, _cameraConfig.TargetHeight, 0f);
            ApplyCameraTargetRotation();

            if (!PlayerInputReader.TryCreate(InputSystem.actions, out _input))
            {
                Debug.LogWarning("[Player] Action Player/Move, Look, Sprint, atau Jump tidak ditemukan; input nonaktif.", this);
            }
        }

        private void Update()
        {
            Tick(Time.deltaTime);
        }

        /// <summary>Satu langkah controller. Dipanggil dari <c>Update</c>; terbuka untuk test.</summary>
        internal void Tick(float deltaTime)
        {
            if (deltaTime <= 0f)
            {
                return;
            }

            var move = Vector2.zero;
            var isRunning = false;
            var jumpPressed = false;
            if (_input != null)
            {
                _look.Step(_input.Look, _input.IsLookFromPointer, deltaTime);
                move = _input.Move;
                isRunning = _input.IsRunning;
                jumpPressed = _input.JumpPressedThisFrame;
            }

            var locomotionInput = new PlayerLocomotionInput(move, isRunning, jumpPressed, _look.Yaw);
            var displacement = _locomotion.Step(locomotionInput, _characterController.isGrounded, deltaTime);
            var flags = _characterController.Move(displacement);
            if ((flags & CollisionFlags.Above) != 0)
            {
                _locomotion.CancelUpwardVelocity();
            }

            transform.rotation = _calculator.StepRotation(transform.rotation, _locomotion.HorizontalVelocity, deltaTime);
            ApplyCameraTargetRotation();
        }

        /// <summary>Memindahkan karakter dan mengatur arah pandang (spawn, teleport, test).</summary>
        internal void Teleport(Vector3 position, float yawDegrees, float pitchDegrees)
        {
            _characterController.enabled = false;
            transform.SetPositionAndRotation(position, Quaternion.Euler(0f, yawDegrees, 0f));
            _characterController.enabled = true;
            _locomotion.ResetMotion();
            _look.SetAngles(yawDegrees, pitchDegrees);
            ApplyCameraTargetRotation();
        }

        private void ApplyCapsuleSettings()
        {
            var height = _movementConfig.CapsuleHeight;
            _characterController.height = height;
            _characterController.radius = _movementConfig.CapsuleRadius;
            _characterController.center = new Vector3(0f, height * CapsuleCenterFraction, 0f);
            _characterController.stepOffset = _movementConfig.StepOffset;
            _characterController.slopeLimit = _movementConfig.SlopeLimit;
            _characterController.minMoveDistance = MinMoveDistance;
        }

        private void ApplyCameraTargetRotation()
        {
            // Kamera tidak ikut berputar bersama badan: rotasi dunia ditimpa setiap frame.
            _cameraTarget.rotation = _look.Rotation;
        }
    }
}
