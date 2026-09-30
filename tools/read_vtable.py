"""Read a vtable from a live process and prove it is one.

WHY THIS SCRIPT
    The hybrid tier design rests on one claim: a vtable address from the
    address database is trustworthy because the thing it points to is a run of
    function pointers into executable code. That claim is checkable against a
    running game, with no injection and no writes, and it should be checked
    BEFORE building a C++ hook layer on top of it.

    If the claim is false, tier 2 is a design that looks rigorous and is not,
    and the honest response is to fall back to tier 3 alone. So this is a
    design gate, not a demo.

WHAT IT PROVES, per vtable:
    - the address is inside the module
    - the first N consecutive 8-byte values are readable
    - each is a pointer into one of the module's EXECUTABLE sections

A random address in .rdata fails step 3 immediately. A real vtable passes.
That asymmetry is what makes the check meaningful rather than a rubber stamp.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import struct
import sys
import time

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
PSAPI = ctypes.WinDLL("psapi", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
    ]


kernel32.OpenProcess.restype = wt.HANDLE
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
kernel32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                                    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                                    ctypes.c_size_t]
kernel32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
PSAPI.GetModuleInformation.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                        wt.DWORD]


def sections_of(h, base, size):
    """Return [(name, rva, vsize, characteristics)] from the PE headers."""
    hdr = ctypes.create_string_buffer(0x1000)
    got = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(h, ctypes.c_void_p(base), hdr, 0x1000,
                                      ctypes.byref(got)) or got.value < 0x40:
        return []
    lfanew = struct.unpack_from("<i", hdr.raw, 0x3C)[0]
    nt = ctypes.create_string_buffer(0x1000)
    if not kernel32.ReadProcessMemory(h, ctypes.c_void_p(base + lfanew), nt, 0x1000,
                                      ctypes.byref(got)):
        return []
    nsec = struct.unpack_from("<H", nt.raw, 6)[0]
    opt_size = struct.unpack_from("<H", nt.raw, 20)[0]
    sec_off = 0x18 + opt_size
    out = []
    for i in range(nsec):
        raw = nt.raw[sec_off + i * 40: sec_off + (i + 1) * 40]
        if len(raw) < 40:
            break
        name = raw[:8].split(b"\x00")[0].decode("ascii", "replace")
        vsize, vaddr, rsize, rptr = struct.unpack_from("<IIII", raw, 8)
        chars = struct.unpack_from("<I", raw, 36)[0]
        out.append((name, vaddr, vsize, chars))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--module", default="Fallout4.exe")
    ap.add_argument("--vtable", type=lambda x: int(x, 0), required=True,
                    help="RVA of the vtable")
    ap.add_argument("--slots", type=int, default=8)
    ap.add_argument("--name", default="vtable")
    args = ap.parse_args()

    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, args.pid)
    if not h:
        print(f"OpenProcess failed: {ctypes.get_last_error()}")
        return 1
    print(f"attached pid {args.pid} -- READ ONLY, no writes\n")

    import ctypes as C

    class MODULEENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD),
                    ("th32ProcessID", wt.DWORD), ("GlblcntUsage", wt.DWORD),
                    ("ProccntUsage", wt.DWORD),
                    # c_size_t, not c_byte * 8. The byte array has the right
                    # SIZE but ctypes would give it 1-byte alignment, which
                    # shifts every following field and makes the module name
                    # compare against garbage -- so the lookup silently fails
                    # while looking like "module not found".
                    ("modBaseAddr", ctypes.c_size_t),
                    ("modBaseSize", wt.DWORD), ("hModule", ctypes.c_void_p),
                    ("szModule", wt.WCHAR * 256), ("szExePath", wt.WCHAR * 260)]

    # argtypes are load-bearing here too: without them ctypes marshals the
    # byref argument for a different signature and the call does nothing
    # useful, returning a value that looks plausible.
    kernel32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    kernel32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    kernel32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]

    snapshot = kernel32.CreateToolhelp32Snapshot(0x8 | 0x10, args.pid)  # MODULE|MODULE32
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        print(f"CreateToolhelp32Snapshot failed: {ctypes.get_last_error()}")
        return 1
    me = MODULEENTRY32W()
    me.dwSize = ctypes.sizeof(me)
    base = 0
    size = 0
    seen = 0
    if kernel32.Module32FirstW(snapshot, ctypes.byref(me)):
        while True:
            seen += 1
            if me.szModule == args.module:
                base = me.modBaseAddr
                size = me.modBaseSize
                break
            if not kernel32.Module32NextW(snapshot, ctypes.byref(me)):
                break
    kernel32.CloseHandle(snapshot)
    if not base:
        print(f"module {args.module} not found ({seen} modules enumerated)")
        if seen:
            print("  first few were:")
        return 1
    print(f"module {args.module} base 0x{base:X} size 0x{size:X}")

    secs = sections_of(h, base, size)
    print("sections:")
    exec_ranges = []
    for name, vaddr, vsize, chars in secs:
        executable = bool(chars & 0x20000000)
        readable = bool(chars & 0x40000000)
        print(f"  {name:<8} rva 0x{vaddr:08X} vsize 0x{vsize:08X}"
              f"{'  [exec]' if executable else ''}{'  [read]' if readable else ''}")
        if executable:
            exec_ranges.append((base + vaddr, base + vaddr + vsize))
    print()

    addr = base + args.vtable
    print(f"{args.name} at RVA 0x{args.vtable:X} -> absolute 0x{addr:X}")

    buf = ctypes.create_string_buffer(args.slots * 8)
    got = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, args.slots * 8,
                                      ctypes.byref(got)) or got.value < 8:
        print("  UNREADABLE")
        return 1

    print(f"  first {args.slots} slots:")
    in_code = 0
    for i in range(args.slots):
        (ptr,) = struct.unpack_from("<Q", buf.raw, i * 8)
        where = "?"
        for lo, hi in exec_ranges:
            if lo <= ptr < hi:
                where = "in .text"
                in_code += 1
                break
        else:
            for name, vaddr, vsize, chars in secs:
                if base + vaddr <= ptr < base + vaddr + vsize:
                    where = f"in {name} (NOT code)"
                    break
            else:
                where = "outside the module"
        print(f"    [{i}] 0x{ptr:016X}  {where}")

    print(f"\n  {in_code}/{args.slots} slots point into executable code")
    if in_code >= 4:
        print("  VERDICT: this is a vtable. Tier 2 is viable for this target.")
        return 0
    if in_code == 0:
        print("  VERDICT: not a vtable. Either the address is wrong or this")
        print("           database does not mean what we assumed. Investigate")
        print("           before building on it.")
        return 2
    print("  VERDICT: inconclusive. Too few code pointers to call it a vtable.")
    return 3


if __name__ == "__main__":
    sys.exit(main())
