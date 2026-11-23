# usage: pain.sh name package map points   (one run; never start two at once)
PY=/c/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe
B=/c/X360/ISOs/H3M/.local/OpenH3M-source/work/rexglue-sdk/out/win-amd64
cd /c/Programming/GitHub/OpenH3M
while tasklist | grep -qi halo3mp.exe; do sleep 5; done
rm -rf .local/pc-port/$1
$PY -B tools/map-review/speed-review/run_pc_port.py --build $B --game .local/xenia-canary/game-local --package .local/pc-port/packages/$2 --map $3 --run .local/pc-port/$1 --seconds 245 --benchmark-points .local/pc-port/$4 --captures 118000,144000,170000 "--extra-args=--halo3mp_benchmark_uncapped=true --d3d12_log_frame_workload=true $5" > .local/pc-port/$1.out 2>&1
rm -rf .local/pc-port/$1/bin .local/pc-port/$1/cache .local/pc-port/$1/0000000000000000
cat .local/pc-port/$1/runtime*.log | grep -aE "map-benchmark\] (placed|RESULT)|\[workload\]" | sort | awk '
/placed/ {n++; d=0; i=0; c=0; next}
/workload/ && n {match($0,/draws_per_frame=[0-9]+/); a=substr($0,RSTART+16,RLENGTH-16); match($0,/indices_per_frame=[0-9]+/); b=substr($0,RSTART+18,RLENGTH-18); d+=a; i+=b; c++}
/RESULT/ {match($0,/fps=[0-9.]+/); printf "%s spot %d: %s draws/frame %.0f triangles/frame %.0f\n", name, n, substr($0,RSTART,RLENGTH), d/c, i/c/3}' name=$1
