<#
CareerHub Windows bootstrap: diagnose by default, install only with -Install.
No elevation, native downloads, persistent environment changes or config copies.
#>
[CmdletBinding()]
param(
    [switch]$Install,
    [switch]$CheckOnly,
    [switch]$Json,
    [switch]$CheckOllama,
    [switch]$CheckInstallability,
    [string[]]$Model = @(),
    [string]$PythonExe
)
$ErrorActionPreference = 'Stop'
if ($Install -and ($CheckOnly -or $Json)) {
    throw 'Use -Install separately from -CheckOnly/-Json.'
}
Push-Location $PSScriptRoot
try {
    $candidates = @()
    if ($PythonExe) {
        $candidates += @{ Exe = $PythonExe; Prefix = @() }
    } else {
        $candidates += @{ Exe = 'py'; Prefix = @('-3.12') }
        $candidates += @{ Exe = 'python'; Prefix = @() }
        if (Test-Path -LiteralPath '.venv\Scripts\python.exe') {
            $candidates += @{ Exe = (Join-Path $PSScriptRoot '.venv\Scripts\python.exe'); Prefix = @() }
        }
    }
    $selected = $null
    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Exe -ErrorAction SilentlyContinue)) { continue }
        $prefix = $candidate.Prefix
        $version = & $candidate.Exe @prefix -B -c 'import sys; print(str(sys.version_info.major)+chr(46)+str(sys.version_info.minor))' 2>$null
        if ($LASTEXITCODE -eq 0 -and "$version".Trim() -eq '3.12') {
            $selected = $candidate
            break
        }
    }
    if (-not $selected) {
        throw 'Python 3.12 not found/unsupported environment. Install from python.org or pass -PythonExe. Existing .venv is never replaced.'
    }
    $arguments = @($selected.Prefix) + @('-B', (Join-Path $PSScriptRoot 'tools\careerhub_setup.py'))
    if ($Install) { $arguments += '--install' }
    if ($Json) { $arguments += '--json' }
    if ($CheckOllama) { $arguments += '--check-ollama' }
    if ($CheckInstallability) { $arguments += '--check-installability' }
    foreach ($name in $Model) { $arguments += @('--model', $name) }
    & $selected.Exe @arguments
    $code = $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    $code = 1
} finally {
    Pop-Location
}
exit $code
