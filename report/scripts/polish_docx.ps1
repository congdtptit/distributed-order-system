param(
  [Parameter(Mandatory=$true)][string]$DocxPath,
  [string]$AssetsDir = (Join-Path (Split-Path $PSScriptRoot -Parent) 'assets')
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$workDir = Join-Path ([System.IO.Path]::GetTempPath()) ("polish_docx_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $workDir | Out-Null

function Read-XmlFile([string]$p) {
  $xml = New-Object System.Xml.XmlDocument
  $xml.PreserveWhitespace = $true
  $xml.Load($p)
  return $xml
}

function Save-XmlFile([System.Xml.XmlDocument]$xml, [string]$p) {
  $settings = New-Object System.Xml.XmlWriterSettings
  $settings.Encoding = New-Object System.Text.UTF8Encoding($false)
  $settings.Indent = $false
  $xw = [System.Xml.XmlWriter]::Create($p, $settings)
  try { $xml.Save($xw) } finally { $xw.Close() }
}

$wNs = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
$rNs = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
$relNs = 'http://schemas.openxmlformats.org/package/2006/relationships'
$wpNs = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
$aNs = 'http://schemas.openxmlformats.org/drawingml/2006/main'
$picNs = 'http://schemas.openxmlformats.org/drawingml/2006/picture'
$wp14Ns = 'http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing'

function Parse-Fragment([System.Xml.XmlDocument]$doc, [string]$xmlFragment) {
  $wrapped = "<root xmlns:w=`"$wNs`" xmlns:r=`"$rNs`" xmlns:wp=`"$wpNs`" xmlns:a=`"$aNs`" xmlns:pic=`"$picNs`" xmlns:wp14=`"$wp14Ns`">$xmlFragment</root>"
  $fragDoc = New-Object System.Xml.XmlDocument
  $fragDoc.PreserveWhitespace = $true
  $fragDoc.LoadXml($wrapped)
  $nodes = New-Object 'System.Collections.Generic.List[System.Xml.XmlNode]'
  foreach ($ch in $fragDoc.DocumentElement.ChildNodes) {
    if ($ch.NodeType -eq [System.Xml.XmlNodeType]::Element) {
      [void]$nodes.Add($doc.ImportNode($ch, $true))
    }
  }
  return $nodes.ToArray()
}

try {
  # 1. Extract DOCX cleanly
  $zipRead = [System.IO.Compression.ZipFile]::OpenRead($DocxPath)
  foreach ($entry in $zipRead.Entries) {
    if ([string]::IsNullOrEmpty($entry.Name)) { continue }
    $relPath = $entry.FullName -replace '/', [System.IO.Path]::DirectorySeparatorChar
    $dest = Join-Path $workDir $relPath
    New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
    $fs = [System.IO.File]::Create($dest)
    $s = $entry.Open()
    $s.CopyTo($fs)
    $s.Close(); $fs.Close()
  }
  $zipRead.Dispose()

  # 2. Copy cover assets into word/media/
  $mediaDir = Join-Path $workDir 'word\media'
  New-Item -ItemType Directory -Force -Path $mediaDir | Out-Null
  foreach ($asset in @('cover_border.png', 'logo_ptit.png', 'logo_faculty.png')) {
    $src = Join-Path $AssetsDir $asset
    if (-not (Test-Path $src)) { throw "Missing asset: $src" }
    Copy-Item $src (Join-Path $mediaDir $asset) -Force
  }

  # 3. Create clean Headers & Footers for 3 sections:
  #    hdr_empty.xml / ftr_empty.xml (Cover Page Section 1)
  #    ftr_roman.xml (Front-matter Section 2: subtle centered roman numeral)
  #    hdr_body.xml / ftr_body.xml (Body Section 3: clean header rule + Trang X)
  $hdrEmpty = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="$wNs" xmlns:r="$rNs"><w:p><w:pPr><w:pStyle w:val="Header"/></w:pPr></w:p></w:hdr>
"@
  $ftrEmpty = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="$wNs" xmlns:r="$rNs"><w:p><w:pPr><w:pStyle w:val="Footer"/></w:pPr></w:p></w:ftr>
"@
  $ftrRoman = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="$wNs" xmlns:r="$rNs">
  <w:p>
    <w:pPr><w:spacing w:before="40" w:after="0"/><w:jc w:val="center"/></w:pPr>
    <w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>
    <w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>
    <w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:fldChar w:fldCharType="separate"/></w:r>
    <w:r><w:rPr><w:noProof/><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t>i</w:t></w:r>
    <w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>
  </w:p>
</w:ftr>
"@
  $hdrBody = $hdrEmpty
  $ftrBody = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="$wNs" xmlns:r="$rNs">
  <w:p>
    <w:pPr><w:spacing w:before="40" w:after="0"/><w:jc w:val="center"/></w:pPr>
    <w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>
    <w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>
    <w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:fldChar w:fldCharType="separate"/></w:r>
    <w:r><w:rPr><w:noProof/><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t>1</w:t></w:r>
    <w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>
  </w:p>
</w:ftr>
"@
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText((Join-Path $workDir 'word\header_ptit_empty.xml'), $hdrEmpty, $utf8NoBom)
  [System.IO.File]::WriteAllText((Join-Path $workDir 'word\footer_ptit_empty.xml'), $ftrEmpty, $utf8NoBom)
  [System.IO.File]::WriteAllText((Join-Path $workDir 'word\footer_ptit_roman.xml'), $ftrRoman, $utf8NoBom)
  [System.IO.File]::WriteAllText((Join-Path $workDir 'word\header_ptit_body.xml'), $hdrBody, $utf8NoBom)
  [System.IO.File]::WriteAllText((Join-Path $workDir 'word\footer_ptit_body.xml'), $ftrBody, $utf8NoBom)

  # Register new header/footer files in [Content_Types].xml
  $ctPath = Join-Path $workDir '[Content_Types].xml'
  $ctXml = Read-XmlFile $ctPath
  $ctNs = 'http://schemas.openxmlformats.org/package/2006/content-types'
  $overrides = @(
    @{ Part = '/word/header_ptit_empty.xml'; Type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml' },
    @{ Part = '/word/footer_ptit_empty.xml'; Type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml' },
    @{ Part = '/word/footer_ptit_roman.xml'; Type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml' },
    @{ Part = '/word/header_ptit_body.xml'; Type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml' },
    @{ Part = '/word/footer_ptit_body.xml'; Type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml' }
  )
  $mgrCt = New-Object System.Xml.XmlNamespaceManager($ctXml.NameTable); $mgrCt.AddNamespace('ct',$ctNs)
  if ($ctXml.DocumentElement.SelectNodes("ct:Default[@Extension='png']", $mgrCt).Count -eq 0) {
    $defPng = $ctXml.CreateElement('Default', $ctNs)
    $null = $defPng.SetAttribute('Extension', 'png')
    $null = $defPng.SetAttribute('ContentType', 'image/png')
    $ctXml.DocumentElement.PrependChild($defPng) | Out-Null
  }
  foreach ($ov in $overrides) {
    if ($ctXml.DocumentElement.SelectNodes("ct:Override[@PartName='$($ov.Part)']", $mgrCt).Count -eq 0) {
      $el = $ctXml.CreateElement('Override', $ctNs)
      $null = $el.SetAttribute('PartName', $ov.Part)
      $null = $el.SetAttribute('ContentType', $ov.Type)
      $ctXml.DocumentElement.AppendChild($el) | Out-Null
    }
  }
  Save-XmlFile $ctXml $ctPath

  # Register relationships in word/_rels/document.xml.rels
  $relsPath = Join-Path $workDir 'word\_rels\document.xml.rels'
  $relsXml = Read-XmlFile $relsPath
  $newRels = @(
    @{ Id = 'rIdCoverBorder'; Type = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'; Target = 'media/cover_border.png' },
    @{ Id = 'rIdLogoPtit'; Type = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'; Target = 'media/logo_ptit.png' },
    @{ Id = 'rIdLogoFaculty'; Type = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'; Target = 'media/logo_faculty.png' },
    @{ Id = 'rIdHdrEmpty'; Type = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/header'; Target = 'header_ptit_empty.xml' },
    @{ Id = 'rIdFtrEmpty'; Type = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer'; Target = 'footer_ptit_empty.xml' },
    @{ Id = 'rIdFtrRoman'; Type = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer'; Target = 'footer_ptit_roman.xml' },
    @{ Id = 'rIdHdrBody'; Type = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/header'; Target = 'header_ptit_body.xml' },
    @{ Id = 'rIdFtrBody'; Type = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer'; Target = 'footer_ptit_body.xml' }
  )
  $mgrRels = New-Object System.Xml.XmlNamespaceManager($relsXml.NameTable); $mgrRels.AddNamespace('r', $relNs)
  foreach ($nr in $newRels) {
    $old = $relsXml.DocumentElement.SelectSingleNode("r:Relationship[@Id='$($nr.Id)']", $mgrRels)
    if ($old) { $relsXml.DocumentElement.RemoveChild($old) | Out-Null }
    $el = $relsXml.CreateElement('Relationship', $relNs)
    $el.SetAttribute('Id', $nr.Id)
    $el.SetAttribute('Type', $nr.Type)
    $el.SetAttribute('Target', $nr.Target)
    $relsXml.DocumentElement.AppendChild($el) | Out-Null
  }
  Save-XmlFile $relsXml $relsPath

  # 4. Upgrade word/styles.xml to exact PTIT/RMS academic standard
  $stylesPath = Join-Path $workDir 'word\styles.xml'
  $stylesXml = Read-XmlFile $stylesPath
  $mgrS = New-Object System.Xml.XmlNamespaceManager($stylesXml.NameTable); $mgrS.AddNamespace('w', $wNs)

  # Patch docDefaults to Times New Roman 12pt pure black #000000
  $docDef = $stylesXml.SelectSingleNode('//w:docDefaults', $mgrS)
  if ($docDef) {
    $defFrag = @"
<w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:color w:val="000000"/><w:sz w:val="24"/><w:szCs w:val="24"/><w:lang w:val="vi-VN" w:eastAsia="vi-VN" w:bidi="ar-SA"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:before="0" w:after="100" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault>
"@
    $docDef.RemoveAll()
    foreach ($n in (Parse-Fragment $stylesXml $defFrag)) { $docDef.AppendChild($n) | Out-Null }
  }

  function Upsert-Style([string]$styleId, [string]$styleXmlStr) {
    $existing = $stylesXml.SelectSingleNode("//w:style[@w:styleId='$styleId']", $mgrS)
    $nodes = @(Parse-Fragment $stylesXml $styleXmlStr)
    $newNode = $nodes[0]
    if ($existing) {
      $existing.ParentNode.ReplaceChild($newNode, $existing) | Out-Null
    } else {
      $stylesXml.DocumentElement.AppendChild($newNode) | Out-Null
    }
  }

  Upsert-Style 'Normal' @"
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="0" w:after="100" w:line="276" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:color w:val="000000"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
"@
  Upsert-Style 'BodyText' @"
<w:style w:type="paragraph" w:styleId="BodyText"><w:name w:val="Body Text"/><w:basedOn w:val="Normal"/><w:link w:val="BodyTextChar"/><w:qFormat/><w:pPr><w:spacing w:before="0" w:after="100" w:line="276" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:style>
"@
  Upsert-Style 'Compact' @"
<w:style w:type="paragraph" w:customStyle="1" w:styleId="Compact"><w:name w:val="Compact"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="15" w:after="25" w:line="240" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr><w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
"@
  Upsert-Style 'Heading1' @"
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="140"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr></w:style>
"@
  Upsert-Style 'Heading2' @"
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="180" w:after="70"/><w:jc w:val="left"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="27"/><w:szCs w:val="27"/></w:rPr></w:style>
"@
  Upsert-Style 'Heading3' @"
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="130" w:after="50"/><w:jc w:val="left"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="25"/><w:szCs w:val="25"/></w:rPr></w:style>
"@
  Upsert-Style 'Heading4' @"
<w:style w:type="paragraph" w:styleId="Heading4"><w:name w:val="heading 4"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="110" w:after="45"/><w:jc w:val="left"/><w:outlineLvl w:val="3"/></w:pPr><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
"@
  Upsert-Style 'Heading5' @"
<w:style w:type="paragraph" w:styleId="Heading5"><w:name w:val="heading 5"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="90" w:after="35"/><w:ind w:left="140"/><w:jc w:val="left"/><w:outlineLvl w:val="4"/></w:pPr><w:rPr><w:b/><w:bCs/><w:i/><w:iCs/><w:color w:val="000000"/><w:sz w:val="23"/><w:szCs w:val="23"/></w:rPr></w:style>
"@
  # Force Heading1Char..Heading9Char linked character styles to pure black 000000
  foreach ($hcCol in @($stylesXml.SelectNodes("//w:style[starts-with(@w:styleId,'Heading')]//w:color", $mgrS))) {
    $null = $hcCol.SetAttribute('val', $wNs, '000000')
  }
  Upsert-Style 'TableCaption' @"
<w:style w:type="paragraph" w:customStyle="1" w:styleId="TableCaption"><w:name w:val="Table Caption"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:spacing w:before="45" w:after="160"/><w:jc w:val="center"/></w:pPr><w:rPr><w:i/><w:iCs/><w:color w:val="000000"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:style>
"@
  Upsert-Style 'TableCaption0' @"
<w:style w:type="paragraph" w:customStyle="1" w:styleId="TableCaption0"><w:name w:val="TableCaption"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:spacing w:before="45" w:after="160"/><w:jc w:val="center"/></w:pPr><w:rPr><w:i/><w:iCs/><w:color w:val="000000"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:style>
"@
  Upsert-Style 'ImageCaption' @"
<w:style w:type="paragraph" w:customStyle="1" w:styleId="ImageCaption"><w:name w:val="Image Caption"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:spacing w:before="40" w:after="160"/><w:jc w:val="center"/></w:pPr><w:rPr><w:i/><w:iCs/><w:color w:val="000000"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:style>
"@
  Upsert-Style 'CaptionedFigure' @"
<w:style w:type="paragraph" w:customStyle="1" w:styleId="CaptionedFigure"><w:name w:val="Captioned Figure"/><w:basedOn w:val="Normal"/><w:next w:val="ImageCaption"/><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="40"/><w:jc w:val="center"/></w:pPr></w:style>
"@
  Upsert-Style 'Figure' @"
<w:style w:type="paragraph" w:customStyle="1" w:styleId="Figure"><w:name w:val="Figure"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="40"/><w:jc w:val="center"/></w:pPr></w:style>
"@
  Upsert-Style 'VerbatimChar' @"
<w:style w:type="character" w:customStyle="1" w:styleId="VerbatimChar"><w:name w:val="Verbatim Char"/><w:basedOn w:val="DefaultParagraphFont"/><w:rPr><w:rFonts w:ascii="Consolas" w:eastAsia="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/><w:color w:val="0F172A"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
"@
  Upsert-Style 'SourceCode' @"
<w:style w:type="paragraph" w:customStyle="1" w:styleId="SourceCode"><w:name w:val="Source Code"/><w:basedOn w:val="Normal"/><w:pPr><w:keepLines/><w:pBdr><w:top w:val="single" w:sz="4" w:space="6" w:color="CBD5E1"/><w:left w:val="single" w:sz="18" w:space="8" w:color="2563EB"/><w:bottom w:val="single" w:sz="4" w:space="6" w:color="CBD5E1"/><w:right w:val="single" w:sz="4" w:space="6" w:color="CBD5E1"/></w:pBdr><w:shd w:val="clear" w:color="auto" w:fill="F8FAFC"/><w:spacing w:before="80" w:after="100" w:line="225" w:lineRule="auto"/><w:ind w:left="140" w:right="140"/><w:jc w:val="left"/></w:pPr><w:rPr><w:rFonts w:ascii="Consolas" w:eastAsia="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/><w:color w:val="0F172A"/><w:sz w:val="17"/><w:szCs w:val="17"/></w:rPr></w:style>
"@
  Upsert-Style 'TOC1' @"
<w:style w:type="paragraph" w:styleId="TOC1"><w:name w:val="toc 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9061"/></w:tabs><w:spacing w:before="28" w:after="10" w:line="216" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
"@
  Upsert-Style 'TOC2' @"
<w:style w:type="paragraph" w:styleId="TOC2"><w:name w:val="toc 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9061"/></w:tabs><w:spacing w:before="4" w:after="8" w:line="210" w:lineRule="auto"/><w:ind w:left="280"/><w:jc w:val="left"/></w:pPr><w:rPr><w:color w:val="000000"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:style>
"@
  Upsert-Style 'TOC3' @"
<w:style w:type="paragraph" w:styleId="TOC3"><w:name w:val="toc 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9061"/></w:tabs><w:spacing w:after="4" w:line="204" w:lineRule="auto"/><w:ind w:left="560"/><w:jc w:val="left"/></w:pPr><w:rPr><w:color w:val="000000"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
"@
  Upsert-Style 'Table' @"
<w:style w:type="table" w:default="1" w:styleId="Table"><w:name w:val="Table"/><w:basedOn w:val="TableNormal"/><w:qFormat/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/><w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/><w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/></w:tblBorders><w:tblCellMar><w:top w:w="50" w:type="dxa"/><w:left w:w="75" w:type="dxa"/><w:bottom w:w="50" w:type="dxa"/><w:right w:w="75" w:type="dxa"/></w:tblCellMar></w:tblPr><w:pPr><w:spacing w:before="15" w:after="20" w:line="230" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:color w:val="000000"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr></w:style>
"@
  Save-XmlFile $stylesXml $stylesPath

  # 5. Transform word/document.xml
  $docPath = Join-Path $workDir 'word\document.xml'
  $docXml = Read-XmlFile $docPath
  $mgrD = New-Object System.Xml.XmlNamespaceManager($docXml.NameTable)
  $mgrD.AddNamespace('w', $wNs)
  $mgrD.AddNamespace('wp', $wpNs)
  $body = $docXml.SelectSingleNode('/w:document/w:body', $mgrD)

  # Remove any Pandoc auto-generated empty <w:sdt> TOC at start (we place ours cleanly at __PTIT_TOC_PLACEHOLDER__)
  foreach ($sdt in @($body.SelectNodes('./w:sdt', $mgrD))) {
    $body.RemoveChild($sdt) | Out-Null
  }

  # Remove Pandoc leading empty TOC header paragraph if present
  foreach ($p in @($body.SelectNodes('./w:p', $mgrD))) {
    $txt = $p.InnerText.Trim()
    if ($txt -eq '__PTIT_COVER_PAGE__') {
      $coverXml = @"
<w:p>
  <w:pPr><w:keepLines/><w:spacing w:before="320" w:after="40"/><w:jc w:val="center"/></w:pPr>
  <w:r><w:rPr><w:noProof/></w:rPr>
    <w:drawing>
      <wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="251658240" behindDoc="1" locked="0" layoutInCell="0" allowOverlap="1">
        <wp:simplePos x="0" y="0"/>
        <wp:positionH relativeFrom="page"><wp:align>center</wp:align></wp:positionH>
        <wp:positionV relativeFrom="page"><wp:posOffset>723600</wp:posOffset></wp:positionV>
        <wp:extent cx="6480000" cy="9244800"/>
        <wp:effectExtent l="0" t="0" r="0" b="0"/>
        <wp:wrapNone/>
        <wp:docPr id="9001" name="CoverFrameBorder"/>
        <wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="$aNs" noChangeAspect="1"/></wp:cNvGraphicFramePr>
        <a:graphic xmlns:a="$aNs"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
          <pic:pic xmlns:pic="$picNs">
            <pic:nvPicPr><pic:cNvPr id="0" name="cover_border.png"/><pic:cNvPicPr/></pic:nvPicPr>
            <pic:blipFill><a:blip r:embed="rIdCoverBorder"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
            <pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="6480000" cy="9244800"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
          </pic:pic>
        </a:graphicData></a:graphic>
      </wp:anchor>
    </w:drawing>
  </w:r>
  <w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG</w:t></w:r>
</w:p>
<w:p>
  <w:pPr><w:keepLines/><w:spacing w:before="0" w:after="380"/><w:jc w:val="center"/></w:pPr>
  <w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>VIỆN KHOA HỌC KỸ THUẬT BƯU ĐIỆN</w:t></w:r>
</w:p>
<w:tbl>
  <w:tblPr><w:tblW w:w="0" w:type="auto"/><w:jc w:val="center"/><w:tblBorders><w:top w:val="none"/><w:left w:val="none"/><w:bottom w:val="none"/><w:right w:val="none"/><w:insideH w:val="none"/><w:insideV w:val="none"/></w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPr>
  <w:tblGrid><w:gridCol w:w="1672"/><w:gridCol w:w="879"/><w:gridCol w:w="2041"/></w:tblGrid>
  <w:tr>
    <w:trPr><w:jc w:val="center"/></w:trPr>
    <w:tc><w:tcPr><w:tcW w:w="1672" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="906469" cy="1152000"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="9002" name="Picture 9002"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="$aNs" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="$aNs"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="$picNs"><pic:nvPicPr><pic:cNvPr id="0" name="logo_ptit.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdLogoPtit"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="906469" cy="1152000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p></w:tc>
    <w:tc><w:tcPr><w:tcW w:w="879" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:jc w:val="center"/></w:pPr></w:p></w:tc>
    <w:tc><w:tcPr><w:tcW w:w="2041" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="1152000" cy="1152000"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="9003" name="Picture 9003"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="$aNs" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="$aNs"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="$picNs"><pic:nvPicPr><pic:cNvPr id="0" name="logo_faculty.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdLogoFaculty"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1152000" cy="1152000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p></w:tc>
  </w:tr>
</w:tbl>
<w:p><w:pPr><w:keepLines/><w:spacing w:before="460" w:after="60" w:line="269" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="48"/><w:szCs w:val="48"/></w:rPr><w:t>BÁO CÁO BÀI TẬP LỚN</w:t></w:r></w:p>
<w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="60" w:line="269" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="48"/><w:szCs w:val="48"/></w:rPr><w:t>PHÁT TRIỂN ỨNG DỤNG</w:t></w:r></w:p>
<w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="320" w:line="269" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="48"/><w:szCs w:val="48"/></w:rPr><w:t>PHÂN TÁN</w:t></w:r></w:p>
<w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="440" w:line="293" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="27"/><w:szCs w:val="27"/></w:rPr><w:t>ĐỀ TÀI 4:</w:t></w:r><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="27"/><w:szCs w:val="27"/></w:rPr><w:br/><w:t>PHÂN TÍCH, THIẾT KẾ VÀ XÂY DỰNG HỆ THỐNG</w:t></w:r><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="27"/><w:szCs w:val="27"/></w:rPr><w:br/><w:t>ĐẶT HÀNG TẠI QUẦY VÀ ONLINE HỢP NHẤT</w:t></w:r></w:p>
<w:tbl>
  <w:tblPr><w:tblW w:w="0" w:type="auto"/><w:jc w:val="center"/><w:tblBorders><w:top w:val="none"/><w:left w:val="none"/><w:bottom w:val="none"/><w:right w:val="none"/><w:insideH w:val="none"/><w:insideV w:val="none"/></w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="15" w:type="dxa"/><w:left w:w="30" w:type="dxa"/><w:bottom w:w="25" w:type="dxa"/><w:right w:w="30" w:type="dxa"/></w:tblCellMar></w:tblPr>
  <w:tblGrid><w:gridCol w:w="2891"/><w:gridCol w:w="4365"/></w:tblGrid>
  <w:tr><w:trPr><w:jc w:val="center"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="2891" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="60" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Giảng viên hướng dẫn:</w:t></w:r></w:p></w:tc><w:tc><w:tcPr><w:tcW w:w="4365" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="60" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>ThS. Đặng Anh Tuấn</w:t></w:r></w:p></w:tc></w:tr>
  <w:tr><w:trPr><w:jc w:val="center"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="2891" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="60" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Lớp học phần:</w:t></w:r></w:p></w:tc><w:tc><w:tcPr><w:tcW w:w="4365" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="60" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>INT1498-20261-01</w:t></w:r></w:p></w:tc></w:tr>
  <w:tr><w:trPr><w:jc w:val="center"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="2891" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="60" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Nhóm thực hiện:</w:t></w:r></w:p></w:tc><w:tc><w:tcPr><w:tcW w:w="4365" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="60" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Nhóm 10</w:t></w:r></w:p></w:tc></w:tr>
  <w:tr><w:trPr><w:jc w:val="center"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="2891" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="0" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Sinh viên thực hiện:</w:t></w:r></w:p></w:tc><w:tc><w:tcPr><w:tcW w:w="4365" w:type="dxa"/></w:tcPr>
    <w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="50" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Nguyễn Xuân Bắc – B23DCCC016</w:t></w:r></w:p>
    <w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="50" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Đặng Thành Công – B23DCCC024</w:t></w:r></w:p>
    <w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="50" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Nguyễn Trung Dân – B23DCCC028</w:t></w:r></w:p>
    <w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="50" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Phạm Xuân Kỳ – B23DCCC092</w:t></w:r></w:p>
    <w:p><w:pPr><w:keepLines/><w:spacing w:before="0" w:after="0" w:line="288" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Nguyễn Đức Thành – B23DCCC152</w:t></w:r></w:p>
  </w:tc></w:tr>
</w:tbl>
<w:p>
  <w:pPr>
    <w:keepLines/><w:spacing w:before="820" w:after="0"/><w:jc w:val="center"/>
    <w:sectPr>
      <w:headerReference w:type="default" r:id="rIdHdrEmpty"/>
      <w:footerReference w:type="default" r:id="rIdFtrEmpty"/>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1332" w:right="1417" w:bottom="1021" w:left="1417" w:header="708" w:footer="708" w:gutter="0"/>
      <w:pgNumType w:start="1"/>
      <w:cols w:space="720"/>
    </w:sectPr>
  </w:pPr>
  <w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>Hà Nội – 2026</w:t></w:r>
</w:p>
"@
      foreach ($n in (Parse-Fragment $docXml $coverXml)) { $body.InsertBefore($n, $p) | Out-Null }
      $body.RemoveChild($p) | Out-Null
    }
    elseif ($txt -eq '__PTIT_TOC_PLACEHOLDER__') {
      $tocXml = @"
<w:p><w:pPr><w:keepNext/><w:spacing w:before="80" w:after="90"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000"/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr><w:t>MỤC LỤC</w:t></w:r></w:p>
<w:sdt>
  <w:sdtPr>
    <w:id w:val="901001"/>
    <w:docPartObj><w:docPartGallery w:val="Table of Contents"/><w:docPartUnique/></w:docPartObj>
  </w:sdtPr>
  <w:sdtContent>
    <w:p><w:pPr><w:pStyle w:val="TOC1"/></w:pPr><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \o "1-3" \h \z \u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Đang cập nhật mục lục...</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>
  </w:sdtContent>
</w:sdt>
"@
      foreach ($n in (Parse-Fragment $docXml $tocXml)) { $body.InsertBefore($n, $p) | Out-Null }
      $body.RemoveChild($p) | Out-Null
    }
    elseif ($txt -eq '__PTIT_SECTION_MAIN__') {
      # Continuous decimal numbering starting at 1 immediately after the Cover Page (no section reset)
      $body.RemoveChild($p) | Out-Null
    }
  }

  # Set final body <w:sectPr> (All pages after Cover: continuous decimal page numbers starting at 1, no header, bare centered footer)
  $finalSect = $body.SelectSingleNode('./w:sectPr', $mgrD)
  $sec3Xml = @"
<w:sectPr>
  <w:headerReference w:type="default" r:id="rIdHdrEmpty"/>
  <w:footerReference w:type="default" r:id="rIdFtrBody"/>
  <w:pgSz w:w="11906" w:h="16838"/>
  <w:pgMar w:top="1247" w:right="1134" w:bottom="1247" w:left="1701" w:header="708" w:footer="708" w:gutter="0"/>
  <w:pgNumType w:fmt="decimal" w:start="1"/>
  <w:cols w:space="720"/>
</w:sectPr>
"@
  $newSec3 = @(Parse-Fragment $docXml $sec3Xml)[0]
  if ($finalSect) { $body.ReplaceChild($newSec3, $finalSect) | Out-Null } else { $body.AppendChild($newSec3) | Out-Null }

  # Force explicit pageBreakBefore on main Heading1 boundaries & clean redundant page-break paragraphs
  $allParas = @($body.SelectNodes('./w:p', $mgrD))
  for ($pi = 0; $pi -lt $allParas.Count; $pi++) {
    $p = $allParas[$pi]
    $st = $p.SelectSingleNode('./w:pPr/w:pStyle/@w:val', $mgrD)
    if ($st -and $st.Value -eq 'Heading1') {
      $txt = $p.InnerText.Trim()
      if ($txt -match '^(PHẦN |LỜI MỞ ĐẦU|DANH MỤC |TÀI LIỆU THAM KHẢO)') {
        $pPr = $p.SelectSingleNode('./w:pPr', $mgrD)
        if (-not $pPr.SelectSingleNode('./w:pageBreakBefore', $mgrD)) {
          $pb = $docXml.CreateElement('w', 'pageBreakBefore', $wNs)
          $pStyleNode = $pPr.SelectSingleNode('./w:pStyle', $mgrD)
          if ($pStyleNode) { $pPr.InsertAfter($pb, $pStyleNode) | Out-Null } else { $pPr.PrependChild($pb) | Out-Null }
        }
        # Remove empty standalone <w:br w:type="page"/> paragraph right before this Heading1 to avoid blank pages
        $prev = $p.PreviousSibling
        while ($prev -and ($prev.LocalName -match '^bookmark')) { $prev = $prev.PreviousSibling }
        if ($prev -and $prev.LocalName -eq 'p' -and $prev.InnerText.Trim() -eq '' -and $prev.SelectSingleNode('.//w:br[@w:type="page"]', $mgrD) -and -not $prev.SelectSingleNode('.//w:sectPr', $mgrD)) {
          $body.RemoveChild($prev) | Out-Null
        }
      }
    }
    # Guarantee TableCaption/TableCaption0 sits cleanly below the table, centered, without gluing to the next section
    if ($st -and $st.Value -in @('TableCaption0','TableCaption')) {
      $pPrTc = $p.SelectSingleNode('./w:pPr', $mgrD)
      $psNode = $pPrTc.SelectSingleNode('./w:pStyle', $mgrD)
      foreach ($tag in @('keepNext','spacing','jc')) {
        $oldT = $pPrTc.SelectSingleNode("./w:$tag", $mgrD)
        if ($oldT) { $pPrTc.RemoveChild($oldT) | Out-Null }
      }
      $newPs = $docXml.CreateElement('w', 'pStyle', $wNs)
      $null = $newPs.SetAttribute('val', $wNs, 'TableCaption')
      $pPrTc.ReplaceChild($newPs, $psNode) | Out-Null
      $spTc = $docXml.CreateElement('w', 'spacing', $wNs); $null = $spTc.SetAttribute('before', $wNs, '45'); $null = $spTc.SetAttribute('after', $wNs, '160'); $pPrTc.AppendChild($spTc) | Out-Null
      $jcTc = $docXml.CreateElement('w', 'jc', $wNs); $null = $jcTc.SetAttribute('val', $wNs, 'center'); $pPrTc.AppendChild($jcTc) | Out-Null
    }
    # Style inline SourceCode or blockquotes & ensure CaptionedFigure has keepNext
    if ($st -and $st.Value -in @('BlockText','Preformatted')) {
      $null = $p.SelectSingleNode('./w:pPr/w:pStyle', $mgrD).SetAttribute('val', $wNs, 'SourceCode')
    }
    $drawing = $p.SelectSingleNode('.//w:drawing', $mgrD)
    if ($drawing -and -not $drawing.SelectSingleNode('.//wp:anchor', $mgrD)) {
      # Keep inline figure together with caption below
      $pPr = $p.SelectSingleNode('./w:pPr', $mgrD)
      if (-not $pPr) { $pPr = $docXml.CreateElement('w', 'pPr', $wNs); $p.PrependChild($pPr) | Out-Null }
      if (-not $pPr.SelectSingleNode('./w:keepNext', $mgrD)) {
        $kn = $docXml.CreateElement('w', 'keepNext', $wNs)
        $pStyleNode = $pPr.SelectSingleNode('./w:pStyle', $mgrD)
        if ($pStyleNode) { $pPr.InsertAfter($kn, $pStyleNode) | Out-Null } else { $pPr.PrependChild($kn) | Out-Null }
      }
      if (-not $pPr.SelectSingleNode('./w:jc', $mgrD)) {
        $jc = $docXml.CreateElement('w', 'jc', $wNs); $null = $jc.SetAttribute('val', $wNs, 'center'); $pPr.AppendChild($jc) | Out-Null
      }
      # Ensure inline diagram fits cleanly within printable area (max width 5544000 EMU = 15.4cm, max height 7200000 EMU = 20.0cm)
      foreach ($ext in @($drawing.SelectNodes('.//wp:extent', $mgrD))) {
        $cx = [int64]$ext.GetAttribute('cx')
        $cy = [int64]$ext.GetAttribute('cy')
        if ($cx -gt 0 -and $cy -gt 0) {
          $maxW = 5544000; $maxH = 7200000
          $scale = 1.0
          if ($cx -gt $maxW) { $scale = [Math]::Min($scale, $maxW / $cx) }
          if ($cy -gt $maxH) { $scale = [Math]::Min($scale, $maxH / $cy) }
          if ($scale -lt 1.0) {
            $ncx = [int64][Math]::Round($cx * $scale)
            $ncy = [int64][Math]::Round($cy * $scale)
            $null = $ext.SetAttribute('cx', "$ncx")
            $null = $ext.SetAttribute('cy', "$ncy")
            $aMgr = New-Object System.Xml.XmlNamespaceManager($docXml.NameTable); $aMgr.AddNamespace('a', $aNs)
            foreach ($xfExt in @($drawing.SelectNodes('.//a:ext', $aMgr))) {
              $null = $xfExt.SetAttribute('cx', "$ncx")
              $null = $xfExt.SetAttribute('cy', "$ncy")
            }
          }
        }
      }
    }
  }

  # 6. Upgrade ALL content tables: smart proportional column widths (sum = 9071 dxa), cantSplit, tblHeader, crisp header & zebra shading!
  $TOTAL_W = 9071
  foreach ($tbl in @($body.SelectNodes('./w:tbl', $mgrD))) {
    $tblPr = $tbl.SelectSingleNode('./w:tblPr', $mgrD)
    # Skip our 2 borderless cover layout tables!
    if ($tblPr -and $tblPr.InnerXml -match 'w:val="none"') { continue }

    $rows = @($tbl.SelectNodes('./w:tr', $mgrD))
    if ($rows.Count -eq 0) { continue }
    $firstCells = @($rows[0].SelectNodes('./w:tc', $mgrD))
    $nCols = $firstCells.Count
    if ($nCols -le 0) { continue }

    $colNames = @()
    for ($c = 0; $c -lt $nCols; $c++) { $colNames += ($firstCells[$c].InnerText -replace '\s+', ' ').Trim() }
    $hdr0 = $colNames[0]
    $hdr2 = if ($nCols -gt 2) { $colNames[2] } else { '' }

    $widths = $null
    $cellSz = '19'     # 9.5pt default clean academic table font
    $cellPadH = '75'   # horizontal cell padding dxa
    $isCenterCol = New-Object bool[] $nCols

    if ($nCols -eq 6 -and $hdr0 -eq 'Field') {
      # 24 DB schema tables: widen Key if FK reference present, plus Field & Type
      $hasLongKey = $false
      foreach ($r in $rows) {
        $cs = @($r.SelectNodes('./w:tc', $mgrD))
        if ($cs.Count -gt 3 -and $cs[3].InnerText.Trim().Length -gt 5) { $hasLongKey = $true; break }
      }
      $widths = if ($hasLongKey) { @(1940, 1500, 480, 1280, 1020, 2851) } else { @(2080, 1480, 560, 580, 1180, 3191) }
      $cellPadH = '60'
      $isCenterCol[2] = $true; if (-not $hasLongKey) { $isCenterCol[3] = $true }
    } elseif ($nCols -eq 10) {
      # Bảng 4.8 JMeter 10-column table: ensure STT, 1.500, 0,00% never wrap mid-token
      $widths = @(520, 1920, 680, 770, 740, 660, 760, 760, 760, 1501)
      $cellSz = '18'; $cellPadH = '50'
      foreach ($ci in @(0,2,3,4,5,6,7,8,9)) { $isCenterCol[$ci] = $true }
    } elseif ($nCols -eq 8) {
      # Bảng 4.9 E2E latency 8-column table
      $widths = @(1250, 1380, 1150, 1060, 1080, 1060, 1000, 1091)
      $cellSz = '19'; $cellPadH = '60'
      for ($ci = 0; $ci -lt 8; $ci++) { $isCenterCol[$ci] = $true }
    } elseif ($nCols -eq 6 -and $hdr0 -eq 'Giải pháp') {
      # Bảng 1.1 Market solutions comparison: keep Lightspeed / MISA CukCuk unbroken on 1 line
      $widths = @(1280, 1120, 1680, 1780, 1600, 1611)
      $cellSz = '19'; $cellPadH = '65'
      $isCenterCol[1] = $true
    } elseif ($nCols -eq 4 -and $hdr0 -eq 'STT' -and $hdr2 -eq 'Tên bảng') {
      # Bảng 2.5 List of 24 tables
      $widths = @(560, 1650, 2150, 4711)
      $cellSz = '19'; $cellPadH = '70'
      $isCenterCol[0] = $true
    } else {
      # Compute column weight heuristic from header label + cell text lengths
      $colScores = New-Object double[] $nCols
      $minWidths = New-Object int[] $nCols

      for ($c = 0; $c -lt $nCols; $c++) {
        $hdrTxt = $colNames[$c]
        $sumLen = 0
        $maxLen = 0
        foreach ($r in $rows) {
          $cells = @($r.SelectNodes('./w:tc', $mgrD))
          if ($c -lt $cells.Count) {
            $t = ($cells[$c].InnerText -replace '\s+', ' ').Trim()
            if ($t.Length -gt $maxLen) { $maxLen = $t.Length }
            $sumLen += [Math]::Min($t.Length, 140)
          }
        }
        $avgLen = $sumLen / [Math]::Max(1, $rows.Count)
        $score = [Math]::Max($avgLen * 1.15, $maxLen * 0.65)
        $minW = [Math]::Max(520, [Math]::Min(1800, ($hdrTxt.Length * 95) + 260))

        if ($hdrTxt -match '^(STT|TT)$') {
          $minW = 540; $score = 4; $isCenterCol[$c] = $true
        } elseif ($hdrTxt -match '^(Null|Tầng|Số test|Lỗi|Lỗi %|Mẫu)$') {
          $minW = 680; $score = 8; $isCenterCol[$c] = $true
        } elseif ($hdrTxt -match '^(Kết quả|Trạng thái)$') {
          $minW = 920; $score = 12; $isCenterCol[$c] = $true
        } elseif ($hdrTxt -match '^(Mã|Ký hiệu|Mã ca|Thấp nhất|Cao nhất|Trung bình|Trung vị|95%|Thông lượng)') {
          $minW = [Math]::Max(860, [Math]::Min(1400, $hdrTxt.Length * 95 + 220))
          $score = [Math]::Max($score, 12)
          if ($hdrTxt -match '^(Thấp nhất|Cao nhất|Trung bình|Trung vị|95%|Thông lượng|Số người|Tổng số)') { $isCenterCol[$c] = $true }
        } elseif ($hdrTxt -match '^(Kiểu dữ liệu|Kiểu)$') {
          $minW = 1350; $score = [Math]::Max($score, 20)
        } elseif ($hdrTxt -match '^(Tên bảng|Tên trường|Thuộc tính|Mặc định)') {
          $minW = 1400; $score = [Math]::Max($score, 22)
        }
        $minWidths[$c] = $minW
        $colScores[$c] = [Math]::Max(6.0, $score)
      }

      $sumMin = ($minWidths | Measure-Object -Sum).Sum
      $widths = New-Object int[] $nCols
      if ($sumMin -ge $TOTAL_W) {
        for ($c = 0; $c -lt $nCols; $c++) {
          $widths[$c] = [int][Math]::Floor($TOTAL_W * $minWidths[$c] / $sumMin)
        }
      } else {
        $rem = $TOTAL_W - $sumMin
        $sumScore = ($colScores | Measure-Object -Sum).Sum
        for ($c = 0; $c -lt $nCols; $c++) {
          $widths[$c] = $minWidths[$c] + [int][Math]::Floor($rem * ($colScores[$c] / $sumScore))
        }
      }
      $widestIdx = 0
      for ($c = 1; $c -lt $nCols; $c++) { if ($widths[$c] -gt $widths[$widestIdx]) { $widestIdx = $c } }
      $widths[$widestIdx] += ($TOTAL_W - ($widths | Measure-Object -Sum).Sum)
    }

    # Rewrite tblPr (ECMA-376 strict order: tblStyle, tblW, tblBorders, tblLayout, tblCellMar, tblLook) + tblGrid
    if (-not $tblPr) { $tblPr = $docXml.CreateElement('w', 'tblPr', $wNs); $tbl.PrependChild($tblPr) | Out-Null }
    $tblPr.RemoveAll()
    $cellPadV = if ($rows.Count -ge 16) { '40' } else { '48' }
    $tblPrFrag = @"
<w:tblStyle w:val="Table"/>
<w:tblW w:w="$TOTAL_W" w:type="dxa"/>
<w:tblBorders>
  <w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>
  <w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>
  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>
  <w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>
  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>
  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>
</w:tblBorders>
<w:tblLayout w:type="fixed"/>
<w:tblCellMar><w:top w:w="$cellPadV" w:type="dxa"/><w:left w:w="$cellPadH" w:type="dxa"/><w:bottom w:w="$cellPadV" w:type="dxa"/><w:right w:w="$cellPadH" w:type="dxa"/></w:tblCellMar>
<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="1" w:noVBand="1"/>
"@
    foreach ($n in @(Parse-Fragment $docXml $tblPrFrag)) { $tblPr.AppendChild($n) | Out-Null }

    $tblGrid = $tbl.SelectSingleNode('./w:tblGrid', $mgrD)
    if ($tblGrid) { $tblGrid.RemoveAll() } else { $tblGrid = $docXml.CreateElement('w', 'tblGrid', $wNs); $tbl.InsertAfter($tblGrid, $tblPr) | Out-Null }
    for ($c = 0; $c -lt $nCols; $c++) {
      $gc = $docXml.CreateElement('w', 'gridCol', $wNs)
      $null = $gc.SetAttribute('w', $wNs, "$($widths[$c])")
      $tblGrid.AppendChild($gc) | Out-Null
    }

    # Check whether this table is followed directly by a TableCaption below it
    $nextAfterTbl = $tbl.NextSibling
    while ($nextAfterTbl -and ($nextAfterTbl.NodeType -ne [System.Xml.XmlNodeType]::Element -or $nextAfterTbl.LocalName -match '^bookmark')) { $nextAfterTbl = $nextAfterTbl.NextSibling }
    $hasBottomCaption = $false
    if ($nextAfterTbl -and $nextAfterTbl.LocalName -eq 'p') {
      $pStyleEl = $nextAfterTbl.SelectSingleNode('./w:pPr/w:pStyle', $mgrD)
      $nStVal = if ($pStyleEl) { $pStyleEl.GetAttribute('val', $wNs) } else { '' }
      if ($nStVal -in @('TableCaption','TableCaption0') -or $nextAfterTbl.InnerText.Trim() -match '^Bảng\s+\d+\.\d+\.') {
        $hasBottomCaption = $true
      }
    }

    # Style each row and cell explicitly
    for ($ri = 0; $ri -lt $rows.Count; $ri++) {
      $tr = $rows[$ri]
      $trPr = $tr.SelectSingleNode('./w:trPr', $mgrD)
      if (-not $trPr) { $trPr = $docXml.CreateElement('w', 'trPr', $wNs); $tr.PrependChild($trPr) | Out-Null }
      if (-not $trPr.SelectSingleNode('./w:cantSplit', $mgrD)) { $trPr.AppendChild($docXml.CreateElement('w', 'cantSplit', $wNs)) | Out-Null }
      if ($ri -eq 0 -and -not $trPr.SelectSingleNode('./w:tblHeader', $mgrD)) { $trPr.AppendChild($docXml.CreateElement('w', 'tblHeader', $wNs)) | Out-Null }

      $cells = @($tr.SelectNodes('./w:tc', $mgrD))
      for ($ci = 0; $ci -lt $cells.Count; $ci++) {
        $tc = $cells[$ci]
        $tcPr = $tc.SelectSingleNode('./w:tcPr', $mgrD)
        if (-not $tcPr) { $tcPr = $docXml.CreateElement('w', 'tcPr', $wNs); $tc.PrependChild($tcPr) | Out-Null }
        $tcPr.RemoveAll()
        if ($ci -lt $widths.Count) {
          $tcW = $docXml.CreateElement('w', 'tcW', $wNs)
          $null = $tcW.SetAttribute('w', $wNs, "$($widths[$ci])")
          $null = $tcW.SetAttribute('type', $wNs, 'dxa')
          $tcPr.AppendChild($tcW) | Out-Null
        }
        if ($ri -eq 0) {
          $va = $docXml.CreateElement('w', 'vAlign', $wNs); $null = $va.SetAttribute('val', $wNs, 'center'); $tcPr.AppendChild($va) | Out-Null
        }

        # Normalize cell paragraphs and runs in strict schema order
        foreach ($cp in @($tc.SelectNodes('./w:p', $mgrD))) {
          $cpPr = $cp.SelectSingleNode('./w:pPr', $mgrD)
          if (-not $cpPr) { $cpPr = $docXml.CreateElement('w', 'pPr', $wNs); $cp.PrependChild($cpPr) | Out-Null }
          foreach ($tag in @('keepNext','spacing','jc')) {
            $oldTag = $cpPr.SelectSingleNode("./w:$tag", $mgrD)
            if ($oldTag) { $cpPr.RemoveChild($oldTag) | Out-Null }
          }
          $needKeepNext = ($ri -eq 0) -or ($hasBottomCaption -and $ri -eq ($rows.Count - 1))
          if ($needKeepNext) {
            $kn = $docXml.CreateElement('w', 'keepNext', $wNs)
            $cpStyle = $cpPr.SelectSingleNode('./w:pStyle', $mgrD)
            if ($cpStyle) { $cpPr.InsertAfter($kn, $cpStyle) | Out-Null } else { $cpPr.PrependChild($kn) | Out-Null }
          }
          $sp = $docXml.CreateElement('w', 'spacing', $wNs)
          $null = $sp.SetAttribute('before', $wNs, '15'); $null = $sp.SetAttribute('after', $wNs, '20'); $null = $sp.SetAttribute('line', $wNs, '230'); $null = $sp.SetAttribute('lineRule', $wNs, 'auto')
          $cpPr.AppendChild($sp) | Out-Null

          $jc = $docXml.CreateElement('w', 'jc', $wNs)
          if ($ci -lt $isCenterCol.Count -and $isCenterCol[$ci]) { $null = $jc.SetAttribute('val', $wNs, 'center') } else { $null = $jc.SetAttribute('val', $wNs, 'left') }
          $cpPr.AppendChild($jc) | Out-Null

          foreach ($run in @($cp.SelectNodes('.//w:r', $mgrD))) {
            $rPr = $run.SelectSingleNode('./w:rPr', $mgrD)
            if (-not $rPr) { $rPr = $docXml.CreateElement('w', 'rPr', $wNs); $run.PrependChild($rPr) | Out-Null }
            $hadBold = $null -ne $rPr.SelectSingleNode('./w:b', $mgrD)
            $hadItalic = $null -ne $rPr.SelectSingleNode('./w:i', $mgrD)
            $rStyleNode = $rPr.SelectSingleNode('./w:rStyle', $mgrD)
            $rPr.RemoveAll()
            if ($rStyleNode -and $ri -gt 0) { $rPr.AppendChild($rStyleNode) | Out-Null }
            if ($ri -eq 0 -or $hadBold) {
              $rPr.AppendChild($docXml.CreateElement('w', 'b', $wNs)) | Out-Null
              $rPr.AppendChild($docXml.CreateElement('w', 'bCs', $wNs)) | Out-Null
            }
            if ($hadItalic) {
              $rPr.AppendChild($docXml.CreateElement('w', 'i', $wNs)) | Out-Null
              $rPr.AppendChild($docXml.CreateElement('w', 'iCs', $wNs)) | Out-Null
            }
            $colEl = $docXml.CreateElement('w', 'color', $wNs)
            $null = $colEl.SetAttribute('val', $wNs, '000000')
            $rPr.AppendChild($colEl) | Out-Null
            $szEl = $docXml.CreateElement('w', 'sz', $wNs); $null = $szEl.SetAttribute('val', $wNs, $cellSz); $rPr.AppendChild($szEl) | Out-Null
            $szCsEl = $docXml.CreateElement('w', 'szCs', $wNs); $null = $szCsEl.SetAttribute('val', $wNs, $cellSz); $rPr.AppendChild($szCsEl) | Out-Null
          }
        }
      }
    }
  }

  # Guarantee zero trailing blank page when document ends with a table right before final sectPr
  $finalSecNode = $body.SelectSingleNode('./w:sectPr', $mgrD)
  if ($finalSecNode) {
    $prevEl = $finalSecNode.PreviousSibling
    while ($prevEl -and ($prevEl.LocalName -match '^bookmark')) { $prevEl = $prevEl.PreviousSibling }
    if ($prevEl -and $prevEl.LocalName -eq 'tbl') {
      $tinyPara = @(Parse-Fragment $docXml '<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/><w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr></w:pPr></w:p>')[0]
      $body.InsertBefore($tinyPara, $finalSecNode) | Out-Null
    } elseif ($prevEl -and $prevEl.LocalName -eq 'p' -and $prevEl.InnerText.Trim() -eq '') {
      $pPrTail = $prevEl.SelectSingleNode('./w:pPr', $mgrD)
      if (-not $pPrTail) { $pPrTail = $docXml.CreateElement('w', 'pPr', $wNs); $prevEl.PrependChild($pPrTail) | Out-Null }
      $pPrTail.RemoveAll()
      foreach ($n in @(Parse-Fragment $docXml '<w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/><w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr>')) { $pPrTail.AppendChild($n) | Out-Null }
    }
  }

  # Final sweep: replace any remaining TableCaption0 anywhere in document.xml
  $tcFixed = 0
  foreach ($ps in @($docXml.SelectNodes('.//w:pStyle[@w:val="TableCaption0"]', $mgrD))) {
    $pPrNode = $ps.ParentNode
    $newPs = $docXml.CreateElement('w', 'pStyle', $wNs)
    $null = $newPs.SetAttribute('val', $wNs, 'TableCaption')
    $pPrNode.ReplaceChild($newPs, $ps) | Out-Null
    $tcFixed++
  }
  Write-Host "Normalized TableCaption styles: $tcFixed"

  Save-XmlFile $docXml $docPath

  # 7. Repack DOCX strictly with forward slashes '/' (ZipArchive compatibility!)
  $tmpOut = "$DocxPath.tmp"
  if (Test-Path $tmpOut) { Remove-Item $tmpOut -Force }
  $outFs = [System.IO.File]::Open($tmpOut, [System.IO.FileMode]::Create)
  $zipWrite = New-Object System.IO.Compression.ZipArchive($outFs, [System.IO.Compression.ZipArchiveMode]::Create)
  try {
    $allFiles = Get-ChildItem $workDir -Recurse -File
    foreach ($f in $allFiles) {
      $rel = $f.FullName.Substring($workDir.Length + 1).Replace('\', '/')
      $ent = $zipWrite.CreateEntry($rel, [System.IO.Compression.CompressionLevel]::Optimal)
      $es = $ent.Open()
      $fsIn = [System.IO.File]::OpenRead($f.FullName)
      $fsIn.CopyTo($es)
      $fsIn.Close(); $es.Close()
    }
  } finally {
    $zipWrite.Dispose()
    $outFs.Close()
  }
  Move-Item $tmpOut $DocxPath -Force
  Write-Host "Polished DOCX cleanly: $DocxPath ($([Math]::Round((Get-Item $DocxPath).Length / 1KB, 1)) KB)"
} finally {
  if (Test-Path $workDir) { Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue }
}
