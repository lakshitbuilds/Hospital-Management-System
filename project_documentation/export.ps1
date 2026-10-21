$ErrorActionPreference = 'Stop'
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open((Join-Path $PSScriptRoot 'HMS_Project_Documentation.docx'), $false, $false)
    $document.Repaginate()
    $document.Fields.Update() | Out-Null
    foreach ($toc in $document.TablesOfContents) { $toc.Update() }
    $document.Repaginate()
    foreach ($toc in $document.TablesOfContents) { $toc.UpdatePageNumbers() }
    $document.Save()
    $pageCount = $document.ComputeStatistics(2)
    $document.ExportAsFixedFormat((Join-Path $PSScriptRoot 'HMS_Project_Documentation.pdf'), 17)
    Write-Output "Exported $pageCount pages"
} finally {
    if ($null -ne $document) { $document.Close($false) }
    if ($null -ne $word) { $word.Quit() }
}
