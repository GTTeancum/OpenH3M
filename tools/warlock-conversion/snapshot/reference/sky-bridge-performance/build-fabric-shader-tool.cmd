@echo off
cd /d C:\X360\ISOs\H3M\.local\OpenH3M-source
if not exist work\sky-bridge\fabric-cutout-build mkdir work\sky-bridge\fabric-cutout-build
set TEMP=C:\X360\ISOs\H3M\.local\OpenH3M-source\.local\build-temp
set TMP=%TEMP%
call "C:\Program Files (x86)\Microsoft Visual Studio 10.0\VC\vcvarsall.bat" x86 > nul
cl /nologo /wd4838 /EHsc /MD /DWIN32 /I"C:\Program Files (x86)\Microsoft Xbox 360 SDK\include\win32" tools\warlock-conversion\snapshot\reference\sky-bridge-performance\fabric-shader-tool.cpp /Fework\sky-bridge\fabric-cutout-build\shader-tool.exe /Fowork\sky-bridge\fabric-cutout-build\shader-tool.obj /link /LIBPATH:"C:\Program Files (x86)\Microsoft Xbox 360 SDK\lib\win32\vs2010" d3dx9.lib xgraphics.lib d3d9.lib advapi32.lib gdi32.lib
