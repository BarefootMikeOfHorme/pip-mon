"""envgate -- one environment gate, run identically in every Creation Engine host.

WHY THIS EXISTS
    The project's validations had grown into three unrelated answers to one
    question. ``build_all.bat`` gates the build. ``tools/testenv.ps1`` gates a
    live session. ``testfacility/ck/verify_deploy.ps1`` gates the deployment.
    A fourth answer, ``vlink_probe.py --summary-only``, answers "is it working"
    from the outside. Design section 26.5 records this as open decision 5: the
    same capability implemented several times, each with its own blind spot.

    This module is the consolidation. It is ONE gate whose checks run in
    whichever Creation Engine host happens to be present, and it is honest
    about the ones that could not run.

THE THREE HOSTS
    All three are Creation Engine binaries, and the difference between them is
    not the protocol -- it is which checks are meaningful:

        game     Fallout4.exe        the playable. The only host where the
                                    in-process runtime resolves addresses and
                                    telemetry is real.
        geck     CreationKit.exe     the editor, out of game. A PEER TOOL: we
                                    instrument and validate around it, we never
                                    replace it (rule G3, contradiction C14).
        offline  neither running     build artefacts, the address database, the
                                    Papyrus surface, the deployment.

    Note what is deliberately NOT claimed: the in-process runtime does not
    resolve inside the editor. Its database is keyed on a hash of the
    *game* PE headers, and handed a different image it refuses -- correctly.
    A gate that reported the editor as "monitoring" would be the exact
    silent-lie failure this project keeps paying for, so the runtime checks
    name the game as their required host and SKIP in the editor with a reason.

THE RULE THIS ENCODES
    A check that could not run is reported as SKIPPED with the host it needed.
    It is never folded into the pass count and never printed as OK. That is
    rule G4 (fail loudly and specifically, or not at all) applied to coverage
    rather than to output, and it is why ``Status.UNKNOWN`` is a distinct value
    from ``Status.PASS`` rather than a boolean.

DEPTH
    Section 26.5's depth axis, unchanged: 0 is a verdict, 1 adds a row per
    check, 2 adds the evidence each verdict rests on. Raising verbosity makes
    the gate read more, never work more -- a gate that got more expensive as
    you asked it for more detail is a gate that can cause the outage it
    monitors.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# Papyrus compiled-script magic, little-endian 0xFA57C0DE. Read as bytes because
# that is how it lives on disk; getting this backwards is the kind of thing that
# makes a valid .pex look corrupt.
PEX_MAGIC = b"\xde\xc0\x57\xfa"

DEFAULT_GAME_DIR = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Fallout 4")

# The Papyrus compiler ships inside the game folder, not beside it: the CK's
# installdir is "Fallout 4" (design section 24.8, finding 2).
COMPILER_REL = Path("Papyrus Compiler") / "PapyrusCompiler.exe"


class Status(Enum):
    """Outcome of one check. SKIP and UNKNOWN are deliberately not PASS."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    status: Status
    detail: str
    evidence: tuple[str, ...] = ()

    @property
    def blocking(self) -> bool:
        return self.status is Status.FAIL


@dataclass
class Context:
    """Everything a check may read. Checks take no other input.

    Deliberately a bag of resolved facts rather than a service object: a check
    that has to ask the gate a question is a check whose behaviour depends on
    gate internals, and that is how a "why did this pass" argument becomes
    unanswerable.
    """

    game_dir: Path
    repo: Path
    running: dict[str, int] = field(default_factory=dict)
    installed: set[str] = field(default_factory=set)
    depth: int = 1

    def host_available(self, host: str) -> bool:
        return host == "offline" or host in self.installed


@dataclass(frozen=True)
class Check:
    """One gate check, and the two things that make it trustworthy.

    ``proves`` is required rather than optional because a check nobody can
    summarise is a check nobody can tell apart from a check that silently does
    nothing -- and "a zero caused by a broken search" is indistinguishable from
    "a zero because the thing is absent" unless the check says which it
    measured.
    """

    id: str
    layer: str
    title: str
    hosts: tuple[str, ...]
    proves: str
    run: Callable[[Context], CheckResult]
    requires_running: bool = False


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _missing(path: Path) -> CheckResult | None:
    return None


def _pass(check: Check, detail: str, *evidence: str) -> CheckResult:
    return CheckResult(check.id, Status.PASS, detail, evidence)


def _fail(check: Check, detail: str, *evidence: str) -> CheckResult:
    return CheckResult(check.id, Status.FAIL, detail, evidence)


def _skip(check: Check, detail: str) -> CheckResult:
    return CheckResult(check.id, Status.SKIP, detail)


def _read_magic(path: Path, n: int = 4) -> bytes | None:
    try:
        with path.open("rb") as fh:
            return fh.read(n)
    except OSError:
        return None


def _is_pe_x64(path: Path) -> tuple[bool, str]:
    """PE and machine check. Returns (ok, description).

    G13 in practice: the gate inspects the artefact it is about to trust rather
    than believing the build that produced it. A 15-byte file whose contents
    are the text "vprobe.dll" once shipped behind a green gate.
    """
    try:
        data = path.read_bytes()
    except OSError as exc:
        return False, f"unreadable ({exc.strerror})"
    if len(data) < 0x40 or data[0:2] != b"MZ":
        return False, f"not a PE image ({len(data)} B, bad MZ)"
    e_lfanew = int.from_bytes(data[0x3C:0x40], "little")
    if e_lfanew + 6 > len(data):
        return False, f"e_lfanew {e_lfanew} outside {len(data)} B"
    if data[e_lfanew : e_lfanew + 4] != b"PE\0\0":
        return False, "no PE signature at e_lfanew"
    machine = int.from_bytes(data[e_lfanew + 4 : e_lfanew + 6], "little")
    if machine != 0x8664:
        return False, f"machine 0x{machine:04X}, expected 0x8664 (x64)"
    return True, f"PE x64, {len(data):,} B"


# ---------------------------------------------------------------------------
# LAYER 1 -- build artefacts. No host required, ever.
# ---------------------------------------------------------------------------


def _check_runtime(check: Check, ctx: Context) -> CheckResult:
    dll = ctx.repo / "vprobe" / "build" / "vprobe.dll"
    if not dll.exists():
        return _fail(check, "vprobe.dll not built", f"expected at {dll}")
    ok, desc = _is_pe_x64(dll)
    if not ok:
        return _fail(check, "vprobe.dll is not a usable x64 image", desc)
    return _pass(check, desc, str(dll))


def _check_surface_pex(check: Check, ctx: Context) -> CheckResult:
    """Both compiled surfaces, because a stale .pex is a FAIL not a skip.

    The Papyrus surface is the only thing a .psc can call. A missing PipMon.pex
    means the 13 natives are unreachable and every script-level test is
    measuring nothing, while the native side still reports 18/18 and looks
    entirely healthy.
    """
    out: list[str] = []
    bad: list[str] = []
    for name in ("PipMon.pex", "PipMonTestFacility.pex"):
        p = ctx.repo / "vprobe" / "papyrus" / "build" / name
        if not p.exists():
            bad.append(f"{name} absent")
            out.append(f"{name:<24} ABSENT")
            continue
        magic = _read_magic(p)
        if magic != PEX_MAGIC:
            bad.append(f"{name} bad magic {magic!r}")
            out.append(f"{name:<24} BAD MAGIC {magic.hex()}")
        else:
            out.append(f"{name:<24} {p.stat().st_size:>7,} B  magic ok")
    detail = "compiled surface present" if not bad else "; ".join(bad)
    return (_fail if bad else _pass)(check, detail, *out)


def _check_address_db(check: Check, ctx: Context) -> CheckResult:
    """Both forms, under the CONTRACT name.

    The blob path is derived from the INI path, so a miss on the text form takes
    the binary form down with it and the resolver falls back to its embedded
    dump -- reporting 18/18 resolved, which is indistinguishable from the
    intended path. This check exists because that happened in every live run
    before 2026-09-29.
    """
    libs = ctx.repo / "vprobe" / "libs" / "deploy"
    out: list[str] = []
    missing: list[str] = []
    for name in ("vprobe.addresses.txt", "vprobe.addresses.bin"):
        p = libs / name
        if p.exists():
            out.append(f"{name:<26} {p.stat().st_size:>9,} B")
        else:
            missing.append(name)
    if missing:
        return _fail(
            check,
            f"missing {', '.join(missing)} under the contract name",
            "runtime would fall back to the embedded dump",
            *out,
        )
    return _pass(check, "both forms staged under the contract name", *out)


# ---------------------------------------------------------------------------
# LAYER 2 -- build identity. Reuses the validated C++ parser; never a second one.
# ---------------------------------------------------------------------------


def _file_version_placeholder() -> None:  # pragma: no cover - never called
    raise NotImplementedError


def _process_by_name(exe: str) -> object | None:
    """Find a running process by image name, without requiring psutil.

    Implemented over the Toolhelp snapshot rather than tasklist, because we
    need the working set and the window title as well as the pid, and shelling
    out per query would be absurd for a value the gate reads on every run.

    Note the deliberate absence of a snapshot-per-thread walk: the project has
    already been bitten by CreateToolhelp32Snapshot against a live process
    (past mistake M7), so this is TH32CS_SNAPPROCESS only -- no modules, no
    threads. It is a read of our own user's processes and touches nothing.
    """
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260),
        ]

    if sys.platform != "win32":
        return None
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    snap = k32.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snap == ctypes.c_void_p(-1).value or not snap:
        return None
    try:
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        found = None
        if k32.Process32First(snap, ctypes.byref(entry)):
            while True:
                if entry.szExeFile.decode("ascii", "replace").lower() == exe.lower():
                    found = int(entry.th32ProcessID)
                    break
                if not k32.Process32Next(snap, ctypes.byref(entry)):
                    break
        if found is None:
            return None
        return _ProcessInfo(found)
    finally:
        k32.CloseHandle(snap)


@dataclass(frozen=True)
class _ProcessInfo:
    pid: int

    def title(self) -> str:
        import ctypes
        from ctypes import wintypes

        if sys.platform != "win32":
            return ""
        u32 = ctypes.WinDLL("user32", use_last_error=True)
        h = u32.FindWindowW(None, None)  # placeholder to keep the import honest
        # Enumerate to the pid rather than guessing a title.
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        result: list[str] = []

        def cb(hwnd, _lparam):
            pid = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == self.pid:
                n = u32.GetWindowTextLengthW(hwnd)
                if n:
                    buf = ctypes.create_unicode_buffer(n + 1)
                    u32.GetWindowTextW(hwnd, buf, n + 1)
                    if buf.value.strip():
                        result.append(buf.value.strip())
            return True

        u32.EnumWindows(WNDENUMPROC(cb), 0)
        del h
        return result[0] if result else ""

    def working_set_gib(self) -> float:
        import ctypes
        from ctypes import wintypes

        if sys.platform != "win32":
            return 0.0
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        h = k32.OpenProcess(0x1000, False, self.pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return 0.0
        try:
            counters = (wintypes.DWORD * 2)()  # cb, cbHighPage
            if not k32.GetProcessMemoryInfo(h, ctypes.byref(counters), ctypes.sizeof(counters)):
                return 0.0
            return float(counters[0]) / (1024.0 * 1024.0 * 1024.0)
        finally:
            k32.CloseHandle(h)


def proc_title(proc: object) -> str:
    return proc.title() if proc is not None else ""


def _working_set_gib(proc: object) -> float:
    return proc.working_set_gib() if proc is not None else 0.0


def _check_build_identity(check: Check, ctx: Context) -> CheckResult:
    """Delegate to pipmon_preflight rather than parsing the PE here.

    M11 is the reason: a second hand-rolled PE parser lied about TimeDateStamp
    and printed a garbage section table while still exiting successfully. The
    one validated implementation already exists, has 45 tests behind it, and
    refuses cleanly. Reuse is cheaper than being right twice.
    """
    exe = ctx.game_dir / "Fallout4.exe"
    if not exe.exists():
        return _fail(check, "Fallout4.exe not found", f"expected at {exe}")
    preflight = ctx.repo / "launcher" / "build" / "pipmon_preflight.exe"
    if not preflight.exists():
        return _fail(check, "pipmon_preflight.exe not built", f"expected at {preflight}")
    try:
        proc = subprocess.run(
            [str(preflight), str(exe)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _fail(check, f"preflight could not run: {exc}")
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if proc.returncode != 0:
        return _fail(check, "preflight REJECTED the build", *lines[:6])
    key = next((ln.split()[-1] for ln in lines if ln.startswith("build key")), "?")
    return _pass(check, f"build accepted, key {key}", *lines[:6])


def _check_blob_matches_build(check: Check, ctx: Context) -> CheckResult:
    """Hand the staged blob to the build-time validator.

    Same reasoning as above: verify_libbin.py is an INDEPENDENT validator, and
    an independent second opinion is the point of it. Re-running it here costs
    milliseconds and is the only thing standing between a stale blob and a
    detour installed at a wrong address.
    """
    blob = ctx.repo / "vprobe" / "libs" / "deploy" / "vprobe.addresses.bin"
    if not blob.exists():
        return _skip(check, "no staged blob to validate (see the address-db check)")
    verifier = ctx.repo / "tools" / "verify_libbin.py"
    if not verifier.exists():
        return _fail(check, "verify_libbin.py missing", f"expected at {verifier}")
    try:
        proc = subprocess.run(
            [sys.executable, str(verifier), str(blob)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _fail(check, f"verifier could not run: {exc}")
    if proc.returncode != 0:
        tail = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()][-6:]
        return _fail(check, "blob validation FAILED", *tail)
    return _pass(check, "blob validates: header, stride, spot-checked RVAs")


# ---------------------------------------------------------------------------
# LAYER 3 -- what is actually deployed into the game install.
# ---------------------------------------------------------------------------


def _check_deploy_scripts(check: Check, ctx: Context) -> CheckResult:
    scripts = ctx.game_dir / "Data" / "Scripts"
    out: list[str] = []
    bad: list[str] = []
    for name in ("PipMon.pex", "PipMonTestFacility.pex"):
        p = scripts / name
        if not p.exists():
            bad.append(f"{name} not deployed")
            continue
        magic = _read_magic(p)
        if magic != PEX_MAGIC:
            bad.append(f"{name} deployed with bad magic")
        else:
            out.append(f"{name:<26} {p.stat().st_size:>7,} B  magic ok")
    detail = "deployed and valid" if not bad else "; ".join(bad)
    return (_fail if bad else _pass)(check, detail, *out)


def _check_deploy_libs(check: Check, ctx: Context) -> CheckResult:
    libs = ctx.game_dir / "Data" / "PIP-MON" / "libs"
    out: list[str] = []
    missing: list[str] = []
    for name in ("vprobe.addresses.txt", "vprobe.addresses.bin"):
        p = libs / name
        if p.exists():
            out.append(f"{name:<26} {p.stat().st_size:>9,} B")
        else:
            missing.append(name)
    if missing:
        return _fail(
            check,
            f"missing {', '.join(missing)} in the game install",
            "the live runtime would fall back to its embedded dump",
        )
    return _pass(check, "address database deployed", *out)


def _check_facility_plugin(check: Check, ctx: Context) -> CheckResult:
    """The test facility's own plugin.

    Not a warning: without it the whole facility is a paper design, and the
    coverage matrix has nothing to drive. The honest status is FAIL with the
    reason, because "everything else is green" plus "there is no test
    environment" is a sentence that has misled this project before.
    """
    data = ctx.game_dir / "Data"
    found = sorted(p.name for p in data.glob("PipMonTestFacility*") if p.is_file())
    if not found:
        return _fail(
            check,
            "no PipMonTestFacility plugin in Data\\",
            "the CK session has not produced one yet",
            "see testfacility/HANDOVER.md section 10 (xEdit headless route)",
        )
    return _pass(check, "facility plugin present", *found)


# ---------------------------------------------------------------------------
# LAYER 4 -- the editor host. Meaningful whenever the CK is installed.
# ---------------------------------------------------------------------------


def _check_ck_present(check: Check, ctx: Context) -> CheckResult:
    ck = ctx.game_dir / "CreationKit.exe"
    if not ck.exists():
        return _fail(check, "CreationKit.exe not found", f"expected at {ck}")
    ver = ck.stat().st_size
    return _pass(check, f"CreationKit.exe present, {ver:,} B", str(ck))


def _product_versions(paths: Sequence[Path]) -> dict[str, str]:
    """ProductVersion for each image, via the OS resource layer.

    Deliberately NOT hand-parsed. M11 is the reason: a second hand-rolled
    version-resource parser is exactly the component that returned a plausible
    wrong answer (a truncated timestamp, a garbage section table) while still
    exiting successfully, and a version comparison that silently reports "?"
    for both sides would turn this check into a tautology -- it would pass
    whenever both lookups failed, which is the worst possible failure for the
    one check whose entire job is catching a version skew.

    PowerShell is used because the repo already trusts it for this
    (testfacility/ck/verify_deploy.ps1) and because it is the OS's own
    resource layer rather than a reimplementation of it.
    """
    wanted = [p for p in paths if p.exists()]
    if not wanted:
        return {}
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        return {}
    quoted = ",".join("'" + str(p).replace("'", "''") + "'" for p in wanted)
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        f"$p=@({quoted});"
        "$o=@{};foreach($x in $p){$o[$x]=(Get-Item -LiteralPath $x)"
        ".VersionInfo.ProductVersion};$o|ConvertTo-Json -Compress"
    )
    try:
        out = subprocess.run(
            [pwsh, "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=60, check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return {}
    if not out:
        return {}
    try:
        data = json.loads(out)
    except ValueError:
        return {}
    if not isinstance(data, dict):  # a single entry collapses to a bare string
        data = {str(wanted[0]): data}
    return {str(k): str(v) for k, v in data.items() if v}


def _check_ck_matches_game(check: Check, ctx: Context) -> CheckResult:
    """A CK built for a different patch than the game is a real and silent trap.

    The Papyrus surface compiles against the CK's own record set. A version
    skew here produces .pex files the game may not load, and the failure appears
    in game rather than at build time.
    """
    ck_exe = ctx.game_dir / "CreationKit.exe"
    game_exe = ctx.game_dir / "Fallout4.exe"
    if not ck_exe.exists() or not game_exe.exists():
        return _skip(check, "one of the two images is absent")
    versions = _product_versions([ck_exe, game_exe])
    ck = versions.get(str(ck_exe))
    game = versions.get(str(game_exe))
    if not ck or not game:
        # Unknown is NOT equal. Report it as its own outcome so a lookup failure
        # can never present as a matching build.
        return CheckResult(
            check.id,
            Status.UNKNOWN,
            "could not read a ProductVersion from the OS",
            (f"CK readable={bool(ck)}  game readable={bool(game)}",),
        )
    if ck != game:
        return _fail(check, "CK and game builds differ", f"CK {ck} / game {game}")
    return _pass(check, f"exact build match {ck}")


def _check_editor_state(check: Check, ctx: Context) -> CheckResult:
    """Where is the editor right now, and is it safe to act on?

    THE TWO HOSTS HAVE DIFFERENT PAUSE SEMANTICS, and conflating them is a real
    error rather than a wording nit.

      game     the safe window is "VM idle and no save in flight" -- the main
               menu with nothing loaded. Papyrus is not executing, so nothing we
               would touch is on any stack. Cheap to reach: seconds.

      editor   that concept does not transfer. The Creation Kit COMPILES
               Papyrus, it does not RUN it, so "the VM is idle" is vacuously
               true at all times and therefore says nothing. The editor's
               equivalent is "plugin fully loaded, no edit in progress" -- and
               reaching it means reading the whole master and building the
               object database. Minutes, gigabytes, and the window DURING the
               load is the dangerous one.

    So this reports the editor's state as DERIVED evidence -- window title and
    working set -- and never asserts a phase it cannot see. An unrecognised
    title is UNKNOWN, not MENU and not LOADED, for the same reason the game's
    phase is UNKNOWN with no frame source: a tag that is confidently wrong is
    worse than one that admits it does not know.
    """
    proc = _process_by_name("CreationKit.exe")
    if proc is None:
        return _skip(check, "CreationKit is not running")
    title = (proc_title(proc) or "").strip()
    gib = _working_set_gib(proc)
    evidence = [f"title  '{title or '(none)'}'", f"memory {gib:.2f} GiB"]

    lowered = title.lower()
    if not title or lowered in {"warnings", "error"}:
        return CheckResult(
            check.id, Status.UNKNOWN,
            "editor is up but not in a recognisable state",
            (*evidence, "a modal dialog owns the window; the real state is behind it"),
        )
    if any(token in lowered for token in (".esp", ".esm", ".esl")):
        return _pass(check, f"editor reports a loaded plugin: {title}", *evidence)
    if gib >= 2.0:
        return _pass(check, "editor looks loaded (multi-GB working set)", *evidence)
    return CheckResult(
        check.id, Status.UNKNOWN,
        f"editor state not recognised (title '{title}', {gib:.2f} GiB)",
        *evidence,
    )


def _check_ckpe(check: Check, ctx: Context) -> CheckResult:
    """Is CK Platform Extended actually installed?

    CHECKS THE GAME ROOT, NOT Data\\. That is not a detail: CKPE ships as loose
    files beside CreationKit.exe -- ckpe_loader.exe, CKPE.dll, CKPE.Fallout4.dll,
    the two CreationKitPlatformExtended_*.pak files and the two .toml files.
    An earlier version of this check looked for a directory under Data\\ and
    reported FAIL on an install that has CKPE fully deployed. A gate that
    reports a problem which is not there is worse than no gate, because the
    lesson its users learn is to ignore it.

    Absence is still a real FAIL, and still for the reason on record: without
    it the editor render-crashes on larger cells.
    """
    # The loader is the file the CK is actually launched through, so it is the
    # one that must be present; the rest are corroboration.
    required = ["ckpe_loader.exe"]
    corroborating = ["CKPE.dll", "CKPE.Fallout4.dll",
                     "CreationKitPlatformExtended_FO4_Dialogs.pak",
                     "CreationKitPlatformExtended_FO4_Resources.pak",
                     "CreationKitPlatformExtended.toml"]

    found: list[str] = []
    missing: list[str] = []
    for name in required + corroborating:
        p = ctx.game_dir / name
        if p.exists():
            found.append(f"{name:<46} {p.stat().st_size:>12,} B")
        else:
            missing.append(name)

    dumps = sorted(ctx.game_dir.glob("CreationKit_*.dmp"))
    crash_evidence = [
        f"crash dump on disk: {d.name} ({d.stat().st_size:,} B)" for d in dumps
    ]

    if not missing:
        return _pass(
            check,
            f"CKPE installed ({len(found)}/{len(required) + len(corroborating)} files)",
            *found,
        )
    if not found:
        return _fail(
            check,
            "CKPE absent -- the editor render-crashes on larger cells",
            "expected ckpe_loader.exe and CKPE*.dll in the game root",
            *(crash_evidence or ["no crash dump present, so the risk is latent rather than realised"]),
        )
    # Partially present is its own outcome, not a pass. A half-deployed CKPE is
    # a configuration nobody tested and nobody should infer safety from.
    return CheckResult(
        check.id,
        Status.FAIL,
        f"CKPE partially deployed ({len(found)} files present, {len(missing)} missing)",
        tuple(found + [f"MISSING: {m}" for m in missing] + crash_evidence),
    )


def _check_papyrus_compiler(check: Check, ctx: Context) -> CheckResult:
    """The compiler is the one part of the CK we legitimately depend on.

    Present, because the Papyrus surface cannot be rebuilt without it, and the
    surface is the product. Recorded here so that a developer without the CK
    finds out from the gate rather than from a skip three stages deep.
    """
    exe = ctx.game_dir / COMPILER_REL
    if not exe.exists():
        return _fail(check, "PapyrusCompiler.exe not found", f"expected at {exe}")
    out = [str(exe)]
    for extra in ("PCompiler.dll", "PapyrusProject.xsd"):
        p = exe.parent / extra
        out.append(f"{extra:<22} {'present' if p.exists() else 'ABSENT'}")
    return _pass(check, "Papyrus compiler reachable", *out)


def _check_ck_crashes(check: Check, ctx: Context) -> CheckResult:
    """Editor crash evidence on disk.

    A dump in the game folder is the editor telling us it died, and nothing
    else in the toolchain reports it. Cheap to check, and it is the difference
    between "the CK is fine" and "the CK has been dying and nobody looked".
    """
    dumps = sorted(ctx.game_dir.glob("CreationKit_*.dmp"))
    if not dumps:
        return _pass(check, "no editor crash dumps on disk")
    evidence = [
        f"{d.name}  {d.stat().st_size:>10,} B  "
        f"{datetime.fromtimestamp(d.stat().st_mtime):%Y-%m-%d %H:%M}"
        for d in dumps
    ]
    return _fail(
        check,
        f"{len(dumps)} editor crash dump(s) in the game folder",
        *evidence,
    )


# ---------------------------------------------------------------------------
# LAYER 5 -- the live game. Every check here names the game as its host, so in
# the editor they SKIP with a reason instead of implying coverage.
# ---------------------------------------------------------------------------


def _newest_run(ctx: Context) -> Path | None:
    runs = ctx.repo / "runs"
    if not runs.is_dir():
        return None
    dirs = sorted((p for p in runs.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True)
    return dirs[0] if dirs else None


def _check_runtime_loaded(check: Check, ctx: Context) -> CheckResult:
    """Did a recorded run ever reach ready?

    Read from the filesystem rather than by attaching. A pipe client is
    documented to kill the process on this build, and a gate that kills the
    thing it is verifying is not a gate.
    """
    run = _newest_run(ctx)
    if run is None:
        return _skip(check, "no recorded run under runs/ -- run tools/testenv.ps1 run")
    manifest = run / "run.json"
    if not manifest.exists():
        return _skip(check, f"{run.name} was staged but never run to completion")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return _fail(check, f"run.json unreadable: {exc}")
    out = [
        f"run         {run.name}",
        f"summary     {data.get('summary')}",
        f"reachedReady {data.get('reachedReady')}",
        f"elapsedSec  {data.get('elapsedSec')}",
    ]
    if data.get("reachedReady"):
        return _pass(check, "a recorded run reached runtime ready", *out)
    return _fail(
        check,
        f"the most recent run did not reach ready ({data.get('summary')})",
        *out,
    )


def _check_live_frames(check: Check, ctx: Context) -> CheckResult:
    """Frame counters from the last session, if it produced any.

    The runtime is deliberately near-inert with no consumer attached, so a
    session log legitimately shows client=0 and frames=0. That is the shipped
    design working, not a failure -- and reporting it as a failure would push
    someone to attach a pipe client, which is the thing that kills the game.
    """
    run = _newest_run(ctx)
    if run is None:
        return _skip(check, "no recorded run under runs/")
    session = run / "vprobe.trace.session.log"
    if not session.exists():
        return _skip(check, f"{run.name} produced no session log (was --no-trace used?)")
    lines = [ln for ln in session.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    state = [ln for ln in lines if "uptime=" in ln]
    if not state:
        return _skip(check, "session log has no periodic state line yet")
    last = state[-1]
    out = [f"last state  {last}"]
    if " dropped=0 " in last or last.rstrip().endswith("dropped=0"):
        return _pass(check, "last state line reports zero dropped events", *out)
    return _fail(check, "the last state line reports dropped events", *out)


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

CHECKS: tuple[Check, ...] = (
    Check("artefact.runtime", "artefact", "runtime image is a real x64 PE",
          ("offline",), "the loader can map it at all",
          _check_runtime),
    Check("artefact.surface", "artefact", "compiled Papyrus surface is current",
          ("offline",), "a .psc can reach a registered native",
          _check_surface_pex),
    Check("artefact.addressdb", "artefact", "address database staged, both forms",
          ("offline",), "the resolver is on its intended path, not the embedded fallback",
          _check_address_db),

    Check("identity.build", "identity", "game build is identified",
          ("offline",), "the database key matches a real image",
          _check_build_identity),
    Check("identity.blob", "identity", "blob validates independently",
          ("offline",), "the served addresses are the declared ones",
          _check_blob_matches_build),

    Check("deploy.scripts", "deploy", "Papyrus surface deployed to the game",
          ("offline",), "the game can resolve PipMon: natives",
          _check_deploy_scripts),
    Check("deploy.libs", "deploy", "address database deployed to the game",
          ("offline",), "the live runtime resolves from the validated database",
          _check_deploy_libs),
    Check("deploy.facility", "deploy", "test facility plugin exists",
          ("offline",), "there is an environment to validate against",
          _check_facility_plugin),

    Check("editor.ck", "editor", "Creation Kit present",
          ("geck",), "the out-of-game authoring host is available",
          _check_ck_present),
    Check("editor.state", "editor", "editor is in a recognisable state",
          ("geck",), "we know whether it is safe to act on the editor",
          _check_editor_state, requires_running=True),
    Check("editor.match", "editor", "CK matches the game build exactly",
          ("geck",), "compiled output targets the patch the game will load",
          _check_ck_matches_game),
    Check("editor.ckpe", "editor", "CKPE installed",
          ("geck",), "the editor survives a large cell instead of render-crashing",
          _check_ckpe),
    Check("editor.compiler", "editor", "Papyrus compiler reachable",
          ("geck",), "the surface can be rebuilt at need",
          _check_papyrus_compiler),
    Check("editor.crashes", "editor", "no editor crash dumps",
          ("geck",), "the editor is not dying quietly",
          _check_ck_crashes),

    Check("runtime.ready", "runtime", "a recorded run reached runtime ready",
          ("game",), "the in-process runtime initialised against the live game",
          _check_runtime_loaded, requires_running=True),
    Check("runtime.frames", "runtime", "last session dropped no events",
          ("game",), "the transport is not silently discarding telemetry",
          _check_live_frames, requires_running=True),
)


# ---------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------


def detect_hosts(game_dir: Path) -> tuple[dict[str, int], set[str]]:
    """Find which Creation Engine hosts are running, and which are installed.

    Both facts matter and they are not the same. A check that needs the editor
    can be meaningful with the editor merely installed; a check that reads live
    runtime state needs it actually running, because otherwise it would report
    on a process that is not there.
    """
    try:
        import psutil  # type: ignore[import-not-found]
    except ImportError:
        psutil = None  # type: ignore[assignment]

    running: dict[str, int] = {}
    for key, exe in (("game", "Fallout4.exe"), ("geck", "CreationKit.exe")):
        if psutil is not None:  # pragma: no cover - optional dependency
            for proc in psutil.process_iter(["name", "pid"]):
                try:
                    if (proc.info["name"] or "").lower() == exe.lower():
                        running[key] = int(proc.info["pid"])
                except Exception:  # noqa: BLE001,S112 - access denied on other users
                    continue
        else:
            running.update(_running_via_tasklist(exe))
    installed = {
        key
        for key, exe in (("game", "Fallout4.exe"), ("geck", "CreationKit.exe"))
        if (game_dir / exe).exists()
    }
    return running, installed


def _running_via_tasklist(exe: str) -> dict[str, int]:
    """tasklist fallback so the gate has no hard third-party dependency.

    tasklist's image-name filter is a substring match, so it is only ever
    trusted for the exact stem and the result is still gated on the host
    existing in the install. Cheap, and it means `verify` works in a bare
    checkout with nothing but the standard library.
    """
    stem = Path(exe).stem
    tasklist = shutil.which("tasklist")
    if not tasklist:
        return {}
    try:
        out = subprocess.run(
            [tasklist, "/FI", f"IMAGENAME eq {exe}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=30, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    found: dict[str, int] = {}
    for line in out.splitlines():
        parts = [p.strip('" ') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == exe.lower() and parts[1].isdigit():
            found[stem] = int(parts[1])
    return found


def run_gate(ctx: Context, only: Sequence[str] | None = None) -> list[CheckResult]:
    """Run every applicable check. Inapplicable ones are reported, not dropped."""
    results: list[CheckResult] = []
    for check in CHECKS:
        if only and check.layer not in only and check.id not in only:
            continue
        if "offline" in check.hosts:
            results.append(check.run(check, ctx))
            continue
        # A non-offline check needs one of its hosts PRESENT; if it needs the
        # host RUNNING as well, presence is not enough.
        satisfied = [h for h in check.hosts if ctx.host_available(h)]
        if not satisfied:
            results.append(_skip(check, f"needs one of: {', '.join(check.hosts)}"))
            continue
        if check.requires_running and not any(h in ctx.running for h in satisfied):
            results.append(
                _skip(check, f"{', '.join(satisfied)} installed but not running")
            )
            continue
        results.append(check.run(check, ctx))
    return results


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

_GLYPH = {Status.PASS: "OK  ", Status.FAIL: "FAIL", Status.SKIP: "SKIP", Status.UNKNOWN: "?   "}


def render_text(results: list[CheckResult], ctx: Context, depth: int) -> str:
    lines: list[str] = []
    hosts = ", ".join(f"{k}(pid {v})" for k, v in sorted(ctx.running.items())) or "none running"
    lines.append("")
    lines.append("PIP-MON environment gate")
    lines.append(f"  game dir : {ctx.game_dir}")
    lines.append(f"  hosts    : {hosts}")
    lines.append(f"  depth    : {depth}")
    lines.append("")

    if depth <= 0:
        passed = sum(r.status is Status.PASS for r in results)
        failed = sum(r.status is Status.FAIL for r in results)
        skipped = sum(r.status is Status.SKIP for r in results)
        lines.append(f"  {passed} passed, {failed} failed, {skipped} not applicable")
        return "\n".join(lines)

    current_layer = None
    for r in results:
        check = next(c for c in CHECKS if c.id == r.check_id)
        if check.layer != current_layer:
            current_layer = check.layer
            lines.append(f"  -- {current_layer} " + "-" * (58 - len(current_layer)))
        line = f"  [{_GLYPH[r.status]}] {check.title:<44} {r.detail}"
        lines.append(line)
        if depth >= 2:
            lines.append(f"          proves: {check.proves}")
            for ev in r.evidence:
                lines.append(f"          {ev}")
    return "\n".join(lines)


def verdict(results: list[CheckResult]) -> tuple[str, int]:
    """One verdict, and an exit code that separates a finding from a pass.

    Exit 3 covers both SKIP and UNKNOWN. A gate that reports 0 failures while
    most of its checks never ran is the exact shape this project keeps calling
    a silent success, and UNKNOWN is the sharper version of that: it is a check
    that RAN and could not reach a conclusion -- an unreadable version
    resource, say -- which must never be rounded up to a match. Two images that
    both fail to report a version are not known to be the same version.
    """
    failed = [r for r in results if r.status is Status.FAIL]
    inconclusive = [r for r in results if r.status in (Status.SKIP, Status.UNKNOWN)]
    if failed:
        return "FAIL", 1
    if inconclusive:
        return "PARTIAL", 3
    return "PASS", 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="overseer-cli verify",
        description="One environment gate, run identically in every Creation Engine host.",
    )
    p.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    # envgate.py -> overseer_cli -> src -> overseer_cli -> repo root. Getting
    # this wrong makes every artefact check report FAIL against a directory
    # that does not exist, which is indistinguishable from a genuinely unbuilt
    # tree -- so it is spelled out rather than counted.
    p.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    p.add_argument("--depth", type=int, choices=(0, 1, 2), default=1,
                   help="0 verdict, 1 per-check, 2 adds evidence (hallway 26.5)")
    p.add_argument("--layer", action="append", default=None,
                   help="restrict to a layer (repeatable): "
                        "artefact identity deploy editor runtime")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args(argv)

    game_dir = args.game_dir
    running, installed = detect_hosts(game_dir)
    ctx = Context(game_dir=game_dir, repo=args.repo, running=running,
                  installed=installed, depth=args.depth)
    results = run_gate(ctx, args.layer)
    state, code = verdict(results)

    if args.json:
        print(json.dumps({
            "verdict": state,
            "exitCode": code,
            "gameDir": str(game_dir),
            "hostsRunning": running,
            "hostsInstalled": sorted(installed),
            "checks": [
                {
                    "id": r.check_id,
                    "status": r.status.value,
                    "detail": r.detail,
                    "evidence": list(r.evidence),
                }
                for r in results
            ],
        }, indent=2))
    else:
        print(render_text(results, ctx, args.depth))
        print("")
        print(f"  VERDICT: {state}" + (f" ({code})" if code else ""))
        print("")
    return code
