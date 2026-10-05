param()
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing

$code = @"
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class ServixBrandTools
{
    public static Bitmap RemoveConnectedNearWhite(string path)
    {
        using (var src = new Bitmap(path))
        {
            var bmp = new Bitmap(src.Width, src.Height, PixelFormat.Format32bppArgb);
            using (var g = Graphics.FromImage(bmp)) g.DrawImageUnscaled(src, 0, 0);

            var rect = new Rectangle(0, 0, bmp.Width, bmp.Height);
            var data = bmp.LockBits(rect, ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
            var stride = Math.Abs(data.Stride);
            var bytes = new byte[stride * bmp.Height];
            Marshal.Copy(data.Scan0, bytes, 0, bytes.Length);
            var visited = new bool[bmp.Width * bmp.Height];
            var queue = new Queue<int>();

            Func<int, bool> isBackground = (index) =>
            {
                int y = index / bmp.Width;
                int x = index % bmp.Width;
                int p = y * stride + x * 4;
                int b = bytes[p];
                int g2 = bytes[p + 1];
                int r = bytes[p + 2];
                int max = Math.Max(r, Math.Max(g2, b));
                int min = Math.Min(r, Math.Min(g2, b));
                return min >= 232 && (max - min) <= 24;
            };

            Action<int> seed = (index) =>
            {
                if (!visited[index] && isBackground(index))
                {
                    visited[index] = true;
                    queue.Enqueue(index);
                }
            };

            for (int x = 0; x < bmp.Width; x++)
            {
                seed(x);
                seed((bmp.Height - 1) * bmp.Width + x);
            }
            for (int y = 0; y < bmp.Height; y++)
            {
                seed(y * bmp.Width);
                seed(y * bmp.Width + bmp.Width - 1);
            }

            while (queue.Count > 0)
            {
                int index = queue.Dequeue();
                int y = index / bmp.Width;
                int x = index % bmp.Width;
                int p = y * stride + x * 4;
                bytes[p + 3] = 0;

                if (x > 0) { int n = index - 1; if (!visited[n] && isBackground(n)) { visited[n] = true; queue.Enqueue(n); } }
                if (x + 1 < bmp.Width) { int n = index + 1; if (!visited[n] && isBackground(n)) { visited[n] = true; queue.Enqueue(n); } }
                if (y > 0) { int n = index - bmp.Width; if (!visited[n] && isBackground(n)) { visited[n] = true; queue.Enqueue(n); } }
                if (y + 1 < bmp.Height) { int n = index + bmp.Width; if (!visited[n] && isBackground(n)) { visited[n] = true; queue.Enqueue(n); } }
            }

            Marshal.Copy(bytes, 0, data.Scan0, bytes.Length);
            bmp.UnlockBits(data);
            return bmp;
        }
    }
}
"@

Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing

$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $root 'assets\logo.png'
$transparentPath = Join-Path $root 'assets\logo-transparent.png'
$iconPath = Join-Path $root 'assets\app-icon-generated.png'

if (-not (Test-Path $source)) { throw "SERVIX source logo not found: $source" }

$logo = [ServixBrandTools]::RemoveConnectedNearWhite($source)
try {
    $logo.Save($transparentPath, [System.Drawing.Imaging.ImageFormat]::Png)

    # The installed Windows icon uses the emblem portion of the exact SERVIX artwork.
    $crop = New-Object System.Drawing.Rectangle(
        [int]($logo.Width * 0.08),
        [int]($logo.Height * 0.02),
        [int]($logo.Width * 0.84),
        [int]($logo.Height * 0.71)
    )
    $icon = New-Object System.Drawing.Bitmap(1024, 1024, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
        $g = [System.Drawing.Graphics]::FromImage($icon)
        try {
            $g.Clear([System.Drawing.Color]::Transparent)
            $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

            $padding = 66
            $available = 1024 - (2 * $padding)
            $ratio = [Math]::Min($available / $crop.Width, $available / $crop.Height)
            $drawW = [int]($crop.Width * $ratio)
            $drawH = [int]($crop.Height * $ratio)
            $dest = New-Object System.Drawing.Rectangle(
                [int]((1024 - $drawW) / 2),
                [int]((1024 - $drawH) / 2),
                $drawW,
                $drawH
            )
            $g.DrawImage($logo, $dest, $crop, [System.Drawing.GraphicsUnit]::Pixel)
        }
        finally { $g.Dispose() }
        $icon.Save($iconPath, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally { $icon.Dispose() }
}
finally { $logo.Dispose() }

Write-Host "Prepared SERVIX transparent logo: $transparentPath"
Write-Host "Prepared SERVIX Windows icon: $iconPath"
