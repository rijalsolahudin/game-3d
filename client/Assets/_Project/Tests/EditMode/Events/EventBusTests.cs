using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using Game.Core.Events;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Game.Tests.EditMode.Events
{
    public sealed class EventBusTests
    {
        private readonly List<string> _calls = new();

        [SetUp]
        public void SetUp()
        {
            // ClearAll tidak mengecilkan kapasitas; test resize memakai ResizeTestEvent khusus.
            EventBus.ClearAll();
            _calls.Clear();
        }

        [TearDown]
        public void TearDown()
        {
            EventBus.ClearAll();
        }

        [Test]
        public void Publish_DeliversEventToAllSubscribersInOrder()
        {
            var received = new List<int>();
            EventBus.Subscribe((in TestEvent e) => received.Add(e.Value));
            EventBus.Subscribe((in TestEvent e) => received.Add(e.Value * 10));

            EventBus.Publish(new TestEvent(3));

            Assert.That(received, Is.EqualTo(new[] { 3, 30 }));
        }

        [Test]
        public void Publish_WithoutSubscribers_DoesNothing()
        {
            Assert.DoesNotThrow(() => EventBus.Publish(new TestEvent(1)));
        }

        [Test]
        public void Publish_OnlyReachesSubscribersOfSameType()
        {
            var testCount = 0;
            var otherCount = 0;
            EventBus.Subscribe((in TestEvent _) => testCount++);
            EventBus.Subscribe((in OtherTestEvent _) => otherCount++);

            EventBus.Publish(new OtherTestEvent(1f));

            Assert.That(testCount, Is.EqualTo(0));
            Assert.That(otherCount, Is.EqualTo(1));
        }

        [Test]
        public void Subscribe_NullHandler_Throws()
        {
            Assert.Throws<ArgumentNullException>(() => EventBus.Subscribe<TestEvent>(null!));
        }

        [Test]
        public void DisposeToken_StopsDelivery()
        {
            var count = 0;
            var subscription = EventBus.Subscribe((in TestEvent _) => count++);

            EventBus.Publish(new TestEvent(1));
            subscription.Dispose();
            EventBus.Publish(new TestEvent(2));

            Assert.That(count, Is.EqualTo(1));
            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(0));
        }

        [Test]
        public void DisposeToken_Twice_OnlyRemovesOwnSubscription()
        {
            GameEventHandler<TestEvent> handler = OnTestEventRecord;
            var first = EventBus.Subscribe(handler);
            EventBus.Subscribe(handler);

            first.Dispose();
            first.Dispose();
            EventBus.Publish(new TestEvent(1));

            Assert.That(_calls.Count, Is.EqualTo(1));
        }

        [Test]
        public void DefaultToken_DisposeIsNoOp()
        {
            EventBus.Subscribe<TestEvent>(OnTestEventRecord);
            var empty = default(EventSubscription<TestEvent>);

            Assert.That(empty.IsValid, Is.False);
            empty.Dispose();

            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(1));
        }

        [Test]
        public void Unsubscribe_ByHandler_StopsDelivery()
        {
            EventBus.Subscribe<TestEvent>(OnTestEventRecord);

            var removed = EventBus.Unsubscribe<TestEvent>(OnTestEventRecord);
            EventBus.Publish(new TestEvent(1));

            Assert.That(removed, Is.True);
            Assert.That(_calls, Is.Empty);
            Assert.That(EventBus.Unsubscribe<TestEvent>(OnTestEventRecord), Is.False);
        }

        [Test]
        public void UnsubscribeSelf_DuringPublish_IsSafeAndOthersStillReceive()
        {
            var subscription = default(EventSubscription<TestEvent>);
            var selfCount = 0;
            var otherCount = 0;
            subscription = EventBus.Subscribe((in TestEvent _) =>
            {
                selfCount++;
                subscription.Dispose();
            });
            EventBus.Subscribe((in TestEvent _) => otherCount++);

            EventBus.Publish(new TestEvent(1));
            EventBus.Publish(new TestEvent(2));

            Assert.That(selfCount, Is.EqualTo(1));
            Assert.That(otherCount, Is.EqualTo(2));
            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(1));
        }

        [Test]
        public void UnsubscribeLaterHandler_DuringPublish_SkipsItImmediately()
        {
            var laterCount = 0;
            var later = default(EventSubscription<TestEvent>);
            EventBus.Subscribe((in TestEvent _) => later.Dispose());
            later = EventBus.Subscribe((in TestEvent _) => laterCount++);

            EventBus.Publish(new TestEvent(1));

            Assert.That(laterCount, Is.EqualTo(0));
        }

        [Test]
        public void SubscribeDuringPublish_ReceivesFromNextPublish()
        {
            var lateCount = 0;
            var added = false;
            EventBus.Subscribe((in TestEvent _) =>
            {
                if (added)
                {
                    return;
                }

                added = true;
                EventBus.Subscribe((in TestEvent _) => lateCount++);
            });

            EventBus.Publish(new TestEvent(1));
            Assert.That(lateCount, Is.EqualTo(0));

            EventBus.Publish(new TestEvent(2));
            Assert.That(lateCount, Is.EqualTo(1));
        }

        [Test]
        public void NestedPublish_DeliversToAll()
        {
            var otherCount = 0;
            EventBus.Subscribe((in TestEvent e) => EventBus.Publish(new OtherTestEvent(e.Value)));
            EventBus.Subscribe((in OtherTestEvent _) => otherCount++);

            EventBus.Publish(new TestEvent(5));

            Assert.That(otherCount, Is.EqualTo(1));
        }

        [Test]
        public void HandlerException_IsLoggedAndDoesNotStopOtherHandlers()
        {
            var count = 0;
            EventBus.Subscribe((in TestEvent _) => throw new InvalidOperationException("boom"));
            EventBus.Subscribe((in TestEvent _) => count++);

            LogAssert.Expect(LogType.Exception, new Regex("boom"));
            EventBus.Publish(new TestEvent(1));

            Assert.That(count, Is.EqualTo(1));
        }

        [Test]
        public void DestroyedUnityObjectSubscriber_IsRemovedAutomatically()
        {
            var subscriber = ScriptableObject.CreateInstance<UnityObjectSubscriber>();
            EventBus.Subscribe<TestEvent>(subscriber.OnTestEvent);
            EventBus.Publish(new TestEvent(1));
            Assert.That(subscriber.ReceivedCount, Is.EqualTo(1));

            UnityEngine.Object.DestroyImmediate(subscriber);
            LogAssert.Expect(LogType.Warning, new Regex(@"\[EventBus\]"));
            EventBus.Publish(new TestEvent(2));

            Assert.That(subscriber.ReceivedCount, Is.EqualTo(1));
            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(0));
        }

        [Test]
        public void ClearAll_RemovesSubscribersOfEveryType()
        {
            EventBus.Subscribe<TestEvent>(OnTestEventRecord);
            EventBus.Subscribe((in OtherTestEvent _) => { });

            EventBus.ClearAll();

            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(0));
            Assert.That(EventBus.SubscriberCount<OtherTestEvent>(), Is.EqualTo(0));
        }

        [Test]
        public void ManySubscribers_GrowAndShrinkCorrectly()
        {
            const int total = 20;
            var subscriptions = new EventSubscription<TestEvent>[total];
            var count = 0;
            for (var i = 0; i < total; i++)
            {
                subscriptions[i] = EventBus.Subscribe((in TestEvent _) => count++);
            }

            for (var i = 0; i < total; i += 2)
            {
                subscriptions[i].Dispose();
            }

            EventBus.Publish(new TestEvent(1));

            Assert.That(count, Is.EqualTo(total / 2));
            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(total / 2));
        }

        [Test]
        public void ClearAll_InsideHandler_StopsRemainingHandlersAndAllowsResubscribe()
        {
            var laterCount = 0;
            EventBus.Subscribe((in TestEvent _) => EventBus.ClearAll());
            EventBus.Subscribe((in TestEvent _) => laterCount++);

            EventBus.Publish(new TestEvent(1));

            Assert.That(laterCount, Is.EqualTo(0));
            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(0));

            var newCount = 0;
            EventBus.Subscribe((in TestEvent _) => newCount++);
            EventBus.Publish(new TestEvent(2));

            Assert.That(newCount, Is.EqualTo(1));
            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(1));
        }

        [Test]
        public void NestedPublishOfSameType_WhileUnsubscribing_KeepsDeliveryConsistent()
        {
            var bValues = new List<int>();
            var cValues = new List<int>();
            var bSubscription = default(EventSubscription<TestEvent>);
            EventBus.Subscribe((in TestEvent e) =>
            {
                if (e.Value == 1)
                {
                    EventBus.Publish(new TestEvent(2));
                }
            });
            bSubscription = EventBus.Subscribe((in TestEvent e) =>
            {
                bValues.Add(e.Value);
                bSubscription.Dispose();
            });
            EventBus.Subscribe((in TestEvent e) => cValues.Add(e.Value));

            EventBus.Publish(new TestEvent(1));

            Assert.That(bValues, Is.EqualTo(new[] { 2 }));
            Assert.That(cValues, Is.EqualTo(new[] { 2, 1 }));
            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(2));

            EventBus.Publish(new TestEvent(3));
            Assert.That(bValues, Is.EqualTo(new[] { 2 }));
            Assert.That(cValues, Is.EqualTo(new[] { 2, 1, 3 }));
        }

        [Test]
        public void SubscribeInsideHandler_ThatResizesArray_DeliversCorrectly()
        {
            var initialCapacity = EventChannel<ResizeTestEvent>.Capacity;
            var calls = new int[initialCapacity + 1];
            var added = false;

            EventBus.Subscribe((in ResizeTestEvent _) =>
            {
                calls[0]++;
                if (added)
                {
                    return;
                }

                added = true;
                EventBus.Subscribe((in ResizeTestEvent _) => calls[initialCapacity]++);
            });
            for (var i = 1; i < initialCapacity; i++)
            {
                var index = i;
                EventBus.Subscribe((in ResizeTestEvent _) => calls[index]++);
            }

            Assert.That(EventBus.SubscriberCount<ResizeTestEvent>(), Is.EqualTo(initialCapacity),
                "Channel harus penuh agar subscribe di dalam handler memicu Array.Resize.");

            EventBus.Publish(new ResizeTestEvent());

            Assert.That(EventChannel<ResizeTestEvent>.Capacity, Is.GreaterThan(initialCapacity));
            for (var i = 0; i < initialCapacity; i++)
            {
                Assert.That(calls[i], Is.EqualTo(1), $"Handler {i} pada publish pertama.");
            }

            Assert.That(calls[initialCapacity], Is.EqualTo(0));

            EventBus.Publish(new ResizeTestEvent());

            for (var i = 0; i <= initialCapacity; i++)
            {
                Assert.That(calls[i], Is.EqualTo(i == initialCapacity ? 1 : 2), $"Handler {i} pada publish kedua.");
            }
        }

        [Test]
        public void StaleTokenAfterClearAll_DoesNotRemoveNewSubscription()
        {
            var staleSubscription = EventBus.Subscribe<TestEvent>(OnTestEventRecord);
            EventBus.ClearAll();
            EventBus.Subscribe<TestEvent>(OnTestEventRecord);

            staleSubscription.Dispose();
            EventBus.Publish(new TestEvent(1));

            Assert.That(EventBus.SubscriberCount<TestEvent>(), Is.EqualTo(1));
            Assert.That(_calls.Count, Is.EqualTo(1));
        }

        private void OnTestEventRecord(in TestEvent evt)
        {
            _calls.Add("record");
        }
    }
}
