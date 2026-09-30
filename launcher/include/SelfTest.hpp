// SelfTest.hpp -- pre-flight integrity core validation.
#pragma once

namespace f4mon::preflight {

// Runs every pre-flight check that does not require a game to be present.
// Returns 0 on success. The launcher calls this BEFORE resuming the target
// process, so a non-zero result is a clean abort rather than a crash later.
int runSelfTest();

} // namespace f4mon::preflight
