using System;
using System.Collections;
using Game.Core.Events;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using Object = UnityEngine.Object;

namespace Game.Tests.PlayMode.Events
{
    /// <summary>AC3: subscriber MonoBehaviour yang di-destroy berhenti menerima event tanpa leak.</summary>
    public sealed class EventBusLifetimeTests
    {
        private const int ToggleCycles = 100;
        private const int LeakProbeCycles = 5000;

        // Tanpa pelepasan registrasi, 5000 siklus menahan ±1 MB (callback info + delegate + box).
        private const long LeakProbeMaxGrowthBytes = 256 * 1024;

        [SetUp]
        public void SetUp()
        {
            EventBus.ClearAll();
        }

        [TearDown]
        public void TearDown()
        {
            EventBus.ClearAll();
        }

        [UnityTest]
        public IEnumerator SubscribeUntilDestroyed_ReleasesSubscriptionWhenDestroyed()
        {
            var gameObject = new GameObject("event-listener");
            var listener = gameObject.AddComponent<EventListenerComponent>();

            EventBus.Publish(new PlayModeTestEvent(1));
            Assert.That(listener.ReceivedCount, Is.EqualTo(1));
            Assert.That(EventBus.SubscriberCount<PlayModeTestEvent>(), Is.EqualTo(1));

            Object.Destroy(gameObject);
            yield return null;

            Assert.That(EventBus.SubscriberCount<PlayModeTestEvent>(), Is.EqualTo(0));
            Assert.DoesNotThrow(() => EventBus.Publish(new PlayModeTestEvent(2)));
            Assert.That(listener.ReceivedCount, Is.EqualTo(1));
        }

        [UnityTest]
        public IEnumerator SubscribeUntilDestroyed_TokenCanBeDisposedEarly()
        {
            var gameObject = new GameObject("event-listener-early");
            var listener = gameObject.AddComponent<EventListenerComponent>();
            var count = 0;
            var subscription = listener.SubscribeUntilDestroyed((in PlayModeTestEvent _) => count++);

            subscription.Dispose();
            EventBus.Publish(new PlayModeTestEvent(1));
            Assert.That(count, Is.EqualTo(0));

            Object.Destroy(gameObject);
            yield return null;

            Assert.That(EventBus.SubscriberCount<PlayModeTestEvent>(), Is.EqualTo(0));
        }

        [UnityTest]
        public IEnumerator EnableDisableCycles_DoNotAccumulateSubscriptions()
        {
            var gameObject = new GameObject("event-listener-toggle");
            var listener = gameObject.AddComponent<ToggleEventListenerComponent>();

            for (var i = 0; i < ToggleCycles; i++)
            {
                listener.enabled = false;
                Assert.That(EventBus.SubscriberCount<PlayModeTestEvent>(), Is.EqualTo(0));
                listener.enabled = true;
                Assert.That(EventBus.SubscriberCount<PlayModeTestEvent>(), Is.EqualTo(1));
            }

            EventBus.Publish(new PlayModeTestEvent(1));
            Assert.That(listener.ReceivedCount, Is.EqualTo(1));

            Object.Destroy(gameObject);
            yield return null;

            Assert.That(EventBus.SubscriberCount<PlayModeTestEvent>(), Is.EqualTo(0));
        }

        [UnityTest]
        public IEnumerator RepeatedSubscribeDispose_DoesNotRetainDestroyRegistrations()
        {
            var gameObject = new GameObject("event-listener-leak-probe");
            var owner = gameObject.AddComponent<EventListenerComponent>();
            GameEventHandler<PlayModeTestEvent> handler = OnProbeEvent;

            // Warm-up: JIT dan pertumbuhan struktur internal sebelum diukur.
            RunSubscribeDisposeCycles(owner, handler, LeakProbeCycles);
            var before = GC.GetTotalMemory(true);

            RunSubscribeDisposeCycles(owner, handler, LeakProbeCycles);
            var after = GC.GetTotalMemory(true);

            Assert.That(after - before, Is.LessThan(LeakProbeMaxGrowthBytes),
                "Registrasi destroyCancellationToken menumpuk setelah Dispose.");
            Assert.That(EventBus.SubscriberCount<PlayModeTestEvent>(), Is.EqualTo(1),
                "Hanya langganan Awake milik EventListenerComponent yang tersisa.");

            Object.Destroy(gameObject);
            yield return null;

            Assert.That(EventBus.SubscriberCount<PlayModeTestEvent>(), Is.EqualTo(0));
        }

        [UnityTest]
        public IEnumerator SubscribeUntilDestroyed_OnDestroyedOwner_ThrowsObjectDisposed()
        {
            var gameObject = new GameObject("event-listener-destroyed");
            var listener = gameObject.AddComponent<EventListenerComponent>();
            Object.Destroy(gameObject);
            yield return null;

            Assert.Throws<ObjectDisposedException>(
                () => listener.SubscribeUntilDestroyed<PlayModeTestEvent>(OnProbeEvent));
            Assert.That(EventBus.SubscriberCount<PlayModeTestEvent>(), Is.EqualTo(0));
        }

        [Test]
        public void SubscribeUntilDestroyed_NullOwner_ThrowsArgumentNull()
        {
            MonoBehaviour owner = null!;

            Assert.Throws<ArgumentNullException>(
                () => owner.SubscribeUntilDestroyed<PlayModeTestEvent>(OnProbeEvent));
        }

        private static void RunSubscribeDisposeCycles(
            MonoBehaviour owner, GameEventHandler<PlayModeTestEvent> handler, int cycles)
        {
            for (var i = 0; i < cycles; i++)
            {
                owner.SubscribeUntilDestroyed(handler).Dispose();
            }
        }

        private static void OnProbeEvent(in PlayModeTestEvent evt)
        {
        }
    }
}
