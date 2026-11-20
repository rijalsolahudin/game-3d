using NUnit.Framework;
using UnityEngine.Rendering;

namespace Game.Tests.PlayMode
{
    /// <summary>
    /// Smoke test: proyek berjalan dengan render pipeline URP aktif (ARC §1.1).
    /// </summary>
    public sealed class RenderPipelineSmokeTests
    {
        [Test]
        public void ScriptableRenderPipelineIsActive()
        {
            Assert.That(GraphicsSettings.currentRenderPipeline, Is.Not.Null);
            Assert.That(GraphicsSettings.currentRenderPipeline.GetType().Name,
                Is.EqualTo("UniversalRenderPipelineAsset"));
        }
    }
}
