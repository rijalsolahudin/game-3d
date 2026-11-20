using System.Collections.Generic;
using System.Text.RegularExpressions;
using Game.Core.Events;
using Game.Core.Flow;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Game.Tests.EditMode.Flow
{
    public sealed class GameStateMachineTests
    {
        private readonly List<GameStateChanged> _received = new();
        private EventSubscription<GameStateChanged> _subscription;

        [SetUp]
        public void SetUp()
        {
            _received.Clear();
            _subscription = EventBus.Subscribe<GameStateChanged>(OnGameStateChanged);
        }

        [TearDown]
        public void TearDown()
        {
            _subscription.Dispose();
        }

        private void OnGameStateChanged(in GameStateChanged evt)
        {
            _received.Add(evt);
        }

        [Test]
        public void StartsInBoot_ByDefault()
        {
            Assert.That(new GameStateMachine().Current, Is.EqualTo(GameState.Boot));
        }

        [Test]
        public void FullHappyPath_BootToMenuToLoadingToPlayingPausedAndBack()
        {
            var machine = new GameStateMachine();

            Assert.That(machine.TryTransitionTo(GameState.Menu), Is.True);
            Assert.That(machine.TryTransitionTo(GameState.Loading), Is.True);
            Assert.That(machine.TryTransitionTo(GameState.Playing), Is.True);
            Assert.That(machine.TryTransitionTo(GameState.Paused), Is.True);
            Assert.That(machine.TryTransitionTo(GameState.Playing), Is.True);
            Assert.That(machine.TryTransitionTo(GameState.Paused), Is.True);
            Assert.That(machine.TryTransitionTo(GameState.Loading), Is.True);
            Assert.That(machine.TryTransitionTo(GameState.Menu), Is.True);

            Assert.That(machine.Current, Is.EqualTo(GameState.Menu));
            Assert.That(_received.Count, Is.EqualTo(8));
        }

        [TestCase(GameState.Boot, GameState.Menu)]
        [TestCase(GameState.Menu, GameState.Loading)]
        [TestCase(GameState.Loading, GameState.Playing)]
        [TestCase(GameState.Loading, GameState.Menu)]
        [TestCase(GameState.Playing, GameState.Paused)]
        [TestCase(GameState.Paused, GameState.Playing)]
        [TestCase(GameState.Paused, GameState.Loading)]
        public void ValidTransition_ChangesStateAndPublishesEvent(GameState from, GameState to)
        {
            var machine = new GameStateMachine(from);

            var result = machine.TryTransitionTo(to);

            Assert.That(result, Is.True);
            Assert.That(machine.Current, Is.EqualTo(to));
            Assert.That(_received.Count, Is.EqualTo(1));
            Assert.That(_received[0].Previous, Is.EqualTo(from));
            Assert.That(_received[0].Current, Is.EqualTo(to));
        }

        [TestCase(GameState.Menu, GameState.Paused)]
        [TestCase(GameState.Menu, GameState.Playing)]
        [TestCase(GameState.Boot, GameState.Playing)]
        [TestCase(GameState.Boot, GameState.Loading)]
        [TestCase(GameState.Boot, GameState.Paused)]
        [TestCase(GameState.Loading, GameState.Paused)]
        [TestCase(GameState.Loading, GameState.Boot)]
        [TestCase(GameState.Playing, GameState.Menu)]
        [TestCase(GameState.Playing, GameState.Loading)]
        [TestCase(GameState.Playing, GameState.Boot)]
        [TestCase(GameState.Paused, GameState.Menu)]
        [TestCase(GameState.Menu, GameState.Boot)]
        [TestCase(GameState.Menu, GameState.Menu)]
        [TestCase(GameState.Playing, GameState.Playing)]
        [TestCase(GameState.Paused, GameState.Paused)]
        public void InvalidTransition_IsRejectedWithWarningAndNoEvent(GameState from, GameState to)
        {
            var machine = new GameStateMachine(from);
            LogAssert.Expect(LogType.Warning, new Regex($"Transisi tidak valid ditolak: {from} → {to}"));

            var result = machine.TryTransitionTo(to);

            Assert.That(result, Is.False);
            Assert.That(machine.Current, Is.EqualTo(from));
            Assert.That(_received, Is.Empty);
        }

        [Test]
        public void TransitionTable_MatchesTryTransition_ForEveryPair()
        {
            var states = (GameState[])System.Enum.GetValues(typeof(GameState));
            foreach (var from in states)
            {
                foreach (var to in states)
                {
                    var machine = new GameStateMachine(from);
                    var expected = GameStateMachine.IsValidTransition(from, to);
                    if (!expected)
                    {
                        LogAssert.Expect(LogType.Warning, new Regex("Transisi tidak valid"));
                    }

                    Assert.That(machine.TryTransitionTo(to), Is.EqualTo(expected), $"{from} → {to}");
                }
            }
        }

        [TestCase(GameState.Boot, false)]
        [TestCase(GameState.Menu, false)]
        [TestCase(GameState.Loading, false)]
        [TestCase(GameState.Playing, true)]
        [TestCase(GameState.Paused, false)]
        public void OnlyPlaying_AllowsGameplayInput(GameState state, bool expected)
        {
            Assert.That(GameStateMachine.AllowsGameplayInput(state), Is.EqualTo(expected));
            Assert.That(new GameStateChanged(GameState.Boot, state).AllowsGameplayInput, Is.EqualTo(expected));
        }
    }
}
