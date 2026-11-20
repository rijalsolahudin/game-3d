using System;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace Game.Editor
{
    /// <summary>
    /// Build standalone dari command line (lokal maupun CI), memakai scene yang aktif di Build Settings.
    /// Contoh:
    /// <code>
    /// Unity -batchmode -quit -projectPath client -executeMethod Game.Editor.BuildScript.BuildLinux -buildOutput build/Tumanggal.x86_64
    /// Unity -batchmode -quit -projectPath client -executeMethod Game.Editor.BuildScript.BuildWindows -buildOutput build/Tumanggal.exe
    /// </code>
    /// Tambahkan <c>-developmentBuild</c> untuk development build. Exit code 1 bila build gagal.
    /// </summary>
    public static class BuildScript
    {
        private const string OutputArgument = "-buildOutput";
        private const string DevelopmentArgument = "-developmentBuild";

        public static void BuildLinux()
        {
            Build(BuildTarget.StandaloneLinux64, "build/linux/Tumanggal.x86_64");
        }

        public static void BuildWindows()
        {
            Build(BuildTarget.StandaloneWindows64, "build/windows/Tumanggal.exe");
        }

        private static void Build(BuildTarget target, string defaultOutput)
        {
            var args = Environment.GetCommandLineArgs();
            var output = ReadArgument(args, OutputArgument) ?? defaultOutput;
            var options = args.Contains(DevelopmentArgument) ? BuildOptions.Development : BuildOptions.None;
            var scenes = EditorBuildSettings.scenes.Where(scene => scene.enabled).Select(scene => scene.path).ToArray();

            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = output,
                target = target,
                options = options,
            });

            var summary = report.summary;
            Debug.Log($"[Build] {target} → {output}: {summary.result}, {summary.totalSize} B, " +
                      $"{summary.totalErrors} error, {summary.totalWarnings} warning, {summary.totalTime}.");
            if (Application.isBatchMode && summary.result != BuildResult.Succeeded)
            {
                EditorApplication.Exit(1);
            }
        }

        private static string? ReadArgument(string[] args, string name)
        {
            for (var i = 0; i < args.Length - 1; i++)
            {
                if (args[i] == name)
                {
                    return args[i + 1];
                }
            }

            return null;
        }
    }
}
