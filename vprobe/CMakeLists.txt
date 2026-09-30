cmake_minimum_required(VERSION 3.24)

# ---------------------------------------------------------------------------
# vprobe -- Component 1 of PIP-MON.
#
# In-process F4SE plugin (vprobe.dll) that probes the Papyrus VM and streams
# raw telemetry over V-Link to the external OverseerCLI dashboard.
#
# This target builds to an ASLR-clean x64 DLL with a relocation INI, which is
# what Address Library requires. It is the ONLY artefact that goes into
# Fallout4/Data/F4SE/Plugins/.
# ---------------------------------------------------------------------------

project(vprobe VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT WIN32 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
  message(FATAL_ERROR "vprobe targets Windows x64 only.")
endif()

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

# AddressLib derives RVAs relative to a fixed image base, so ASLR must be off.
option(VPROBE_ASLR "Leave the DLL ASLR-compatible" OFF)

set(VPROBE_STAGE_DIR "${CMAKE_SOURCE_DIR}/../stage"
    CACHE PATH "Deploy staging root (game Data dir)")

# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

set(VPROBE_SOURCES
  src/main.cpp
  src/IPCServer.cpp
  src/DynamicScanner.cpp
  src/VersionConfig.cpp
  src/Detour.cpp
  src/PapyrusHooks.cpp
  src/ReadySignal.cpp
  # Self-test (VPROBE_SelfTest*) and the two entry-point/ABI files. These were
  # missing from this list while the .bat build compiled them, so a CMake
  # configure would silently produce a vprobe.dll with no exported self-test
  # and no PIP-MON entry points -- a green build of the wrong thing. Keep this
  # list in step with build_vprobe.bat.
  src/SelfTest.cpp
  src/PipmonEntry.cpp
  src/PapyrusApi.cpp
)

add_library(vprobe SHARED ${VPROBE_SOURCES})

target_include_directories(vprobe
  PUBLIC  "${CMAKE_CURRENT_SOURCE_DIR}/include"
  PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src"
)

# --- Address Library / CommonLibF4 tiers -----------------------------------

option(VPROBE_FETCH_DEPS "Fetch CommonLibF4 / AddressLib if not pre-located" ON)
set(CLIB_F4_INCLUDE_DIR "" CACHE PATH "CommonLibF4 include root")
set(ADDRESSLIB_INCLUDE_DIR "" CACHE PATH "AddressLib include root")
set(VPROBE_ADDRESS_DUMP "" CACHE FILEPATH "Embedded AddressLib JSON dump")

if(VPROBE_FETCH_DEPS AND NOT CLIB_F4_INCLUDE_DIR)
  include(FetchContent)
  set(BUILD_LIBPAPYRUS OFF CACHE BOOL "" FORCE)
  set(BUILD_LIBUI OFF CACHE BOOL "" FORCE)
  FetchContent_Declare(CommonLibF4
    GIT_REPOSITORY https://github.com/Nukem9/CommonLibF4.git
    GIT_TAG        main
    GIT_SHALLOW    TRUE)
  FetchContent_MakeAvailable(CommonLibF4)
  FetchContent_Declare(AddressLib
    GIT_REPOSITORY https://github.com/Nukem9/AddressLib.git
    GIT_TAG        master
    GIT_SHALLOW    TRUE)
  FetchContent_MakeAvailable(AddressLib)
endif()

if(CLIB_F4_INCLUDE_DIR)
  target_include_directories(vprobe SYSTEM PRIVATE
    "${CLIB_F4_INCLUDE_DIR}"
    "${CLIB_F4_INCLUDE_DIR}/../CommonLib/src"
    "${CLIB_F4_INCLUDE_DIR}/../CommonLibF4/src")
endif()
if(ADDRESSLIB_INCLUDE_DIR)
  target_include_directories(vprobe SYSTEM PRIVATE "${ADDRESSLIB_INCLUDE_DIR}")
endif()

# --- Embedded address dump (Tier 1 when no INI is present) ------------------

if(VPROBE_ADDRESS_DUMP)
  target_sources(vprobe PRIVATE "${VPROBE_ADDRESS_DUMP}")
  target_compile_definitions(vprobe PRIVATE VPROBE_EMBEDDED_ADDRESS_DUMP=1)
  message(STATUS "vprobe: embedding AddressLib dump ${VPROBE_ADDRESS_DUMP}")
else()
  target_compile_definitions(vprobe PRIVATE VPROBE_EMBEDDED_ADDRESS_DUMP=0)
endif()

# --- Windows libs -----------------------------------------------------------

target_link_libraries(vprobe PRIVATE
  Psapi
  TlHelp32
)

# --- Warning / optimisation profile ----------------------------------------

if(MSVC)
  target_compile_options(vprobe PRIVATE /W4 /permissive- /Zc:__cplusplus /MP /utf-8 /EHsc)
  target_compile_definitions(vprobe PRIVATE
    _CRT_SECURE_NO_WARNINGS NOMINMAX WIN32_LEAN_AND_MEAN UNICODE _UNICODE)
else()
  target_compile_options(vprobe PRIVATE
    -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-initializers)
endif()

set_target_properties(vprobe PROPERTIES
  OUTPUT_NAME              "vprobe"
  PREFIX                   ""
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/$<CONFIG>"
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/$<CONFIG>"
)

if(NOT VPROBE_ASLR)
  # /DYNAMICBASE:NO in both compile and link so the image base is fixed at
  # 0x180000000, matching what AddressLib INIs were generated against.
  if(MSVC)
    target_link_options(vprobe PRIVATE /DYNAMICBASE:NO)
    target_compile_options(vprobe PRIVATE /DYNAMICBASE:NO)
  endif()
  target_compile_definitions(vprobe PRIVATE VPROBE_ASLR_DISABLED=1)
endif()

# --- Deploy stage -----------------------------------------------------------

install(TARGETS vprobe RUNTIME DESTINATION ".")

message(STATUS "vprobe ${PROJECT_VERSION}")
message(STATUS "  build type : ${CMAKE_BUILD_TYPE}")
message(STATUS "  aslr       : ${VPROBE_ASLR}")
message(STATUS "  pipe       : \\\\.\\pipe\\vlink_telemetry")
message(STATUS "  stage dir  : ${VPROBE_STAGE_DIR}")
