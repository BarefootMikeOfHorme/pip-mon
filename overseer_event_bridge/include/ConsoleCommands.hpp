// ConsoleCommands.hpp
#pragma once

namespace f4mon::bridge {
class Bridge;
}

namespace f4mon::bridge::console {

// Registers every PIP-MON command against the game console. Safe to call from
// the .esp's OnLoad script block, which already runs on the main thread.
void registerAll(Bridge& bridge);

// Removes every registration. Called from OnUnload; without this, reloading a
// save in a cell that still has the plugin loaded leaves duplicate commands,
// and the second registration silently wins -- which is a genuinely confusing
// bug to chase.
void unregisterAll(Bridge& bridge);

} // namespace f4mon::bridge::console
