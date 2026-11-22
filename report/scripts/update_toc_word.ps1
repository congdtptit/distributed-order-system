param(
  [Parameter(Mandatory=$true)][string]$DocxPath
)

$ErrorActionPreference = 'Stop'
# Only clean up orphaned headless COM Automation Word instances; never kill interactive user Word windows
Get-CimInstance Win32_Process -Filter "Name='WINWORD.EXE'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match '-Embedding|/Automation' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 300

$word = New-Object -ComObject Word.Application
$word.Visible = $true
$word.WindowState = 2 # minimized
$word.DisplayAlerts = 0
$doc = $null
try {
  $doc = $word.Documents.Open((Resolve-Path $DocxPath).Path, $false, $false)
  if ($doc.TablesOfContents.Count -gt 0) {
    foreach ($toc in $doc.TablesOfContents) {
      $toc.Update()
    }
  }
  $doc.Fields.Update() | Out-Null
  foreach ($sec in $doc.Sections) {
    foreach ($hdr in $sec.Headers) { $hdr.Range.Fields.Update() | Out-Null }
    foreach ($ftr in $sec.Footers) { $ftr.Range.Fields.Update() | Out-Null }
  }
  $doc.Repaginate()
  $pages = $doc.ComputeStatistics(2)
  $doc.Save()
  Write-Host "Updated TOC & Fields cleanly in Word -> total pages: $pages"
} finally {
  if ($doc) { $save = $false; $doc.Close([ref]$save) }
  $word.Quit()
}
