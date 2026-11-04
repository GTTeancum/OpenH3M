@echo off
setlocal
cd /d C:\X360\ISOs\H3M\.local\OpenH3M-source
set TEMP=%CD%\.local\build-temp
set TMP=%TEMP%
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
"C:\Program Files\LLVM\bin\clang++.exe" -std=c++17 -D_CRT_SECURE_NO_WARNINGS tools/warlock-conversion/snapshot/reference/sky-bridge-performance/sky-coverage-probe-gpu-test.cpp -o work/sky-bridge/fabric-coverage-build/gpu-test.exe -ld3d12 -ldxgi -ld3dcompiler
exit /b %ERRORLEVEL%
