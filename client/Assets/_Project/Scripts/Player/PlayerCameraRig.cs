using Unity.Cinemachine;
using UnityEngine;

namespace Game.Player
{
    /// <summary>
    /// Menerapkan <see cref="PlayerCameraConfig"/> ke kamera Cinemachine pemain: jarak/bahu
    /// <see cref="CinemachineThirdPersonFollow"/>, lensa, dan deteksi tabrakan (sphere cast) agar
    /// kamera tidak menembus bangunan atau terrain dan mendekat dengan redaman saat terhalang.
    /// Orbit (yaw/pitch) berasal dari rotasi titik fokus yang diputar <see cref="ThirdPersonController"/>.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(CinemachineCamera), typeof(CinemachineThirdPersonFollow))]
    public sealed class PlayerCameraRig : MonoBehaviour
    {
        // CinemachineThirdPersonFollow.CameraSide: 1 = bahu kanan (bukan tuning; offset ada di config).
        private const float RightShoulderSide = 1f;

        // Tag bawaan Unity untuk objek tanpa tag (identitas, bukan tuning).
        private const string UntaggedTag = "Untagged";

        [SerializeField] private PlayerCameraConfig _config = null!;

        private void Awake()
        {
            if (_config == null)
            {
                Debug.LogError("[Player] PlayerCameraConfig belum di-assign di PlayerCameraRig.", this);
                enabled = false;
                return;
            }

            Apply(GetComponent<CinemachineCamera>(), GetComponent<CinemachineThirdPersonFollow>());
        }

        /// <summary>
        /// Tag yang diabaikan sphere cast kamera: tag root target. Mengembalikan string kosong bila target
        /// tidak ada atau root-nya "Untagged"; mengabaikan "Untagged" berarti mengabaikan hampir semua
        /// collider (bangunan, terrain) sehingga kamera menembus dinding.
        /// </summary>
        internal static string ResolveIgnoreTag(Transform? target)
        {
            if (target == null)
            {
                return string.Empty;
            }

            var tag = target.root.tag;
            return tag == UntaggedTag ? string.Empty : tag;
        }

        private void Apply(CinemachineCamera cinemachineCamera, CinemachineThirdPersonFollow follow)
        {
            var lens = cinemachineCamera.Lens;
            lens.FieldOfView = _config.FieldOfView;
            lens.NearClipPlane = _config.NearClipPlane;
            cinemachineCamera.Lens = lens;

            follow.ShoulderOffset = _config.ShoulderOffset;
            follow.VerticalArmLength = _config.VerticalArmLength;
            follow.CameraSide = RightShoulderSide;
            follow.CameraDistance = _config.CameraDistance;
            follow.Damping = _config.FollowDamping;

            var target = cinemachineCamera.Follow;
            var obstacles = follow.AvoidObstacles;
            obstacles.Enabled = true;
            obstacles.CollisionFilter = _config.CollisionLayers;
            // Kapsul pemain sendiri tidak boleh dianggap penghalang.
            obstacles.IgnoreTag = ResolveIgnoreTag(target);
            if (obstacles.IgnoreTag.Length == 0)
            {
                Debug.LogError("[Player] Root target kamera tidak ber-tag (mis. \"Player\"); kapsul pemain bisa " +
                               "dianggap penghalang kamera. Beri tag pada root pemain.", this);
            }
            obstacles.CameraRadius = _config.CameraRadius;
            obstacles.DampingIntoCollision = _config.DampingIntoCollision;
            obstacles.DampingFromCollision = _config.DampingFromCollision;
            follow.AvoidObstacles = obstacles;
        }
    }
}
