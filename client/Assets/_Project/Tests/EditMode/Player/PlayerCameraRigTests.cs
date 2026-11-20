using Game.Player;
using NUnit.Framework;
using UnityEngine;

namespace Game.Tests.EditMode.Player
{
    /// <summary>
    /// IgnoreTag kamera tidak boleh "Untagged": Cinemachine akan mengabaikan semua collider tanpa tag
    /// (bangunan, terrain) sehingga kamera menembus dinding.
    /// </summary>
    public sealed class PlayerCameraRigTests
    {
        private GameObject _root = null!;
        private Transform _target = null!;

        [SetUp]
        public void SetUp()
        {
            _root = new GameObject("Player");
            _target = new GameObject("CameraTarget").transform;
            _target.SetParent(_root.transform, false);
        }

        [TearDown]
        public void TearDown()
        {
            Object.DestroyImmediate(_root);
        }

        [Test]
        public void ResolveIgnoreTag_TaggedRoot_ReturnsRootTag()
        {
            _root.tag = "Player";

            Assert.That(PlayerCameraRig.ResolveIgnoreTag(_target), Is.EqualTo("Player"));
        }

        [Test]
        public void ResolveIgnoreTag_UntaggedRoot_ReturnsEmpty()
        {
            Assert.That(_root.tag, Is.EqualTo("Untagged"));

            Assert.That(PlayerCameraRig.ResolveIgnoreTag(_target), Is.Empty);
        }

        [Test]
        public void ResolveIgnoreTag_TaggedChildButUntaggedRoot_ReturnsEmpty()
        {
            _target.gameObject.tag = "Player";

            Assert.That(PlayerCameraRig.ResolveIgnoreTag(_target), Is.Empty);
        }

        [Test]
        public void ResolveIgnoreTag_NoTarget_ReturnsEmpty()
        {
            Assert.That(PlayerCameraRig.ResolveIgnoreTag(null), Is.Empty);
        }
    }
}
