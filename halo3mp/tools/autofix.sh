#!/usr/bin/env bash
# Iteratively resolve "Call to invalid or unregistered function" faults by
# declaring each faulting address as a function boundary in the manifest,
# regenerating, rebuilding, and re-running.

set -u
export PATH="/c/Program Files/LLVM/bin:/c/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/Ninja:$PATH"

PROJ="C:/Programming/GitHub/Halo-3-MP/halo3mp"
S="C:/Users/smmel/AppData/Local/Temp/claude/C--Programming-GitHub-Halo-3-MP/e89cb8dd-3e15-4102-9817-291201e6f2ea/scratchpad"
REX="C:/Programming/GitHub/Halo-3-MP/work/rexglue-sdk/out/win-amd64/Release/rexglue.exe"
EXE="$PROJ/out/build/win-amd64-release/halo3mp.exe"
GAMEDATA="C:/Programming/GitHub/Halo-3-MP/work/gamedata"
MAX=${1:-40}

cd "$PROJ" || exit 1

for i in $(seq 1 "$MAX"); do
  LOG="$S/auto_run.log"
  rm -f "$LOG"

  # Run the title briefly and capture where it dies.
  powershell.exe -NoProfile -Command "
    \$p = Start-Process -FilePath '$EXE' -ArgumentList '--game_data_root=$GAMEDATA','--gpu_plugin=xenos','--log_file=$LOG','--log_level=info' -PassThru -WorkingDirectory '$(dirname "$EXE")'
    Start-Sleep -Seconds 30
    \$s = Get-Process -Id \$p.Id -ErrorAction SilentlyContinue
    if (\$s) { Write-Output 'ALIVE'; Stop-Process -Id \$p.Id -Force } else { Write-Output \"EXITED \$(\$p.ExitCode)\" }
  " > "$S/auto_status.txt" 2>&1

  STATUS=$(cat "$S/auto_status.txt" | tr -d '\r')
  echo "=== iter $i: $STATUS"

  if echo "$STATUS" | grep -q ALIVE; then
    echo "SURVIVED_30S at iteration $i"
    echo "alive" > "$S/auto_result.txt"
    break
  fi

  ADDR=$(grep -o "unregistered function at guest address 0x[0-9A-Fa-f]*" "$LOG" 2>/dev/null | tail -1 | grep -o "0x[0-9A-Fa-f]*")
  if [ -z "$ADDR" ]; then
    echo "NO_FATAL_ADDRESS - different failure"
    tail -6 "$LOG"
    echo "nofatal" > "$S/auto_result.txt"
    break
  fi

  if grep -qi "$ADDR = {" halo3mp_manifest.toml; then
    echo "ADDRESS $ADDR ALREADY DECLARED - not converging"
    echo "stuck:$ADDR" > "$S/auto_result.txt"
    break
  fi

  RES=$(python "$S/addfunc.py" "$ADDR")
  echo "  $ADDR -> $RES"
  case "$RES" in
    added:*) ;;
    *) echo "ROUTING FAILED: $RES"; echo "route:$RES" > "$S/auto_result.txt"; break ;;
  esac

  "$REX" codegen halo3mp_manifest.toml > "$S/auto_codegen.log" 2>&1
  if [ $? -ne 0 ]; then echo "CODEGEN FAILED"; tail -12 "$S/auto_codegen.log"; echo "codegenfail" > "$S/auto_result.txt"; break; fi

  python "$S/genstubs.py" > /dev/null 2>&1

  cmake --build --preset win-amd64-release > "$S/auto_build.log" 2>&1
  if [ $? -ne 0 ]; then echo "BUILD FAILED"; grep -i "error" "$S/auto_build.log" | head -8; echo "buildfail" > "$S/auto_result.txt"; break; fi
done

echo "=== declared functions now ==="
grep "= { name" "$PROJ/halo3mp_manifest.toml"
