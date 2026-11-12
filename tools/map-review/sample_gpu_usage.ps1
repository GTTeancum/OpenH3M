$sample = Get-Counter '\GPU Engine(*)\Utilization Percentage' -ErrorAction Stop
$rows = foreach ($counter in $sample.CounterSamples) {
    if ($counter.CookedValue -lt 0.1) { continue }
    $processNumber = 0
    if ($counter.InstanceName -match '^pid_(\d+)_') { $processNumber = [int]$Matches[1] }
    $processName = (Get-Process -Id $processNumber -ErrorAction SilentlyContinue).ProcessName
    [pscustomobject]@{ instance=$counter.InstanceName; process_id=$processNumber; process=$processName; percent=$counter.CookedValue }
}
@{ utc=$sample.Timestamp.ToUniversalTime().ToString('o'); engines=@($rows) } | ConvertTo-Json -Depth 4 -Compress
