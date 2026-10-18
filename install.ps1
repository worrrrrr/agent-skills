# Link this repo's skills into the global OpenCode skills directory.
# Windows junctions: single source of truth, no copies, no admin required.
#
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $repo "skills"
$dest = Join-Path $HOME ".agents\skills"

if (-not (Test-Path $source)) { throw "skills/ not found next to install.ps1" }
New-Item -ItemType Directory -Force -Path $dest | Out-Null

Get-ChildItem $source -Directory | ForEach-Object {
    $target = Join-Path $dest $_.Name
    $skip = $false
    if (Test-Path $target) {
        $item = Get-Item $target -Force
        if ($item.LinkType -eq "Junction") {
            & cmd /c rmdir "$target" | Out-Null
            if (Test-Path $target) { throw "cannot remove junction: $target" }
        } else {
            Write-Host "skip (exists, not a junction): $target"
            $skip = $true
        }
    }
    if (-not $skip) {
        New-Item -ItemType Junction -Path $target -Target $_.FullName | Out-Null
        if (-not (Test-Path $target)) { throw "cannot create junction: $target" }
        Write-Host "linked $($_.Name) -> $($_.FullName)"
    }
}
