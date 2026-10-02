# Gera o logo do ReperIO (docs/images/logo*.png) com o .NET do Windows.
# Uso: powershell -ExecutionPolicy Bypass -File tools\make_logo.ps1
# O ícone .ico é montado depois por tools/make_icon.py a partir destes PNGs.
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root "docs\images"
New-Item -ItemType Directory -Force -Path $out | Out-Null

function New-Logo([int]$size, [string]$path) {
    $bmp = New-Object System.Drawing.Bitmap $size, $size
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.Clear([System.Drawing.Color]::Transparent)
    $s = $size / 512.0

    # Fundo: quadrado arredondado escuro
    $r = 96 * $s
    $rect = New-Object System.Drawing.RectangleF (16 * $s), (16 * $s), (480 * $s), (480 * $s)
    $gp = New-Object System.Drawing.Drawing2D.GraphicsPath
    $gp.AddArc($rect.X, $rect.Y, 2 * $r, 2 * $r, 180, 90)
    $gp.AddArc($rect.Right - 2 * $r, $rect.Y, 2 * $r, 2 * $r, 270, 90)
    $gp.AddArc($rect.Right - 2 * $r, $rect.Bottom - 2 * $r, 2 * $r, 2 * $r, 0, 90)
    $gp.AddArc($rect.X, $rect.Bottom - 2 * $r, 2 * $r, 2 * $r, 90, 90)
    $gp.CloseFigure()
    $bg = New-Object System.Drawing.Drawing2D.LinearGradientBrush $rect, `
        ([System.Drawing.Color]::FromArgb(255, 52, 56, 60)), ([System.Drawing.Color]::FromArgb(255, 30, 32, 35)), 90
    $g.FillPath($bg, $gp)

    # "Repertório": linhas de arquivos ao fundo
    $line = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 110, 118, 128))
    foreach ($i in 0..4) {
        $y = (112 + 58 * $i) * $s
        $w = @(300, 250, 280, 200, 240)[$i] * $s
        $g.FillRectangle($line, (96 * $s), $y, $w, (22 * $s))
    }

    # Lupa (azul do app #4A90D9) com destaque verde (#5CB85C) do arquivo encontrado
    $blue = [System.Drawing.Color]::FromArgb(255, 74, 144, 217)
    $green = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 92, 184, 92))
    $lens = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(70, 74, 144, 217))
    $cx = 300 * $s; $cy = 250 * $s; $rad = 118 * $s
    $g.FillEllipse($lens, $cx - $rad, $cy - $rad, 2 * $rad, 2 * $rad)
    $g.FillRectangle($green, (232 * $s), (237 * $s), (136 * $s), (26 * $s))
    $pen = New-Object System.Drawing.Pen $blue, (34 * $s)
    $g.DrawEllipse($pen, $cx - $rad, $cy - $rad, 2 * $rad, 2 * $rad)
    $handle = New-Object System.Drawing.Pen $blue, (58 * $s)
    $handle.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $handle.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $g.DrawLine($handle, (388 * $s), (338 * $s), (440 * $s), (390 * $s))

    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
}

New-Logo 512 (Join-Path $out "logo.png")
foreach ($sz in 256, 64, 48, 32, 16) { New-Logo $sz (Join-Path $out ("logo_{0}.png" -f $sz)) }
"Logo gerado em $out"
