using System;
using System.Threading;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Game.Core.Flow
{
    /// <summary>
    /// Memuat scene secara async dengan <see cref="Awaitable"/> sehingga main thread tetap
    /// merender frame selama pemuatan (tidak membeku).
    /// </summary>
    public static class SceneLoader
    {
        // Konstanta API Unity (bukan tuning): progress AsyncOperation berhenti di 0.9 selama
        // allowSceneActivation = false, artinya data scene sudah termuat dan siap diaktifkan.
        private const float ReadyForActivationProgress = 0.9f;

        /// <summary>
        /// Memuat <paramref name="sceneName"/> menggantikan scene aktif (mode Single). Aktivasi
        /// ditahan sampai data termuat dan <paramref name="minimumSeconds"/> (waktu nyata) lewat.
        /// </summary>
        /// <exception cref="ArgumentException">Scene tidak ada di Build Settings.</exception>
        /// <exception cref="OperationCanceledException"><paramref name="cancellationToken"/> dibatalkan.</exception>
        public static async Awaitable LoadSingleAsync(string sceneName, float minimumSeconds,
            CancellationToken cancellationToken)
        {
            var startTime = Time.realtimeSinceStartupAsDouble;
            var operation = SceneManager.LoadSceneAsync(sceneName, LoadSceneMode.Single);
            if (operation == null)
            {
                throw new ArgumentException($"Scene '{sceneName}' tidak ada di Build Settings.", nameof(sceneName));
            }

            operation.allowSceneActivation = false;
            try
            {
                while (operation.progress < ReadyForActivationProgress
                       || Time.realtimeSinceStartupAsDouble - startTime < minimumSeconds)
                {
                    await Awaitable.NextFrameAsync(cancellationToken);
                }
            }
            finally
            {
                // Operasi yang aktivasinya ditahan memblokir antrean pemuatan Unity; selalu lepaskan,
                // termasuk saat dibatalkan.
                operation.allowSceneActivation = true;
            }

            while (!operation.isDone)
            {
                await Awaitable.NextFrameAsync(cancellationToken);
            }
        }
    }
}
