@echo off
setlocal

set "OPENH3M_ROOT=%~dp0"
set "OPENH3M_GAME=%OPENH3M_ROOT%game"

if not exist "%OPENH3M_GAME%\default.xex" (
    echo OpenH3M could not find game\default.xex.
    echo.
    echo Extract your legally obtained Halo 3: ODST Multiplayer Disc ^(Disc 2^)
    echo into the game folder beside this launcher, preserving its directory structure.
    echo The result must contain game\default.xex and game\maps\.
    echo.
    pause
    exit /b 1
)

if not exist "%OPENH3M_ROOT%OpenH3M.exe" (
    echo OpenH3M.exe is missing from this folder.
    pause
    exit /b 1
)

start "" /D "%OPENH3M_ROOT%" /BELONORMAL "%OPENH3M_ROOT%OpenH3M.exe" ^
    --game_data_root "%OPENH3M_GAME%" ^
    --gpu_plugin xenos ^
    --no-fullscreen ^
    --window_width 1280 ^
    --window_height 720 ^
    --video_mode_width 1280 ^
    --video_mode_height 720 ^
    --anisotropic_override=3 ^
    --render_target_path_d3d12=rtv ^
    --gamma_render_target_as_unorm16=false ^
    --readback_memexport=false ^
    --gpu_allow_invalid_fetch_constants=true ^
    --halo3mp_title_fps=true ^
    --keyboard_controller=true ^
    --keyboard_controller_log=false ^
    %*
