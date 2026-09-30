cmake_minimum_required(VERSION 3.24)

# ---------------------------------------------------------------------------
# pipmon_preflight -- Component 0 of PIP-MON.
#
# The launcher-side integrity core. Runs while the target process is still
# suspended, so the build can be identified, config validated and the runtime
# self-tested BEFORE a single hook is installed and before the game executes
# its first instruction.
#
# Design intent, stated because it is the whole point of this component:
#   Fallout 4 is a 90 MB binary whose internals shift with every patch, and a
#   signature resolved against the wrong build lands in the wrong function.
#   Discovering that after resume costs the player a crash. Discovering it
#   here costs them a sentence. This component is what converts the first
#   failure mode into the second.
#
# It replaces the maintenance model of F4SE's `f4se_1_10_xxx.dll`, where every
# game patch required a matching build of the core DLL. Here there is ONE
# binary for every build plus a build->profile table, and an unknown build is
# refused rather than guessed at.
# ---------------------------------------------------------------------------

project(pipmon_preflight VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT WIN32 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
  message(FATAL_ERROR "pipmon_preflight targets Windows x64 only.")
endif()

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

add_executable(pipmon_preflight
  src/main.cpp
  src/BuildIdentity.cpp
  src/ProcessLaunch.cpp
  src/SelfTest.cpp
)

# ---------------------------------------------------------------------------
# Test fixtures for the load path.
#
# These are NOT mocks. pf_helper_target is a real Win32 process that really is
# created suspended, really is injected into, and really is resumed;
# pf_helper_dll really is loaded by the ordinary loader and really signals a
# handshake from DllMain. The silent variant loads and never signals, which is
# the only way to prove the handshake timeout actually catches a runtime that
# failed to come up -- a case that a working-only test suite never exercises.
# ---------------------------------------------------------------------------

add_executable(pf_helper_target tests/test_helper_target.cpp)
target_link_libraries(pf_helper_target PRIVATE User32)
set_target_properties(pf_helper_target PROPERTIES
  OUTPUT_NAME              "pf_helper_target"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/$<CONFIG>")

# The three states a launcher must tell apart, from ONE source file, so the
# variants cannot diverge in anything but the macro that defines them.
#
#   pf_helper_dll           signals loaded AND ready   -> launcher: Ok
#   pf_helper_dll_noready   signals loaded only        -> launcher: Degraded
#   pf_helper_dll_noloaded  signals nothing            -> launcher: timeout
#
# The last two earn their keep. A launcher that cannot distinguish them from
# success is indistinguishable from one that works, right up until a runtime
# fails to initialise on a user's machine.
#
# These include vprobe's ReadySignal.hpp rather than repeating the event names,
# so the test can never pass against a contract the real runtime does not use.
set(PIPMON_HELPER_INCLUDES
  "${CMAKE_CURRENT_SOURCE_DIR}/include"
  "${CMAKE_CURRENT_SOURCE_DIR}/../vprobe/include")

set(PIPMON_DLL_VARIANTS pf_helper_dll pf_helper_dll_noready pf_helper_dll_noloaded)

foreach(t ${PIPMON_DLL_VARIANTS})
  add_library(${t} SHARED tests/test_helper_dll.cpp)
  target_include_directories(${t} PRIVATE ${PIPMON_HELPER_INCLUDES})
  set_target_properties(${t} PROPERTIES
    OUTPUT_NAME              "${t}"
    PREFIX                   ""
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/$<CONFIG>")
endforeach()

target_compile_definitions(pf_helper_dll_noready  PRIVATE PIPMON_DLL_NO_READY=1)
target_compile_definitions(pf_helper_dll_noloaded PRIVATE PIPMON_DLL_NO_LOADED=1)

foreach(t pf_helper_target ${PIPMON_DLL_VARIANTS})
  if(MSVC)
    target_compile_options(${t} PRIVATE /W4 /permissive- /Zc:__cplusplus /utf-8 /EHsc)
    target_compile_definitions(${t} PRIVATE
      _CRT_SECURE_NO_WARNINGS NOMINMAX WIN32_LEAN_AND_MEAN UNICODE _UNICODE)
  endif()
endforeach()

# There is exactly one entry point (wmain in main.cpp). It dispatches
# --self-test, so the validation suite runs with no game, no config and no
# network.

target_include_directories(pipmon_preflight
  PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include")

# BCrypt supplies SHA-256 for the tamper check, so we do not hand-roll a
# crypto primitive on a code path whose job is to detect a modified binary.
target_link_libraries(pipmon_preflight PRIVATE
  Bcrypt
  Psapi
)

if(MSVC)
  target_compile_options(pipmon_preflight PRIVATE
    /W4 /permissive- /Zc:__cplusplus /MP /utf-8 /EHsc)
  target_compile_definitions(pipmon_preflight PRIVATE
    _CRT_SECURE_NO_WARNINGS NOMINMAX WIN32_LEAN_AND_MEAN UNICODE _UNICODE)
else()
  target_compile_options(pipmon_preflight PRIVATE
    -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-minitializers)
endif()

set_target_properties(pipmon_preflight PROPERTIES
  OUTPUT_NAME              "pipmon_preflight"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/$<CONFIG>"
)

message(STATUS "pipmon_preflight ${PROJECT_VERSION}")
message(STATUS "  build type : ${CMAKE_BUILD_TYPE}")
message(STATUS "  self-test  : pipmon_preflight --self-test")
