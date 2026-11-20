using Game.Core.Events;
using NUnit.Framework;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;

namespace Game.Tests.EditMode.Events
{
    /// <summary>
    /// AC2: Publish di jalur Update tidak beralokasi. Constraint <c>AllocatingGCMemory</c>
    /// memakai Profiler recorder "GC.Alloc", sama dengan kolom GC Alloc di Profiler.
    /// </summary>
    public sealed class EventBusAllocationTests
    {
        private const int SubscriberCount = 8;

        private int _received;
        private float _sum;
        private EventSubscription<TestEvent> _selfRemovingSubscription;

        [SetUp]
        public void SetUp()
        {
            EventBus.ClearAll();
            _received = 0;
            _sum = 0f;
        }

        [TearDown]
        public void TearDown()
        {
            EventBus.ClearAll();
        }

        [Test]
        public void Publish_WithSeveralSubscribers_DoesNotAllocate()
        {
            for (var i = 0; i < SubscriberCount; i++)
            {
                EventBus.Subscribe<TestEvent>(OnTestEvent);
            }

            var evt = new TestEvent(7);
            EventBus.Publish(in evt); // warm-up (JIT, static ctor)

            Assert.That(() => EventBus.Publish(in evt), Is.Not.AllocatingGCMemory());
            Assert.That(_received, Is.GreaterThan(SubscriberCount));
        }

        [Test]
        public void Publish_WithoutSubscribers_DoesNotAllocate()
        {
            var evt = new OtherTestEvent(1f);
            EventBus.Publish(in evt);

            Assert.That(() => EventBus.Publish(in evt), Is.Not.AllocatingGCMemory());
        }

        [Test]
        public void PublishMultipleTypes_DoesNotAllocate()
        {
            EventBus.Subscribe<TestEvent>(OnTestEvent);
            EventBus.Subscribe<OtherTestEvent>(OnOtherTestEvent);
            var testEvent = new TestEvent(1);
            var otherEvent = new OtherTestEvent(0.5f);
            EventBus.Publish(in testEvent);
            EventBus.Publish(in otherEvent);

            Assert.That(() =>
            {
                EventBus.Publish(in testEvent);
                EventBus.Publish(in otherEvent);
            }, Is.Not.AllocatingGCMemory());
            Assert.That(_sum, Is.GreaterThan(0f));
        }

        [Test]
        public void Publish_WhenHandlerUnsubscribesItself_DoesNotAllocate()
        {
            EventBus.Subscribe<TestEvent>(OnTestEvent);
            _selfRemovingSubscription = EventBus.Subscribe<TestEvent>(OnTestEventDisposeSelf);
            EventBus.Subscribe<TestEvent>(OnTestEvent);
            var evt = new TestEvent(1);

            // Warm-up jalur unsubscribe-saat-publish + pemadatan (JIT), lalu pasang ulang.
            EventBus.Publish(in evt);
            _selfRemovingSubscription = EventBus.Subscribe<TestEvent>(OnTestEventDisposeSelf);
            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(3));

            Assert.That(() => EventBus.Publish(in evt), Is.Not.AllocatingGCMemory());
            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(2));
        }

        private void OnTestEventDisposeSelf(in TestEvent evt)
        {
            _selfRemovingSubscription.Dispose();
        }

        private void OnTestEvent(in TestEvent evt)
        {
            _received += evt.Value > 0 ? 1 : 0;
        }

        private void OnOtherTestEvent(in OtherTestEvent evt)
        {
            _sum += evt.Amount;
        }
    }
}
