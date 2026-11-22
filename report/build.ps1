$ErrorActionPreference = 'Stop'

$reportDir = Split-Path $PSScriptRoot -Parent
if ((Split-Path $MyInvocation.MyCommand.Path -Parent) -match 'report$') {
  $reportDir = Split-Path $MyInvocation.MyCommand.Path -Parent
}
$buildDir = Join-Path $reportDir 'build'
New-Item -ItemType Directory -Force -Path (Join-Path $buildDir 'images') | Out-Null

$chapters = @(
  '00-bia.md',
  '01-khao-sat.md',
  '02-phan-tich-thiet-ke.md',
  '03-xay-dung.md',
  '04-kiem-thu.md'
)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$sb = New-Object System.Text.StringBuilder
foreach ($c in $chapters) {
  $p = Join-Path $reportDir $c
  $txt = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8).TrimEnd()
  $txt = [regex]::Replace($txt, '<!--\s*include:\s*([^\s]+)\s*-->', {
    param($m)
    $incPath = Join-Path $reportDir ($m.Groups[1].Value -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path $incPath)) { throw "Missing include file: $incPath" }
    return [System.IO.File]::ReadAllText($incPath, [System.Text.Encoding]::UTF8).TrimEnd()
  })
  [void]$sb.Append($txt)
  [void]$sb.Append("`n`n")
}
$mergedMd = Join-Path $buildDir 'bao-cao.md'
[System.IO.File]::WriteAllText($mergedMd, $sb.ToString(), $utf8NoBom)

# Stage assets needed in buildDir (mirroring clean v1 images only)
Get-ChildItem (Join-Path $buildDir 'images') -File | Remove-Item -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $reportDir 'images\*.png') (Join-Path $buildDir 'images') -Force
Copy-Item (Join-Path $reportDir 'fit-images.lua') $buildDir -Force
Copy-Item (Join-Path $reportDir 'ptit-layout.lua') $buildDir -Force
Copy-Item (Join-Path $reportDir 'reference.docx') $buildDir -Force

$outDocx = Join-Path $buildDir 'bao-cao.docx'

Write-Host "1/3 Running Pandoc via Docker (pandoc/core:3.8)..."
$mountPath = $buildDir -replace '\\', '/'
docker run --rm `
  -v "${mountPath}:/work" `
  -w /work `
  pandoc/core:3.8 `
  bao-cao.md `
  --from=markdown+pipe_tables+table_captions+raw_html+fenced_code_blocks+backtick_code_blocks `
  --to=docx `
  --lua-filter=fit-images.lua `
  --lua-filter=ptit-layout.lua `
  --reference-doc=reference.docx `
  -o bao-cao.docx

if ($LASTEXITCODE -ne 0 -or -not (Test-Path $outDocx)) {
  throw "Pandoc export failed!"
}

Write-Host "2/3 Applying PTIT-RIPT cover frame, logos, proportional fixed tables & academic styling..."
& (Join-Path $reportDir 'scripts\polish_docx.ps1') -DocxPath $outDocx -AssetsDir (Join-Path $reportDir 'assets')

Write-Host "3/3 Updating Word Table of Contents & pagination fields..."
& (Join-Path $reportDir 'scripts\update_toc_word.ps1') -DocxPath $outDocx

# Final integrity check: forward-slash ZIP entries only
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipChk = [System.IO.Compression.ZipFile]::OpenRead($outDocx)
$bad = @($zipChk.Entries | Where-Object { $_.FullName -like '*\*' })
$zipChk.Dispose()
if ($bad.Count -gt 0) {
  throw "Found $($bad.Count) backslash entries inside DOCX ZIP!"
}
Write-Host "BUILD COMPLETE: $outDocx ($((Get-Item $outDocx).Length) bytes, 0 backslash ZIP entries)"
