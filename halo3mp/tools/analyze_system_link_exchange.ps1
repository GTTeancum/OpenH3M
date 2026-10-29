param(
    [string]$HostLogPath = "",
    [string]$FindLogPath = "",
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ([string]::IsNullOrWhiteSpace($HostLogPath)) {
    $HostLogPath = Join-Path $projectRoot "out\build\win-amd64-release\system_link_probe\system_link_probe.log"
}
if ([string]::IsNullOrWhiteSpace($FindLogPath)) {
    $FindLogPath = Join-Path $projectRoot "out\build\win-amd64-release\system_link_find_probe\system_link_probe.log"
}
foreach ($path in @($HostLogPath, $FindLogPath)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing System Link exchange log: $path"
    }
}

function Read-ExchangeLog {
    param([string]$Path, [ValidateSet("Host", "Find")][string]$Role)

    $result = [ordered]@{
        Role = $Role
        RouteConfirmed = $false
        VirtualizedPorts = New-Object 'System.Collections.Generic.HashSet[int]'
        TitleSizes = New-Object 'System.Collections.Generic.List[int]'
        ReceivedSizes = New-Object 'System.Collections.Generic.List[int]'
        DeliveredPackets = 0
        PayloadLoggingDisabled = $true
        CleanShutdown = $false
        FatalCount = 0
    }
    $expectedRoute = if ($Role -eq "Host") { "system-link-host-probe" } else { "system-link-find-probe" }

    foreach ($line in (Get-Content -LiteralPath $Path)) {
        if ($line -match "Halo3MP smoke context route='$expectedRoute'") {
            $result.RouteConfirmed = $true
        }
        if ($line -match "bind caller=.* port=(1000|1001) virtualized=true result=0") {
            [void]$result.VirtualizedPorts.Add([int]$Matches[1])
        }
        if ($line -match "System Link title datagram .* bytes=(\d+) .* payload_log=false") {
            $result.TitleSizes.Add([int]$Matches[1])
        }
        if ($line -match "System Link console datagram bytes=(\d+).* delivered=(\d+).* payload_log=false") {
            $result.ReceivedSizes.Add([int]$Matches[1])
            $result.DeliveredPackets += [int]$Matches[2]
        }
        if ($line -match "payload_log=true") {
            $result.PayloadLoggingDisabled = $false
        }
        if ($line -match "Window closing, shutting down|Title terminated; hard-exiting process") {
            $result.CleanShutdown = $true
        }
        if ($line -match "fatal|panic|bugcheck|access violation|0x80000003|ASSERT") {
            ++$result.FatalCount
        }
    }
    return [pscustomobject]$result
}

$hostResult = Read-ExchangeLog -Path $HostLogPath -Role Host
$findResult = Read-ExchangeLog -Path $FindLogPath -Role Find
$finderQueryObserved = $findResult.TitleSizes -contains 14
$hostConsumedQuery = $hostResult.ReceivedSizes -contains 14
$hostResponseSizes = @($hostResult.TitleSizes | Where-Object { $_ -gt 14 })
$hostResponseObserved = $hostResponseSizes.Count -gt 0
$finderConsumedResponse = @($findResult.ReceivedSizes | Where-Object { $hostResponseSizes -contains $_ }).Count -gt 0
$portsVirtualized = @($hostResult.VirtualizedPorts).Count -eq 2 -and @($findResult.VirtualizedPorts).Count -eq 2
$privacySafe = $hostResult.PayloadLoggingDisabled -and $findResult.PayloadLoggingDisabled
$clean = $hostResult.CleanShutdown -and $findResult.CleanShutdown
$fatalCount = $hostResult.FatalCount + $findResult.FatalCount
$exchangeComplete = $hostResult.RouteConfirmed -and $findResult.RouteConfirmed -and $portsVirtualized -and
    $finderQueryObserved -and $hostConsumedQuery -and $hostResponseObserved -and
    $finderConsumedResponse -and $privacySafe -and $clean -and $fatalCount -eq 0

$result = [pscustomobject]@{
    Status = if ($exchangeComplete) { "exchange_complete" } else { "exchange_incomplete" }
    ExchangeComplete = $exchangeComplete
    PortsVirtualized = $portsVirtualized
    FinderQueryObserved = $finderQueryObserved
    HostConsumedQuery = $hostConsumedQuery
    HostResponseObserved = $hostResponseObserved
    HostResponseSizes = $hostResponseSizes
    FinderConsumedResponse = $finderConsumedResponse
    HostDeliveredPackets = $hostResult.DeliveredPackets
    FinderDeliveredPackets = $findResult.DeliveredPackets
    PayloadLoggingDisabled = $privacySafe
    CleanShutdown = $clean
    FatalCount = $fatalCount
    HostLogPath = (Resolve-Path -LiteralPath $HostLogPath).Path
    FindLogPath = (Resolve-Path -LiteralPath $FindLogPath).Path
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 3
} else {
    $result | Format-List
}

if (-not $exchangeComplete) {
    exit 1
}
