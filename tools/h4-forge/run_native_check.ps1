param([ValidateSet('snap','reload')][string]$Mode='snap',[ValidateSet('1x1','2x1','dish','dish-door','arch','base-round','arena-wall')][string]$Bank='1x1',[switch]$Anchors,[switch]$Coordinates,[ValidateSet('snap','coordinate','menu','arch-menu','overlap')][string]$Result='snap',[string]$Physics='',[switch]$NativeMenu,[ValidateSet('position','rotation','rotation-cancel','resume','lifecycle')][string]$MenuCase='position',[switch]$AutoStartup,[switch]$Overlap,[switch]$SpawnClearance,[switch]$MovementGate,[ValidateSet('forge_gulch','forge_island')][string]$Map='forge_gulch')
$ErrorActionPreference='Stop'
$repo=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location -LiteralPath $repo
$env:TEMP=Join-Path $repo 'work/build-temp'
$env:TMP=$env:TEMP
if($AutoStartup -and ($Mode -ne 'snap' -or $Coordinates)){throw 'AutoStartup requires snap without the disabled-magnets coordinate diagnostic'}
$python='C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe'
if($Overlap -and ($Mode -ne 'snap' -or $Bank -notin @('1x1','2x1') -or $Physics -notin @('normal','fixed','phased') -or $NativeMenu -or $Anchors -or $Coordinates -or $AutoStartup)){
 throw 'Overlap requires a Bank snap fixture and one physics mode, without other specialized routes'
}
if($Mode -eq 'snap' -and !$SpawnClearance){
 $fixtureArgs=@('-B','tools/h4-forge/build_snap_fixture.py','--bank',$Bank)
 if($Overlap){$fixtureArgs+='--overlap'}
 & $python @fixtureArgs
 if($LASTEXITCODE -ne 0){throw 'Could not build native fixture'}
}
$exe=Join-Path $repo 'work/rexglue-sdk/out/win-amd64/halo3mp.exe'
$sha=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
$layout=if($Mode -eq 'snap'){'snap-fixture.bin'}else{"$Result-result.bin"}
if($Mode -eq 'snap' -and $Bank -ne '1x1'){$layout="snap-fixture-$Bank.bin"}
if($Overlap){$layout="overlap-fixture-$Bank.bin"}
$checkArgs=@('-B','tools/warlock-conversion/snapshot/tools/trace_loading.py',
 '--project','C:/X360/ISOs/H3M','--game',(Join-Path $repo 'work/installed-map-corrections/game'),
 '--exe',$exe,'--expected-exe-sha256',$sha,
 '--dlc-installed-root','work/dlc/installed-current','--dlc-map',$Map,
 '--slot','sandbox','--saved-layout',"work/h4-forge-research/isolated/$layout",
 '--cache-root','work/chiron/final-cache','--capture','--capture-times-ms','155000','--seconds','240','--sample-native-variant')
if($Anchors){
 if($Mode -ne 'snap'){throw 'Anchor inspection requires the snap route'}
 if($NativeMenu){throw 'Anchor inspection uses its own held-object route'}
 $checkArgs[$checkArgs.IndexOf('--capture-times-ms')+1]='136000,140000'
 $checkArgs+=@('--host-capture-after-ms','136000','--advanced-forge-anchor-check')
}
if($NativeMenu){
 if($Mode -ne 'snap'){throw 'Native menu check requires a scenery snap route'}
 $checkArgs[$checkArgs.IndexOf('--capture-times-ms')+1]='133000,150000'
 if($MenuCase -in @('rotation','rotation-cancel')){$checkArgs[$checkArgs.IndexOf('--capture-times-ms')+1]='142200,143500,145500,149500'}
 if($MenuCase -eq 'resume'){$checkArgs[$checkArgs.IndexOf('--capture-times-ms')+1]='143000,154000'}
 if($MenuCase -eq 'lifecycle'){$checkArgs[$checkArgs.IndexOf('--capture-times-ms')+1]='148000,157000'}
 $checkArgs+=@('--advanced-forge-test-menu',"--advanced-forge-test-menu-case=$MenuCase")
}
if($MenuCase -ne 'position' -and !$NativeMenu){throw 'MenuCase requires NativeMenu'}
if($Mode -eq 'snap'){
 $checkArgs+=@('--forge-scenery-check')
 if($AutoStartup){$checkArgs+=@('--advanced-forge-auto')}else{$checkArgs+=@('--advanced-forge-data','work/h4-forge-research')}
 $checkArgs+=@('--advanced-forge-test-position=-44.7924538,-197.9406281,2.582953')
 if($Bank -like 'dish*'){$checkArgs[-1]='--advanced-forge-test-position=-44.7924538,-197.9406281,3.8';$checkArgs+=@('--forge-scenery-index',$(if($Bank -eq 'dish'){'36'}else{'37'}))}
 if($Bank -eq '2x1'){$checkArgs+=@('--forge-scenery-index','6')}
 if($Bank -eq 'arch'){$checkArgs+=@('--forge-scenery-index','2')}
 if($Bank -eq 'arena-wall'){if(!$SpawnClearance){throw 'Arena Wall requires SpawnClearance'};$checkArgs+=@('--forge-scenery-index','0')}
 if($Bank -eq 'base-round'){
  if($NativeMenu -or $Anchors -or $Coordinates -or $Physics){throw 'Base Round uses its dedicated released-disc inspection route'}
  $checkArgs[$checkArgs.IndexOf('--advanced-forge-test-position=-44.7924538,-197.9406281,2.582953')]='--advanced-forge-test-position=-51.5694468,-190.1296933,1.4892261'
  $checkArgs+=@('--forge-scenery-index','8','--advanced-forge-base-round-check')
  $checkArgs[$checkArgs.IndexOf('--capture-times-ms')+1]='136000,155000'
 }
 if($Coordinates){$checkArgs+=@('--advanced-forge-test-coordinates=-44.125,-197.5,3,90,0,0')}
 if($Physics){$checkArgs+=@("--advanced-forge-test-physics=$Physics")}
 if($Overlap){
  $checkArgs+=@('--advanced-forge-test-coordinates=-44.7924538,-197.9406281,2.582953,0,0,0')
  $checkArgs[$checkArgs.IndexOf('--capture-times-ms')+1]='136000,150000'
 }
}
if($Overlap -or ($Mode -eq 'reload' -and $Result -eq 'overlap')){
 $map=Get-ChildItem -LiteralPath (Join-Path $repo 'work/dlc/installed-current') -Filter forge_gulch.map -Recurse -File | Select-Object -First 1
 if(!$map){throw 'Missing overlap fixture cache'}
 $checkArgs+=@('--sample-object-map',$map.FullName)
}
if($Coordinates -and $Mode -ne 'snap'){throw 'Coordinate test requires snap route'}
if($Physics -and $Mode -ne 'snap'){throw 'Physics test requires snap route'}
if($SpawnClearance){
 if($Mode -ne 'snap' -or $Anchors -or $Coordinates -or $Physics -or $Overlap){throw 'Spawn clearance requires ordinary scenery creation'}
 # Exercise the native spawn distance, without forced poses or fixture objects.
 $layoutIndex=$checkArgs.IndexOf('--saved-layout')
 $checkArgs=@($checkArgs[0..($layoutIndex-1)])+@($checkArgs[($layoutIndex+2)..($checkArgs.Count-1)])
 $checkArgs=@($checkArgs | Where-Object {$_ -notlike '--advanced-forge-test-position=*'})
 $captureIndex=$checkArgs.IndexOf('--capture-times-ms')+1
 $captureTimes=if($NativeMenu){'130500,'+$checkArgs[$captureIndex]}else{'130500,133000,137000'}
 $checkArgs[$captureIndex]=(($captureTimes -split ',' | ForEach-Object {[int]$_+6000}) -join ',')
 $checkArgs+='--forge-spawn-clearance-check'
 if(!$NativeMenu){$checkArgs+=@('--exclusive-input','--inspection-input','132000:RT+600,132000:LSDOWN+500,134000:RT+600,134000:LSUP+500')}
}
if($MovementGate){
 if($Mode -ne 'snap' -or $Bank -ne '1x1' -or $SpawnClearance -or $NativeMenu -or $Coordinates -or $Anchors -or $Physics -or $Overlap){throw 'MovementGate requires the ordinary Bank1x1 snap fixture'}
 # Controlled target isolates live processed movement -> original H4 gate.
 # This is not a free-drag/collision/re-grab acceptance test.
 $checkArgs[$checkArgs.IndexOf('--capture-times-ms')+1]='134500,135500,137000'
}
# Reload deliberately supplies no Advanced Forge options or private H4 data.
& $python @checkArgs
if($LASTEXITCODE -ne 0){throw "Native $Mode check failed: $LASTEXITCODE"}
