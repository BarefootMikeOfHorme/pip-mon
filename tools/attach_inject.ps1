# attach_inject.ps1 -- inject a DLL into an already-running process.
#
# WHY THIS EXISTS SEPARATELY FROM THE LAUNCHER
#   The launcher spawns suspended and injects before the target runs. That
#   works in the lab against our helper target, and it failed against the real
#   game, which wants to come up through Fallout4Launcher.exe first. Rather
#   than restructure the launcher around that, the simpler model is used: the
#   user starts the game the way they normally do, and we attach afterwards.
#   This script is that attach, done deliberately and reversibly.
#
# WHAT IT DOES, in order:
#   1. find the target process by name
#   2. confirm the DLL exists and is a PE image
#   3. open the process with the rights injection requires
#   4. VirtualAllocEx + WriteProcessMemory the DLL path
#   5. CreateRemoteThread on LoadLibraryW
#   6. read the thread's exit code, which is the module handle
#
# WHAT IT DELIBERATELY DOES NOT DO:
#   - it does not suspend the process
#   - it does not write any code, only a path string
#   - it does not free or patch anything after the loader has run
#   - it leaves the injected module loaded, because unloading a module that
#     started a thread is exactly the mistake that killed the test harness
#     earlier (see PAST MISTAKES). Detach is the user's call, not ours.
#
# THIS IS A REAL WRITE INTO A LIVE GAME. That is the point of it, and it is
# why the inert helper DLL exists: it loads, does nothing, and signals
# nothing, so the mechanism can be proven against the real target before any
# code of ours runs inside it.
param(
    [Parameter(Mandatory = $true)][string]$ProcessName,
    [Parameter(Mandatory = $true)][string]$DllPath,
    [int]$TimeoutMs = 30000
)

$ErrorActionPreference = 'Stop'

# --- 1. locate the target -------------------------------------------------
$proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Sort-Object WorkingSet64 -Descending | Select-Object -First 1
if (-not $proc) { throw "process '$ProcessName' is not running" }
Write-Host "target      $($proc.ProcessName) pid=$($proc.Id)" -ForegroundColor Cyan

# --- 2. validate the payload before touching anything ---------------------
if (-not (Test-Path -LiteralPath $DllPath)) { throw "DLL not found: $DllPath" }
$bytes = [System.IO.File]::ReadAllBytes($DllPath)
if ($bytes[0] -ne 0x4D -or $bytes[1] -ne 0x5A) { throw "not a PE image: $DllPath" }
$arch = [BitConverter]::ToUInt16($bytes, [BitConverter]::ToInt32($bytes, 0x3C) + 4)
if ($arch -ne 0x8664) { throw "not x64 (machine 0x$('{0:X4}' -f $arch)): $DllPath" }
Write-Host "payload     $([IO.Path]::GetFileName($DllPath))  $($bytes.Length) bytes  x64 ok" -ForegroundColor DarkGray

# --- 3. open with injection rights ----------------------------------------
$sig = @'
[DllImport("kernel32.dll", SetLastError=true)]
public static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
[DllImport("kernel32.dll", SetLastError=true)]
public static extern IntPtr VirtualAllocEx(IntPtr h, IntPtr addr, IntPtr size, uint alloc, uint prot);
[DllImport("kernel32.dll", SetLastError=true)]
public static extern bool WriteProcessMemory(IntPtr h, IntPtr addr, byte[] buf, IntPtr size, out IntPtr written);
[DllImport("kernel32.dll", SetLastError=true)]
public static extern IntPtr CreateRemoteThread(IntPtr h, IntPtr attr, IntPtr stack, IntPtr start, IntPtr param, uint flags, out IntPtr tid);
[DllImport("kernel32.dll", SetLastError=true)]
public static extern uint WaitForSingleObject(IntPtr h, uint ms);
[DllImport("kernel32.dll", SetLastError=true)]
public static extern bool GetExitCodeThread(IntPtr h, out uint code);
[DllImport("kernel32.dll", SetLastError=true)]
public static extern bool VirtualFreeEx(IntPtr h, IntPtr addr, IntPtr size, uint type);
[DllImport("kernel32.dll", SetLastError=true)]
public static extern bool CloseHandle(IntPtr h);
[DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern IntPtr GetModuleHandleW(string name);
[DllImport("kernel32.dll", CharSet=CharSet.Ansi, SetLastError=true)]
public static extern IntPtr GetProcAddress(IntPtr mod, string name);
[DllImport("kernel32.dll", SetLastError=true)]
public static extern bool IsWow64Process(IntPtr h, out bool wow64);
'@
$k32 = Add-Type -MemberDefinition $sig -Name K32 -Namespace Attach -PassThru

# PROCESS_ALL_ACCESS is the simplest thing that works. It is broad on
# purpose-free grounds: the alternative is assembling an explicit rights mask
# and getting one bit wrong, which fails later and less visibly.
$h = $k32::OpenProcess(0x1F0FFF, $false, $proc.Id)   # ALL_ACCESS
if ($h -eq [IntPtr]::Zero) { throw "OpenProcess failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }
Write-Host "opened      with injection rights" -ForegroundColor DarkGray

$remote = [IntPtr]::Zero
$thread = [IntPtr]::Zero
try {
    $pathBytes = [Text.Encoding]::Unicode.GetBytes($DllPath + "`0")
    $size = [IntPtr]$pathBytes.Length

    $remote = $k32::VirtualAllocEx($h, [IntPtr]::Zero, $size, 0x3000, 0x04)  # COMMIT|RESERVE, RW
    if ($remote -eq [IntPtr]::Zero) { throw "VirtualAllocEx failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }

    $written = [IntPtr]::Zero
    if (-not $k32::WriteProcessMemory($h, $remote, $pathBytes, $size, [ref]$written)) {
        throw "WriteProcessMemory failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
    }
    if ($written.ToInt64() -ne $size.ToInt64()) { throw "short write: $($written.ToInt64()) of $($size.ToInt64())" }

    # LoadLibraryW in OUR process. kernel32 is mapped at the same address in
    # every process of the same bitness, so this is valid in the target --
    # the same assumption the C++ launcher makes, and the same one it asserts.
    $mod = $k32::GetModuleHandleW("kernel32.dll")
    $fn  = $k32::GetProcAddress($mod, "LoadLibraryW")
    if ($fn -eq [IntPtr]::Zero) { throw "could not resolve LoadLibraryW" }

    $tid = [IntPtr]::Zero
    $thread = $k32::CreateRemoteThread($h, [IntPtr]::Zero, [IntPtr]::Zero, $fn, $remote, 0, [ref]$tid)
    if ($thread -eq [IntPtr]::Zero) { throw "CreateRemoteThread failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }

    $wr = $k32::WaitForSingleObject($thread, [uint32]$TimeoutMs)
    if ($wr -ne 0) { throw "loader thread timed out after $TimeoutMs ms" }

    $code = [uint32]0
    [void]$k32::GetExitCodeThread($thread, [ref]$code)

    if ($code -eq 0) {
        Write-Host "result      FAILED - LoadLibraryW returned 0 (module not found or not loadable)" -ForegroundColor Red
        exit 1
    }
    # A 64-bit HMODULE truncated to 32 bits by GetExitCodeThread. The low word
    # is real; the high word is discarded by the API. Non-zero low word is the
    # success signal, and its absence is the failure signal.
    Write-Host "result      LOADED  (module handle low word 0x$('{0:X8}' -f $code))" -ForegroundColor Green
}
finally {
    # Free the path buffer. The loaded module is deliberately left alone:
    # unloading a module that started a thread pulls the code out from under it.
    if ($remote -ne [IntPtr]::Zero) { [void]$k32::VirtualFreeEx($h, $remote, [IntPtr]::Zero, 0x8000) }
    if ($thread -ne [IntPtr]::Zero) { [void]$k32::CloseHandle($thread) }
    [void]$k32::CloseHandle($h)
}
