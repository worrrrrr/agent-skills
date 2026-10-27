# Install skills + owner prompt. Works from the repo OR from a downloaded zip.
#
#   # 1) จาก repo (junction: single source of truth, ไม่ก๊อป)
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
#   # 2) จากไฟล์ที่โหลดมา (zip หรือโฟลเดอร์ที่แตกแล้ว)
#   powershell -ExecutionPolicy Bypass -File install.ps1 -FromZip .\agent-skills-0.3.0.zip
#
#   # 3) ติดตั้งแบบสำเนา (เครื่องอื่น / ไม่ต้องการ junction)
#   powershell -ExecutionPolicy Bypass -File install.ps1 -FromZip .\agent-skills-0.3.0.zip -Copy
param(
    [string]$FromZip = "",
    [switch]$Copy
)

$ErrorActionPreference = "Stop"
$agentsRoot = Join-Path $HOME ".agents"
$skillsDest = Join-Path $agentsRoot "skills"
New-Item -ItemType Directory -Force -Path $skillsDest | Out-Null

# หา root ที่มี owner.prompt.md + skills/
if ($FromZip) {
    if (-not (Test-Path -LiteralPath $FromZip)) { throw "not found: $FromZip" }
    if ((Get-Item -LiteralPath $FromZip).PSIsContainer) {
        $root = (Resolve-Path -LiteralPath $FromZip).Path
    } else {
        $tmp = Join-Path $env:TEMP ("agent-skills-" + [guid]::NewGuid().ToString("N"))
        Expand-Archive -LiteralPath $FromZip -DestinationPath $tmp -Force
        $root = $tmp
    }
} else {
    $root = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$source = Join-Path $root "skills"
if (-not (Test-Path $source)) { throw "skills/ not found in $root" }

$prompt = Join-Path $root "owner.prompt.md"
if (Test-Path $prompt) {
    Copy-Item -LiteralPath $prompt -Destination (Join-Path $agentsRoot "owner.prompt.md") -Force
    Write-Host "prompt -> $agentsRoot\owner.prompt.md"
}

Get-ChildItem $source -Directory | ForEach-Object {
    $target = Join-Path $skillsDest $_.Name
    $existing = Test-Path $target
    if ($existing) {
        $item = Get-Item $target -Force
        if ($item.LinkType -eq "Junction") {
            & cmd /c rmdir "$target" | Out-Null
            $existing = Test-Path $target
        } elseif ($Copy) {
            Remove-Item -LiteralPath $target -Recurse -Force
            $existing = $false
        } else {
            Write-Host "skip (exists, not a junction): $target"
        }
    }
    if (-not $existing) {
        if ($Copy -or $FromZip) {
            Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force
            Write-Host "copied $($_.Name)"
        } else {
            New-Item -ItemType Junction -Path $target -Target $_.FullName | Out-Null
            Write-Host "linked $($_.Name) -> $($_.FullName)"
        }
    }
}

Write-Host ""
Write-Host "installed:"
Get-ChildItem $skillsDest -Directory | ForEach-Object { Write-Host "  - $($_.Name)" }
