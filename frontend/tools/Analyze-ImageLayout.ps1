param(
    [string]$ImagePath,
    [switch]$QuickMode
)

# Image Layout & Color Extraction Tool
# Usage: .\Analyze-ImageLayout.ps1 "path/to/image.jpg"

if (-not $ImagePath) {
    Write-Host "Usage Error"
    Write-Host ""
    Write-Host "Basic usage:"
    Write-Host "  .\Analyze-ImageLayout.ps1 'C:\path\to\image.jpg'"
    Write-Host ""
    Write-Host "Quick mode (TOP5 only):"
    Write-Host "  .\Analyze-ImageLayout.ps1 'C:\path\to\image.jpg' -QuickMode"
    Write-Host ""
    Write-Host "Example:"
    Write-Host "  .\Analyze-ImageLayout.ps1 'materials\image.png'"
    Write-Host ""
    exit
}

# Check file exists
if (-not (Test-Path $ImagePath)) {
    Write-Host "ERROR: File not found: $ImagePath"
    exit
}

# Load image
try {
    [Reflection.Assembly]::LoadWithPartialName("System.Drawing") | Out-Null
    $img = New-Object System.Drawing.Bitmap($ImagePath)
} catch {
    Write-Host "ERROR: Cannot load image: $_"
    exit
}

$fileName = Split-Path $ImagePath -Leaf
$fileSize = Get-Item $ImagePath | ForEach-Object { [math]::Round($_.Length/1MB, 2) }

Write-Host ""
Write-Host "IMAGE ANALYSIS REPORT"
Write-Host "=" * 80
Write-Host "File: $fileName"
Write-Host "Size: $($img.Width) x $($img.Height) px"
Write-Host "File Size: $fileSize MB"
Write-Host ""

# Key regions sampling
Write-Host "KEY REGIONS SAMPLING"
Write-Host "-" * 80

$regions = @(
    @{ Name = "Top-Left"; X = 0.1; Y = 0.1 },
    @{ Name = "Top-Center"; X = 0.5; Y = 0.05 },
    @{ Name = "Top-Right"; X = 0.9; Y = 0.1 },
    @{ Name = "Mid-Left"; X = 0.1; Y = 0.5 },
    @{ Name = "Center"; X = 0.5; Y = 0.5 },
    @{ Name = "Mid-Right"; X = 0.9; Y = 0.5 },
    @{ Name = "Bot-Left"; X = 0.1; Y = 0.9 },
    @{ Name = "Bot-Center"; X = 0.5; Y = 0.95 },
    @{ Name = "Bot-Right"; X = 0.9; Y = 0.9 }
)

$regions | ForEach-Object {
    $px = [int]($img.Width * $_.X)
    $py = [int]($img.Height * $_.Y)

    if ($px -ge $img.Width) { $px = $img.Width - 1 }
    if ($py -ge $img.Height) { $py = $img.Height - 1 }

    $pixel = $img.GetPixel($px, $py)
    $hex = "#{0:X2}{1:X2}{2:X2}" -f $pixel.R, $pixel.G, $pixel.B
    $brightness = [math]::Round(($pixel.R + $pixel.G + $pixel.B) / 3)

    Write-Host ("[{0,-12}] @ ({1:4}, {2:4}) | {3} | RGB({4:3}, {5:3}, {6:3}) | Brightness: {7}" -f $_.Name, $px, $py, $hex, $pixel.R, $pixel.G, $pixel.B, $brightness)
}

Write-Host ""

# Color statistics
if ($QuickMode) {
    Write-Host "COLOR STATISTICS (Quick Mode - TOP5)"
    $topCount = 5
} else {
    Write-Host "COLOR STATISTICS (Full scan - TOP10)"
    $topCount = 10
}

Write-Host "-" * 80

$colorMap = @{}
$step = 5

Write-Host "Scanning... (this may take a few seconds)"

for ($y = 0; $y -lt $img.Height; $y += $step) {
    for ($x = 0; $x -lt $img.Width; $x += $step) {
        $pixel = $img.GetPixel($x, $y)

        $r = [int]($pixel.R / 20) * 20
        $g = [int]($pixel.G / 20) * 20
        $b = [int]($pixel.B / 20) * 20

        $key = "#{0:X2}{1:X2}{2:X2}" -f $r, $g, $b

        if ($colorMap.ContainsKey($key)) {
            $colorMap[$key] += 1
        } else {
            $colorMap[$key] = 1
        }
    }
}

Write-Host "Scan complete!"
Write-Host ""
Write-Host "Top $topCount Colors:"

$totalPixels = ($colorMap.Values | Measure-Object -Sum).Sum

$colorMap.GetEnumerator() |
    Sort-Object {$_.Value} -Descending |
    Select-Object -First $topCount |
    ForEach-Object {
        $hex = $_.Key
        $count = $_.Value
        $percent = [math]::Round(($count / $totalPixels) * 100, 1)

        $barLength = [int]($percent / 2)
        $bar = "#" * $barLength + "-" * ([math]::Max(0, 50 - $barLength))

        Write-Host ("  {0} ({1:5.1f}%) [{2}]" -f $hex, $percent, $bar)
    }

Write-Host ""
Write-Host "Analysis Complete!"
Write-Host ""

$img.Dispose()
