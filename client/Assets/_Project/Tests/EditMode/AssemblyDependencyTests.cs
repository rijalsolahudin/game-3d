using System.Collections.Generic;
using NUnit.Framework;
using UnityEditor.Compilation;

namespace Game.Tests.EditMode
{
    /// <summary>
    /// Menjaga arah dependensi assembly sesuai ARC §2.3:
    /// UI → (Exploration, Vehicles, Player, World) → Core; Save → Net → Core.
    /// </summary>
    public sealed class AssemblyDependencyTests
    {
        private static readonly Dictionary<string, string[]> AllowedReferences = new()
        {
            { "Game.Core", new string[0] },
            { "Game.World", new[] { "Game.Core" } },
            { "Game.Player", new[] { "Game.Core" } },
            { "Game.Vehicles", new[] { "Game.Core" } },
            { "Game.Exploration", new[] { "Game.Core" } },
            { "Game.Net", new[] { "Game.Core" } },
            { "Game.Save", new[] { "Game.Net", "Game.Core" } },
            { "Game.UI", new[] { "Game.Core", "Game.World", "Game.Player", "Game.Vehicles", "Game.Exploration" } },
        };

        private static Dictionary<string, Assembly> LoadGameAssemblies()
        {
            var result = new Dictionary<string, Assembly>();
            foreach (var assembly in CompilationPipeline.GetAssemblies(AssembliesType.Player))
            {
                if (AllowedReferences.ContainsKey(assembly.name))
                {
                    result[assembly.name] = assembly;
                }
            }

            return result;
        }

        [Test]
        public void AllModuleAssembliesExist()
        {
            var assemblies = LoadGameAssemblies();

            foreach (var name in AllowedReferences.Keys)
            {
                Assert.That(assemblies.ContainsKey(name), Is.True, $"Assembly {name} tidak ditemukan.");
            }
        }

        [Test]
        public void ModuleAssembliesOnlyReferenceAllowedGameAssemblies()
        {
            foreach (var pair in LoadGameAssemblies())
            {
                var allowed = new HashSet<string>(AllowedReferences[pair.Key]);
                foreach (var reference in pair.Value.assemblyReferences)
                {
                    if (!reference.name.StartsWith("Game."))
                    {
                        continue;
                    }

                    Assert.That(allowed.Contains(reference.name), Is.True,
                        $"{pair.Key} tidak boleh mereferensikan {reference.name} (ARC §2.3).");
                }
            }
        }
    }
}
