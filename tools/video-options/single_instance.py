"""Serialize validation launches; never close an existing user game."""
import ctypes,subprocess,json

_mutex=None
def acquire():
 global _mutex
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
 kernel.CreateMutexW.restype=ctypes.c_void_p
 _mutex=kernel.CreateMutexW(None,False,'Local\\SpartanVideoValidation')
 if not _mutex or ctypes.get_last_error()==183:
  raise SystemExit('Another video validation runner is active; refusing overlap.')
 ensure_no_game()

def ensure_no_game():
 command="@(Get-Process -Name halo3mp,OpenH3M -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress"
 result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True)
 if result.stdout.strip() and json.loads(result.stdout):
  raise SystemExit('A Halo game instance is already running; refusing another launch.')
