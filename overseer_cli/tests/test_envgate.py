"""Tests for the environment gate.

The gate is the component that tells you whether everything else can be
trusted, so it gets tested at least as hard as the things it reports on. Two
failure shapes get specific attention because they are the ones this project
has actually shipped:

  - a check that could not run reported as a pass (silent degradation, G4)
  - a check that ran and found nothing reported identically to a check that
    never ran (M12: a zero from a broken search vs a zero from an absent thing)

The second is why ``Status.SKIP`` exists as a value distinct from ``Status.PASS``
and why ``verdict()`` returns a non-zero code when checks were skipped.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from overseer_cli import envgate as eg
from overseer_cli.envgate import Check, Context, Status, verdict


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _ctx(tmp_path: Path, **kw) -> Context:
    """A context pointing at an empty tree, so nothing passes by accident."""
    game = tmp_path / "game"
    repo = tmp_path / "repo"
    game.mkdir(parents=True, exist_ok=True)
    (repo / "vprobe" / "build").mkdir(parents=True, exist_ok=True)
    (repo / "vprobe" / "papyrus" / "build").mkdir(parents=True, exist_ok=True)
    (repo / "vprobe" / "libs" / "deploy").mkdir(parents=True, exist_ok=True)
    return Context(game_dir=game, repo=repo, **kw)


def _check(check_id: str = "t.x", layer: str = "artefact", hosts=("offline",),
           requires_running: bool = False) -> Check:
    return Check(
        id=check_id,
        layer=layer,
        title="title",
        hosts=hosts,
        proves="something",
        run=lambda c, ctx: CheckResult_(c.id),
        requires_running=requires_running,
    )


def CheckResult_(check_id: str):  # noqa: N802 - tiny local helper
    return eg.CheckResult(check_id, Status.PASS, "ok")


def _write_pex(path: Path, payload: bytes = b"") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(eg.PEX_MAGIC + payload)


# ---------------------------------------------------------------------------
# verdict: a skip must never read as a pass
# ---------------------------------------------------------------------------


def test_all_pass_is_zero():
    state, code = verdict([eg.CheckResult("a", Status.PASS, "")])
    assert state == "PASS"
    assert code == 0


def test_any_fail_is_one_and_outranks_skip():
    state, code = verdict([
        eg.CheckResult("a", Status.SKIP, "needs game"),
        eg.CheckResult("b", Status.FAIL, "broken"),
    ])
    assert state == "FAIL"
    assert code == 1


def test_skipped_checks_produce_a_non_zero_code():
    """The whole point. Zero failures with most checks unrun is not a pass."""
    state, code = verdict([eg.CheckResult("a", Status.SKIP, "needs game")])
    assert state == "PARTIAL"
    assert code == 3, "a gate that skipped must not exit 0"


def test_unknown_is_not_a_pass_either():
    state, code = verdict([eg.CheckResult("a", Status.UNKNOWN, "unreadable")])
    assert state == "PARTIAL"
    assert code == 3


def test_skip_is_a_distinct_value_from_pass():
    assert Status.SKIP is not Status.PASS
    assert Status.SKIP.value != Status.PASS.value


# ---------------------------------------------------------------------------
# registry integrity
# ---------------------------------------------------------------------------


def test_check_ids_are_unique():
    ids = [c.id for c in eg.CHECKS]
    assert len(ids) == len(set(ids)), "duplicate check id would collapse rows"


def test_every_check_states_what_it_proves():
    for c in eg.CHECKS:
        assert c.proves.strip(), f"{c.id} has no 'proves' claim"


def test_every_check_names_a_known_host():
    known = {"offline", "game", "geck"}
    for c in eg.CHECKS:
        assert c.hosts, f"{c.id} names no host"
        assert set(c.hosts) <= known, f"{c.id} names an unknown host {c.hosts}"


def test_runtime_checks_require_the_game_running():
    """A live-runtime check must not be satisfiable by the game merely existing.

    Otherwise it reports on a process that is not there, which is the same class
    of confident-wrong as a phase tag that claims MENU with no frame source.
    """
    for c in eg.CHECKS:
        if c.layer == "runtime":
            assert c.requires_running, f"{c.id} reads live state but does not require running"
            assert "game" in c.hosts, f"{c.id} reads live game state but does not name the game"


# ---------------------------------------------------------------------------
# host applicability
# ---------------------------------------------------------------------------


def test_offline_check_always_runs():
    ctx = _ctx(Path("/nonexistent"))
    results = eg.run_gate(ctx, only=["artefact.runtime"])
    assert len(results) == 1
    # It ran -- and it failed, because nothing is built. The distinction that
    # matters is that it is FAIL and not SKIP.
    assert results[0].status is Status.FAIL


def test_check_whose_host_is_absent_is_skipped_with_a_reason(tmp_path):
    ctx = _ctx(tmp_path, installed=set())
    results = eg.run_gate(ctx, only=["editor.ck"])
    assert len(results) == 1
    assert results[0].status is Status.SKIP
    assert "geck" in results[0].detail, "a skip must name the host it needed"


def test_installed_but_not_running_is_a_distinct_skip(tmp_path):
    """Presence is not running, and the two skips say different things."""
    ctx = _ctx(tmp_path, installed={"game"}, running={})
    results = eg.run_gate(ctx, only=["runtime.ready"])
    assert results[0].status is Status.SKIP
    assert "not running" in results[0].detail


def test_running_host_satisfies_a_requires_running_check(tmp_path):
    ctx = _ctx(tmp_path, installed={"game"}, running={"game": 4242})
    results = eg.run_gate(ctx, only=["runtime.ready"])
    # Not a SKIP any more. With no runs/ directory it SKIPs for the other,
    # legitimate reason -- and the message proves which one applies.
    assert results[0].status is Status.SKIP
    assert "runs/" in results[0].detail


def test_layer_filter_restricts_the_set(tmp_path):
    ctx = _ctx(tmp_path)
    results = eg.run_gate(ctx, only=["deploy"])
    assert results, "layer filter matched nothing"
    assert all(r.check_id.startswith("deploy.") for r in results)


# ---------------------------------------------------------------------------
# PE validation -- hostile input, because that is the input that arrives (G8)
# ---------------------------------------------------------------------------


def _minimal_pe(machine: int = 0x8664, *, e_lfanew: int = 0x80, sig: bytes = b"PE\0\0",
                size: int = 0x200) -> bytes:
    """A synthetic PE. The header is written only when it fits.

    A fixture that raises while constructing the hostile input would test the
    fixture, not the parser, so the out-of-range case is produced by simply not
    writing -- which is what a truncated file with a lying e_lfanew looks like.
    """
    buf = bytearray(size)
    buf[0:2] = b"MZ"
    struct.pack_into("<I", buf, 0x3C, e_lfanew)
    if e_lfanew + 6 <= size:
        buf[e_lfanew:e_lfanew + 4] = sig
        struct.pack_into("<H", buf, e_lfanew + 4, machine)
    return bytes(buf)


def test_valid_x64_pe_is_accepted(tmp_path):
    p = tmp_path / "ok.dll"
    p.write_bytes(_minimal_pe())
    ok, desc = eg._is_pe_x64(p)
    assert ok and "x64" in desc


def test_truncated_download_is_refused(tmp_path):
    p = tmp_path / "short.dll"
    p.write_bytes(b"MZ" + b"\0" * 10)
    ok, desc = eg._is_pe_x64(p)
    assert not ok
    assert "PE" in desc or "MZ" in desc


def test_text_pretending_to_be_a_dll_is_refused(tmp_path):
    """M10 happened for real: a 15-byte file whose bytes are the word vprobe.dll."""
    p = tmp_path / "vprobe.dll"
    p.write_bytes(b"vprobe.dll  -\r\n")
    ok, _ = eg._is_pe_x64(p)
    assert not ok


def test_32_bit_image_is_refused(tmp_path):
    p = tmp_path / "x86.dll"
    p.write_bytes(_minimal_pe(machine=0x014C))
    ok, desc = eg._is_pe_x64(p)
    assert not ok
    assert "0x014C" in desc


def test_elfanew_outside_the_file_is_refused(tmp_path):
    p = tmp_path / "liar.dll"
    p.write_bytes(_minimal_pe(e_lfanew=0x7FFFFFFF))
    ok, _ = eg._is_pe_x64(p)
    assert not ok


def test_missing_pe_signature_is_refused(tmp_path):
    p = tmp_path / "nosig.dll"
    p.write_bytes(_minimal_pe(sig=b"XXXX"))
    ok, _ = eg._is_pe_x64(p)
    assert not ok


def test_unreadable_path_is_refused_not_raised(tmp_path):
    ok, desc = eg._is_pe_x64(tmp_path / "nope.dll")
    assert not ok
    assert "unreadable" in desc


# ---------------------------------------------------------------------------
# Papyrus surface
# ---------------------------------------------------------------------------


def test_both_pex_present_and_valid_passes(tmp_path):
    ctx = _ctx(tmp_path)
    _write_pex(ctx.repo / "vprobe" / "papyrus" / "build" / "PipMon.pex", b"x" * 32)
    _write_pex(ctx.repo / "vprobe" / "papyrus" / "build" / "PipMonTestFacility.pex", b"y" * 32)
    r = eg._check_surface_pex(_check(), ctx)
    assert r.status is Status.PASS


def test_absent_pex_fails_rather_than_skipping(tmp_path):
    """A missing surface makes every script-level test measure nothing.

    It is a FAIL, not a SKIP, because it is not a host limitation -- the file
    is simply not there, and the native side will report 18/18 regardless.
    """
    ctx = _ctx(tmp_path)
    r = eg._check_surface_pex(_check(), ctx)
    assert r.status is Status.FAIL
    assert "absent" in r.detail.lower()


def test_bad_pex_magic_fails_with_the_bytes_named(tmp_path):
    ctx = _ctx(tmp_path)
    bad = ctx.repo / "vprobe" / "papyrus" / "build" / "PipMon.pex"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_bytes(b"\x00\x01\x02\x03")
    r = eg._check_surface_pex(_check(), ctx)
    assert r.status is Status.FAIL
    # The evidence must carry the actual bytes: "a negative result must carry
    # its own evidence" (M12).
    assert any("BAD MAGIC" in e for e in r.evidence)


# ---------------------------------------------------------------------------
# address database -- the check that would have caught the silent fallback
# ---------------------------------------------------------------------------


def test_missing_txt_also_implicates_the_bin(tmp_path):
    """The blob path derives from the INI path, so one miss takes both down."""
    ctx = _ctx(tmp_path)
    deploy = ctx.repo / "vprobe" / "libs" / "deploy"
    (deploy / "vprobe.addresses.bin").write_bytes(b"PLIB")
    r = eg._check_address_db(_check(), ctx)
    assert r.status is Status.FAIL
    assert "vprobe.addresses.txt" in r.detail
    assert any("embedded dump" in e for e in r.evidence)


def test_both_forms_present_passes(tmp_path):
    ctx = _ctx(tmp_path)
    deploy = ctx.repo / "vprobe" / "libs" / "deploy"
    deploy.mkdir(parents=True, exist_ok=True)
    (deploy / "vprobe.addresses.txt").write_text("x")
    (deploy / "vprobe.addresses.bin").write_bytes(b"PLIB")
    r = eg._check_address_db(_check(), ctx)
    assert r.status is Status.PASS


# ---------------------------------------------------------------------------
# editor host
# ---------------------------------------------------------------------------


def test_ckpe_absent_is_a_failure_with_the_known_consequence(tmp_path):
    ctx = _ctx(tmp_path, installed={"geck"})
    (ctx.game_dir / "CreationKit.exe").write_bytes(b"MZ")
    (ctx.game_dir / "Data").mkdir(parents=True)
    r = eg._check_ckpe(_check(hosts=("geck",)), ctx)
    assert r.status is Status.FAIL
    assert "render-crash" in r.detail


def test_ckpe_is_detected_in_the_game_root_not_under_data(tmp_path):
    """Regression. CKPE ships as loose files beside CreationKit.exe.

    An earlier version of this check looked for a directory under Data\\ and
    reported FAIL on an install where CKPE was fully deployed. A gate that
    invents a problem is worse than no gate, so this asserts the real layout.
    """
    ctx = _ctx(tmp_path, installed={"geck"})
    (ctx.game_dir / "CreationKit.exe").write_bytes(b"MZ")
    (ctx.game_dir / "ckpe_loader.exe").write_bytes(b"MZ" * 4096)
    (ctx.game_dir / "CKPE.dll").write_bytes(b"MZ" * 4096)
    (ctx.game_dir / "CKPE.Fallout4.dll").write_bytes(b"MZ" * 4096)
    (ctx.game_dir / "CreationKitPlatformExtended_FO4_Dialogs.pak").write_bytes(b"BTD")
    (ctx.game_dir / "CreationKitPlatformExtended_FO4_Resources.pak").write_bytes(b"BTD")
    (ctx.game_dir / "CreationKitPlatformExtended.toml").write_text("x")
    r = eg._check_ckpe(_check(hosts=("geck",)), ctx)
    assert r.status is Status.PASS, r.detail


def test_partially_deployed_ckpe_is_its_own_failure(tmp_path):
    """A half-deployed CKPE is not a pass. Nobody tested that configuration."""
    ctx = _ctx(tmp_path, installed={"geck"})
    (ctx.game_dir / "CreationKit.exe").write_bytes(b"MZ")
    (ctx.game_dir / "ckpe_loader.exe").write_bytes(b"MZ" * 4096)
    r = eg._check_ckpe(_check(hosts=("geck",)), ctx)
    assert r.status is Status.FAIL
    assert "partially" in r.detail
    assert any(e.startswith("MISSING:") for e in r.evidence)


def test_ckpe_payload_under_data_alone_does_not_count(tmp_path):
    """The old false positive, pinned: Data\\ is not where CKPE lives."""
    ctx = _ctx(tmp_path, installed={"geck"})
    (ctx.game_dir / "CreationKit.exe").write_bytes(b"MZ")
    (ctx.game_dir / "Data" / "CKPE").mkdir(parents=True)
    r = eg._check_ckpe(_check(hosts=("geck",)), ctx)
    assert r.status is Status.FAIL


def test_ckpe_present_passes(tmp_path):
    ctx = _ctx(tmp_path, installed={"geck"})
    (ctx.game_dir / "CreationKit.exe").write_bytes(b"MZ")
    (ctx.game_dir / "ckpe_loader.exe").write_bytes(b"MZ")
    (ctx.game_dir / "CKPE.dll").write_bytes(b"MZ")
    (ctx.game_dir / "CKPE.Fallout4.dll").write_bytes(b"MZ")
    (ctx.game_dir / "CreationKitPlatformExtended_FO4_Dialogs.pak").write_bytes(b"BTD")
    (ctx.game_dir / "CreationKitPlatformExtended_FO4_Resources.pak").write_bytes(b"BTD")
    (ctx.game_dir / "CreationKitPlatformExtended.toml").write_text("x")
    r = eg._check_ckpe(_check(hosts=("geck",)), ctx)
    assert r.status is Status.PASS


def test_editor_crash_dump_is_reported_with_size_and_time(tmp_path):
    ctx = _ctx(tmp_path, installed={"geck"})
    (ctx.game_dir / "CreationKit.exe").write_bytes(b"MZ")
    (ctx.game_dir / "CreationKit_2026-09-30_03-55.dmp").write_bytes(b"\0" * 1024)
    r = eg._check_ck_crashes(_check(hosts=("geck",)), ctx)
    assert r.status is Status.FAIL
    assert any("1,024 B" in e for e in r.evidence)


def test_no_crash_dump_passes(tmp_path):
    ctx = _ctx(tmp_path, installed={"geck"})
    (ctx.game_dir / "CreationKit.exe").write_bytes(b"MZ")
    r = eg._check_ck_crashes(_check(hosts=("geck",)), ctx)
    assert r.status is Status.PASS


# ---------------------------------------------------------------------------
# facility plugin
# ---------------------------------------------------------------------------


def test_missing_facility_plugin_fails_and_points_at_the_route(tmp_path):
    ctx = _ctx(tmp_path)
    (ctx.game_dir / "Data").mkdir(parents=True, exist_ok=True)
    r = eg._check_facility_plugin(_check(), ctx)
    assert r.status is Status.FAIL
    assert any("xEdit" in e for e in r.evidence)


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------


def test_depth_zero_is_a_verdict_only(tmp_path):
    ctx = _ctx(tmp_path)
    results = eg.run_gate(ctx, only=["deploy.libs"])
    out = eg.render_text(results, ctx, 0)
    assert "passed" in out
    assert "proves:" not in out, "depth 0 must not emit per-check rows"


def test_depth_one_has_rows_but_no_evidence(tmp_path):
    ctx = _ctx(tmp_path)
    results = eg.run_gate(ctx, only=["deploy.libs"])
    out = eg.render_text(results, ctx, 1)
    assert "deploy" in out
    assert "proves:" not in out


def test_depth_two_adds_the_provenance(tmp_path):
    ctx = _ctx(tmp_path)
    results = eg.run_gate(ctx, only=["deploy.libs"])
    out = eg.render_text(results, ctx, 2)
    assert "proves:" in out


def test_a_failure_never_renders_as_ok(tmp_path):
    ctx = _ctx(tmp_path)
    results = eg.run_gate(ctx, only=["deploy.facility"])
    out = eg.render_text(results, ctx, 1)
    assert "[FAIL]" in out
    assert "[OK  ]" not in out


def test_a_skip_never_renders_as_ok(tmp_path):
    ctx = _ctx(tmp_path, installed=set())
    results = eg.run_gate(ctx, only=["editor.ck"])
    out = eg.render_text(results, ctx, 1)
    assert "[SKIP]" in out
    assert "[OK  ]" not in out


# ---------------------------------------------------------------------------
# json surface
# ---------------------------------------------------------------------------


def test_json_output_is_parseable_and_carries_status_per_check(tmp_path, capsys):
    game = tmp_path / "game"
    repo = tmp_path / "repo"
    game.mkdir()
    rc = eg.main(["--game-dir", str(game), "--repo", str(repo), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] in {"PASS", "FAIL", "PARTIAL"}
    assert payload["checks"]
    for c in payload["checks"]:
        assert c["status"] in {"PASS", "FAIL", "SKIP", "UNKNOWN"}
        assert c["id"] and isinstance(c["evidence"], list)
    assert rc != 0, "an empty tree must not report success"


def test_json_reports_hosts_separately_from_installed(tmp_path, capsys):
    game = tmp_path / "game"
    repo = tmp_path / "repo"
    game.mkdir()
    repo.mkdir()
    eg.main(["--game-dir", str(game), "--repo", str(repo), "--json"])
    payload = json.loads(capsys.readouterr().out)
    # Both keys always present, so a consumer never has to distinguish "no host"
    # from "field missing".
    assert "hostsRunning" in payload
    assert "hostsInstalled" in payload
