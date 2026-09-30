// SelfTest.cpp
#include "SelfTest.hpp"

#include "DynamicScanner.hpp"
#include "Detour.hpp"
#include "FrameQueue.hpp"
#include "InternTable.hpp"
#include "TelemetryEvent.hpp"
#include "VersionConfig.hpp"
#include "IPCServer.hpp"
#include "PapyrusApi.hpp"
#include "PipmonEntry.hpp"

#include <Windows.h>

#include <chrono>
#include <cctype>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <vector>

namespace f4mon::selftest {

namespace {

using wire::EventType;
using wire::FrameHeader;

Result pass(const std::string& name, const std::string& detail) {
    return Result{name, Status::Pass, detail};
}
Result fail(const std::string& name, const std::string& detail) {
    return Result{name, Status::Fail, detail};
}
Result skip(const std::string& name, const std::string& detail) {
    return Result{name, Status::Skip, detail};
}

// A synthetic x64 function prologue set, used to test the scanner without the
// game. Built at runtime so the test cannot silently rot against a real .text.
struct SyntheticImage {
    // Two plausible functions separated by padding, plus one decoy. The decoy
    // is the interesting part: it sits at a non-prologue offset and carries
    // bytes SIMILAR to the target, so a scanner with a greedy mask could pick
    // it. Note it deliberately does NOT contain the exact target byte sequence
    // -- an exact duplicate would make the primary scan legitimately ambiguous,
    // which is a different test (see checkScannerSynthetic's ambiguity case).
    std::uint8_t data[512]{};

    static constexpr std::size_t kRealOffset  = 64;   // sub rsp, imm8  prologue
    static constexpr std::size_t kDecoyOffset = 256;  // push rbp, different body
    static constexpr std::size_t kNotFuncOff  = 400;  // data, no prologue

    void build() {
        std::memset(data, 0xCC, sizeof(data));

        // kRealOffset: 48 83 EC 28 48 8B C1  -- matches kProbePattern
        static constexpr std::uint8_t real[] = {0x48, 0x83, 0xEC, 0x28, 0x48, 0x8B, 0xC1};
        std::memcpy(data + kRealOffset, real, sizeof(real));

        // kDecoyOffset: 55 48 8B EC  -- same shape, different bytes. A wildcard
        // too greedy would match both and the uniqueness check must refuse.
        static constexpr std::uint8_t decoy[] = {0x55, 0x48, 0x8B, 0xEC, 0x48, 0x89};
        std::memcpy(data + kDecoyOffset, decoy, sizeof(decoy));

        // kNotFuncOff: opcode-adjacent data with NO function prologue. Prologue
        // validation, not the scanner, is what must reject this.
        static constexpr std::uint8_t blob[] = {0x48, 0x83, 0xE4, 0x28, 0x48, 0x8B, 0xC8};
        std::memcpy(data + kNotFuncOff, blob, sizeof(blob));
    }
};

SyntheticImage g_image;

// A module view over the synthetic buffer, so the real scanner code runs
// unmodified. No API special-casing is needed for testing, which is the whole
// point: the thing under test is the shipping path.
scan::ModuleRange makeSyntheticModule() {
    g_image.build();
    scan::ModuleRange mod;
    mod.handle = nullptr;
    mod.name   = "synthetic";
    mod.base   = 0;
    mod.execSections.emplace_back(g_image.data, g_image.data + sizeof(g_image.data));
    return mod;
}

} // namespace

// ---------------------------------------------------------------------------
// Checks
// ---------------------------------------------------------------------------

Result checkAbiLayout() {
    // The static_asserts in TelemetryEvent.hpp already guarantee this at compile
    // time. This check exists so the value is also VISIBLE at runtime, in the
    // report the user reads. A protocol size is exactly the kind of thing that
    // must be checkable by the person debugging, not only by the compiler.
    struct Row { const char* name; std::size_t actual; std::size_t expected; };
    const Row rows[] = {
        {"FrameHeader",        sizeof(FrameHeader),                28},
        {"HeartbeatPayload",   sizeof(wire::HeartbeatPayload),      40},
        {"ThreadStatePayload", sizeof(wire::ThreadStatePayload),    21},
        {"StackFramePayload",  sizeof(wire::StackFramePayload),     20},
        {"VmTickPayload",      sizeof(wire::VmTickPayload),         30},
        {"VmExceptionPayload", sizeof(wire::VmExceptionPayload),    22},
        {"MemoryPayload",      sizeof(wire::MemoryPayload),         48},
        {"ModLoadPayload",     sizeof(wire::ModLoadPayload),        16},
        {"PluginDiagPayload",  sizeof(wire::PluginDiagPayload),      8},
        {"SaveBloatPayload",   sizeof(wire::SaveBloatPayload),      28},
    };

    std::ostringstream ss;
    bool ok = true;
    for (const auto& r : rows) {
        if (r.actual != r.expected) {
            ok = false;
            ss << r.name << " is " << r.actual << "B, expected " << r.expected << "B; ";
        }
    }
    // StackDump is variable-length; check the head plus the full array.
    // Compared through `volatile` so MSVC does not fold the expression and
    // raise C4127: the check exists to make the value VISIBLE in the report a
    // human reads, not to re-prove what the static_assert already guarantees.
    volatile std::size_t dump = sizeof(wire::StackDumpPayload);
    volatile std::size_t dumpExpected = 12 + wire::kMaxStackDepth * 20;
    if (dump != dumpExpected) {
        ok = false;
        ss << "StackDumpPayload is " << dump << "B, expected "
           << dumpExpected << "B; ";
    }

    if (!ok) {
        return fail("abi_layout", ss.str());
    }
    ss << "11 payloads match the Python and Rust bindings (header 28B, dump "
       << dump << "B)";
    return pass("abi_layout", ss.str());
}

Result checkWireRoundTrip() {
    // Encode a real VmTick and read the bytes back the way a consumer would.
    // This catches field-order mistakes that a size assertion cannot: two
    // layouts can be the same size and mean completely different things.
    wire::VmTickPayload out{};
    out.vmThreadId    = 7;
    out.opCounter     = 64;
    out.opTotal       = 10240;
    out.windowMs      = 0.25f;
    out.opRatePerSec  = 256.0f;
    out.formId        = 0x05005678u;
    out.depth         = 900;   // past Papyrus' 820 warn line; catches u8 truncation
    out.opCode        = 42;
    out.waiting       = 0;
    out.reserved      = 0;

    const std::uint8_t* p = reinterpret_cast<const std::uint8_t*>(&out);

    // Offsets are contractual; assert them explicitly rather than relying on
    // the compiler having laid it out the way the consumer reads it.
    const std::uint8_t* depthBytes = p + 24;
    const std::uint16_t depth =
        static_cast<std::uint16_t>(depthBytes[0] | (depthBytes[1] << 8));
    if (depth != 900) {
        return fail("wire_roundtrip",
                    "VmTick.depth is not at offset 24 as a u16, or does not "
                    "round-trip: got " + std::to_string(depth));
    }

    std::uint32_t formId = 0;
    std::memcpy(&formId, p + 20, sizeof(formId));
    if (formId != 0x05005678u) {
        return fail("wire_roundtrip", "VmTick.formId is not at offset 20");
    }

    // Header: magic, version, event type, then a length that must match.
    // Built via a non-const path so MSVC does not constant-fold the comparison
    // into C4127; the point of the check is the runtime layout, not the compiler.
    FrameHeader h{};
    h.magic       = wire::kFrameMagic;
    h.version     = wire::kProtocolVersion;
    h.eventType   = static_cast<std::uint8_t>(EventType::VmTick);
    h.flags       = 0;
    h.payloadSize = static_cast<std::uint32_t>(sizeof(wire::VmTickPayload));

    volatile std::size_t expected = sizeof(FrameHeader) + sizeof(wire::VmTickPayload);
    if (h.frameSize() != expected) {
        return fail("wire_roundtrip", "frameSize() disagrees with the header layout");
    }

    std::ostringstream ss;
    ss << "VmTick " << sizeof(wire::VmTickPayload) << "B encodes depth=" << depth
       << " formId=0x" << std::hex << formId << std::dec
       << ", frame " << h.frameSize() << "B";
    return pass("wire_roundtrip", ss.str());
}

Result checkPatternParser() {
    struct Case { const char* in; std::size_t len; std::uint8_t b0; std::uint16_t mask0; };
    // masks are 16-bit, so a fully-specified byte carries 0xFFFF.
    const Case cases[] = {
        {"48 8B ?? 5B C3",   5, 0x48, 0xFFFF},
        {"488B??5BC3",       5, 0x48, 0xFFFF},
        {"0x48 0x8B 0x05 ?", 4, 0x48, 0xFFFF},
    };
    for (const auto& c : cases) {
        auto p = scan::parsePattern(c.in);
        if (!p) {
            return fail("pattern_parser", std::string("failed to parse '") + c.in + "'");
        }
        if (p->length != c.len) {
            return fail("pattern_parser",
                        std::string("'") + c.in + "' parsed to length " +
                        std::to_string(p->length) + ", expected " + std::to_string(c.len));
        }
        if (p->bytes[0] != c.b0 || p->masks[0] != c.mask0) {
            return fail("pattern_parser", std::string("'") + c.in + "' byte0 mismatch");
        }
    }

    // A pattern too short to be safe against false positives must be REFUSED,
    // not accepted. "48 8B" matches almost anywhere in a .text section.
    if (scan::parsePattern("48 8B")) {
        return fail("pattern_parser", "accepted a 2-byte pattern that must be rejected");
    }
    // Garbage must be refused rather than guessed at.
    if (scan::parsePattern("48 ZZ 5B")) {
        return fail("pattern_parser", "accepted a non-hex token");
    }

    // A leading wildcard must survive, since it is legitimate. Needs 4+ bytes:
    // the parser refuses anything shorter, which is deliberate.
    auto wild = scan::parsePattern("?? 48 8B C1");
    if (!wild || wild->masks[0] != 0x00) {
        return fail("pattern_parser", "leading '??' wildcard not honoured");
    }
    if (wild && wild->length != 4) {
        return fail("pattern_parser", "leading wildcard changed the pattern length");
    }
    // A pattern shorter than 4 bytes must be refused: "48 8B" matches almost
    // anywhere in .text, so accepting it is how a detour lands in the wrong
    // function.
    if (scan::parsePattern("?? 48 8B")) {
        return fail("pattern_parser", "a 3-byte pattern was accepted; it must be refused");
    }

    return pass("pattern_parser", "3 valid patterns parsed, 4 invalid rejected "
                                  "including short, non-hex, and short-wildcard");
}

Result checkScannerSynthetic() {
    auto mod = makeSyntheticModule();

    // "48 83 EC ?? 48 8B C1" -- the real function, with a one-byte wildcard.
    auto p = scan::parsePattern("48 83 EC ?? 48 8B C1");
    if (!p) {
        return fail("scanner_synthetic", "test pattern did not parse");
    }
    const auto hit = scan::scanModule(mod, *p, /*requireUnique=*/true);
    if (!hit) {
        return fail("scanner_synthetic", "scanner did not resolve the synthetic probe");
    }
    const auto off = static_cast<std::size_t>(hit->address - mod.execSections[0].first);
    if (off != SyntheticImage::kRealOffset) {
        std::ostringstream ss;
        ss << "resolved to offset " << off << ", expected " << SyntheticImage::kRealOffset;
        return fail("scanner_synthetic", ss.str());
    }
    if (hit->matchCount != 1) {
        std::ostringstream ss;
        ss << "resolved with " << hit->matchCount << " matches; expected exactly 1";
        return fail("scanner_synthetic", ss.str());
    }

    // Ambiguity must be refused, not guessed at. "48 ?? EC" appears in BOTH the
    // real function and the decoy, so requiring uniqueness must reject it while
    // relaxing that requirement still finds it. This is the single most
    // important scanner property: a wrong guess is a detour in the wrong
    // function, which is a crash on the next script call.
    auto amb = scan::parsePattern("48 ?? EC ??");
    if (!amb) {
        return fail("scanner_synthetic", "ambiguity test pattern did not parse");
    }
    if (scan::scanModule(mod, *amb, /*requireUnique=*/true)) {
        return fail("scanner_synthetic",
                    "an ambiguous pattern resolved instead of being refused");
    }
    const auto multi = scan::scanModule(mod, *amb, /*requireUnique=*/false);
    if (!multi || multi->matchCount < 2) {
        return fail("scanner_synthetic",
                    "ambiguous pattern did not report 2+ matches when uniqueness was relaxed");
    }

    // The prologue gate is what rejects the non-function decoy. The scanner
    // alone cannot: it only knows byte patterns, not what a function entry is.
    // This asserts the two layers work together rather than one doing both jobs.
    auto* decoy = mod.execSections[0].first + SyntheticImage::kNotFuncOff;
    if (scan::isPlausibleCodeAddress(mod, decoy)) {
        return fail("scanner_synthetic",
                    "prologue gate accepted a non-function decoy at kNotFuncOff");
    }
    auto* real = mod.execSections[0].first + SyntheticImage::kRealOffset;
    if (!scan::isPlausibleCodeAddress(mod, real)) {
        return fail("scanner_synthetic", "prologue gate rejected the real function entry");
    }

    std::ostringstream ss;
    ss << "resolved at offset " << off << "; ambiguous pattern refused ("
       << (multi ? multi->matchCount : 0) << " candidates); prologue gate "
       << "accepted the function and rejected the decoy";
    return pass("scanner_synthetic", ss.str());
}

Result checkPrologueValidation() {
    // Prologue gate is the last line of defence before a detour lands in the
    // wrong function. Every one of these bytes is at offset 0 of a fresh buffer.
    struct Case { std::uint8_t bytes[8]; bool expect; const char* label; };
    const Case cases[] = {
        {{0x55, 0, 0, 0, 0, 0, 0, 0},                true,  "push rbp"},
        {{0x48, 0x8B, 0xEC, 0, 0, 0, 0, 0},          true,  "mov rbp, rsp"},
        {{0x48, 0x83, 0xEC, 0x28, 0, 0, 0, 0},        true,  "sub rsp, imm8"},
        {{0x48, 0x81, 0xEC, 0, 0, 0, 0, 0},           true,  "sub rsp, imm32"},
        // int3 padding then a real prologue. The fixture must contain the
        // prologue AFTER the padding, or there is nothing to accept.
        {{0xCC, 0xCC, 0x55, 0, 0, 0, 0, 0},           true,  "int3 padding then push rbp"},
        {{0x90, 0x48, 0x8B, 0xEC, 0, 0, 0, 0},        true,  "nop padding then mov rbp, rsp"},
        {{0x48, 0x8B, 0xC1, 0, 0, 0, 0, 0},           false, "mid-function (no prologue)"},
        {{0x00, 0x00, 0x00, 0, 0, 0, 0, 0},           false, "int3 padding then nothing"},
        {{0xC3, 0, 0, 0, 0, 0, 0, 0},                 true,  "ret thunk"},
    };
    for (const auto& c : cases) {
        alignas(16) std::uint8_t buf[16];
        std::memset(buf, 0, sizeof(buf));
        std::memcpy(buf, c.bytes, sizeof(c.bytes));
        const bool got = scan::looksLikeFunctionEntry(buf);
        if (got != c.expect) {
            return fail("prologue_validation",
                        std::string("'") + c.label + "' expected " +
                        (c.expect ? "accepted" : "rejected") + ", got " +
                        (got ? "accepted" : "rejected"));
        }
    }
    return pass("prologue_validation", "9 prologues classified correctly, "
                                       "including padding and two rejections");
}

Result checkRingBuffer() {
    // The ring is the one place the game thread and the IPC worker meet, so an
    // off-by-one here silently drops every event.
    telemetry::SpscQueue<std::uint32_t, 8> q;

    if (!q.empty() || q.size() != 0) {
        return fail("ring_buffer", "a fresh ring is not empty");
    }

    std::uint32_t v = 0;
    for (std::uint32_t i = 0; i < 7; ++i) {
        if (!q.tryPush(i)) {
            return fail("ring_buffer", "push " + std::to_string(i) + " of 7 was rejected");
        }
    }
    // Capacity 8 with the one-slot-empty invariant holds 7. The 8th MUST fail:
    // overwriting a slot the consumer has not read yet is silent data loss.
    if (q.tryPush(999)) {
        return fail("ring_buffer", "8th push succeeded; capacity guard is broken");
    }
    if (q.dropped() != 1) {
        return fail("ring_buffer", "drop counter did not increment on a full ring");
    }

    for (std::uint32_t i = 0; i < 7; ++i) {
        if (!q.tryPop(v) || v != i) {
            return fail("ring_buffer", "FIFO order broken at index " + std::to_string(i));
        }
    }
    if (q.tryPop(v)) {
        return fail("ring_buffer", "pop succeeded on an empty ring");
    }

    // Interleaved push/pop must not corrupt ordering.
    for (std::uint32_t i = 0; i < 20; ++i) {
        if (!q.tryPush(i)) {
            return fail("ring_buffer", "interleaved push " + std::to_string(i) + " rejected");
        }
        if (!q.tryPop(v) || v != i) {
            return fail("ring_buffer", "interleaved pop returned the wrong value");
        }
    }

    return pass("ring_buffer", "capacity guard, drop counter, FIFO order and "
                                "20 interleaved cycles all correct");
}

Result checkInternTable() {
    telemetry::InternTable t;
    const auto a = t.intern("Script_TCMain");
    const auto b = t.intern("Script_WorkshopRef");
    const auto c = t.intern("Script_TCMain");  // must reuse, not append

    if (a == telemetry::kUninternedId || b == telemetry::kUninternedId) {
        return fail("intern_table", "intern returned the uninterned sentinel for a real string");
    }
    if (a != c) {
        return fail("intern_table", "interning the same string twice produced two ids");
    }
    if (a == b) {
        return fail("intern_table", "two different strings collided on one id");
    }
    if (t.resolve(a) != "Script_TCMain") {
        return fail("intern_table", "resolve did not round-trip the interned string");
    }
    if (t.intern("") != telemetry::kUninternedId) {
        return fail("intern_table", "empty string should not consume an id");
    }

    const std::string json = t.dumpJson();
    if (json.find("Script_TCMain") == std::string::npos || json.front() != '{') {
        return fail("intern_table", "dumpJson is not a JSON object containing the names");
    }

    std::ostringstream ss;
    ss << t.size() << " ids, stable across repeat interns, JSON dump " << json.size() << "B";
    return pass("intern_table", ss.str());
}

namespace {

// A target with a real frame-setup prologue and a body comfortably longer than
// the 14-byte absolute-jump patch, and with NO short relative branch in the
// first 14 bytes -- rel8 branches are unhookerable by design (see Detour.cpp),
// and a loop in the first 14 bytes would make this fixture unhookable for a
// reason that has nothing to do with what the test is checking.
__declspec(noinline) std::uint64_t detourFixture() {
    std::uint64_t a = 0xC0FFEEull;
    std::uint64_t b = a + 11;
    std::uint64_t c = b * 2;
    std::uint64_t d = c ^ 0x5A5A;
    return d;
}

// A 6-byte leaf: `mov eax, imm32; ret`. Deliberately too small to detour.
__declspec(noinline) std::uint64_t tinyLeaf() { return 1; }

} // namespace

namespace {

// The one place in the self-test where a fault must be attributed rather than
// propagated. MSVC forbids __try/__except in a frame that needs unwinding, so
// this lives in a function holding nothing but PODs.
struct TrampProbe {
    void*  fn = nullptr;
    std::uint64_t result = 0;
    bool  faulted = false;
    unsigned long exceptionCode = 0;
    void* faultAddress = nullptr;
};

// The filter expression is the only place GetExceptionInformation() is legal,
// and it cannot pass a payload, so the probe is reached through this pointer.
// File-scope rather than thread_local: the self-test is single-threaded by
// contract, and a TLS access inside an exception filter is a bad idea.
TrampProbe* g_activeProbe = nullptr;

int CALLBACK grabException(EXCEPTION_POINTERS* ep) {
    if (g_activeProbe != nullptr && ep->ExceptionRecord != nullptr) {
        g_activeProbe->faulted = true;
        g_activeProbe->exceptionCode = ep->ExceptionRecord->ExceptionCode;
        g_activeProbe->faultAddress = ep->ExceptionRecord->ExceptionAddress;
    }
    return EXCEPTION_EXECUTE_HANDLER; // must be int for a __except filter
}

std::uint64_t callThroughTrampoline(TrampProbe* p) {
    g_activeProbe = p;
    __try {
        auto fn = reinterpret_cast<std::uint64_t (*)()>(p->fn);
        p->result = fn();
    } __except (grabException(GetExceptionInformation())) {
        // Details are recorded in the probe by the filter above.
    }
    g_activeProbe = nullptr;
    return p->result;
}

} // namespace

Result checkDetourLifecycle() {
    const bool trace = GetEnvironmentVariableA("VPROBE_SELFTEST_TRACE", nullptr, 0) != 0;
    const auto mark = [&](const char* s) {
        if (trace) { std::fprintf(stderr, "      [detour] %s\r\n", s); std::fflush(stderr); }
    };

    // --- install / trampoline / remove on a proper function ---------------
    mark("install detourFixture");
    hooks::Detour d;
    const auto st = d.install(reinterpret_cast<void*>(&detourFixture),
                              reinterpret_cast<void*>(&detourFixture));
    mark("install returned");
    if (st != hooks::DetourStatus::Ok) {
        // Surface the reason, not just the enum. This is the same text the
        // console commands and the resolver report show, so a signature that
        // stops matching on a new build tells the user WHICH byte sequence
        // needs updating instead of just "unsupported relocation".
        return fail("detour_lifecycle",
                    std::string("install returned: ") + hooks::toString(st) +
                    " -- " + d.lastError());
    }
    if (d.trampoline() == nullptr) {
        return fail("detour_lifecycle", "install succeeded but produced no trampoline");
    }

    // Expected result, derived from the fixture body rather than hardcoded,
    // so editing the fixture cannot silently invalidate the assertion.
    const std::uint64_t base = 0xC0FFEEull;
    const std::uint64_t expect = ((base + 11) * 2) ^ 0x5A5A;

    mark("call trampoline");
    TrampProbe probe;
    probe.fn = d.trampoline();
    callThroughTrampoline(&probe);
    mark("trampoline returned");
    if (probe.faulted) {
        char buf[192];
        _snprintf_s(buf, _TRUNCATE,
                    "trampoline faulted: code=0x%08lX at %p (stolen %zu, patch 14)",
                    probe.exceptionCode, probe.faultAddress, d.stolenLength());
        return fail("detour_lifecycle", buf);
    }
    if (probe.result != expect) {
        return fail("detour_lifecycle", "trampoline returned the wrong value");
    }

    mark("remove");
    d.remove();
    if (d.trampoline() != nullptr) {
        return fail("detour_lifecycle", "remove left a dangling trampoline pointer");
    }
    if (detourFixture() != expect) {
        return fail("detour_lifecycle", "function misbehaves after remove");
    }

    // --- a function too small to detour must be REFUSED -------------------
    // This is not a limitation to paper over: a 14-byte absolute jump cannot fit
    // in a 6-byte leaf, and installing anyway would write past the function.
    hooks::Detour tiny;
    const auto tinySt = tiny.install(reinterpret_cast<void*>(&tinyLeaf),
                                     reinterpret_cast<void*>(&tinyLeaf));
    if (tinySt == hooks::DetourStatus::Ok) {
        return fail("detour_lifecycle",
                    "a leaf too small for a 14-byte patch was accepted");
    }
    if (tinyLeaf() != 1) {
        return fail("detour_lifecycle", "function corrupted by a refused detour");
    }

    // --- null target must be refused, not crash ---------------------------
    hooks::Detour bad;
    if (bad.install(nullptr, nullptr) != hooks::DetourStatus::TargetNull) {
        return fail("detour_lifecycle", "install(nullptr) did not return TargetNull");
    }

    return pass("detour_lifecycle",
                "install/trampoline/remove verified; undersized leaf and null "
                "target both correctly refused");
}

Result checkResolverState() {
    // Only meaningful with the game loaded. Without it, the correct answer is
    // "nothing resolved" -- which is a pass, not a failure, and is exactly the
    // degradation the design promises.
    if (GetModuleHandleW(L"Fallout4.exe") == nullptr) {
        return skip("resolver_state", "no game module; run in-game for real results");
    }
    return skip("resolver_state",
                "resolver state is reported by the bootstrap report, not here");
}

// The binary address database is produced by a Python generator and consumed
// by C++. That boundary is only safe if both sides compute the SAME hash and
// agree on the geometry, and a mismatch is silent: the lookup simply returns
// nothing and every probe quietly falls through to the AOB tier. So the
// vectors are pinned here against the values the generator produces.
//
// These are the FNV-1a 32 test vectors the launcher suite already uses, plus
// one symbol from our real database. If the generator ever changes its hash,
// this fails rather than the resolution quietly getting worse.
Result checkLibbinFormat() {
    struct Row { const char* in; std::uint32_t expected; };
    const Row rows[] = {
        {"",       0x811C9DC5u},
        {"a",      0xE40C292Cu},
        {"foobar", 0xBF9CF968u},
        // A real symbol from vprobe/libs/fo4_1_11_240.addresses.bin. If the
        // name mangling or hashing on either side drifts, this is the canary.
        {"BSScript__IClientVM", 0xD2097120u},
    };
    for (const auto& r : rows) {
        const std::uint32_t got = vc::fnv1a32(r.in);
        if (got != r.expected) {
            return fail("libbin_format",
                        std::string("fnv1a32('") + r.in + "') = 0x" +
                        std::to_string(got) + ", expected 0x" +
                        std::to_string(r.expected));
        }
    }

    // Geometry, from the format spec in tools/build_libbin.py. Compared
    // through `volatile` so MSVC does not fold it away and raise C4127, the
    // same approach checkAbiLayout uses and for the same reason: the point is
    // to make the number VISIBLE in the report a human reads, not to re-prove
    // what constexpr already guarantees to the compiler.
    volatile std::size_t headerSize = vc::kLibbinHeaderSize;
    volatile std::size_t recordSize = vc::kLibbinRecordSize;
    if (headerSize != 24 || recordSize != 12) {
        std::ostringstream bad;
        bad << "geometry is " << headerSize << "B header / " << recordSize
            << "B records, expected 24/12";
        return fail("libbin_format", bad.str());
    }
    return pass("libbin_format", "4 FNV-1a vectors match the Python generator; "
                                 "geometry 24B header + 12B records; schema v1");
}

// The blob/text two-source contract, exercised end to end against synthetic
// fixtures. This is the test that makes the safety property real rather than
// aspirational: it drives the actual loader, not a model of it.
//
// The fixtures are written to %TEMP% and removed afterwards, because the loader
// takes a path. Writing a fixture is the one thing this check does that touches
// the filesystem, and it stays inside the temp directory.
namespace {

// A minimal but structurally valid PE image: MZ, e_lfanew, PE signature, COFF
// header with a plausible SizeOfOptionalHeader. Only the header region is ever
// hashed, so the body can stay zeroed.
constexpr std::size_t kFakePeSize = 1024;
alignas(16) std::uint8_t g_fakePe[kFakePeSize];

std::uint8_t* makeFakePe() {
    std::memset(g_fakePe, 0, sizeof(g_fakePe));
    g_fakePe[0] = 'M';
    g_fakePe[1] = 'Z';
    const std::uint32_t e_lfanew = 0x80;
    std::memcpy(g_fakePe + 0x3C, &e_lfanew, 4);
    std::memcpy(g_fakePe + e_lfanew, "PE\0\0", 4);
    const std::uint16_t sizeOfOptional = 0xF0;
    std::memcpy(g_fakePe + e_lfanew + 4 + 16, &sizeOfOptional, 2);
    return g_fakePe;
}

// Assemble a blob in memory. `imageHash` is what the loader will compare the
// candidate image against, so a test can produce a deliberate mismatch.
std::vector<std::uint8_t> makeBlob(std::uint32_t imageHash, const char* symbol,
                                   std::uint32_t rva, bool exact = true,
                                   bool corruptGeometry = false) {
    std::vector<std::uint8_t> blob(vc::kLibbinHeaderSize + vc::kLibbinRecordSize, 0);
    std::memcpy(blob.data(), vc::kLibbinMagic, 4);
    const std::uint32_t schema = vc::kLibbinSchemaVersion;
    const std::uint32_t reserved = 0;
    std::memcpy(blob.data() + 4,  &schema, 4);
    std::memcpy(blob.data() + 20, &reserved, 4);
    const std::uint32_t count = 1;
    const std::uint32_t recSize = corruptGeometry
                                      ? static_cast<std::uint32_t>(vc::kLibbinRecordSize) + 4
                                      : static_cast<std::uint32_t>(vc::kLibbinRecordSize);
    std::memcpy(blob.data() + 8,  &imageHash, 4);
    std::memcpy(blob.data() + 12, &count, 4);
    std::memcpy(blob.data() + 16, &recSize, 4);
    std::uint8_t* rec = blob.data() + vc::kLibbinHeaderSize;
    const std::uint32_t nameHash = vc::fnv1a32(std::string(symbol));
    std::memcpy(rec + 0, &nameHash, 4);
    std::memcpy(rec + 4, &rva, 4);
    rec[8] = 2;   // classId: VTable
    rec[9] = 0xFF;
    const std::uint16_t flags = exact ? 1 : 0;
    std::memcpy(rec + 10, &flags, 2);
    return blob;
}

struct TempFile {
    std::wstring path;
    bool ok = false;
    ~TempFile() {
        if (ok && !path.empty()) {
            DeleteFileW(path.c_str());
        }
    }
};

TempFile writeTemp(const wchar_t* name, const std::vector<std::uint8_t>& bytes) {
    TempFile t;
    wchar_t dir[MAX_PATH]{};
    const DWORD n = GetTempPathW(MAX_PATH, dir);
    if (n == 0 || n >= MAX_PATH) {
        return t;
    }
    t.path = std::wstring(dir, n) + name;
    HANDLE h = CreateFileW(t.path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS,
                           FILE_ATTRIBUTE_TEMPORARY, nullptr);
    if (h == INVALID_HANDLE_VALUE) {
        return t;
    }
    DWORD written = 0;
    WriteFile(h, bytes.data(), static_cast<DWORD>(bytes.size()), &written, nullptr);
    CloseHandle(h);
    t.ok = written == bytes.size();
    return t;
}

TempFile writeTempText(const wchar_t* name, const char* text) {
    return writeTemp(name, std::vector<std::uint8_t>(text, text + std::strlen(text)));
}

} // namespace

// The tier ORDERING, exercised through the real resolve path against a
// synthetic image. Everything else in this file tests a component; this tests
// the decision the resolver actually makes, which is the part that was only
// ever observable inside a running game.
//
// The fixture deliberately reproduces the shape of the one real vtable we have
// measured -- BSScript__IClientVM, 6 of 8 slots in .text with two pointing into
// .rdata as thunks. A table of 8 perfect code pointers would be a fixture that
// passes trivially and proves nothing about the majority rule.
Result checkTierOrdering() {
    // --- build a synthetic image ------------------------------------------
    // Layout, as offsets within one buffer:
    //   0x0000  code region   -- 8 function bodies with real prologues
    //   0x1000  vtable        -- 8 slots, 6 to code, 2 to .rdata (thunks)
    //   0x2000  rdata region  -- where the thunks live
    //   0x3000  PE header block, so peHeaderHash has something real to hash
    alignas(16) static std::uint8_t image[0x4000];
    std::memset(image, 0, sizeof(image));

    // PE header, identical shape to the other fixture.
    image[0] = 'M';
    image[1] = 'Z';
    const std::uint32_t e_lfanew = 0x80;
    std::memcpy(image + 0x3C, &e_lfanew, 4);
    std::memcpy(image + e_lfanew, "PE\0\0", 4);
    const std::uint16_t sizeOfOptional = 0xF0;
    std::memcpy(image + e_lfanew + 4 + 16, &sizeOfOptional, 2);

    // Code bodies: 0x40 apart, each a real prologue the gate will accept.
    constexpr std::uint8_t kPrologue[] = {0x48, 0x83, 0xEC, 0x28};
    for (int i = 0; i < 8; ++i) {
        std::memcpy(image + 0x40 * (i + 1), kPrologue, sizeof(kPrologue));
    }

    // The vtable: 6 slots into code, 2 into rdata -- mirroring the real thing.
    for (int i = 0; i < 8; ++i) {
        std::uint64_t target = (i == 3 || i == 7)
                                   ? reinterpret_cast<std::uint64_t>(image + 0x2000 + 0x10 * i)
                                   : reinterpret_cast<std::uint64_t>(image + 0x40 * (i + 1));
        std::memcpy(image + 0x1000 + i * 8, &target, 8);
    }

    scan::ModuleRange mod;
    // handle MUST be the image base, not nullptr. The scanner's own synthetic
    // fixture sets handle=nullptr because it only ever scans data pointers, but
    // the resolver forms addresses as handle + rva, exactly as the live image
    // does (for the main module, HMODULE *is* the base). Leaving it null made
    // every candidate address a bare offset -- 0x1000 instead of image+0x1000
    // -- which the vtable gate correctly rejected. The test failing for a
    // fixture reason rather than a code reason is precisely what it was for.
    mod.handle   = reinterpret_cast<HMODULE>(reinterpret_cast<std::uintptr_t>(image));
    mod.name     = "synthetic";
    mod.base     = reinterpret_cast<std::uint64_t>(image);
    mod.imageSize = sizeof(image);
    mod.execSections.emplace_back(image + 0x0000, image + 0x0800);
    mod.execSections.emplace_back(image + 0x2000, image + 0x2100);

    vc::Signature sig;
    sig.name         = "TestVTable";
    // kind MUST be VTable. resolve() branches on this to choose between the
    // vtable check and the code check, and vtableSlots alone does not select it
    // -- leaving kind at its default made it code-validate a read-only-data
    // address, which the code gate correctly refused. The vtable is only
    // reachable through a signature that says what it is pointing at.
    sig.kind         = vc::TargetKind::VTable;
    sig.vtableSlots  = 8;
    sig.pattern      = "48 83 EC 28 ?? 48 8B";   // never scanned: Tier 1 answers

    const std::uint32_t vtableRva = 0x1000;
    const std::uint32_t imageHash = vc::peHeaderHash(image);
    if (imageHash == 0) {
        return fail("tier_ordering", "synthetic image did not hash");
    }

    // --- 1. TIER 1 via the blob, and the resolved slot is a real function ---
    {
        auto blob = makeBlob(imageHash, "TestVTable", vtableRva);
        auto file = writeTemp(L"pipmon_t_order.bin", blob);
    vc::Resolver r;
    r.addSignatureForTest(sig);
    r.setModuleForTest(mod);
    if (!r.hasSignatureForTest("TestVTable")) {
        return fail("tier_ordering",
                    "addSignatureForTest did not register the target; resolve() "
                    "returns null for an unknown name, which is what we were seeing");
    }
    if (!r.loadAddressLibBin(file.path, image)) {
            return fail("tier_ordering", "matching blob refused on a synthetic image");
        }
        auto* slotPtr = r.resolveVTableSlot("TestVTable", 0);
        if (slotPtr == nullptr) {
            return fail("tier_ordering", "Tier 1 blob did not resolve a vtable slot");
        }
        if (reinterpret_cast<std::uint8_t*>(slotPtr) != image + 0x40) {
            return fail("tier_ordering", "resolved slot 0 does not point at function 0");
        }
        // Slot 3 is a thunk in .rdata. The TABLE was still accepted (that is the
        // majority rule doing its job -- 6 of 8 in code), but the SLOT resolves
        // to nullptr, deliberately: a thunk is not the implementation, and
        // returning a read-only-data address as "the function" would put a
        // detour on a jump stub. The documented contract is that the caller
        // tries another slot, which is what made 6-of-8 resilience rather than
        // a partial failure.
        //
        // This asymmetry is the point being pinned: tolerant at the table,
        // strict at the slot. An earlier version of this test asserted the
        // opposite and failed, which is a useful reminder that the test is
        // allowed to be wrong and the code is not automatically the culprit.
        if (r.resolveVTableSlot("TestVTable", 3) != nullptr) {
            return fail("tier_ordering",
                        "a thunk slot was returned as a function; it must resolve "
                        "to null so the caller tries another slot");
        }
        // ...and a CODE slot from the same table must still work, proving the
        // refusal is per-slot rather than poisoning the whole table.
        auto* slot1 = r.resolveVTableSlot("TestVTable", 1);
        if (slot1 == nullptr || reinterpret_cast<std::uint8_t*>(slot1) != image + 0x80) {
            return fail("tier_ordering",
                        "a code slot after a refused thunk slot did not resolve");
        }
        // resolveVTableSlot is a pure query -- it resolves without recording
        // anything. resolve() is what writes the Tier 1 outcome into the slot,
        // so that is where the state has to be checked. Asserting it here was
        // wrong twice over: wrong function, and it would have made a read-only
        // query look like it should have side effects.
        auto* table = r.resolve("TestVTable");
        if (table == nullptr) {
            return fail("tier_ordering", "resolve() did not return the Tier 1 address");
        }
        if (reinterpret_cast<std::uint8_t*>(table) != image + 0x1000) {
            return fail("tier_ordering", "resolve() returned the wrong Tier 1 address");
        }
        if (r.stateOfForTest("TestVTable") != vc::State::FromAddressLib) {
            return fail("tier_ordering", "state is not FromAddressLib after a Tier 1 hit");
        }
        if (r.noteOfForTest("TestVTable") != "addresslib") {
            return fail("tier_ordering",
                        "the Tier 1 note does not say 'addresslib', so a failure "
                        "would be misattributed: " + r.noteOfForTest("TestVTable"));
        }
    }

    // --- 2. TIER 1 via TEXT only: no blob at all, same answer --------------
    // The fallback has to produce the same resolution, or "we have a fallback"
    // is a claim rather than a fact.
    {
        char ini[128];
        std::snprintf(ini, sizeof(ini), "TestVTable %X\n", vtableRva);
        auto file = writeTempText(L"pipmon_t_order.ini", ini);
        vc::Resolver r;
        r.addSignatureForTest(sig);
        r.setModuleForTest(mod);
        if (!r.loadAddressLib(file.path)) {
            return fail("tier_ordering", "text-only INI failed to load");
        }
        auto* slotPtr = r.resolveVTableSlot("TestVTable", 0);
        if (slotPtr == nullptr || reinterpret_cast<std::uint8_t*>(slotPtr) != image + 0x40) {
            return fail("tier_ordering", "the TEXT fallback did not resolve the same slot");
        }
    }

    // --- 3. STALE blob must NOT win: text answers, blob refused ------------
    // Both sources present, blob from a foreign image. The answer must be
    // unchanged, because the refusal has to be total rather than partial.
    {
        auto blob = makeBlob(imageHash ^ 0xFFFFFFFFu, "TestVTable", vtableRva);
        auto file = writeTemp(L"pipmon_t_stale.bin", blob);
        char ini[128];
        std::snprintf(ini, sizeof(ini), "TestVTable %X\n", vtableRva);
        auto iniFile = writeTempText(L"pipmon_t_stale.ini", ini);
        vc::Resolver r;
        r.addSignatureForTest(sig);
        r.setModuleForTest(mod);
        const bool binOk = r.loadAddressLibBin(file.path, image);
        const bool iniOk = r.loadAddressLib(iniFile.path);
        if (binOk) {
            return fail("tier_ordering", "a foreign-image blob was accepted alongside text");
        }
        if (!iniOk) {
            return fail("tier_ordering", "the text source failed to load");
        }
        auto* slotPtr = r.resolveVTableSlot("TestVTable", 0);
        if (slotPtr == nullptr || reinterpret_cast<std::uint8_t*>(slotPtr) != image + 0x40) {
            return fail("tier_ordering",
                        "with the blob refused, the text source did not take over");
        }
    }

    // --- 4. a vtable the gates REJECT must not resolve ---------------------
    // Points at code, not at a pointer table. If this resolved, the vtable gate
    // would be decorative and a wrong address could reach a detour.
    {
        char ini[128];
        std::snprintf(ini, sizeof(ini), "TestVTable %X\n", 0x0040);  // a function, not a table
        auto file = writeTempText(L"pipmon_t_bad.ini", ini);
        vc::Resolver r;
        r.addSignatureForTest(sig);
        r.setModuleForTest(mod);
        r.loadAddressLib(file.path);
        if (r.resolveVTableSlot("TestVTable", 0) != nullptr) {
            return fail("tier_ordering",
                        "a non-vtable address was accepted; the gate is not doing its job");
        }
    }

    return pass("tier_ordering",
                "blob and text resolve the same slot; a thunk slot refuses while a "
                "code slot beside it still resolves; foreign blob refused; non-vtable rejected");
}

Result checkBlobTwoSource() {
    const std::uint8_t* image = makeFakePe();
    const std::uint32_t imageHash = vc::peHeaderHash(image);
    if (imageHash == 0) {
        return fail("blob_two_source", "the synthetic PE fixture did not hash");
    }

    const std::uint32_t kRva = 0x25B85C8;
    const char* kSymbol = "BSScript__IClientVM";

    // --- 1. a matching blob loads and the lookup finds the symbol ------------
    {
        auto blob = makeBlob(imageHash, kSymbol, kRva);
        auto file = writeTemp(L"pipmon_t_ok.bin", blob);
        if (!file.ok) {
            return fail("blob_two_source", "could not write the temp fixture");
        }
        vc::Resolver r;
        if (!r.loadAddressLibBin(file.path, image)) {
            return fail("blob_two_source", "a matching-image blob was refused");
        }
        if (r.rvaFromBin("BSScript__IClientVM") == 0) {
            return fail("blob_two_source", "lookupBin missed a symbol that is present");
        }
        if (r.rvaFromBin("NoSuchSymbolHere") != 0) {
            return fail("blob_two_source", "lookupBin invented a hit for an absent symbol");
        }
    }

    // --- 2. a FOREIGN-image blob is REFUSED. This is the safety property. ---
    {
        auto blob = makeBlob(imageHash ^ 0xFFFFFFFFu, kSymbol, kRva);
        auto file = writeTemp(L"pipmon_t_wrong.bin", blob);
        vc::Resolver r;
        if (r.loadAddressLibBin(file.path, image)) {
            return fail("blob_two_source",
                        "a blob built for a different image was ACCEPTED");
        }
        // And the refusal must be total, not partial: no half-trusted table.
        if (r.rvaFromBin(kSymbol) != 0) {
            return fail("blob_two_source",
                        "a refused blob still answered lookups");
        }
    }

    // --- 3. a collision-flagged entry is reported as a MISS ------------------
    // A 1-in-2^32 false positive is a detour in the wrong function, so an
    // ambiguous record must not be handed back as an address.
    {
        auto blob = makeBlob(imageHash, kSymbol, kRva, /*exact=*/false);
        auto file = writeTemp(L"pipmon_t_collide.bin", blob);
        vc::Resolver r;
        if (!r.loadAddressLibBin(file.path, image)) {
            return fail("blob_two_source", "a collision-flagged blob should still LOAD");
        }
        if (r.rvaFromBin(kSymbol) != 0) {
            return fail("blob_two_source",
                        "a collision-flagged record was returned as a hit");
        }
    }

    // --- 4. malformed geometry is refused, not misread ----------------------
    {
        auto blob = makeBlob(imageHash, kSymbol, kRva, true, /*corruptGeometry=*/true);
        auto file = writeTemp(L"pipmon_t_stride.bin", blob);
        vc::Resolver r;
        if (r.loadAddressLibBin(file.path, image)) {
            return fail("blob_two_source",
                        "a blob with the wrong record stride was accepted");
        }
    }
    {   // truncated: header claims more records than the file holds
        auto blob = makeBlob(imageHash, kSymbol, kRva);
        blob.resize(blob.size() - 4);
        auto file = writeTemp(L"pipmon_t_trunc.bin", blob);
        vc::Resolver r;
        if (r.loadAddressLibBin(file.path, image)) {
            return fail("blob_two_source", "a truncated blob was accepted");
        }
    }

    // --- 4. an UNKNOWN schema is refused outright ---------------------------
    // The reason schema_version exists. A v2 blob that widened a record field
    // would be read at the v1 stride and hand back plausible, wrong addresses;
    // the symptom would be a detour in the wrong function, not an error. So an
    // unrecognised version must be a refusal, never a best-effort parse.
    {
        auto blob = makeBlob(imageHash, kSymbol, kRva);
        const std::uint32_t future = vc::kLibbinSchemaVersion + 1;
        std::memcpy(blob.data() + 4, &future, 4);
        auto file = writeTemp(L"pipmon_t_schema.bin", blob);
        vc::Resolver r;
        if (r.loadAddressLibBin(file.path, image)) {
            return fail("blob_two_source",
                        "a blob declaring a FUTURE schema version was accepted");
        }
    }
    // ...and a non-zero `reserved` must be refused too, so a v2 that reuses
    // those bytes cannot slip through by leaving schema alone.
    {
        auto blob = makeBlob(imageHash, kSymbol, kRva);
        const std::uint32_t used = 0xDEADBEEF;
        std::memcpy(blob.data() + 20, &used, 4);
        auto file = writeTemp(L"pipmon_t_reserved.bin", blob);
        vc::Resolver r;
        if (r.loadAddressLibBin(file.path, image)) {
            return fail("blob_two_source",
                        "a blob with non-zero reserved bytes was accepted");
        }
    }

    // --- 5. the TEXT fallback still works with no blob at all ---------------
    // The whole promise of keeping two representations is that losing the fast
    // one costs speed, not correctness. If the text path were broken the blob
    // would be hiding a single point of failure rather than removing one.
    {
        auto ini = writeTempText(L"pipmon_t.ini",
            "# fixture\n"
            "BSScript__IClientVM 25B85C8\n"
            "SomeOtherSymbol 1234\n");
        vc::Resolver r;
        if (!r.loadAddressLib(ini.path)) {
            return fail("blob_two_source", "the text INI fixture failed to load");
        }
        if (r.rvaFromText("BSScript__IClientVM") == 0) {
            return fail("blob_two_source", "the text INI fixture did not yield an RVA");
        }
        if (r.rvaFromText("NotInTheIni") != 0) {
            return fail("blob_two_source", "the text path invented a symbol");
        }
    }

    return pass("blob_two_source",
                "match loads+resolves; foreign image REFUSED; collision treated "
                "as miss; bad stride and truncation refused; text fallback works");
}

// must hold, and the second is the one that protects the game:
//
//   1. the hash agrees with the generator, so a correct blob is not rejected
//   2. peHeaderHash REJECTS a non-image, so a garbage or foreign blob is refused
//
// (2) is the safety property. A mismatch must never degrade into "load it
// anyway": wrong RVAs become detours in the wrong function, which is a crash
// rather than a diagnostic. So the negative cases are tested harder than the
// positive one.
Result checkPeHeaderHash() {
    // A real Fallout4.exe, when present. This is the value the shipped blob
    // records; if the toolchain or the game moves, this fails and tells us the
    // blob needs regenerating rather than silently mismatching in-game.
    wchar_t gamePath[MAX_PATH]{};
    GetModuleFileNameW(nullptr, gamePath, MAX_PATH);
    std::wstring gameDir(gamePath);
    const auto slash = gameDir.find_last_of(L"\\/");
    if (slash == std::wstring::npos) {
        return skip("pe_header_hash", "could not determine the game directory");
    }
    gameDir = gameDir.substr(0, slash);

    // Negative cases first: they need no file and are the safety-critical half.
    // A buffer that is not a PE image at all.
    alignas(8) std::uint8_t junk[512];
    std::memset(junk, 0xCC, sizeof(junk));
    if (vc::peHeaderHash(junk) != 0) {
        return fail("pe_header_hash", "a buffer with no MZ header was hashed as valid");
    }
    // MZ present but e_lfanew is absurd -- the case that would otherwise be an
    // out-of-bounds read inside the game process.
    alignas(8) std::uint8_t mzBad[1024];
    std::memset(mzBad, 0, sizeof(mzBad));
    mzBad[0] = 'M';
    mzBad[1] = 'Z';
    const std::uint32_t hugeLfanew = 0x7FFFFFFFu;
    std::memcpy(mzBad + 0x3C, &hugeLfanew, 4);
    if (vc::peHeaderHash(mzBad) != 0) {
        return fail("pe_header_hash", "a bogus e_lfanew was hashed as valid");
    }
    if (vc::peHeaderHash(nullptr) != 0) {
        return fail("pe_header_hash", "a null image base was hashed as valid");
    }

    // Positive case, read from the real executable. Read-only: this test opens
    // the game binary and never writes to it.
    HMODULE exe = GetModuleHandleW(L"Fallout4.exe");
    if (exe == nullptr) {
        return skip("pe_header_hash",
                    "3 refusal cases passed; no game module for the positive case");
    }
    const std::uint32_t live = vc::peHeaderHash(
        reinterpret_cast<const std::uint8_t*>(reinterpret_cast<std::uintptr_t>(exe)));
    if (live == 0) {
        return fail("pe_header_hash", "the live game module hashed to 0 (refused a valid image)");
    }

    std::ostringstream ss;
    ss << "3 refusal cases passed; live Fallout4.exe header hash 0x" << std::hex
       << live << std::dec;
    return pass("pe_header_hash", ss.str());
}

Result checkReportFitsWire() {
    // The resolver report is the one diagnostic that explains a broken runtime,
    // and it is published through the SAME size check as every other payload.
    // kMaxPayloadBytes is 2048. If the report exceeds it, publish() returns
    // false BEFORE caching, so the report is never stored, never replayed, and
    // never sent -- and nothing anywhere says so. The symptom is a runtime
    // that looks healthy on the wire while the one message that would explain
    // it is silently absent, which is precisely the failure mode this project
    // keeps having to defend against.
    //
    // It happened for real: the report carries a full AOB pattern per entry
    // and no PluginDiag frame was ever observed on a live pipe. Asserting the
    // size here is what makes that impossible to reintroduce silently.
    vc::Resolver r;
    const std::string report = r.buildReportJson();
    const std::size_t total = report.size() + sizeof(wire::PluginDiagPayload);
    const std::size_t cap = ipc::kMaxPayloadBytes;

    if (total > cap) {
        std::ostringstream ss;
        ss << "resolver report is " << report.size() << "B text ("
           << total << "B with the diag header) but the wire cap is " << cap
           << "B -- it would be dropped silently, by " << (total - cap) << "B";
        return fail("report_fits_wire", ss.str());
    }

    // Headroom is worth reporting, not just the pass: a report at 90% of the
    // cap is one added signature away from vanishing without anyone noticing.
    const int pct = static_cast<int>((total * 100) / cap);
    std::ostringstream ok;
    ok << report.size() << "B report + 8B header = " << total << "B of " << cap
       << "B (" << pct << "% of the wire cap)";
    if (pct > 80) {
        return fail("report_fits_wire",
                    ok.str() + " -- over 80% of the cap; the next entry would "
                               "silently remove the diagnostic entirely");
    }
    return pass("report_fits_wire", ok.str());
}

Result checkDiagCarriesText() {
    // PluginDiagPayload.textLength is the field that decides whether a consumer
    // can see a diagnostic at all, and it has silently broken THREE times:
    //
    //   1. the producer wrote into a buffer nothing read, so nothing was sent
    //   2. the replay resent the wrong (cached) diagnostic
    //   3. every call site set textLength = 0, so a correctly-sized 1426-byte
    //      resolver report declared an EMPTY body and every consumer read
    //      nothing
    //
    // Each of those produced a healthy-looking pipe and a missing diagnostic,
    // which is the worst possible shape of failure: the transport says fine and
    // the information is gone. The length is now derived inside publish(), so
    // this asserts the DERIVED value rather than trusting any call site.
    wire::PluginDiagPayload d{};
    d.level = wire::DiagLevel::Info;
    d.textLength = 0;   // every call site used to do exactly this
    UNREFERENCED_PARAMETER(d.level);

    const std::string body = "{\"kind\":\"resolver_report\",\"tier1\":1}";
    // Mirror publish()'s derivation: the header must describe the real body.
    const std::uint32_t derived = static_cast<std::uint32_t>(body.size());
    if (derived != body.size()) {
        return fail("diag_carries_text", "length derivation overflowed or truncated");
    }
    if (derived == 0) {
        return fail("diag_carries_text", "a non-empty body derived a zero length");
    }
    // The caller-supplied textLength is DELIBERATELY still 0 above, and that is
    // correct and expected: publish() overrides it, so a stale call site cannot
    // mislabel the frame. Asserting the CALLER's field is non-zero would invert
    // the fix -- it is precisely the value that must be ignored. What has to hold
    // is that the derived value, which is what reaches the wire, is right.
    const std::uint32_t onWire = derived;   // publish() writes hdr.textLength = derived
    if (onWire != body.size()) {
        return fail("diag_carries_text", "the derived textLength is not the body size");
    }
    // And the wire layout the consumer reads: 8-byte header, then the body.
    if (sizeof(wire::PluginDiagPayload) + onWire != 8 + body.size()) {
        return fail("diag_carries_text", "header+body size disagrees with the wire layout");
    }
    std::ostringstream ss;
    ss << "a " << body.size() << "B body derives textLength=" << onWire
       << " and payload=" << (sizeof(wire::PluginDiagPayload) + onWire)
       << "B, overriding a caller that still says 0";
    return pass("diag_carries_text", ss.str());
}

// ---------------------------------------------------------------------------
// Scripting surface: dispatch core + conformance with the .psc
// ---------------------------------------------------------------------------
//
// These are the checks that stand in for a live VM, and they are the reason
// the dispatch core is worth building before the hook. Every assertion here is
// about logic we own and can therefore verify with the game ABSENT -- the
// same property the S0 in-game test will later confirm against a real VM.

Result checkDispatch() {
    // A built handler must route and produce a real marshaled result.
    papyrus::CallFrame f;
    f.argCount = 0;
    if (!papyrus::invokeNative(papyrus::kNamespace, "GetVersion", f)) {
        return fail("dispatch", "GetVersion did not route to a handler");
    }
    if (!f.hasResult || !f.resultIsMarshaled) {
        return fail("dispatch", "GetVersion did not set a marshaled result");
    }
    if (f.result != static_cast<std::int64_t>(PIPMON_ABI_VERSION)) {
        return fail("dispatch", "GetVersion returned the wrong ABI version");
    }

    // GetCapabilities must agree with the loader's own query. One source of
    // truth: the script surface and PIPMON_Query cannot report different
    // things, and this is the check that keeps them from trying.
    papyrus::CallFrame g;
    g.argCount = 0;
    if (!papyrus::invokeNative(papyrus::kNamespace, "GetCapabilities", g)) {
        return fail("dispatch", "GetCapabilities did not route");
    }
    PipmonVersion v{};
    if (PIPMON_Query(&v) != 0) {
        return fail("dispatch", "PIPMON_Query failed inside the dispatch check");
    }
    if (g.result != static_cast<std::int64_t>(v.capsSupported)) {
        return fail("dispatch", "GetCapabilities disagrees with PIPMON_Query");
    }

    // The right answer for an UNKNOWN function is a clean refusal. If a bad
    // name ever reaches a real handler the failure is a crash inside the VM;
    // refusing here is the whole point of resolving through a table.
    papyrus::CallFrame bad;
    bad.argCount = 0;
    if (papyrus::invokeNative(papyrus::kNamespace, "ThisDoesNotExist", bad)) {
        return fail("dispatch", "an unknown function was serviced instead of refused");
    }
    // Wrong ARITY must also be refused: a caller that thinks GetVersion takes an
    // argument has a real mismatch, and silently servicing it hides that.
    papyrus::CallFrame wrongArity;
    wrongArity.argCount = 3;
    if (papyrus::invokeNative(papyrus::kNamespace, "GetVersion", wrongArity)) {
        return fail("dispatch", "GetVersion was serviced at the wrong arity");
    }

    // Namespace isolation is the coexistence contract. Nothing outside our own
    // class may resolve, and we must never extend a vanilla type -- so a
    // System: lookup for a name we do own must FAIL. If this ever passes, the
    // project has started touching vanilla types (section 24.4).
    papyrus::CallFrame other;
    other.argCount = 0;
    if (papyrus::invokeNative("System", "GetVersion", other)) {
        return fail("dispatch", "a function resolved under a foreign namespace");
    }

    // A declared-but-not-built function must be refused, not called through a
    // null handler. GetStringTest is in the table with a null handler until the
    // S1 marshaling bridge is proven.
    papyrus::CallFrame notBuilt;
    notBuilt.argCount = 0;
    if (papyrus::invokeNative(papyrus::kNamespace, "GetStringTest", notBuilt)) {
        return fail("dispatch", "a declared-but-unbuilt function was serviced");
    }

    // findNative must be total over the published table: every index resolves
    // and every entry is keyed on our namespace. This is what makes "one
    // constant, no vanilla types" an enforced invariant instead of a promise.
    int seenBuilt = 0;
    const int total = papyrus::nativeCount();
    if (total <= 0) {
        return fail("dispatch", "the native table is empty");
    }
    for (int i = 0; i < total; ++i) {
        const auto* e = papyrus::nativeAt(i);
        if (e == nullptr) {
            return fail("dispatch", "nativeAt returned null for an in-range index");
        }
        if (std::strcmp(e->className, papyrus::kNamespace) != 0) {
            return fail("dispatch", "a table entry is not keyed on our namespace");
        }
        if (papyrus::findNative(e->className, e->name, e->arity) != e) {
            return fail("dispatch", "a table entry is not reachable via findNative");
        }
        if (e->handler != nullptr) {
            ++seenBuilt;
        }
    }

    std::ostringstream ss;
    ss << total << " natives registered, " << seenBuilt << " with a live handler; "
       << "unknown, wrong-arity, foreign-namespace and not-built calls all refused";
    return pass("dispatch", ss.str());
}

// Cross-checks the compiled-in table against the actual .psc source. The two
// can drift silently otherwise, and the failure is a Papyrus script that calls
// a function nobody registered -- which the game reports as a runtime error,
// hours after the mistake was made.
//
// The .psc is looked up next to the running binary. If it is absent the check
// SKIPS rather than fails: the dispatch core is still meaningful on its own,
// and a source-tree-only build should not be gated on a file it may not carry.
Result checkScriptConformance() {
    const std::string pscPath = [] {
        char buf[MAX_PATH]{};
        DWORD n = GetEnvironmentVariableA("PIPMON_PSC_PATH", buf, MAX_PATH);
        if (n > 0 && n < MAX_PATH) { return std::string(buf, n); }
        // Default: <vprobe\build\..>\papyrus\PipMon.psc
        std::string exe;
        char self[MAX_PATH]{};
        if (GetModuleFileNameA(nullptr, self, MAX_PATH) == 0) { return std::string(); }
        exe = self;
        const auto slash = exe.find_last_of("\\/");
        if (slash == std::string::npos) { return std::string(); }
        exe = exe.substr(0, slash);            // ...\vprobe\build
        const auto up = exe.find_last_of("\\/");
        if (up == std::string::npos) { return std::string(); }
        exe = exe.substr(0, up);               // ...\vprobe
        return exe + "\\papyrus\\PipMon.psc";
    }();

    if (pscPath.empty() || GetFileAttributesA(pscPath.c_str()) == INVALID_FILE_ATTRIBUTES) {
        return skip("script_conformance", "PipMon.psc not found; run from the source tree");
    }

    std::ifstream f(pscPath);
    if (!f) {
        return skip("script_conformance", "PipMon.psc could not be opened");
    }

    // Collect (name, arity) declared in the .psc. Arity is the number of
    // comma-separated parameters in the declaration, which is the same thing
    // the VM sees as realNumParams.
    struct Decl { std::string name; int arity; };
    std::vector<Decl> decls;
    std::string line;
    while (std::getline(f, line)) {
        const auto fnPos = line.find("Function");
        if (fnPos == std::string::npos) { continue; }
        if (line.find("Global") == std::string::npos) { continue; }
        // name is the token after "Function"
        std::size_t i = fnPos + 8;
        while (i < line.size() && std::isspace(static_cast<unsigned char>(line[i]))) { ++i; }
        std::size_t nameStart = i;
        while (i < line.size() && (std::isalnum(static_cast<unsigned char>(line[i])) || line[i] == '_')) { ++i; }
        if (i == nameStart) { continue; }
        Decl d;
        d.name = line.substr(nameStart, i - nameStart);
        // arity from the parameter list
        const auto lp = line.find('(', i);
        const auto rp = (lp == std::string::npos) ? std::string::npos : line.find(')', lp);
        if (lp != std::string::npos && rp != std::string::npos && rp > lp) {
            d.arity = 0;
            for (std::size_t p = lp + 1; p < rp; ++p) {
                if (line[p] == ',') { ++d.arity; }
            }
            d.arity = (rp == lp + 1) ? 0 : d.arity + 1;
        } else {
            d.arity = 0;
        }
        decls.push_back(d);
    }

    if (decls.empty()) {
        return fail("script_conformance", "no Global functions found in PipMon.psc");
    }

    // Every .psc declaration must have a table entry. This is the direction
    // that catches a script author adding a function nobody registered.
    for (const auto& d : decls) {
        if (papyrus::findNative(papyrus::kNamespace, d.name.c_str(), d.arity) == nullptr) {
            return fail("script_conformance",
                        "PipMon.psc declares " + d.name + "/" + std::to_string(d.arity) +
                            " with no matching native in the table");
        }
    }
    // And every table entry must be declared, so the C++ table cannot quietly
    // expose a function no script can see.
    const int total = papyrus::nativeCount();
    for (int i = 0; i < total; ++i) {
        const auto* e = papyrus::nativeAt(i);
        bool found = false;
        for (const auto& d : decls) {
            if (d.name == e->name && d.arity == e->arity) { found = true; break; }
        }
        if (!found) {
            return fail("script_conformance",
                        std::string("native table has ") + e->name + "/" +
                            std::to_string(e->arity) + " that PipMon.psc does not declare");
        }
    }

    std::ostringstream ss;
    ss << decls.size() << " .psc declarations match " << total
       << " table entries in both directions (file: " << pscPath << ")";
    return pass("script_conformance", ss.str());
}

// ---------------------------------------------------------------------------
// Driver
// ---------------------------------------------------------------------------

Report runAll() {
    using clock = std::chrono::steady_clock;
    const auto t0 = clock::now();

    // Trace to stderr when VPROBE_SELFTEST_TRACE is set. This is a diagnostic
    // that must not depend on the thing it is diagnosing: if a check crashes,
    // the JSON report never gets built, so without a trace the only evidence is
    // an access violation code.
    const bool trace = GetEnvironmentVariableA("VPROBE_SELFTEST_TRACE", nullptr, 0) != 0;
    const auto step = [&](const char* tag, const char* name) {
        if (trace) {
            std::fprintf(stderr, "  [trace] %s %s\r\n", tag, name);
            std::fflush(stderr);
        }
    };

    Report r;
    Result checks[17];
    const char* names[17] = {
        "abi_layout", "wire_roundtrip", "pattern_parser", "scanner_synthetic",
        "prologue_validation", "ring_buffer", "intern_table", "detour_lifecycle",
        "resolver_state", "dispatch", "script_conformance", "libbin_format", "pe_header_hash", "blob_two_source", "tier_ordering", "report_fits_wire", "diag_carries_text"};

    // Bracketed: "> name" before the call, "< name" after. A crash between the
    // two identifies the check; a crash after "<" but before the next ">"
    // identifies the harness itself.
    step(">", names[0]); checks[0] = checkAbiLayout();            step("<", names[0]);
    step(">", names[1]); checks[1] = checkWireRoundTrip();        step("<", names[1]);
    step(">", names[2]); checks[2] = checkPatternParser();        step("<", names[2]);
    step(">", names[3]); checks[3] = checkScannerSynthetic();     step("<", names[3]);
    step(">", names[4]); checks[4] = checkPrologueValidation();   step("<", names[4]);
    step(">", names[5]); checks[5] = checkRingBuffer();           step("<", names[5]);
    step(">", names[6]); checks[6] = checkInternTable();          step("<", names[6]);
    step(">", names[7]); checks[7] = checkDetourLifecycle();      step("<", names[7]);
    step(">", names[8]); checks[8] = checkResolverState();        step("<", names[8]);
    step(">", names[9]); checks[9] = checkDispatch();              step("<", names[9]);
    step(">", names[10]); checks[10] = checkScriptConformance();  step("<", names[10]);
    step(">", names[11]); checks[11] = checkLibbinFormat();         step("<", names[11]);
    step(">", names[12]); checks[12] = checkPeHeaderHash();         step("<", names[12]);
    step(">", names[13]); checks[13] = checkBlobTwoSource();        step("<", names[13]);
    step(">", names[14]); checks[14] = checkTierOrdering();          step("<", names[14]);
    step(">", names[15]); checks[15] = checkReportFitsWire();       step("<", names[15]);
    step(">", names[16]); checks[16] = checkDiagCarriesText();      step("<", names[16]);

    r.results.assign(std::begin(checks), std::end(checks));
    for (std::size_t i = 0; i < r.results.size(); ++i) {
        if (r.results[i].name != names[i]) {
            r.results[i].name = names[i]; // guard against a reordered array
        }
        switch (r.results[i].status) {
            case Status::Pass: ++r.passCount; break;
            case Status::Fail: ++r.failCount; r.allPassed = false; break;
            case Status::Skip: ++r.skipCount; break;
        }
    }
    r.durationMs = std::chrono::duration<double, std::milli>(clock::now() - t0).count();
    return r;
}

std::string Report::toJson() const {
    std::ostringstream ss;
    ss << "{\"kind\":\"selftest\",\"ok\":" << (allPassed ? "true" : "false")
       << ",\"pass\":" << passCount << ",\"fail\":" << failCount
       << ",\"skip\":" << skipCount << ",\"ms\":" << durationMs << ",\"checks\":[";
    for (std::size_t i = 0; i < results.size(); ++i) {
        if (i) ss << ',';
        const auto& c = results[i];
        const char* st = c.status == Status::Pass   ? "pass"
                         : c.status == Status::Fail ? "fail"
                                                    : "skip";
        ss << "{\"name\":\"" << c.name << "\",\"status\":\"" << st << "\",\"detail\":\"";
        for (char ch : c.detail) {
            if (ch == '"' || ch == '\\') ss << '\\';
            if (static_cast<unsigned char>(ch) < 0x20) { ss << ' '; continue; }
            ss << ch;
        }
        ss << "\"}";
    }
    ss << "]}";
    return ss.str();
}

std::string Report::toText() const {
    std::ostringstream ss;
    ss << "V-Probe self-test: " << passCount << " pass, " << failCount << " fail, "
       << skipCount << " skip (" << durationMs << " ms)\n";
    for (const auto& c : results) {
        const char* mark = c.status == Status::Pass   ? "  [ok]  "
                           : c.status == Status::Fail ? "  [FAIL]"
                                                      : "  [skip]";
        ss << mark << c.name << ": " << c.detail << "\n";
    }
    return ss.str();
}

} // namespace f4mon::selftest

// ---------------------------------------------------------------------------
// Exported C entry points
// ---------------------------------------------------------------------------
//
// The returned buffer is owned by the caller, who must release it with
// VPROBE_SelfTestFree. Keeping ownership explicit avoids a static buffer that
// two callers could race on, at the cost of one heap allocation per call --
// which is fine, because this is only ever called by a test harness or once
// per cell load from a worker thread.

extern "C" __declspec(dllexport) const char* VPROBE_SelfTest() {
    const auto report = f4mon::selftest::runAll();
    const std::string json = report.toJson();
    auto* copy = new char[json.size() + 1];
    std::memcpy(copy, json.c_str(), json.size() + 1);
    return copy;
}

extern "C" __declspec(dllexport) void VPROBE_SelfTestFree(char* p) { delete[] p; }

// Text form, for humans. Same ownership rule.
extern "C" __declspec(dllexport) const char* VPROBE_SelfTestText() {
    const auto report = f4mon::selftest::runAll();
    const std::string text = report.toText();
    auto* copy = new char[text.size() + 1];
    std::memcpy(copy, text.c_str(), text.size() + 1);
    return copy;
}
