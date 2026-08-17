param(
    [string]$LogPath = "",
    [switch]$RequireConsoleDatagram,
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = Join-Path $projectRoot "out\build\win-amd64-release\system_link_probe\system_link_probe.log"
}
if (-not (Test-Path -LiteralPath $LogPath)) {
    throw "Missing System Link probe log: $LogPath"
}

$listenerPort = 0
$titleLanKeyPresent = $false
$systemFlagsPresent = $false
$systemFlags = ""
$crossPlatform = $null
$insecureSockets = $null
$xbox1Interop = $null
$hostRoute = $false
$keyCreated = $false
$keyRegistered = $false
$privacySafe = $true
$cleanShutdown = $false
$fatalLines = New-Object System.Collections.Generic.List[string]
$sources = New-Object 'System.Collections.Generic.HashSet[string]'
$loggedDatagrams = 0
$observedDatagrams = 0

foreach ($line in (Get-Content -LiteralPath $LogPath)) {
    if ($line -match "Halo3MP smoke context route='system-link-host-probe' expected_state='system_link_host_lobby'") {
        $hostRoute = $true
    }
    if ($line -match "System Link title LAN key present=(true|false) transport_port=(\d+)") {
        $titleLanKeyPresent = $Matches[1] -eq "true"
    }
    if ($line -match "System Link title flags present=(true|false) value=(0x[0-9a-fA-F]+) cross_platform=(true|false) insecure_sockets=(true|false) xbox1_interop=(true|false)") {
        $systemFlagsPresent = $Matches[1] -eq "true"
        $systemFlags = $Matches[2]
        $crossPlatform = $Matches[3] -eq "true"
        $insecureSockets = $Matches[4] -eq "true"
        $xbox1Interop = $Matches[5] -eq "true"
    }
    if ($line -match "System Link console transport listening UDP port=(\d+) payload_log=false") {
        $listenerPort = [int]$Matches[1]
    }
    if ($line -match "\[xnet\] XNetCreateKey .* result=0") {
        $keyCreated = $true
    }
    if ($line -match "\[xnet\] XNetRegisterKey .* registered=\d+ result=0") {
        $keyRegistered = $true
    }
    if ($line -match "System Link console datagram bytes=(\d+) address=(0x[0-9a-fA-F]+) port=(\d+) packets=(\d+) payload_log=(true|false)") {
        ++$loggedDatagrams
        $observedDatagrams = [math]::Max($observedDatagrams, [int64]$Matches[4])
        $privacySafe = $privacySafe -and ($Matches[5] -eq "false")

        $rawAddress = [Convert]::ToUInt32($Matches[2].Substring(2), 16)
        $addressBytes = [BitConverter]::GetBytes($rawAddress)
        $ipAddress = (New-Object System.Net.IPAddress -ArgumentList (,$addressBytes)).ToString()
        [void]$sources.Add("$($ipAddress):$($Matches[3])")
    }
    if ($line -match "payload_log=true") {
        $privacySafe = $false
    }
    if ($line -match "Window closing, shutting down|Title terminated; hard-exiting process") {
        $cleanShutdown = $true
    }
    if ($line -match "fatal|panic|bugcheck|access violation|0x80000003|ASSERT") {
        $fatalLines.Add($line)
    }
}

$hostTransportReady = $hostRoute -and $titleLanKeyPresent -and $systemFlagsPresent -and
    $listenerPort -eq 3074 -and $keyCreated -and $keyRegistered
$consoleTrafficObserved = $observedDatagrams -gt 0
$status = if (-not $privacySafe) {
    "privacy_violation"
} elseif ($fatalLines.Count -gt 0) {
    "fatal"
} elseif (-not $hostTransportReady) {
    "host_not_ready"
} elseif ($consoleTrafficObserved) {
    "console_datagrams_observed"
} else {
    "host_ready_no_console_traffic"
}

$result = [pscustomobject]@{
    Status = $status
    HostTransportReady = $hostTransportReady
    ListenerPort = $listenerPort
    TitleLanKeyPresent = $titleLanKeyPresent
    SystemFlags = $systemFlags
    CrossPlatformSystemLink = $crossPlatform
    InsecureSockets = $insecureSockets
    Xbox1Interop = $xbox1Interop
    KeyCreated = $keyCreated
    KeyRegistered = $keyRegistered
    ConsoleTrafficObserved = $consoleTrafficObserved
    ObservedDatagrams = $observedDatagrams
    LoggedDatagrams = $loggedDatagrams
    Sources = @($sources | Sort-Object)
    PayloadLoggingDisabled = $privacySafe
    CleanShutdown = $cleanShutdown
    FatalCount = $fatalLines.Count
    LogPath = (Resolve-Path -LiteralPath $LogPath).Path
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 3
} else {
    $result | Format-List
}

if (-not $privacySafe) {
    exit 3
}
if ($fatalLines.Count -gt 0 -or -not $hostTransportReady) {
    exit 1
}
if ($RequireConsoleDatagram -and -not $consoleTrafficObserved) {
    exit 2
}
