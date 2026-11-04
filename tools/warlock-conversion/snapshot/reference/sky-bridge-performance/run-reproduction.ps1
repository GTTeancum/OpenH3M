# Private, bounded, process-local replay; never modifies the shared runtime.
param([Parameter(Mandatory=$true)][string]$RunDirectory,[switch]$StageProbe,[switch]$PresentedProbe,[switch]$RegionProbe,[switch]$SwapchainProbe,[string]$PixelRegion='0.54,0.255,0.93,0.425',[string]$ProfileSeed,[ValidateRange(0,20000)][int]$ArmDelayMs=0,[switch]$RegionOnly,[switch]$FullViewport,[switch]$NativeObserver,[switch]$LatePassProbe,[switch]$WaterPassProbe,[switch]$AllDrawTrace,[switch]$RainPassProbe,[switch]$ScreenPassProbe,[ValidateRange(0.03,0.1)][double]$VehicleTolerance=0.03,[ValidateSet(32,33,34,35,36,37,38,39)][int]$Candidate=32,[switch]$HeaderTrace,[switch]$TimingOnly,[switch]$ModelPassProbe,[switch]$CylinderPassProbe,[switch]$BlendTrace,[switch]$CommandTrace,[switch]$CoverageTrace,[switch]$DepthTestTrace,[switch]$DepthValueTrace,[switch]$DepthWriterTrace,[switch]$NativeLivePackage,[switch]$NativeVisualCapture)
$ErrorActionPreference='Stop'
$passiveOnly=$TimingOnly -or $NativeVisualCapture
if($NativeVisualCapture -and ($TimingOnly -or -not $NativeObserver -or $Candidate -ne 36)){throw 'NativeVisualCapture requires candidate36 NativeObserver without TimingOnly'}
if($DepthWriterTrace){$DepthValueTrace=$true;$AllDrawTrace=$true}
$repo='C:/X360/ISOs/H3M/.local/OpenH3M-source'
Set-Location -LiteralPath $repo
$run=(Resolve-Path -LiteralPath $RunDirectory).Path
if (-not $run.StartsWith(($repo.Replace('/','\')+'\work\sky-bridge\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Run is outside Sky Bridge work directory' }
if (Get-Process OpenH3M,halo3mp -ErrorAction SilentlyContinue) { throw 'A game is already running' }
foreach($name in @('arm','draws.bin','pixels.csv','region.csv','swapchain-region.csv','native-state.bin','bitmap-headers.csv','native-blend.bin','coverage.csv','depth-tests.csv','depth-values.csv','recording-configuration.json')) {
    if (Test-Path -LiteralPath (Join-Path $run $name)) { throw 'Run already contains evidence' }
}
if($passiveOnly -and ($CommandTrace -or $BlendTrace -or $ModelPassProbe -or $HeaderTrace -or $StageProbe -or $PresentedProbe -or $RegionProbe -or $SwapchainProbe -or $RegionOnly -or $FullViewport -or $LatePassProbe -or $WaterPassProbe -or $AllDrawTrace -or $RainPassProbe -or $ScreenPassProbe)) { throw 'TimingOnly/NativeVisualCapture exclude GPU/draw/header probe modes' }
if($CoverageTrace -and (-not $ModelPassProbe -or $TimingOnly)) { throw 'CoverageTrace requires ModelPassProbe and excludes timing runs' }
if($DepthTestTrace -and -not $CoverageTrace) { throw 'DepthTestTrace requires CoverageTrace' }
if($DepthValueTrace -and -not ($CoverageTrace -or $DepthWriterTrace)) { throw 'DepthValueTrace requires CoverageTrace or DepthWriterTrace' }
if($DepthWriterTrace -and ($TimingOnly -or $ModelPassProbe -or $StageProbe -or $CoverageTrace -or $RegionOnly -or $DepthTestTrace -or $BlendTrace -or $CommandTrace -or $HeaderTrace -or $PresentedProbe -or $RegionProbe -or $SwapchainProbe -or $FullViewport -or $LatePassProbe -or $WaterPassProbe -or $RainPassProbe -or $ScreenPassProbe)) { throw 'DepthWriterTrace requires its isolated all-draw mode' }
if($CommandTrace -and $RegionOnly) { throw 'CommandTrace requires draw tracing' }
if($RegionOnly -and (($RegionProbe -eq $SwapchainProbe) -or $StageProbe -or $PresentedProbe)) { throw 'RegionOnly requires exactly one region probe and no other probe switches' }
if(($LatePassProbe -or $WaterPassProbe) -and (-not $StageProbe -or $RegionOnly)) { throw 'Pass probes require StageProbe and draw tracing' }
if($LatePassProbe -and $WaterPassProbe) { throw 'Select one pass probe' }
if($ModelPassProbe -and (-not $StageProbe -or $RegionOnly -or $AllDrawTrace -or $LatePassProbe -or $WaterPassProbe -or $RainPassProbe -or $ScreenPassProbe)) { throw 'Model pass requires StageProbe and excludes other pass modes' }
if($ScreenPassProbe -and (-not $StageProbe -or $RegionOnly -or $AllDrawTrace -or $LatePassProbe -or $WaterPassProbe -or $RainPassProbe)) { throw 'Screen pass requires StageProbe and excludes other pass modes' }
if($RainPassProbe -and (-not $StageProbe -or $RegionOnly -or $AllDrawTrace -or $LatePassProbe -or $WaterPassProbe)) { throw 'Rain pass requires StageProbe and excludes other pass modes' }
if($AllDrawTrace -and ($RegionOnly -or $WaterPassProbe)) { throw 'AllDrawTrace conflicts with region-only or water-only recording' }
$hashes=Get-Content -Raw -LiteralPath (Join-Path $run 'runtime-hashes.json') | ConvertFrom-Json
foreach ($entry in $hashes.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $run ('runtime/'+$entry.Name))).Hash.ToLowerInvariant() -ne $entry.Value) { throw 'Private runtime changed' }
}
$payload=Join-Path $repo ('work/sky-bridge/payload-'+$Candidate)
$mapHash=(Get-FileHash -LiteralPath (Join-Path $payload 'sky_bridge.map')).Hash.ToLowerInvariant()
$expectedMap=@{32='311ad88580c5e099546c029f07f93976c346a8bb9bf9b12c1d48f72f5e0c3e5d';33='1705dc69c655d5a0d1e10e1163d45f7ce9e45743bcd7192efce9306ba371ac3c';34='70e5c7aaed939be2c8c718535d8113deb334cd66ed428bd995c7b8573e93aa59';35='9dec756fd9d0b4b3d2af252bb75a7468bccba5e6d3d8034001f8cf0c2f705a8e';36='39873291ea89a3225a53ecda3f9811f7429ab46c8760ebc07a9938fcf8dd0245';37='bbe1b0ac0b3fc67de2db376811a271029794feeba2729faf8624692b355fa0be';38='0bacedb05012c779974e2798f415adea3075d33708f8ec1032e3d3c11d5357dd';39='e33a8b410341d98b7af3785cf2b3f2fff061e7e4f00a25b617772e435ea90d94'}
if($mapHash -ne $expectedMap[$Candidate]){throw 'Unexpected private candidate map'}
$contentArgs=@('--dlc-payload',$payload)
$livePackage=$null;$livePackageHash=$null
if($NativeLivePackage) {
    if($Candidate -ne 36){throw 'Native LIVE validation is pinned to candidate36'}
    $livePackage=Join-Path $repo 'work/sky-bridge/live-candidate-36/5DC3487BF1633DF162B829AF5609E7687F169DE8'
    $livePackageHash=(Get-FileHash -LiteralPath $livePackage).Hash.ToLowerInvariant()
    if($livePackageHash -ne '96c76373c7c092dd169a92efd678e1b68d6d4f59fdab588aaf6d67503064171b'){throw 'Unexpected candidate36 LIVE package'}
    $contentArgs=@('--dlc-package',$livePackage)
}
$env:TEMP=Join-Path $repo '.local/build-temp';$env:TMP=$env:TEMP
$env:OPENH3M_SKY_REPRO_DIR=$run
if($DepthWriterTrace){$env:OPENH3M_SKY_DEPTH_WRITER_TRACE='1';$env:OPENH3M_SKY_TRACE_FRAME_LIMIT='4'}
else {Remove-Item Env:OPENH3M_SKY_DEPTH_WRITER_TRACE,Env:OPENH3M_SKY_TRACE_FRAME_LIMIT -ErrorAction SilentlyContinue}
if($DepthValueTrace){$env:OPENH3M_SKY_DEPTH_VALUE_TRACE='1'}
else {Remove-Item Env:OPENH3M_SKY_DEPTH_VALUE_TRACE -ErrorAction SilentlyContinue}
if($DepthTestTrace){$env:OPENH3M_SKY_DEPTH_TEST_TRACE='1'}
else {Remove-Item Env:OPENH3M_SKY_DEPTH_TEST_TRACE -ErrorAction SilentlyContinue}
if($CoverageTrace){$env:OPENH3M_SKY_COVERAGE_TRACE='1'}
else {Remove-Item Env:OPENH3M_SKY_COVERAGE_TRACE -ErrorAction SilentlyContinue}
if($HeaderTrace){$env:OPENH3M_SKY_HEADER_TRACE_DIR=$run}
else {Remove-Item Env:OPENH3M_SKY_HEADER_TRACE_DIR -ErrorAction SilentlyContinue}
if($BlendTrace){$env:OPENH3M_SKY_BLEND_TRACE_DIR=$run}
else {Remove-Item Env:OPENH3M_SKY_BLEND_TRACE_DIR -ErrorAction SilentlyContinue}
if($CommandTrace){$env:OPENH3M_SKY_COMMAND_TRACE='1'}
else {Remove-Item Env:OPENH3M_SKY_COMMAND_TRACE -ErrorAction SilentlyContinue}
$env:OPENH3M_SKY_REPRO_ARM_DELAY_MS=[string]$ArmDelayMs
$env:OPENH3M_SKY_REPRO_VEHICLE_TOLERANCE=$VehicleTolerance.ToString('R',[Globalization.CultureInfo]::InvariantCulture)
if($NativeObserver) {
    if((Get-Item -LiteralPath (Join-Path $run 'observer-command.bin')).Length -ne 64) { throw 'Invalid native observer command' }
    $env:OPENH3M_SKY_REPRO_NATIVE_OBSERVER='1'
} else { Remove-Item Env:OPENH3M_SKY_REPRO_NATIVE_OBSERVER -ErrorAction SilentlyContinue }
$env:OPENH3M_SKY_TRACE_DIR=$run
$env:OPENH3M_SKY_TRACE_TARGETS='1'
if($LatePassProbe -or $AllDrawTrace) {
    $env:OPENH3M_SKY_TRACE_TARGETS='0'
    $env:OPENH3M_SKY_TRACE_COMPACT=if($DepthWriterTrace){'0'}else{'1'}
    $env:OPENH3M_SKY_STAGE_ALL_DRAWS='1'
} else { Remove-Item Env:OPENH3M_SKY_TRACE_COMPACT,Env:OPENH3M_SKY_STAGE_ALL_DRAWS -ErrorAction SilentlyContinue }
if($WaterPassProbe) {
    $env:OPENH3M_SKY_TRACE_TARGETS='0'
    $env:OPENH3M_SKY_TRACE_WATER='1'
    $env:OPENH3M_SKY_STAGE_WATER_DRAWS='1'
} else { Remove-Item Env:OPENH3M_SKY_TRACE_WATER,Env:OPENH3M_SKY_STAGE_WATER_DRAWS -ErrorAction SilentlyContinue }
if($RainPassProbe) {
    $env:OPENH3M_SKY_TRACE_TARGETS='0'
    $env:OPENH3M_SKY_TRACE_RAIN='1'
    $env:OPENH3M_SKY_STAGE_RAIN_DRAWS='1'
} else { Remove-Item Env:OPENH3M_SKY_TRACE_RAIN,Env:OPENH3M_SKY_STAGE_RAIN_DRAWS -ErrorAction SilentlyContinue }
if($ScreenPassProbe) {
    $env:OPENH3M_SKY_TRACE_TARGETS='0'
    $env:OPENH3M_SKY_TRACE_SCREEN='1'
    $env:OPENH3M_SKY_STAGE_SCREEN_DRAWS='1'
} else { Remove-Item Env:OPENH3M_SKY_TRACE_SCREEN,Env:OPENH3M_SKY_STAGE_SCREEN_DRAWS -ErrorAction SilentlyContinue }
if($ModelPassProbe) {
    $env:OPENH3M_SKY_TRACE_TARGETS='0'
    $env:OPENH3M_SKY_TRACE_MODEL='1'
    $env:OPENH3M_SKY_STAGE_MODEL_DRAWS='1'
} else { Remove-Item Env:OPENH3M_SKY_TRACE_MODEL,Env:OPENH3M_SKY_STAGE_MODEL_DRAWS -ErrorAction SilentlyContinue }
if($CylinderPassProbe) {
    if(-not $StageProbe -or $ModelPassProbe -or $AllDrawTrace -or $passiveOnly -or $RegionOnly -or $ScreenPassProbe -or $RainPassProbe -or $WaterPassProbe -or $LatePassProbe -or $DepthWriterTrace -or $CoverageTrace -or $DepthTestTrace -or $DepthValueTrace){throw 'Cylinder pass requires isolated StageProbe mode'}
    $env:OPENH3M_SKY_TRACE_TARGETS='0'
    $env:OPENH3M_SKY_TRACE_CYLINDER='1'
    $env:OPENH3M_SKY_STAGE_CYLINDER_DRAWS='1'
} else {Remove-Item Env:OPENH3M_SKY_TRACE_CYLINDER,Env:OPENH3M_SKY_STAGE_CYLINDER_DRAWS -ErrorAction SilentlyContinue}
$env:OPENH3M_SKY_PIXEL_PROBE_DIR=$run
$env:OPENH3M_SKY_PIXEL_PROBE_REGION=$PixelRegion
if($DepthWriterTrace){Remove-Item Env:OPENH3M_SKY_PIXEL_PROBE_DIR -ErrorAction SilentlyContinue}
if($RegionOnly -or $passiveOnly) {
    Remove-Item Env:OPENH3M_SKY_TRACE_DIR,Env:OPENH3M_SKY_PIXEL_PROBE_DIR -ErrorAction SilentlyContinue
}
if($StageProbe) { $env:OPENH3M_SKY_STAGE_PROBE_DIR=$run }
else { Remove-Item Env:OPENH3M_SKY_STAGE_PROBE_DIR -ErrorAction SilentlyContinue }
if($PresentedProbe) { $env:OPENH3M_SKY_PIXEL_PROBE_PRESENTED='1' }
else { Remove-Item Env:OPENH3M_SKY_PIXEL_PROBE_PRESENTED -ErrorAction SilentlyContinue }
if($FullViewport) { $env:OPENH3M_SKY_REGION_PROBE_REGION='0,0,1,1' }
else { $env:OPENH3M_SKY_REGION_PROBE_REGION='0.45,0.10,1,0.50' }
if($RegionProbe) { $env:OPENH3M_SKY_REGION_PROBE_DIR=$run }
else { Remove-Item Env:OPENH3M_SKY_REGION_PROBE_DIR -ErrorAction SilentlyContinue }
if($SwapchainProbe) { $env:OPENH3M_SKY_SWAPCHAIN_REGION_PROBE_DIR=$run }
else { Remove-Item Env:OPENH3M_SKY_SWAPCHAIN_REGION_PROBE_DIR -ErrorAction SilentlyContinue }
$profileArgs=@()
if($ProfileSeed) { $profileArgs=@('--profile-seed',$ProfileSeed) }
$timingArgs=@()
if($TimingOnly) { $timingArgs=@('--timing-diagnostics') }
$captureArgs=@()
if($NativeVisualCapture){$captureArgs=@('--capture','--capture-times-ms','115000,116000,117000,118000,119000,120000')}
[ordered]@{cylinder_pass_probe=[bool]$CylinderPassProbe;native_visual_capture=[bool]$NativeVisualCapture;native_capture_times_ms=$(if($NativeVisualCapture){@(115000,116000,117000,118000,119000,120000)}else{@()});native_live_package=[bool]$NativeLivePackage;live_package=$livePackage;live_package_sha256=$livePackageHash;depth_writer_trace=[bool]$DepthWriterTrace;depth_value_trace=[bool]$DepthValueTrace;depth_test_trace=[bool]$DepthTestTrace;coverage_trace=[bool]$CoverageTrace;command_trace=[bool]$CommandTrace;blend_trace=[bool]$BlendTrace;model_pass_probe=[bool]$ModelPassProbe;timing_only=[bool]$TimingOnly;header_trace=[bool]$HeaderTrace;candidate=$Candidate;map_sha256=$mapHash;region_only=[bool]$RegionOnly;full_viewport=[bool]$FullViewport;native_observer=[bool]$NativeObserver;guest_region=[bool]$RegionProbe;swapchain_region=[bool]$SwapchainProbe;stage_probe=[bool]$StageProbe;late_pass_probe=[bool]$LatePassProbe;water_pass_probe=[bool]$WaterPassProbe;rain_pass_probe=[bool]$RainPassProbe;screen_pass_probe=[bool]$ScreenPassProbe;all_draw_trace=[bool]$AllDrawTrace;presented_probe=[bool]$PresentedProbe;draw_trace=(-not ($RegionOnly -or $passiveOnly));pixel_probe=(-not ($RegionOnly -or $passiveOnly -or $DepthWriterTrace));pixel_region=$PixelRegion;region=$env:OPENH3M_SKY_REGION_PROBE_REGION;arm_delay_ms=$ArmDelayMs;vehicle_tolerance=$VehicleTolerance} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'recording-configuration.json')
& 'C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe' -B tools/warlock-conversion/snapshot/tools/trace_loading.py `
    --project C:/X360/ISOs/H3M --game C:/X360/ISOs/H3M `
    --exe (Join-Path $run 'runtime/OpenH3M.exe') --expected-exe-sha256 $hashes.'OpenH3M.exe' `
    --slot zanzibar --dlc-map sky_bridge @contentArgs `
    --cache-root (Join-Path $run 'cache') --exclusive-input --quiet-timing --seconds 180 @profileArgs @timingArgs @captureArgs
if ($LASTEXITCODE -ne 0) { throw 'Private reproduction failed; inspect repository logs' }
