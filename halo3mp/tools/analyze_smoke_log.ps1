param(
    [string]$LogPath = "",
    [int]$TailSamples = 60
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$logRoot = Join-Path $projectRoot "out\build\win-amd64-release\logs"

if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $latest = Get-ChildItem -Path $logRoot -Filter "halo3mp_*.log" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        throw "No halo3mp logs found under $logRoot"
    }
    $LogPath = $latest.FullName
}

if (-not (Test-Path -LiteralPath $LogPath)) {
    throw "Missing log: $LogPath"
}

$lines = Get-Content -LiteralPath $LogPath
$gameplayMaps = New-Object System.Collections.Generic.List[string]
$autosaves = New-Object System.Collections.Generic.List[string]
$fps = New-Object System.Collections.Generic.List[double]
$fpsAfterGameplay = New-Object System.Collections.Generic.List[double]
$fpsRecords = New-Object System.Collections.Generic.List[object]
$eventRecords = New-Object System.Collections.Generic.List[object]
$xamUserSummaryRecords = New-Object System.Collections.Generic.List[object]
$xgiSessionRecords = New-Object System.Collections.Generic.List[object]
$activeUsers = New-Object 'System.Collections.Generic.HashSet[int]'
$localUserMasks = New-Object System.Collections.Generic.List[string]
$fatalLines = New-Object System.Collections.Generic.List[string]
$context = ""
$firstGameplayLine = -1
$firstAutosaveLine = -1
$firstExpectedUserMaskLine = -1
$expectedPlayers = $null
$expectedPlayerMask = $null

function Get-LocalUserCountFromMask {
    param([int]$Mask)

    $count = 0
    for ($bit = 0; $bit -lt 4; ++$bit) {
        if (($Mask -band (1 -shl $bit)) -ne 0) {
            ++$count
        }
    }
    return $count
}

for ($i = 0; $i -lt $lines.Count; ++$i) {
    $line = $lines[$i]

    if ($line -match "Halo3MP smoke context") {
        $context = $line
        if ($line -match "players=(\d+)") {
            $expectedPlayers = [int]$Matches[1]
            $expectedPlayerMask = (1 -shl $expectedPlayers) - 1
        }
    }

    if ($line -match "\[open\]\s+d:\\maps\\([^\\]+)\.map\b") {
        $map = $Matches[1]
        if ($map -notin @("mainmenu", "shared", "campaign")) {
            $gameplayMaps.Add($map)
            if ($firstGameplayLine -lt 0) {
                $firstGameplayLine = $i
            }
        }
    }

    if ($line -match "\[open\]\s+cache1:\\autosave\\([^\\]+\.temp)\b") {
        $autosaves.Add($Matches[1])
        if ($firstAutosaveLine -lt 0) {
            $firstAutosaveLine = $i
        }
    }

    if ($line -match "guest-output FPS\s+([0-9]+(?:\.[0-9]+)?)") {
        $sample = [double]$Matches[1]
        $fps.Add($sample)
        $fpsRecords.Add([pscustomobject]@{ Line = $i; Fps = $sample })
        if ($firstGameplayLine -ge 0 -and $i -gt $firstGameplayLine) {
            $fpsAfterGameplay.Add($sample)
        }
    }

    if ($line -match "\[open\]\s+cache1:\\upload_queue\\") {
        $eventRecords.Add([pscustomobject]@{ Line = $i; Kind = "upload_queue_open" })
    }

    if ($line -match "GPU context update") {
        $eventRecords.Add([pscustomobject]@{ Line = $i; Kind = "gpu_context_update" })
    }

    if ($line -match "\[vblank\]\s+guest interrupt callback") {
        $eventRecords.Add([pscustomobject]@{ Line = $i; Kind = "vblank_callback" })
    }

    if ($line -match "\[fiber\]\s+summary") {
        $eventRecords.Add([pscustomobject]@{ Line = $i; Kind = "fiber_summary" })
    }

    if ($line -match "\[xam-user\]\s+summary\s+t=(\d+)ms\s+mask=(0x[0-9a-fA-F]+)\s+users=(\d+)\s+(.*)$") {
        $summaryTimeMs = [int]$Matches[1]
        $summaryMask = $Matches[2]
        $summaryUsers = [int]$Matches[3]
        $summaryCounts = $Matches[4]
        $counts = @{}
        foreach ($part in ($summaryCounts -split "\s+")) {
            if ($part -match "^([^=]+)=(\d+)$") {
                $countName = $Matches[1]
                $countValue = [int64]$Matches[2]
                $counts[$countName] = $countValue
            }
        }
        $xamUserSummaryRecords.Add([pscustomobject]@{
            Line = $i
            TimeMs = $summaryTimeMs
            Mask = $summaryMask
            Users = $summaryUsers
            Counts = $counts
        })
    }

    if ($line -match "\[xgi-session\]\s+name=([A-Za-z0-9_]+)\b(.*)$") {
        $xgiSessionRecords.Add([pscustomobject]@{
            Line = $i
            Name = $Matches[1]
            Text = $Matches[0]
        })
    }

    if ($line -match "\[input-script\]\s+t=\d+ms\s+user=(\d+)") {
        $user = [int]$Matches[1]
        $nonZeroInput = $false
        if ($line -match "buttons=(0x[0-9a-fA-F]+)") {
            $nonZeroInput = $nonZeroInput -or ([Convert]::ToInt32($Matches[1], 16) -ne 0)
        }
        foreach ($field in @("lx", "ly", "rx", "ry", "lt", "rt")) {
            if ($line -match "$field=(-?\d+)") {
                $nonZeroInput = $nonZeroInput -or ([int]$Matches[1] -ne 0)
            }
        }
        if ($nonZeroInput) {
            [void]$activeUsers.Add($user)
        }
    }

    if ($line -match "\[xam-user\]\s+local user active mask changed\s+(0x[0-9a-fA-F]+)\s+->\s+(0x[0-9a-fA-F]+)") {
        $localUserMasks.Add($Matches[2])
        $newMask = [Convert]::ToInt32($Matches[2].Substring(2), 16)
        if ($null -ne $expectedPlayerMask -and $firstExpectedUserMaskLine -lt 0 -and
            (($newMask -band $expectedPlayerMask) -eq $expectedPlayerMask)) {
            $firstExpectedUserMaskLine = $i
        }
    }

    if ($line -match "(fatal|panic|bugcheck|access violation|0x80000003|ASSERT)") {
        $fatalLines.Add($line)
    }
}

$validGameplay = $gameplayMaps.Count -gt 0 -and $autosaves.Count -gt 0
$xgiSessionCounts = @{}
foreach ($record in $xgiSessionRecords) {
    if (-not $xgiSessionCounts.ContainsKey($record.Name)) {
        $xgiSessionCounts[$record.Name] = 0
    }
    ++$xgiSessionCounts[$record.Name]
}
$xgiSessionSignals = @($xgiSessionCounts.GetEnumerator() |
    Sort-Object Name |
    ForEach-Object { "{0}={1}" -f $_.Name, $_.Value })
$hasSessionSearch = $xgiSessionCounts.ContainsKey("XSessionSearch") -or
    $xgiSessionCounts.ContainsKey("XSessionSearchEx")
$hasSessionCreate = $xgiSessionCounts.ContainsKey("XGISessionCreateImpl")
$hasSessionJoin = $xgiSessionCounts.ContainsKey("XGISessionJoinLocal") -or
    $xgiSessionCounts.ContainsKey("XGISessionJoinRemote")
$hasSessionStart = $xgiSessionCounts.ContainsKey("XSessionStart")
$latestLocalUserMask = if ($localUserMasks.Count -gt 0) { $localUserMasks[$localUserMasks.Count - 1] } else { "0x1" }
$maskValue = [Convert]::ToInt32($latestLocalUserMask.Substring(2), 16)
$latestLocalUserCount = Get-LocalUserCountFromMask -Mask $maskValue
if ($null -ne $expectedPlayerMask -and $firstExpectedUserMaskLine -lt 0 -and
    (($maskValue -band $expectedPlayerMask) -eq $expectedPlayerMask)) {
    $firstExpectedUserMaskLine = 0
}
$expectedSyntheticUsersSeen = $false
if ($null -ne $expectedPlayers) {
    $expectedSyntheticUsersSeen = $activeUsers.Count -ge $expectedPlayers
}
$observedState = if ($fatalLines.Count -gt 0) {
    "fatal"
} elseif ($validGameplay) {
    "gameplay_confirmed"
} elseif ($gameplayMaps.Count -gt 0) {
    "map_loaded_unconfirmed_gameplay"
} elseif ($hasSessionSearch -and -not $hasSessionCreate -and -not $hasSessionStart) {
    "invalid_session_search_lobby"
} elseif ($hasSessionStart) {
    "session_started_without_gameplay"
} elseif ($hasSessionCreate -or $hasSessionJoin) {
    "session_lobby_without_gameplay"
} else {
    "menu_or_lobby"
}
$fpsSet = if ($fpsAfterGameplay.Count -gt 0) { $fpsAfterGameplay } else { $fps }
$tail = @($fpsSet | Select-Object -Last $TailSamples)

function Measure-FpsPhase {
    param(
        $Records,
        [int]$StartLine,
        [int]$EndLine
    )

    $phase = @($Records | Where-Object {
        $_.Line -ge $StartLine -and ($EndLine -lt 0 -or $_.Line -lt $EndLine)
    } | ForEach-Object { $_.Fps })

    if ($phase.Count -eq 0) {
        return $null
    }

    $avg = ($phase | Measure-Object -Average).Average
    $min = ($phase | Measure-Object -Minimum).Minimum
    $max = ($phase | Measure-Object -Maximum).Maximum
    return "{0} samples avg={1} min={2} max={3}" -f $phase.Count,
        [math]::Round($avg, 2), [math]::Round($min, 2), [math]::Round($max, 2)
}

function Measure-EventPhase {
    param(
        $Records,
        [int]$StartLine,
        [int]$EndLine
    )

    if ($StartLine -lt 0) {
        return $null
    }

    $phase = @($Records | Where-Object {
        $_.Line -ge $StartLine -and ($EndLine -lt 0 -or $_.Line -lt $EndLine)
    })

    if ($phase.Count -eq 0) {
        return $null
    }

    $counts = @{}
    foreach ($event in $phase) {
        if (-not $counts.ContainsKey($event.Kind)) {
            $counts[$event.Kind] = 0
        }
        ++$counts[$event.Kind]
    }

    return (($counts.GetEnumerator() | Sort-Object Name | ForEach-Object {
        "{0}={1}" -f $_.Name, $_.Value
    }) -join " ")
}

function Measure-XamUserSummaryPhase {
    param(
        $Records,
        [int]$StartLine,
        [int]$EndLine
    )

    if ($StartLine -lt 0) {
        return $null
    }

    $phase = @($Records | Where-Object {
        $_.Line -ge $StartLine -and ($EndLine -lt 0 -or $_.Line -lt $EndLine)
    })

    if ($phase.Count -eq 0) {
        return $null
    }

    $totals = @{}
    foreach ($sample in $phase) {
        foreach ($name in $sample.Counts.Keys) {
            if (-not $totals.ContainsKey($name)) {
                $totals[$name] = [int64]0
            }
            $totals[$name] += [int64]$sample.Counts[$name]
        }
    }

    $totalCalls = 0
    foreach ($value in $totals.Values) {
        $totalCalls += [int64]$value
    }

    $top = @($totals.GetEnumerator() |
        Sort-Object -Property Value -Descending |
        Select-Object -First 8 |
        ForEach-Object { "{0}={1}" -f $_.Name, $_.Value })

    $latest = $phase[$phase.Count - 1]
    return "samples={0} latest_mask={1} latest_users={2} total_calls={3} top {4}" -f
        $phase.Count, $latest.Mask, $latest.Users, $totalCalls, ($top -join " ")
}

function Measure-XgiSessionPhase {
    param(
        $Records,
        [int]$StartLine,
        [int]$EndLine
    )

    if ($StartLine -lt 0) {
        return $null
    }

    $phase = @($Records | Where-Object {
        $_.Line -ge $StartLine -and ($EndLine -lt 0 -or $_.Line -lt $EndLine)
    })

    if ($phase.Count -eq 0) {
        return $null
    }

    $counts = @{}
    foreach ($record in $phase) {
        if (-not $counts.ContainsKey($record.Name)) {
            $counts[$record.Name] = 0
        }
        ++$counts[$record.Name]
    }

    return (($counts.GetEnumerator() | Sort-Object Name | ForEach-Object {
        "{0}={1}" -f $_.Name, $_.Value
    }) -join " ")
}

if ($tail.Count -gt 0) {
    $avg = ($tail | Measure-Object -Average).Average
    $min = ($tail | Measure-Object -Minimum).Minimum
    $max = ($tail | Measure-Object -Maximum).Maximum
} else {
    $avg = $null
    $min = $null
    $max = $null
}

[pscustomobject]@{
    Log = (Resolve-Path -LiteralPath $LogPath).Path
    Context = $context
    ObservedState = $observedState
    ExpectedPlayers = $expectedPlayers
    ExpectedLocalUserMask = if ($null -ne $expectedPlayerMask) { "0x{0:x}" -f $expectedPlayerMask } else { $null }
    ValidGameplay = $validGameplay
    GameplayMaps = @($gameplayMaps | Select-Object -Unique)
    AutosaveTemps = @($autosaves | Select-Object -Unique)
    XgiSessionSignals = ($xgiSessionSignals -join " ")
    FirstXgiSessionSignal = if ($xgiSessionRecords.Count -gt 0) { $xgiSessionRecords[0].Text } else { $null }
    FirstGameplayLogLine = if ($firstGameplayLine -ge 0) { $firstGameplayLine + 1 } else { $null }
    FirstAutosaveLogLine = if ($firstAutosaveLine -ge 0) { $firstAutosaveLine + 1 } else { $null }
    FirstExpectedUserMaskLogLine = if ($firstExpectedUserMaskLine -ge 0) { $firstExpectedUserMaskLine + 1 } else { $null }
    LatestLocalUserMask = $latestLocalUserMask
    LatestLocalUserCount = $latestLocalUserCount
    ActiveSyntheticUsers = @($activeUsers | Sort-Object)
    ExpectedSyntheticUsersSeen = $expectedSyntheticUsersSeen
    FpsSamples = $fps.Count
    FpsSamplesAfterGameplayMap = $fpsAfterGameplay.Count
    FpsBeforeGameplayMap = (Measure-FpsPhase -Records $fpsRecords -StartLine 0 -EndLine $firstGameplayLine)
    FpsGameplayLoadToAutosave = if ($firstGameplayLine -ge 0) {
        Measure-FpsPhase -Records $fpsRecords -StartLine $firstGameplayLine -EndLine $firstAutosaveLine
    } else { $null }
    FpsAfterAutosaveBeforeExpectedUsers = if ($firstAutosaveLine -ge 0) {
        Measure-FpsPhase -Records $fpsRecords -StartLine $firstAutosaveLine -EndLine $firstExpectedUserMaskLine
    } else { $null }
    FpsAfterExpectedUsers = if ($firstExpectedUserMaskLine -ge 0) {
        Measure-FpsPhase -Records $fpsRecords -StartLine $firstExpectedUserMaskLine -EndLine -1
    } else { $null }
    EventsBeforeGameplayMap = (Measure-EventPhase -Records $eventRecords -StartLine 0 -EndLine $firstGameplayLine)
    EventsGameplayLoadToAutosave = if ($firstGameplayLine -ge 0) {
        Measure-EventPhase -Records $eventRecords -StartLine $firstGameplayLine -EndLine $firstAutosaveLine
    } else { $null }
    EventsAfterAutosaveBeforeExpectedUsers = if ($firstAutosaveLine -ge 0) {
        Measure-EventPhase -Records $eventRecords -StartLine $firstAutosaveLine -EndLine $firstExpectedUserMaskLine
    } else { $null }
    EventsAfterExpectedUsers = if ($firstExpectedUserMaskLine -ge 0) {
        Measure-EventPhase -Records $eventRecords -StartLine $firstExpectedUserMaskLine -EndLine -1
    } else { $null }
    XamUserSummariesBeforeGameplayMap = (Measure-XamUserSummaryPhase -Records $xamUserSummaryRecords -StartLine 0 -EndLine $firstGameplayLine)
    XamUserSummariesGameplayLoadToAutosave = if ($firstGameplayLine -ge 0) {
        Measure-XamUserSummaryPhase -Records $xamUserSummaryRecords -StartLine $firstGameplayLine -EndLine $firstAutosaveLine
    } else { $null }
    XamUserSummariesAfterAutosaveBeforeExpectedUsers = if ($firstAutosaveLine -ge 0) {
        Measure-XamUserSummaryPhase -Records $xamUserSummaryRecords -StartLine $firstAutosaveLine -EndLine $firstExpectedUserMaskLine
    } else { $null }
    XamUserSummariesAfterExpectedUsers = if ($firstExpectedUserMaskLine -ge 0) {
        Measure-XamUserSummaryPhase -Records $xamUserSummaryRecords -StartLine $firstExpectedUserMaskLine -EndLine -1
    } else { $null }
    XgiSessionSignalsBeforeGameplayMap = (Measure-XgiSessionPhase -Records $xgiSessionRecords -StartLine 0 -EndLine $firstGameplayLine)
    XgiSessionSignalsGameplayLoadToAutosave = if ($firstGameplayLine -ge 0) {
        Measure-XgiSessionPhase -Records $xgiSessionRecords -StartLine $firstGameplayLine -EndLine $firstAutosaveLine
    } else { $null }
    XgiSessionSignalsAfterAutosaveBeforeExpectedUsers = if ($firstAutosaveLine -ge 0) {
        Measure-XgiSessionPhase -Records $xgiSessionRecords -StartLine $firstAutosaveLine -EndLine $firstExpectedUserMaskLine
    } else { $null }
    XgiSessionSignalsAfterExpectedUsers = if ($firstExpectedUserMaskLine -ge 0) {
        Measure-XgiSessionPhase -Records $xgiSessionRecords -StartLine $firstExpectedUserMaskLine -EndLine -1
    } else { $null }
    TailSamplesUsed = $tail.Count
    TailAverageFps = if ($null -ne $avg) { [math]::Round($avg, 2) } else { $null }
    TailMinFps = if ($null -ne $min) { [math]::Round($min, 2) } else { $null }
    TailMaxFps = if ($null -ne $max) { [math]::Round($max, 2) } else { $null }
    FatalishLines = $fatalLines.Count
} | Format-List

if (-not $validGameplay) {
    exit 2
}

if ($fatalLines.Count -gt 0) {
    exit 3
}
