// VersionConfig.hpp
//
// Two-tier address resolution shared by every hook.
//
//   Tier 1  AddressLib INI  -> "<name> <rva hex>" lines in
//                              Fallout4/Data/F4SE/Plugins/fo4_runtime_probe/libs/
//                              fo4_runtime_probe.addresses.txt
//   Tier 2  AOB scan        -> a signature table here (see Signatures.hpp)
//
// A resolved address is only handed back if it survives `isPlausibleCodeAddress`, which for
// every Papyrus target means: inside an executable section of Fallout4.exe AND
// passing a prologue check. Anything else reports State::Rejected and
// the corresponding hook simply stays uninstalled. A monitor that disables one
// hook is a working monitor; a monitor that jumps into the wrong function is a
// crash on the next script call.
#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <unordered_map>
#include <vector>

#include "DynamicScanner.hpp"

namespace f4mon::vc {

// ---------------------------------------------------------------------------
// The .bin format contract, shared with the generator
// ---------------------------------------------------------------------------
//
// These three live at namespace scope, not as class members, because they are
// the CONTRACT between tools/build_libbin.py (which writes the blob) and this
// reader (which loads it). Burying them inside Resolver made them invisible to
// the self-test, and a test that cannot see the constant it is asserting is a
// test that quietly stops testing.
//
// Both sides moving together is the whole risk here, so the values are named in
// exactly one place per language and pinned by test vectors in SelfTest.cpp.

// 24 bytes: magic(4) schema(4) buildKey(4) count(4) recSize(4) reserved(4)
inline constexpr std::size_t kLibbinHeaderSize = 24;
// 12 bytes: nameHash(4) rva(4) classId(1) slot(1) flags(2)
inline constexpr std::size_t kLibbinRecordSize = 12;
inline constexpr char        kLibbinMagic[5]    = "PLIB";

// Layout version. Bumped whenever a record field or a header field's meaning
// changes. The reader REFUSES an unrecognised version rather than best-effort
// parsing it -- the whole reason this field exists is that a same-size layout
// change is otherwise read silently and yields plausible, wrong addresses.
inline constexpr std::uint32_t kLibbinSchemaVersion = 1;

// FNV-1a 32-bit, matching the generator and the launcher's existing vectors.
// A lookup that hashed differently across the language boundary would return
// nothing for every symbol, and every probe would fall through to the AOB tier
// with no error anywhere -- which is why this is tested rather than trusted.
[[nodiscard]] std::uint32_t fnv1a32(const std::string& s) noexcept;

// FNV-1a 32 over the PE header region of a loaded image, matching
// pe_header_hash() in tools/build_libbin.py.
//
// This is how a blob is tied to the exact binary it was generated for. It is
// deliberately a header hash rather than Bethesda's build-key STRING: the
// in-process tier does not parse PE structures (by design -- see the detour and
// scanner code, which reads raw bytes for a reason), and the header bytes are
// mapped 1:1 from file to image so both sides compute the same value without
// either one owning a parser. The hash stops at the end of the optional header
// because that region contains the ASLR-dependent image base.
[[nodiscard]] std::uint32_t peHeaderHash(const std::uint8_t* imageBase) noexcept;

enum class State {
    Pending,
    FromAddressLib,  // Tier 1 hit
    FromScan,        // Tier 2 hit
    Rejected,        // resolved but failed validation -- hook disabled
    NotFound,        // no INI entry and no AOB match
};

// What a resolved address actually IS. This is not decoration: the two kinds
// live in different sections of the image and are validated by completely
// different rules.
//
//   Code    -- a function entry in .text. Validated by requiring an
//              executable section plus a plausible prologue.
//   VTable  -- a method table in .rdata. Validated by requiring that a
//              MAJORITY of its consecutive slots point into executable code.
//
// Getting this wrong is not a small error. isPlausibleCodeAddress requires an
// executable section, so pointing it at a vtable rejects 100% of vtables --
// and a 100% rejection rate reads as "the database is bad" rather than "the
// validator assumes the wrong thing". The first draft of the vtable check
// made the mirror-image mistake, demanding that ALL slots point into code,
// which rejects genuine tables that contain import thunks.
enum class TargetKind {
    Code,
    VTable,
};

// One entry in the signature table.
struct Signature {
    std::string name;               // must match the AddressLib key exactly
    std::string pattern;            // "48 8B ?? 5B C3"
    std::uint32_t functionOffset = 0;  // if the pattern is a body fragment, not the entry
    std::string semanticProbe;      // optional extra validation note (see .cpp)
    // How many consecutive pointers to inspect when validating a vtable.
    // A table of one (which is what a single-ID database entry looks like)
    // is not a vtable at all -- it is a single global pointer -- so these
    // targets sample generously and accept a majority.
    std::size_t vtableSlots = 8;
    TargetKind kind = TargetKind::Code;
};

class Resolver {
public:
    Resolver();
    ~Resolver();

    Resolver(const Resolver&) = delete;
    Resolver& operator=(const Resolver&) = delete;

    // Load the AddressLib INI. Safe to call before the game module is present;
    // entries are cached and applied on first resolve.
    bool loadAddressLib(const std::wstring& iniPath);
    // `imageBase` is the base of the image the blob must match, or nullptr to
    // use the loaded game module (and, if there is none, to accept the blob
    // unvalidated for offline use).
    //
    // It is a parameter rather than an internal lookup on purpose. The refusal
    // path -- a blob built for a different patch -- is the safety-critical
    // branch, and while it could only be reached with a live game module, it
    // could not be TESTED without one. A safety property that can only be
    // exercised in a full game is a safety property that is never exercised.
    // Production passes the real module; the self-test passes a synthetic image
    // and asserts the refusal directly.
    bool loadAddressLibBin(const std::wstring& binPath,
                           const std::uint8_t* imageBase = nullptr);
    // --- diagnostics: the two sources, read-only ---------------------------
    //
    // These return plain values rather than exposing BinEntry, so the record
    // layout stays private while the self-test can still drive both sources.
    // They are the observable surface of the fallback contract: 0 means "not
    // found in this source", which is a legitimate answer and not an error.
    //
    // Both are needed because the safety net and the fast path fail DIFFERENTLY,
    // and a test that could only see one of them would miss exactly the case
    // that matters: a blob present and refused, with text still answering.
    [[nodiscard]] std::uint32_t rvaFromBin(const std::string& name) const noexcept {
        const auto* e = lookupBin(name);
        return (e == nullptr) ? 0u : e->rva;
    }
    [[nodiscard]] std::uint32_t rvaFromText(const std::string& name) const noexcept {
        const auto it = rvaByName_.find(name);
        return (it == rvaByName_.end()) ? 0u : it->second;
    }
    [[nodiscard]] bool blobLoaded() const noexcept { return binLoaded_; }
    [[nodiscard]] std::uint32_t blobImageHash() const noexcept { return binBuildKey_; }

    // --- test seams --------------------------------------------------------
    //
    // The tier ORDERING -- blob, then text, then AOB -- is the resolver's
    // central contract, and until now it could only run against a live game.
    // That is the same problem as the blob refusal: a rule that can only be
    // observed in the one environment that is hardest to debug is a rule that
    // gets debugged by inference instead of by test.
    //
    // ModuleRange is a plain struct with public fields precisely so a synthetic
    // image can be described without a PE parser, and these two setters let the
    // self-test install one. They are test-only in the sense that production
    // never calls them; they are NOT debug hooks and expose no game state.
    [[nodiscard]] bool hasSignatureForTest(const std::string& n) const {
        return slots_.find(n) != slots_.end();
    }
    // moduleProbed_ MUST be set alongside the module. resolve() lazily calls
    // describeModule("Fallout4.exe") on first use and overwrites gameModule_
    // wholesale, so a seam that installed a module without marking it probed
    // got silently replaced with a failed lookup -- and Tier 1, which requires
    // a module, was then skipped for no visible reason. The symptom was
    // resolve() returning null with a correct database loaded.
    void setModuleForTest(const scan::ModuleRange& mod) noexcept {
        gameModule_  = mod;
        moduleProbed_ = true;
    }
    void addSignatureForTest(const Signature& sig) {
        Slot slot;
        slot.sig   = sig;
        slot.state = State::Pending;
        order_.push_back(sig.name);
        slots_[sig.name] = std::move(slot);
    }
    // stateOf() is not const-qualified (it lazily probes the module), so the
    // test accessor drops const rather than widening the real API's signature
    // for the sake of a test. Const-correctness of production code is not worth
    // weakening to make a test compile.
    [[nodiscard]] State stateOfForTest(const std::string& n) { return stateOf(n); }
    [[nodiscard]] std::string noteOfForTest(const std::string& n) const {
        const auto it = slots_.find(n);
        return (it == slots_.end()) ? std::string() : it->second.note;
    }

    bool loadEmbeddedDump();   // compiled-in JSON, used when the INI is absent

    [[nodiscard]] State stateOf(const std::string& name);

    // Resolve a single slot of a vtable target.
    //
    // This is the bridge between the two tiers, and the reason a vtable
    // database is worth more than a function list: ONE validated vtable
    // address yields N real function addresses, all of which are in .text by
    // construction because the table is a list of code pointers. So a single
    // Tier-1 entry opens an entire interface, where Tier 3 needed a separate
    // byte pattern per function -- and five of six of those did not match the
    // real binary at all.
    //
    // `slot` is validated the same way a code address is: the pointer must land
    // in an executable section. A vtable that is mostly code but has a bad slot
    // yields a null for that slot and a valid address for the rest, which is
    // the correct outcome -- one bad method must not cost us the interface.
    [[nodiscard]] std::uint8_t* resolveVTableSlot(const std::string& name, std::size_t slot);
    [[nodiscard]] std::uint8_t* resolve(const std::string& name);
    [[nodiscard]] std::string explain(const std::string& name) const;

    // The signature entry for a name, or a Code-kind default if the name is
    // unknown. Returning a default rather than a reference to a temporary
    // matters: a caller that just wants "how should this be validated" must
    // not have to know whether the name is in the table.
    [[nodiscard]] Signature sigOf(const std::string& name) const;

    [[nodiscard]] std::vector<std::string> allNames() const;

    // Aggregate report, emitted as a PluginDiag on connect. The dashboard shows
    // this so a user on a brand-new build immediately sees which probes are live.
    [[nodiscard]] std::string buildReportJson();

    [[nodiscard]] const scan::ModuleRange* gameModule() const { return gameModule_ ? &*gameModule_ : nullptr; }

private:
    [[nodiscard]] std::uint8_t* validateCandidate(const Signature& sig, State& outState,
                                                  std::uint32_t& outRva) const;

    struct Slot {
        Signature sig;
        State     state = State::Pending;
        std::uint8_t* address = nullptr;
        std::uint32_t rva = 0;
        std::size_t   matchCount = 0;
        std::string   note;
    };

    // The binary address database: a fixed-stride table sorted by name hash,
    // binary-searched, loaded with a single read and zero per-entry allocation.
    // This is the preferred Tier-1 source at runtime; rvaByName_ above is the
    // TEXT form and is the fallback when the blob is missing or malformed.
    //
    // Both are kept deliberately rather than normalised into one. The text map
    // is authoritative and human-readable; the blob is a derived fast path. If
    // they ever disagree, the text form is the truth and the blob is stale --
    // so the lookup consults the blob first ONLY when it loaded cleanly, and
    // the text map is never discarded.
    struct BinEntry {
        std::uint32_t nameHash = 0;
        std::uint32_t rva      = 0;
        std::uint8_t  classId  = 0;
        std::uint8_t  slot     = 0xFF;
        bool          exact    = false;   // false => hash collision; treat as miss
    };
    std::vector<BinEntry>            rvaByNameBin_;
    std::uint32_t                    binBuildKey_ = 0;
    bool                             binLoaded_   = false;

    // Binary search over rvaByNameBin_. Returns nullptr on a miss, and also on
    // a non-exact (collision-flagged) hit -- a 1-in-2^32 false positive that
    // lands in the wrong function is exactly the bug class this project has
    // already been bitten by, so an ambiguous entry is reported as absent.
    [[nodiscard]] const BinEntry* lookupBin(const std::string& name) const noexcept;

    // Text-map RVA for a name, or 0 when absent. Exists so the self-test can
    // verify the text FALLBACK path in isolation from the game module -- the
    // fallback is the safety net for the blob, and a safety net that is never
    // exercised is not one.
    [[nodiscard]] std::uint32_t rvaOfForTest(const std::string& name) const noexcept {
        const auto it = rvaByName_.find(name);
        return (it == rvaByName_.end()) ? 0u : it->second;
    }

    std::unordered_map<std::string, Slot> slots_;
    std::unordered_map<std::string, std::uint32_t> rvaByName_;
    std::vector<std::string> order_;

    std::optional<scan::ModuleRange> gameModule_;
    bool  moduleProbed_ = false;
    int   tier1Hits_ = 0;
    int   tier2Hits_ = 0;
    int   rejected_  = 0;
    int   missing_   = 0;
};

} // namespace f4mon::vc
