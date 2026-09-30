// InternTable.hpp
//
// Small fixed-capacity string interner. The probe frequently needs to say
// "script SkyFC09.esp Script_abc123" and the wire format wants an integer.
// Building that string on a hooked game thread is exactly what we must not do,
// so the interned text is captured once (on the worker, or guarded by the
// caller being off the game thread) and afterwards travels as a uint32.
#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace f4mon::telemetry {

inline constexpr std::uint32_t kUninternedId = 0xFFFFFFFFu;
inline constexpr std::size_t   kMaxInternedStrings = 4096;

class InternTable {
public:
    // Not thread-safe by itself; the bridge wraps it in a mutex on the worker
    // path and pre-warms it on the game path during init.
    [[nodiscard]] std::uint32_t intern(std::string_view text) {
        if (text.empty()) {
            return kUninternedId;
        }
        for (std::uint32_t i = 0; i < entries_.size(); ++i) {
            if (entries_[i] == text) {
                return i;
            }
        }
        if (entries_.size() >= kMaxInternedStrings) {
            return kUninternedId;
        }
        entries_.emplace_back(text);
        names_.push_back(std::string(text));
        return static_cast<std::uint32_t>(entries_.size() - 1);
    }

    [[nodiscard]] std::string_view resolve(std::uint32_t id) const noexcept {
        if (id == kUninternedId || id >= names_.size()) {
            return {};
        }
        return names_[id];
    }

    [[nodiscard]] std::size_t size() const noexcept { return names_.size(); }

    // Snapshot for the consumer: the dashboard needs a name table to render
    // script labels. Emitted as a PluginDiag batch on connect.
    [[nodiscard]] std::string dumpJson() const {
        std::string out = "{\"names\":[";
        for (std::size_t i = 0; i < names_.size(); ++i) {
            if (i) { out += ','; }
            out += '"';
            for (char c : names_[i]) {
                if (c == '"' || c == '\\') { out += '\\'; }
                if (static_cast<unsigned char>(c) < 0x20) { continue; }
                out += c;
            }
            out += '"';
        }
        out += "]}";
        return out;
    }

private:
    std::vector<std::string_view> entries_;
    std::vector<std::string> names_;
};

} // namespace f4mon::telemetry
