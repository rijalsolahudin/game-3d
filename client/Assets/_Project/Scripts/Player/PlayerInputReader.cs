using UnityEngine;
using UnityEngine.InputSystem;

namespace Game.Player
{
    /// <summary>
    /// Membaca action map <c>Player</c> dari project-wide actions (<see cref="InputSystem.actions"/>).
    /// Map ini di-enable/disable oleh <c>GameFlowController</c> sesuai state, sehingga saat Paused
    /// semua nilai terbaca nol tanpa pengecekan tambahan. Satu map untuk keyboard-mouse dan gamepad.
    /// Pembacaan bebas alokasi.
    /// </summary>
    public sealed class PlayerInputReader
    {
        // Identitas action di input-actions.inputactions (bukan tuning).
        private const string MoveActionName = "Player/Move";
        private const string LookActionName = "Player/Look";
        private const string SprintActionName = "Player/Sprint";
        private const string JumpActionName = "Player/Jump";

        private readonly InputAction _move;
        private readonly InputAction _look;
        private readonly InputAction _sprint;
        private readonly InputAction _jump;

        private PlayerInputReader(InputAction move, InputAction look, InputAction sprint, InputAction jump)
        {
            _move = move;
            _look = look;
            _sprint = sprint;
            _jump = jump;
        }

        /// <summary>Mencari semua action yang dibutuhkan. False bila asset atau salah satu action tidak ada.</summary>
        public static bool TryCreate(InputActionAsset? actions, out PlayerInputReader? reader)
        {
            reader = null;
            if (actions == null)
            {
                return false;
            }

            var move = actions.FindAction(MoveActionName);
            var look = actions.FindAction(LookActionName);
            var sprint = actions.FindAction(SprintActionName);
            var jump = actions.FindAction(JumpActionName);
            if (move == null || look == null || sprint == null || jump == null)
            {
                return false;
            }

            reader = new PlayerInputReader(move, look, sprint, jump);
            return true;
        }

        public Vector2 Move => _move.ReadValue<Vector2>();

        public Vector2 Look => _look.ReadValue<Vector2>();

        /// <summary>
        /// True bila Look berasal dari pointer (delta piksel per frame); false untuk stik (laju).
        /// </summary>
        public bool IsLookFromPointer
        {
            get
            {
                var control = _look.activeControl;
                return control != null && control.device is Pointer;
            }
        }

        public bool IsRunning => _sprint.IsPressed();

        public bool JumpPressedThisFrame => _jump.WasPressedThisFrame();
    }
}
