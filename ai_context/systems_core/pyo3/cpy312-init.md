---
source_url: https://docs.python.org/3.12/c-api/init.html
title: Initialization, Finalization, and Threads — Python 3.12.14 documentation
retrieved_utc: 2026-09-30T22:16:41Z
content_kind: upstream-documentation-verbatim
trust: >
  Official upstream documentation, quoted verbatim. NOT paraphrased. PyO3 is
  NOT installed in this project; this is reference for a planned bridge, not
  documentation of existing code.
---

# Initialization, Finalization, and Threads

See also [Python Initialization Configuration](init_config.html#init-config).

## Before Python Initialization

In an application embedding Python, the [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize") function must
be called before using any other Python/C API functions; with the exception of
a few functions and the [global configuration variables](#global-conf-vars).

The following functions can be safely called before Python is initialized:

- Configuration functions:

  - [`PyImport_AppendInittab()`](import.html#c.PyImport_AppendInittab "PyImport_AppendInittab")
  - [`PyImport_ExtendInittab()`](import.html#c.PyImport_ExtendInittab "PyImport_ExtendInittab")
  - `PyInitFrozenExtensions()`
  - [`PyMem_SetAllocator()`](memory.html#c.PyMem_SetAllocator "PyMem_SetAllocator")
  - [`PyMem_SetupDebugHooks()`](memory.html#c.PyMem_SetupDebugHooks "PyMem_SetupDebugHooks")
  - [`PyObject_SetArenaAllocator()`](memory.html#c.PyObject_SetArenaAllocator "PyObject_SetArenaAllocator")
  - [`Py_SetPath()`](#c.Py_SetPath "Py_SetPath")
  - [`Py_SetProgramName()`](#c.Py_SetProgramName "Py_SetProgramName")
  - [`Py_SetPythonHome()`](#c.Py_SetPythonHome "Py_SetPythonHome")
  - [`Py_SetStandardStreamEncoding()`](#c.Py_SetStandardStreamEncoding "Py_SetStandardStreamEncoding")
  - [`PySys_AddWarnOption()`](sys.html#c.PySys_AddWarnOption "PySys_AddWarnOption")
  - [`PySys_AddXOption()`](sys.html#c.PySys_AddXOption "PySys_AddXOption")
  - [`PySys_ResetWarnOptions()`](sys.html#c.PySys_ResetWarnOptions "PySys_ResetWarnOptions")
- Informative functions:

  - [`Py_IsInitialized()`](#c.Py_IsInitialized "Py_IsInitialized")
  - [`PyMem_GetAllocator()`](memory.html#c.PyMem_GetAllocator "PyMem_GetAllocator")
  - [`PyObject_GetArenaAllocator()`](memory.html#c.PyObject_GetArenaAllocator "PyObject_GetArenaAllocator")
  - [`Py_GetBuildInfo()`](#c.Py_GetBuildInfo "Py_GetBuildInfo")
  - [`Py_GetCompiler()`](#c.Py_GetCompiler "Py_GetCompiler")
  - [`Py_GetCopyright()`](#c.Py_GetCopyright "Py_GetCopyright")
  - [`Py_GetPlatform()`](#c.Py_GetPlatform "Py_GetPlatform")
  - [`Py_GetVersion()`](#c.Py_GetVersion "Py_GetVersion")
- Utilities:

  - [`Py_DecodeLocale()`](sys.html#c.Py_DecodeLocale "Py_DecodeLocale")
- Memory allocators:

  - [`PyMem_RawMalloc()`](memory.html#c.PyMem_RawMalloc "PyMem_RawMalloc")
  - [`PyMem_RawRealloc()`](memory.html#c.PyMem_RawRealloc "PyMem_RawRealloc")
  - [`PyMem_RawCalloc()`](memory.html#c.PyMem_RawCalloc "PyMem_RawCalloc")
  - [`PyMem_RawFree()`](memory.html#c.PyMem_RawFree "PyMem_RawFree")

Note

The following functions **should not be called** before
[`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"): [`Py_EncodeLocale()`](sys.html#c.Py_EncodeLocale "Py_EncodeLocale"), [`Py_GetPath()`](#c.Py_GetPath "Py_GetPath"),
[`Py_GetPrefix()`](#c.Py_GetPrefix "Py_GetPrefix"), [`Py_GetExecPrefix()`](#c.Py_GetExecPrefix "Py_GetExecPrefix"),
[`Py_GetProgramFullPath()`](#c.Py_GetProgramFullPath "Py_GetProgramFullPath"), [`Py_GetPythonHome()`](#c.Py_GetPythonHome "Py_GetPythonHome"),
[`Py_GetProgramName()`](#c.Py_GetProgramName "Py_GetProgramName") and [`PyEval_InitThreads()`](#c.PyEval_InitThreads "PyEval_InitThreads").

## Global configuration variables

Python has variables for the global configuration to control different features
and options. By default, these flags are controlled by [command line
options](../using/cmdline.html#using-on-interface-options).

When a flag is set by an option, the value of the flag is the number of times
that the option was set. For example, `-b` sets [`Py_BytesWarningFlag`](#c.Py_BytesWarningFlag "Py_BytesWarningFlag")
to 1 and `-bb` sets [`Py_BytesWarningFlag`](#c.Py_BytesWarningFlag "Py_BytesWarningFlag") to 2.

int Py\_BytesWarningFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.bytes_warning`](init_config.html#c.PyConfig.bytes_warning "PyConfig.bytes_warning") should be used instead, see [Python
    Initialization Configuration](init_config.html#init-config).

    Issue a warning when comparing [`bytes`](../library/stdtypes.html#bytes "bytes") or [`bytearray`](../library/stdtypes.html#bytearray "bytearray") with
    [`str`](../library/stdtypes.html#str "str") or [`bytes`](../library/stdtypes.html#bytes "bytes") with [`int`](../library/functions.html#int "int"). Issue an error if greater
    or equal to `2`.

    Set by the [`-b`](../using/cmdline.html#cmdoption-b) option.

    Deprecated since version 3.12.

int Py\_DebugFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.parser_debug`](init_config.html#c.PyConfig.parser_debug "PyConfig.parser_debug") should be used instead, see [Python
    Initialization Configuration](init_config.html#init-config).

    Turn on parser debugging output (for expert only, depending on compilation
    options).

    Set by the [`-d`](../using/cmdline.html#cmdoption-d) option and the [`PYTHONDEBUG`](../using/cmdline.html#envvar-PYTHONDEBUG) environment
    variable.

    Deprecated since version 3.12.

int Py\_DontWriteBytecodeFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.write_bytecode`](init_config.html#c.PyConfig.write_bytecode "PyConfig.write_bytecode") should be used instead, see [Python
    Initialization Configuration](init_config.html#init-config).

    If set to non-zero, Python won’t try to write `.pyc` files on the
    import of source modules.

    Set by the [`-B`](../using/cmdline.html#cmdoption-B) option and the [`PYTHONDONTWRITEBYTECODE`](../using/cmdline.html#envvar-PYTHONDONTWRITEBYTECODE)
    environment variable.

    Deprecated since version 3.12.

int Py\_FrozenFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.pathconfig_warnings`](init_config.html#c.PyConfig.pathconfig_warnings "PyConfig.pathconfig_warnings") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    Suppress error messages when calculating the module search path in
    [`Py_GetPath()`](#c.Py_GetPath "Py_GetPath").

    Private flag used by `_freeze_module` and `frozenmain` programs.

    Deprecated since version 3.12.

int Py\_HashRandomizationFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.hash_seed`](init_config.html#c.PyConfig.hash_seed "PyConfig.hash_seed") and [`PyConfig.use_hash_seed`](init_config.html#c.PyConfig.use_hash_seed "PyConfig.use_hash_seed") should
    be used instead, see [Python Initialization Configuration](init_config.html#init-config).

    Set to `1` if the [`PYTHONHASHSEED`](../using/cmdline.html#envvar-PYTHONHASHSEED) environment variable is set to
    a non-empty string.

    If the flag is non-zero, read the [`PYTHONHASHSEED`](../using/cmdline.html#envvar-PYTHONHASHSEED) environment
    variable to initialize the secret hash seed.

    Deprecated since version 3.12.

int Py\_IgnoreEnvironmentFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.use_environment`](init_config.html#c.PyConfig.use_environment "PyConfig.use_environment") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    Ignore all `PYTHON*` environment variables, e.g.
    [`PYTHONPATH`](../using/cmdline.html#envvar-PYTHONPATH) and [`PYTHONHOME`](../using/cmdline.html#envvar-PYTHONHOME), that might be set.

    Set by the [`-E`](../using/cmdline.html#cmdoption-E) and [`-I`](../using/cmdline.html#cmdoption-I) options.

    Deprecated since version 3.12.

int Py\_InspectFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.inspect`](init_config.html#c.PyConfig.inspect "PyConfig.inspect") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    When a script is passed as first argument or the [`-c`](../using/cmdline.html#cmdoption-c) option is used,
    enter interactive mode after executing the script or the command, even when
    [`sys.stdin`](../library/sys.html#sys.stdin "sys.stdin") does not appear to be a terminal.

    Set by the [`-i`](../using/cmdline.html#cmdoption-i) option and the [`PYTHONINSPECT`](../using/cmdline.html#envvar-PYTHONINSPECT) environment
    variable.

    Deprecated since version 3.12.

int Py\_InteractiveFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.interactive`](init_config.html#c.PyConfig.interactive "PyConfig.interactive") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    Set by the [`-i`](../using/cmdline.html#cmdoption-i) option.

    Deprecated since version 3.12.

int Py\_IsolatedFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.isolated`](init_config.html#c.PyConfig.isolated "PyConfig.isolated") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    Run Python in isolated mode. In isolated mode [`sys.path`](../library/sys.html#sys.path "sys.path") contains
    neither the script’s directory nor the user’s site-packages directory.

    Set by the [`-I`](../using/cmdline.html#cmdoption-I) option.

    Added in version 3.4.

    Deprecated since version 3.12.

int Py\_LegacyWindowsFSEncodingFlag
:   This API is kept for backward compatibility: setting
    [`PyPreConfig.legacy_windows_fs_encoding`](init_config.html#c.PyPreConfig.legacy_windows_fs_encoding "PyPreConfig.legacy_windows_fs_encoding") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    If the flag is non-zero, use the `mbcs` encoding with `replace` error
    handler, instead of the UTF-8 encoding with `surrogatepass` error handler,
    for the [filesystem encoding and error handler](../glossary.html#term-filesystem-encoding-and-error-handler).

    Set to `1` if the [`PYTHONLEGACYWINDOWSFSENCODING`](../using/cmdline.html#envvar-PYTHONLEGACYWINDOWSFSENCODING) environment
    variable is set to a non-empty string.

    See [**PEP 529**](https://peps.python.org/pep-0529/) for more details.

    [Availability](../library/intro.html#availability): Windows.

    Deprecated since version 3.12.

int Py\_LegacyWindowsStdioFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.legacy_windows_stdio`](init_config.html#c.PyConfig.legacy_windows_stdio "PyConfig.legacy_windows_stdio") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    If the flag is non-zero, use [`io.FileIO`](../library/io.html#io.FileIO "io.FileIO") instead of
    `io._WindowsConsoleIO` for [`sys`](../library/sys.html#module-sys "sys: Access system-specific parameters and functions.") standard streams.

    Set to `1` if the [`PYTHONLEGACYWINDOWSSTDIO`](../using/cmdline.html#envvar-PYTHONLEGACYWINDOWSSTDIO) environment
    variable is set to a non-empty string.

    See [**PEP 528**](https://peps.python.org/pep-0528/) for more details.

    [Availability](../library/intro.html#availability): Windows.

    Deprecated since version 3.12.

int Py\_NoSiteFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.site_import`](init_config.html#c.PyConfig.site_import "PyConfig.site_import") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    Disable the import of the module [`site`](../library/site.html#module-site "site: Module responsible for site-specific configuration.") and the site-dependent
    manipulations of [`sys.path`](../library/sys.html#sys.path "sys.path") that it entails. Also disable these
    manipulations if [`site`](../library/site.html#module-site "site: Module responsible for site-specific configuration.") is explicitly imported later (call
    [`site.main()`](../library/site.html#site.main "site.main") if you want them to be triggered).

    Set by the [`-S`](../using/cmdline.html#cmdoption-S) option.

    Deprecated since version 3.12.

int Py\_NoUserSiteDirectory
:   This API is kept for backward compatibility: setting
    [`PyConfig.user_site_directory`](init_config.html#c.PyConfig.user_site_directory "PyConfig.user_site_directory") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    Don’t add the [`user site-packages directory`](../library/site.html#site.USER_SITE "site.USER_SITE") to
    [`sys.path`](../library/sys.html#sys.path "sys.path").

    Set by the [`-s`](../using/cmdline.html#cmdoption-s) and [`-I`](../using/cmdline.html#cmdoption-I) options, and the
    [`PYTHONNOUSERSITE`](../using/cmdline.html#envvar-PYTHONNOUSERSITE) environment variable.

    Deprecated since version 3.12.

int Py\_OptimizeFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.optimization_level`](init_config.html#c.PyConfig.optimization_level "PyConfig.optimization_level") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    Set by the [`-O`](../using/cmdline.html#cmdoption-O) option and the [`PYTHONOPTIMIZE`](../using/cmdline.html#envvar-PYTHONOPTIMIZE) environment
    variable.

    Deprecated since version 3.12.

int Py\_QuietFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.quiet`](init_config.html#c.PyConfig.quiet "PyConfig.quiet") should be used instead, see [Python
    Initialization Configuration](init_config.html#init-config).

    Don’t display the copyright and version messages even in interactive mode.

    Set by the [`-q`](../using/cmdline.html#cmdoption-q) option.

    Added in version 3.2.

    Deprecated since version 3.12.

int Py\_UnbufferedStdioFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.buffered_stdio`](init_config.html#c.PyConfig.buffered_stdio "PyConfig.buffered_stdio") should be used instead, see [Python
    Initialization Configuration](init_config.html#init-config).

    Force the stdout and stderr streams to be unbuffered.

    Set by the [`-u`](../using/cmdline.html#cmdoption-u) option and the [`PYTHONUNBUFFERED`](../using/cmdline.html#envvar-PYTHONUNBUFFERED)
    environment variable.

    Deprecated since version 3.12.

int Py\_VerboseFlag
:   This API is kept for backward compatibility: setting
    [`PyConfig.verbose`](init_config.html#c.PyConfig.verbose "PyConfig.verbose") should be used instead, see [Python
    Initialization Configuration](init_config.html#init-config).

    Print a message each time a module is initialized, showing the place
    (filename or built-in module) from which it is loaded. If greater or equal
    to `2`, print a message for each file that is checked for when
    searching for a module. Also provides information on module cleanup at exit.

    Set by the [`-v`](../using/cmdline.html#cmdoption-v) option and the [`PYTHONVERBOSE`](../using/cmdline.html#envvar-PYTHONVERBOSE) environment
    variable.

    Deprecated since version 3.12.

## Initializing and finalizing the interpreter

void Py\_Initialize()
:   *Part of the [Stable ABI](stable.html#stable).*

    Initialize the Python interpreter. In an application embedding Python,
    this should be called before using any other Python/C API functions; see
    [Before Python Initialization](#pre-init-safe) for the few exceptions.

    This initializes
    the table of loaded modules (`sys.modules`), and creates the fundamental
    modules [`builtins`](../library/builtins.html#module-builtins "builtins: The module that provides the built-in namespace."), [`__main__`](../library/__main__.html#module-__main__ "__main__: The environment where top-level code is run. Covers command-line interfaces, import-time behavior, and ``__name__ == '__main__'``.") and [`sys`](../library/sys.html#module-sys "sys: Access system-specific parameters and functions."). It also initializes
    the module search path (`sys.path`). It does not set `sys.argv`; use
    [`PySys_SetArgvEx()`](#c.PySys_SetArgvEx "PySys_SetArgvEx") for that. This is a no-op when called for a second time
    (without calling [`Py_FinalizeEx()`](#c.Py_FinalizeEx "Py_FinalizeEx") first). There is no return value; it is a
    fatal error if the initialization fails.

    Use the [`Py_InitializeFromConfig()`](init_config.html#c.Py_InitializeFromConfig "Py_InitializeFromConfig") function to customize the
    [Python Initialization Configuration](init_config.html#init-config).

    Note

    On Windows, changes the console mode from `O_TEXT` to `O_BINARY`, which will
    also affect non-Python uses of the console using the C Runtime.

void Py\_InitializeEx(int initsigs)
:   *Part of the [Stable ABI](stable.html#stable).*

    This function works like [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize") if *initsigs* is `1`. If
    *initsigs* is `0`, it skips initialization registration of signal handlers, which
    might be useful when Python is embedded.

    Use the [`Py_InitializeFromConfig()`](init_config.html#c.Py_InitializeFromConfig "Py_InitializeFromConfig") function to customize the
    [Python Initialization Configuration](init_config.html#init-config).

int Py\_IsInitialized()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return true (nonzero) when the Python interpreter has been initialized, false
    (zero) if not. After [`Py_FinalizeEx()`](#c.Py_FinalizeEx "Py_FinalizeEx") is called, this returns false until
    [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize") is called again.

int Py\_FinalizeEx()
:   *Part of the [Stable ABI](stable.html#stable) since version 3.6.*

    Undo all initializations made by [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize") and subsequent use of
    Python/C API functions, and destroy all sub-interpreters (see
    [`Py_NewInterpreter()`](#c.Py_NewInterpreter "Py_NewInterpreter") below) that were created and not yet destroyed since
    the last call to [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"). Ideally, this frees all memory
    allocated by the Python interpreter. This is a no-op when called for a second
    time (without calling [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize") again first).

    Since this is the reverse of [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"), it should be called
    in the same thread with the same interpreter active. That means
    the main thread and the main interpreter.
    This should never be called while [`Py_RunMain()`](init_config.html#c.Py_RunMain "Py_RunMain") is running.

    Normally the return value is `0`.
    If there were errors during finalization (flushing buffered data),
    `-1` is returned.

    This function is provided for a number of reasons. An embedding application
    might want to restart Python without having to restart the application itself.
    An application that has loaded the Python interpreter from a dynamically
    loadable library (or DLL) might want to free all memory allocated by Python
    before unloading the DLL. During a hunt for memory leaks in an application a
    developer might want to free all memory allocated by Python before exiting from
    the application.

    **Bugs and caveats:** The destruction of modules and objects in modules is done
    in random order; this may cause destructors ([`__del__()`](../reference/datamodel.html#object.__del__ "object.__del__") methods) to fail
    when they depend on other objects (even functions) or modules. Dynamically
    loaded extension modules loaded by Python are not unloaded. Small amounts of
    memory allocated by the Python interpreter may not be freed (if you find a leak,
    please report it). Memory tied up in circular references between objects is not
    freed. Some memory allocated by extension modules may not be freed. Some
    extensions may not work properly if their initialization routine is called more
    than once; this can happen if an application calls [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize") and
    [`Py_FinalizeEx()`](#c.Py_FinalizeEx "Py_FinalizeEx") more than once.

    Raises an [auditing event](../library/sys.html#auditing) `cpython._PySys_ClearAuditHooks` with no arguments.

    Added in version 3.6.

void Py\_Finalize()
:   *Part of the [Stable ABI](stable.html#stable).*

    This is a backwards-compatible version of [`Py_FinalizeEx()`](#c.Py_FinalizeEx "Py_FinalizeEx") that
    disregards the return value.

## Process-wide parameters

int Py\_SetStandardStreamEncoding(const char \*encoding, const char \*errors)
:   This API is kept for backward compatibility: setting
    [`PyConfig.stdio_encoding`](init_config.html#c.PyConfig.stdio_encoding "PyConfig.stdio_encoding") and [`PyConfig.stdio_errors`](init_config.html#c.PyConfig.stdio_errors "PyConfig.stdio_errors")
    should be used instead, see [Python Initialization Configuration](init_config.html#init-config).

    This function should be called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"), if it is
    called at all. It specifies which encoding and error handling to use
    with standard IO, with the same meanings as in [`str.encode()`](../library/stdtypes.html#str.encode "str.encode").

    It overrides [`PYTHONIOENCODING`](../using/cmdline.html#envvar-PYTHONIOENCODING) values, and allows embedding code
    to control IO encoding when the environment variable does not work.

    *encoding* and/or *errors* may be `NULL` to use
    [`PYTHONIOENCODING`](../using/cmdline.html#envvar-PYTHONIOENCODING) and/or default values (depending on other
    settings).

    Note that [`sys.stderr`](../library/sys.html#sys.stderr "sys.stderr") always uses the “backslashreplace” error
    handler, regardless of this (or any other) setting.

    If [`Py_FinalizeEx()`](#c.Py_FinalizeEx "Py_FinalizeEx") is called, this function will need to be called
    again in order to affect subsequent calls to [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize").

    Returns `0` if successful, a nonzero value on error (e.g. calling after the
    interpreter has already been initialized).

    Added in version 3.4.

    Deprecated since version 3.11.

void Py\_SetProgramName(const wchar\_t \*name)
:   *Part of the [Stable ABI](stable.html#stable).*

    This API is kept for backward compatibility: setting
    [`PyConfig.program_name`](init_config.html#c.PyConfig.program_name "PyConfig.program_name") should be used instead, see [Python
    Initialization Configuration](init_config.html#init-config).

    This function should be called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize") is called for
    the first time, if it is called at all. It tells the interpreter the value
    of the `argv[0]` argument to the `main()` function of the program
    (converted to wide characters).
    This is used by [`Py_GetPath()`](#c.Py_GetPath "Py_GetPath") and some other functions below to find
    the Python run-time libraries relative to the interpreter executable. The
    default value is `'python'`. The argument should point to a
    zero-terminated wide character string in static storage whose contents will not
    change for the duration of the program’s execution. No code in the Python
    interpreter will change the contents of this storage.

    Use [`Py_DecodeLocale()`](sys.html#c.Py_DecodeLocale "Py_DecodeLocale") to decode a bytes string to get a
    wchar\_t\* string.

    Deprecated since version 3.11.

wchar\_t \*Py\_GetProgramName()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the program name set with [`Py_SetProgramName()`](#c.Py_SetProgramName "Py_SetProgramName"), or the default.
    The returned string points into static storage; the caller should not modify its
    value.

    This function should not be called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"), otherwise
    it returns `NULL`.

    Changed in version 3.10: It now returns `NULL` if called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize").

wchar\_t \*Py\_GetPrefix()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the *prefix* for installed platform-independent files. This is derived
    through a number of complicated rules from the program name set with
    [`Py_SetProgramName()`](#c.Py_SetProgramName "Py_SetProgramName") and some environment variables; for example, if the
    program name is `'/usr/local/bin/python'`, the prefix is `'/usr/local'`. The
    returned string points into static storage; the caller should not modify its
    value. This corresponds to the **prefix** variable in the top-level
    `Makefile` and the [`--prefix`](../using/configure.html#cmdoption-prefix) argument to the **configure**
    script at build time. The value is available to Python code as `sys.prefix`.
    It is only useful on Unix. See also the next function.

    This function should not be called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"), otherwise
    it returns `NULL`.

    Changed in version 3.10: It now returns `NULL` if called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize").

wchar\_t \*Py\_GetExecPrefix()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the *exec-prefix* for installed platform-*dependent* files. This is
    derived through a number of complicated rules from the program name set with
    [`Py_SetProgramName()`](#c.Py_SetProgramName "Py_SetProgramName") and some environment variables; for example, if the
    program name is `'/usr/local/bin/python'`, the exec-prefix is
    `'/usr/local'`. The returned string points into static storage; the caller
    should not modify its value. This corresponds to the **exec\_prefix**
    variable in the top-level `Makefile` and the `--exec-prefix`
    argument to the **configure** script at build time. The value is
    available to Python code as `sys.exec_prefix`. It is only useful on Unix.

    Background: The exec-prefix differs from the prefix when platform dependent
    files (such as executables and shared libraries) are installed in a different
    directory tree. In a typical installation, platform dependent files may be
    installed in the `/usr/local/plat` subtree while platform independent may
    be installed in `/usr/local`.

    Generally speaking, a platform is a combination of hardware and software
    families, e.g. Sparc machines running the Solaris 2.x operating system are
    considered the same platform, but Intel machines running Solaris 2.x are another
    platform, and Intel machines running Linux are yet another platform. Different
    major revisions of the same operating system generally also form different
    platforms. Non-Unix operating systems are a different story; the installation
    strategies on those systems are so different that the prefix and exec-prefix are
    meaningless, and set to the empty string. Note that compiled Python bytecode
    files are platform independent (but not independent from the Python version by
    which they were compiled!).

    System administrators will know how to configure the **mount** or
    **automount** programs to share `/usr/local` between platforms
    while having `/usr/local/plat` be a different filesystem for each
    platform.

    This function should not be called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"), otherwise
    it returns `NULL`.

    Changed in version 3.10: It now returns `NULL` if called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize").

wchar\_t \*Py\_GetProgramFullPath()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the full program name of the Python executable; this is computed as a
    side-effect of deriving the default module search path from the program name
    (set by [`Py_SetProgramName()`](#c.Py_SetProgramName "Py_SetProgramName") above). The returned string points into
    static storage; the caller should not modify its value. The value is available
    to Python code as `sys.executable`.

    This function should not be called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"), otherwise
    it returns `NULL`.

    Changed in version 3.10: It now returns `NULL` if called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize").

wchar\_t \*Py\_GetPath()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the default module search path; this is computed from the program name
    (set by [`Py_SetProgramName()`](#c.Py_SetProgramName "Py_SetProgramName") above) and some environment variables.
    The returned string consists of a series of directory names separated by a
    platform dependent delimiter character. The delimiter character is `':'`
    on Unix and macOS, `';'` on Windows. The returned string points into
    static storage; the caller should not modify its value. The list
    [`sys.path`](../library/sys.html#sys.path "sys.path") is initialized with this value on interpreter startup; it
    can be (and usually is) modified later to change the search path for loading
    modules.

    This function should not be called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"), otherwise
    it returns `NULL`.

    Changed in version 3.10: It now returns `NULL` if called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize").

void Py\_SetPath(const wchar\_t\*)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.7.*

    This API is kept for backward compatibility: setting
    [`PyConfig.module_search_paths`](init_config.html#c.PyConfig.module_search_paths "PyConfig.module_search_paths") and
    [`PyConfig.module_search_paths_set`](init_config.html#c.PyConfig.module_search_paths_set "PyConfig.module_search_paths_set") should be used instead, see
    [Python Initialization Configuration](init_config.html#init-config).

    Set the default module search path. If this function is called before
    [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"), then [`Py_GetPath()`](#c.Py_GetPath "Py_GetPath") won’t attempt to compute a
    default search path but uses the one provided instead. This is useful if
    Python is embedded by an application that has full knowledge of the location
    of all modules. The path components should be separated by the platform
    dependent delimiter character, which is `':'` on Unix and macOS, `';'`
    on Windows.

    This also causes [`sys.executable`](../library/sys.html#sys.executable "sys.executable") to be set to the program
    full path (see [`Py_GetProgramFullPath()`](#c.Py_GetProgramFullPath "Py_GetProgramFullPath")) and for [`sys.prefix`](../library/sys.html#sys.prefix "sys.prefix") and
    [`sys.exec_prefix`](../library/sys.html#sys.exec_prefix "sys.exec_prefix") to be empty. It is up to the caller to modify these
    if required after calling [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize").

    Use [`Py_DecodeLocale()`](sys.html#c.Py_DecodeLocale "Py_DecodeLocale") to decode a bytes string to get a
    wchar\_\* string.

    The path argument is copied internally, so the caller may free it after the
    call completes.

    Changed in version 3.8: The program full path is now used for [`sys.executable`](../library/sys.html#sys.executable "sys.executable"), instead
    of the program name.

    Deprecated since version 3.11.

const char \*Py\_GetVersion()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the version of this Python interpreter. This is a string that looks
    something like

    ```
    "3.0a5+ (py3k:63103M, May 12 2008, 00:53:55) \n[GCC 4.2.3]"
    ```

    The first word (up to the first space character) is the current Python version;
    the first characters are the major and minor version separated by a
    period. The returned string points into static storage; the caller should not
    modify its value. The value is available to Python code as [`sys.version`](../library/sys.html#sys.version "sys.version").

    See also the [`Py_Version`](apiabiversion.html#c.Py_Version "Py_Version") constant.

const char \*Py\_GetPlatform()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the platform identifier for the current platform. On Unix, this is
    formed from the “official” name of the operating system, converted to lower
    case, followed by the major revision number; e.g., for Solaris 2.x, which is
    also known as SunOS 5.x, the value is `'sunos5'`. On macOS, it is
    `'darwin'`. On Windows, it is `'win'`. The returned string points into
    static storage; the caller should not modify its value. The value is available
    to Python code as `sys.platform`.

const char \*Py\_GetCopyright()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the official copyright string for the current Python version, for example

    `'Copyright 1991-1995 Stichting Mathematisch Centrum, Amsterdam'`

    The returned string points into static storage; the caller should not modify its
    value. The value is available to Python code as `sys.copyright`.

const char \*Py\_GetCompiler()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return an indication of the compiler used to build the current Python version,
    in square brackets, for example:

    ```
    "[GCC 2.7.2.2]"
    ```

    The returned string points into static storage; the caller should not modify its
    value. The value is available to Python code as part of the variable
    `sys.version`.

const char \*Py\_GetBuildInfo()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return information about the sequence number and build date and time of the
    current Python interpreter instance, for example

    ```
    "#67, Aug  1 1997, 22:34:28"
    ```

    The returned string points into static storage; the caller should not modify its
    value. The value is available to Python code as part of the variable
    `sys.version`.

void PySys\_SetArgvEx(int argc, wchar\_t \*\*argv, int updatepath)
:   *Part of the [Stable ABI](stable.html#stable).*

    This API is kept for backward compatibility: setting
    [`PyConfig.argv`](init_config.html#c.PyConfig.argv "PyConfig.argv"), [`PyConfig.parse_argv`](init_config.html#c.PyConfig.parse_argv "PyConfig.parse_argv") and
    [`PyConfig.safe_path`](init_config.html#c.PyConfig.safe_path "PyConfig.safe_path") should be used instead, see [Python
    Initialization Configuration](init_config.html#init-config).

    Set [`sys.argv`](../library/sys.html#sys.argv "sys.argv") based on *argc* and *argv*. These parameters are
    similar to those passed to the program’s `main()` function with the
    difference that the first entry should refer to the script file to be
    executed rather than the executable hosting the Python interpreter. If there
    isn’t a script that will be run, the first entry in *argv* can be an empty
    string. If this function fails to initialize [`sys.argv`](../library/sys.html#sys.argv "sys.argv"), a fatal
    condition is signalled using [`Py_FatalError()`](sys.html#c.Py_FatalError "Py_FatalError").

    If *updatepath* is zero, this is all the function does. If *updatepath*
    is non-zero, the function also modifies [`sys.path`](../library/sys.html#sys.path "sys.path") according to the
    following algorithm:

    - If the name of an existing script is passed in `argv[0]`, the absolute
      path of the directory where the script is located is prepended to
      [`sys.path`](../library/sys.html#sys.path "sys.path").
    - Otherwise (that is, if *argc* is `0` or `argv[0]` doesn’t point
      to an existing file name), an empty string is prepended to
      [`sys.path`](../library/sys.html#sys.path "sys.path"), which is the same as prepending the current working
      directory (`"."`).

    Use [`Py_DecodeLocale()`](sys.html#c.Py_DecodeLocale "Py_DecodeLocale") to decode a bytes string to get a
    wchar\_t\* string.

    See also [`PyConfig.orig_argv`](init_config.html#c.PyConfig.orig_argv "PyConfig.orig_argv") and [`PyConfig.argv`](init_config.html#c.PyConfig.argv "PyConfig.argv")
    members of the [Python Initialization Configuration](init_config.html#init-config).

    Note

    It is recommended that applications embedding the Python interpreter
    for purposes other than executing a single script pass `0` as *updatepath*,
    and update [`sys.path`](../library/sys.html#sys.path "sys.path") themselves if desired.
    See [**CVE 2008-5983**](https://www.cve.org/CVERecord?id=CVE-2008-5983).

    On versions before 3.1.3, you can achieve the same effect by manually
    popping the first [`sys.path`](../library/sys.html#sys.path "sys.path") element after having called
    [`PySys_SetArgv()`](#c.PySys_SetArgv "PySys_SetArgv"), for example using:

    ```
    PyRun_SimpleString("import sys; sys.path.pop(0)\n");
    ```

    Added in version 3.1.3.

    Deprecated since version 3.11.

void PySys\_SetArgv(int argc, wchar\_t \*\*argv)
:   *Part of the [Stable ABI](stable.html#stable).*

    This API is kept for backward compatibility: setting
    [`PyConfig.argv`](init_config.html#c.PyConfig.argv "PyConfig.argv") and [`PyConfig.parse_argv`](init_config.html#c.PyConfig.parse_argv "PyConfig.parse_argv") should be used
    instead, see [Python Initialization Configuration](init_config.html#init-config).

    This function works like [`PySys_SetArgvEx()`](#c.PySys_SetArgvEx "PySys_SetArgvEx") with *updatepath* set
    to `1` unless the **python** interpreter was started with the
    [`-I`](../using/cmdline.html#cmdoption-I).

    Use [`Py_DecodeLocale()`](sys.html#c.Py_DecodeLocale "Py_DecodeLocale") to decode a bytes string to get a
    wchar\_t\* string.

    See also [`PyConfig.orig_argv`](init_config.html#c.PyConfig.orig_argv "PyConfig.orig_argv") and [`PyConfig.argv`](init_config.html#c.PyConfig.argv "PyConfig.argv")
    members of the [Python Initialization Configuration](init_config.html#init-config).

    Changed in version 3.4: The *updatepath* value depends on [`-I`](../using/cmdline.html#cmdoption-I).

    Deprecated since version 3.11.

void Py\_SetPythonHome(const wchar\_t \*home)
:   *Part of the [Stable ABI](stable.html#stable).*

    This API is kept for backward compatibility: setting
    [`PyConfig.home`](init_config.html#c.PyConfig.home "PyConfig.home") should be used instead, see [Python
    Initialization Configuration](init_config.html#init-config).

    Set the default “home” directory, that is, the location of the standard
    Python libraries. See [`PYTHONHOME`](../using/cmdline.html#envvar-PYTHONHOME) for the meaning of the
    argument string.

    The argument should point to a zero-terminated character string in static
    storage whose contents will not change for the duration of the program’s
    execution. No code in the Python interpreter will change the contents of
    this storage.

    Use [`Py_DecodeLocale()`](sys.html#c.Py_DecodeLocale "Py_DecodeLocale") to decode a bytes string to get a
    wchar\_t\* string.

    Deprecated since version 3.11.

wchar\_t \*Py\_GetPythonHome()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the default “home”, that is, the value set by a previous call to
    [`Py_SetPythonHome()`](#c.Py_SetPythonHome "Py_SetPythonHome"), or the value of the [`PYTHONHOME`](../using/cmdline.html#envvar-PYTHONHOME)
    environment variable if it is set.

    This function should not be called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"), otherwise
    it returns `NULL`.

    Changed in version 3.10: It now returns `NULL` if called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize").

## Thread State and the Global Interpreter Lock

The Python interpreter is not fully thread-safe. In order to support
multi-threaded Python programs, there’s a global lock, called the [global
interpreter lock](../glossary.html#term-global-interpreter-lock) or [GIL](../glossary.html#term-GIL), that must be held by the current thread before
it can safely access Python objects. Without the lock, even the simplest
operations could cause problems in a multi-threaded program: for example, when
two threads simultaneously increment the reference count of the same object, the
reference count could end up being incremented only once instead of twice.

Therefore, the rule exists that only the thread that has acquired the
[GIL](../glossary.html#term-GIL) may operate on Python objects or call Python/C API functions.
In order to emulate concurrency of execution, the interpreter regularly
tries to switch threads (see [`sys.setswitchinterval()`](../library/sys.html#sys.setswitchinterval "sys.setswitchinterval")). The lock is also
released around potentially blocking I/O operations like reading or writing
a file, so that other Python threads can run in the meantime.

The Python interpreter keeps some thread-specific bookkeeping information
inside a data structure called [`PyThreadState`](#c.PyThreadState "PyThreadState"). There’s also one
global variable pointing to the current [`PyThreadState`](#c.PyThreadState "PyThreadState"): it can
be retrieved using [`PyThreadState_Get()`](#c.PyThreadState_Get "PyThreadState_Get").

### Releasing the GIL from extension code

Most extension code manipulating the [GIL](../glossary.html#term-GIL) has the following simple
structure:

```
Save the thread state in a local variable.
Release the global interpreter lock.
... Do some blocking I/O operation ...
Reacquire the global interpreter lock.
Restore the thread state from the local variable.
```

This is so common that a pair of macros exists to simplify it:

```
Py_BEGIN_ALLOW_THREADS
... Do some blocking I/O operation ...
Py_END_ALLOW_THREADS
```

The [`Py_BEGIN_ALLOW_THREADS`](#c.Py_BEGIN_ALLOW_THREADS "Py_BEGIN_ALLOW_THREADS") macro opens a new block and declares a
hidden local variable; the [`Py_END_ALLOW_THREADS`](#c.Py_END_ALLOW_THREADS "Py_END_ALLOW_THREADS") macro closes the
block.

The block above expands to the following code:

```
PyThreadState *_save;

_save = PyEval_SaveThread();
... Do some blocking I/O operation ...
PyEval_RestoreThread(_save);
```

Here is how these functions work: the global interpreter lock is used to protect the pointer to the
current thread state. When releasing the lock and saving the thread state,
the current thread state pointer must be retrieved before the lock is released
(since another thread could immediately acquire the lock and store its own thread
state in the global variable). Conversely, when acquiring the lock and restoring
the thread state, the lock must be acquired before storing the thread state
pointer.

Note

Calling system I/O functions is the most common use case for releasing
the GIL, but it can also be useful before calling long-running computations
which don’t need access to Python objects, such as compression or
cryptographic functions operating over memory buffers. For example, the
standard [`zlib`](../library/zlib.html#module-zlib "zlib: Low-level interface to compression and decompression routines compatible with gzip.") and [`hashlib`](../library/hashlib.html#module-hashlib "hashlib: Secure hash and message digest algorithms.") modules release the GIL when
compressing or hashing data.

### Non-Python created threads

When threads are created using the dedicated Python APIs (such as the
[`threading`](../library/threading.html#module-threading "threading: Thread-based parallelism.") module), a thread state is automatically associated to them
and the code showed above is therefore correct. However, when threads are
created from C (for example by a third-party library with its own thread
management), they don’t hold the GIL, nor is there a thread state structure
for them.

If you need to call Python code from these threads (often this will be part
of a callback API provided by the aforementioned third-party library),
you must first register these threads with the interpreter by
creating a thread state data structure, then acquiring the GIL, and finally
storing their thread state pointer, before you can start using the Python/C
API. When you are done, you should reset the thread state pointer, release
the GIL, and finally free the thread state data structure.

The [`PyGILState_Ensure()`](#c.PyGILState_Ensure "PyGILState_Ensure") and [`PyGILState_Release()`](#c.PyGILState_Release "PyGILState_Release") functions do
all of the above automatically. The typical idiom for calling into Python
from a C thread is:

```
PyGILState_STATE gstate;
gstate = PyGILState_Ensure();

/* Perform Python actions here. */
result = CallSomeFunction();
/* evaluate result or handle exception */

/* Release the thread. No Python API allowed beyond this point. */
PyGILState_Release(gstate);
```

Note that the `PyGILState_*` functions assume there is only one global
interpreter (created automatically by [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize")). Python
supports the creation of additional interpreters (using
[`Py_NewInterpreter()`](#c.Py_NewInterpreter "Py_NewInterpreter")), but mixing multiple interpreters and the
`PyGILState_*` API is unsupported.

### Cautions about fork()

Another important thing to note about threads is their behaviour in the face
of the C `fork()` call. On most systems with `fork()`, after a
process forks only the thread that issued the fork will exist. This has a
concrete impact both on how locks must be handled and on all stored state
in CPython’s runtime.

The fact that only the “current” thread remains
means any locks held by other threads will never be released. Python solves
this for [`os.fork()`](../library/os.html#os.fork "os.fork") by acquiring the locks it uses internally before
the fork, and releasing them afterwards. In addition, it resets any
[Lock Objects](../library/threading.html#lock-objects) in the child. When extending or embedding Python, there
is no way to inform Python of additional (non-Python) locks that need to be
acquired before or reset after a fork. OS facilities such as
`pthread_atfork()` would need to be used to accomplish the same thing.
Additionally, when extending or embedding Python, calling `fork()`
directly rather than through [`os.fork()`](../library/os.html#os.fork "os.fork") (and returning to or calling
into Python) may result in a deadlock by one of Python’s internal locks
being held by a thread that is defunct after the fork.
[`PyOS_AfterFork_Child()`](sys.html#c.PyOS_AfterFork_Child "PyOS_AfterFork_Child") tries to reset the necessary locks, but is not
always able to.

The fact that all other threads go away also means that CPython’s
runtime state there must be cleaned up properly, which [`os.fork()`](../library/os.html#os.fork "os.fork")
does. This means finalizing all other [`PyThreadState`](#c.PyThreadState "PyThreadState") objects
belonging to the current interpreter and all other
[`PyInterpreterState`](#c.PyInterpreterState "PyInterpreterState") objects. Due to this and the special
nature of the [“main” interpreter](#sub-interpreter-support),
`fork()` should only be called in that interpreter’s “main”
thread, where the CPython global runtime was originally initialized.
The only exception is if `exec()` will be called immediately
after.

### High-level API

These are the most commonly used types and functions when writing C extension
code, or when embedding the Python interpreter:

type PyInterpreterState
:   *Part of the [Limited API](stable.html#stable) (as an opaque struct).*

    This data structure represents the state shared by a number of cooperating
    threads. Threads belonging to the same interpreter share their module
    administration and a few other internal items. There are no public members in
    this structure.

    Threads belonging to different interpreters initially share nothing, except
    process state like available memory, open file descriptors and such. The global
    interpreter lock is also shared by all threads, regardless of to which
    interpreter they belong.

type PyThreadState
:   *Part of the [Limited API](stable.html#stable) (as an opaque struct).*

    This data structure represents the state of a single thread. The only public
    data member is:

    [PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*interp
    :   This thread’s interpreter state.

void PyEval\_InitThreads()
:   *Part of the [Stable ABI](stable.html#stable).*

    Deprecated function which does nothing.

    In Python 3.6 and older, this function created the GIL if it didn’t exist.

    Changed in version 3.9: The function now does nothing.

    Changed in version 3.7: This function is now called by [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"), so you don’t
    have to call it yourself anymore.

    Changed in version 3.2: This function cannot be called before [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize") anymore.

    Deprecated since version 3.9.

int PyEval\_ThreadsInitialized()
:   *Part of the [Stable ABI](stable.html#stable).*

    Returns a non-zero value if [`PyEval_InitThreads()`](#c.PyEval_InitThreads "PyEval_InitThreads") has been called. This
    function can be called without holding the GIL, and therefore can be used to
    avoid calls to the locking API when running single-threaded.

    Changed in version 3.7: The [GIL](../glossary.html#term-GIL) is now initialized by [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize").

    Deprecated since version 3.9.

[PyThreadState](#c.PyThreadState "PyThreadState") \*PyEval\_SaveThread()
:   *Part of the [Stable ABI](stable.html#stable).*

    Release the global interpreter lock (if it has been created) and reset the
    thread state to `NULL`, returning the previous thread state (which is not
    `NULL`). If the lock has been created, the current thread must have
    acquired it.

void PyEval\_RestoreThread([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   *Part of the [Stable ABI](stable.html#stable).*

    Acquire the global interpreter lock (if it has been created) and set the
    thread state to *tstate*, which must not be `NULL`. If the lock has been
    created, the current thread must not have acquired it, otherwise deadlock
    ensues.

    Note

    Calling this function from a thread when the runtime is finalizing
    will terminate the thread, even if the thread was not created by Python.
    You can use `_Py_IsFinalizing()` or [`sys.is_finalizing()`](../library/sys.html#sys.is_finalizing "sys.is_finalizing") to
    check if the interpreter is in process of being finalized before calling
    this function to avoid unwanted termination.

[PyThreadState](#c.PyThreadState "PyThreadState") \*PyThreadState\_Get()
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the current thread state. The global interpreter lock must be held.
    When the current thread state is `NULL`, this issues a fatal error (so that
    the caller needn’t check for `NULL`).

[PyThreadState](#c.PyThreadState "PyThreadState") \*PyThreadState\_Swap([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   *Part of the [Stable ABI](stable.html#stable).*

    Swap the current thread state with the thread state given by the argument
    *tstate*, which may be `NULL`. The global interpreter lock must be held
    and is not released.

The following functions use thread-local storage, and are not compatible
with sub-interpreters:

PyGILState\_STATE PyGILState\_Ensure()
:   *Part of the [Stable ABI](stable.html#stable).*

    Ensure that the current thread is ready to call the Python C API regardless
    of the current state of Python, or of the global interpreter lock. This may
    be called as many times as desired by a thread as long as each call is
    matched with a call to [`PyGILState_Release()`](#c.PyGILState_Release "PyGILState_Release"). In general, other
    thread-related APIs may be used between [`PyGILState_Ensure()`](#c.PyGILState_Ensure "PyGILState_Ensure") and
    [`PyGILState_Release()`](#c.PyGILState_Release "PyGILState_Release") calls as long as the thread state is restored to
    its previous state before the Release(). For example, normal usage of the
    [`Py_BEGIN_ALLOW_THREADS`](#c.Py_BEGIN_ALLOW_THREADS "Py_BEGIN_ALLOW_THREADS") and [`Py_END_ALLOW_THREADS`](#c.Py_END_ALLOW_THREADS "Py_END_ALLOW_THREADS") macros is
    acceptable.

    The return value is an opaque “handle” to the thread state when
    [`PyGILState_Ensure()`](#c.PyGILState_Ensure "PyGILState_Ensure") was called, and must be passed to
    [`PyGILState_Release()`](#c.PyGILState_Release "PyGILState_Release") to ensure Python is left in the same state. Even
    though recursive calls are allowed, these handles *cannot* be shared - each
    unique call to [`PyGILState_Ensure()`](#c.PyGILState_Ensure "PyGILState_Ensure") must save the handle for its call
    to [`PyGILState_Release()`](#c.PyGILState_Release "PyGILState_Release").

    When the function returns, the current thread will hold the GIL and be able
    to call arbitrary Python code. Failure is a fatal error.

    Note

    Calling this function from a thread when the runtime is finalizing
    will terminate the thread, even if the thread was not created by Python.
    You can use `_Py_IsFinalizing()` or [`sys.is_finalizing()`](../library/sys.html#sys.is_finalizing "sys.is_finalizing") to
    check if the interpreter is in process of being finalized before calling
    this function to avoid unwanted termination.

void PyGILState\_Release(PyGILState\_STATE)
:   *Part of the [Stable ABI](stable.html#stable).*

    Release any resources previously acquired. After this call, Python’s state will
    be the same as it was prior to the corresponding [`PyGILState_Ensure()`](#c.PyGILState_Ensure "PyGILState_Ensure") call
    (but generally this state will be unknown to the caller, hence the use of the
    GILState API).

    Every call to [`PyGILState_Ensure()`](#c.PyGILState_Ensure "PyGILState_Ensure") must be matched by a call to
    [`PyGILState_Release()`](#c.PyGILState_Release "PyGILState_Release") on the same thread.

[PyThreadState](#c.PyThreadState "PyThreadState") \*PyGILState\_GetThisThreadState()
:   *Part of the [Stable ABI](stable.html#stable).*

    Get the current thread state for this thread. May return `NULL` if no
    GILState API has been used on the current thread. Note that the main thread
    always has such a thread-state, even if no auto-thread-state call has been
    made on the main thread. This is mainly a helper/diagnostic function.

int PyGILState\_Check()
:   Return `1` if the current thread is holding the GIL and `0` otherwise.
    This function can be called from any thread at any time.
    Only if it has had its Python thread state initialized and currently is
    holding the GIL will it return `1`.
    This is mainly a helper/diagnostic function. It can be useful
    for example in callback contexts or memory allocation functions when
    knowing that the GIL is locked can allow the caller to perform sensitive
    actions or otherwise behave differently.

    Added in version 3.4.

The following macros are normally used without a trailing semicolon; look for
example usage in the Python source distribution.

Py\_BEGIN\_ALLOW\_THREADS
:   *Part of the [Stable ABI](stable.html#stable).*

    This macro expands to `{ PyThreadState *_save; _save = PyEval_SaveThread();`.
    Note that it contains an opening brace; it must be matched with a following
    [`Py_END_ALLOW_THREADS`](#c.Py_END_ALLOW_THREADS "Py_END_ALLOW_THREADS") macro. See above for further discussion of this
    macro.

Py\_END\_ALLOW\_THREADS
:   *Part of the [Stable ABI](stable.html#stable).*

    This macro expands to `PyEval_RestoreThread(_save); }`. Note that it contains
    a closing brace; it must be matched with an earlier
    [`Py_BEGIN_ALLOW_THREADS`](#c.Py_BEGIN_ALLOW_THREADS "Py_BEGIN_ALLOW_THREADS") macro. See above for further discussion of
    this macro.

Py\_BLOCK\_THREADS
:   *Part of the [Stable ABI](stable.html#stable).*

    This macro expands to `PyEval_RestoreThread(_save);`: it is equivalent to
    [`Py_END_ALLOW_THREADS`](#c.Py_END_ALLOW_THREADS "Py_END_ALLOW_THREADS") without the closing brace.

Py\_UNBLOCK\_THREADS
:   *Part of the [Stable ABI](stable.html#stable).*

    This macro expands to `_save = PyEval_SaveThread();`: it is equivalent to
    [`Py_BEGIN_ALLOW_THREADS`](#c.Py_BEGIN_ALLOW_THREADS "Py_BEGIN_ALLOW_THREADS") without the opening brace and variable
    declaration.

### Low-level API

All of the following functions must be called after [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize").

Changed in version 3.7: [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize") now initializes the [GIL](../glossary.html#term-GIL).

[PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*PyInterpreterState\_New()
:   *Part of the [Stable ABI](stable.html#stable).*

    Create a new interpreter state object. The global interpreter lock need not
    be held, but may be held if it is necessary to serialize calls to this
    function.

    Raises an [auditing event](../library/sys.html#auditing) `cpython.PyInterpreterState_New` with no arguments.

void PyInterpreterState\_Clear([PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*interp)
:   *Part of the [Stable ABI](stable.html#stable).*

    Reset all information in an interpreter state object. The global interpreter
    lock must be held.

    Raises an [auditing event](../library/sys.html#auditing) `cpython.PyInterpreterState_Clear` with no arguments.

void PyInterpreterState\_Delete([PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*interp)
:   *Part of the [Stable ABI](stable.html#stable).*

    Destroy an interpreter state object. The global interpreter lock need not be
    held. The interpreter state must have been reset with a previous call to
    [`PyInterpreterState_Clear()`](#c.PyInterpreterState_Clear "PyInterpreterState_Clear").

[PyThreadState](#c.PyThreadState "PyThreadState") \*PyThreadState\_New([PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*interp)
:   *Part of the [Stable ABI](stable.html#stable).*

    Create a new thread state object belonging to the given interpreter object.
    The global interpreter lock need not be held, but may be held if it is
    necessary to serialize calls to this function.

void PyThreadState\_Clear([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   *Part of the [Stable ABI](stable.html#stable).*

    Reset all information in a thread state object. The global interpreter lock
    must be held.

    Changed in version 3.9: This function now calls the `PyThreadState.on_delete` callback.
    Previously, that happened in [`PyThreadState_Delete()`](#c.PyThreadState_Delete "PyThreadState_Delete").

void PyThreadState\_Delete([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   *Part of the [Stable ABI](stable.html#stable).*

    Destroy a thread state object. The global interpreter lock need not be held.
    The thread state must have been reset with a previous call to
    [`PyThreadState_Clear()`](#c.PyThreadState_Clear "PyThreadState_Clear").

void PyThreadState\_DeleteCurrent(void)
:   Destroy the current thread state and release the global interpreter lock.
    Like [`PyThreadState_Delete()`](#c.PyThreadState_Delete "PyThreadState_Delete"), the global interpreter lock must
    be held. The thread state must have been reset with a previous call
    to [`PyThreadState_Clear()`](#c.PyThreadState_Clear "PyThreadState_Clear").

[PyFrameObject](frame.html#c.PyFrameObject "PyFrameObject") \*PyThreadState\_GetFrame([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.10.*

    Get the current frame of the Python thread state *tstate*.

    Return a [strong reference](../glossary.html#term-strong-reference). Return `NULL` if no frame is currently
    executing.

    See also [`PyEval_GetFrame()`](reflection.html#c.PyEval_GetFrame "PyEval_GetFrame").

    *tstate* must not be `NULL`.

    Added in version 3.9.

uint64\_t PyThreadState\_GetID([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.10.*

    Get the unique thread state identifier of the Python thread state *tstate*.

    *tstate* must not be `NULL`.

    Added in version 3.9.

[PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*PyThreadState\_GetInterpreter([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.10.*

    Get the interpreter of the Python thread state *tstate*.

    *tstate* must not be `NULL`.

    Added in version 3.9.

void PyThreadState\_EnterTracing([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   Suspend tracing and profiling in the Python thread state *tstate*.

    Resume them using the [`PyThreadState_LeaveTracing()`](#c.PyThreadState_LeaveTracing "PyThreadState_LeaveTracing") function.

    Added in version 3.11.

void PyThreadState\_LeaveTracing([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   Resume tracing and profiling in the Python thread state *tstate* suspended
    by the [`PyThreadState_EnterTracing()`](#c.PyThreadState_EnterTracing "PyThreadState_EnterTracing") function.

    See also [`PyEval_SetTrace()`](#c.PyEval_SetTrace "PyEval_SetTrace") and [`PyEval_SetProfile()`](#c.PyEval_SetProfile "PyEval_SetProfile")
    functions.

    Added in version 3.11.

[PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*PyInterpreterState\_Get(void)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.9.*

    Get the current interpreter.

    Issue a fatal error if there no current Python thread state or no current
    interpreter. It cannot return NULL.

    The caller must hold the GIL.

    Added in version 3.9.

int64\_t PyInterpreterState\_GetID([PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*interp)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.7.*

    Return the interpreter’s unique ID. If there was any error in doing
    so then `-1` is returned and an error is set.

    The caller must hold the GIL.

    Added in version 3.7.

[PyObject](structures.html#c.PyObject "PyObject") \*PyInterpreterState\_GetDict([PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*interp)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.8.*

    Return a dictionary in which interpreter-specific data may be stored.
    If this function returns `NULL` then no exception has been raised and
    the caller should assume no interpreter-specific dict is available.

    This is not a replacement for [`PyModule_GetState()`](module.html#c.PyModule_GetState "PyModule_GetState"), which
    extensions should use to store interpreter-specific state information.

    Added in version 3.8.

typedef [PyObject](structures.html#c.PyObject "PyObject") \*(\*\_PyFrameEvalFunction)([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate, [\_PyInterpreterFrame](frame.html#c._PyInterpreterFrame "_PyInterpreterFrame") \*frame, int throwflag)
:   Type of a frame evaluation function.

    The *throwflag* parameter is used by the `throw()` method of generators:
    if non-zero, handle the current exception.

    Changed in version 3.9: The function now takes a *tstate* parameter.

    Changed in version 3.11: The *frame* parameter changed from `PyFrameObject*` to `_PyInterpreterFrame*`.

[\_PyFrameEvalFunction](#c._PyFrameEvalFunction "_PyFrameEvalFunction") \_PyInterpreterState\_GetEvalFrameFunc([PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*interp)
:   Get the frame evaluation function.

    See the [**PEP 523**](https://peps.python.org/pep-0523/) “Adding a frame evaluation API to CPython”.

    Added in version 3.9.

void \_PyInterpreterState\_SetEvalFrameFunc([PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*interp, [\_PyFrameEvalFunction](#c._PyFrameEvalFunction "_PyFrameEvalFunction") eval\_frame)
:   Set the frame evaluation function.

    See the [**PEP 523**](https://peps.python.org/pep-0523/) “Adding a frame evaluation API to CPython”.

    Added in version 3.9.

[PyObject](structures.html#c.PyObject "PyObject") \*PyThreadState\_GetDict()
:   *Return value: Borrowed reference.* *Part of the [Stable ABI](stable.html#stable).*

    Return a dictionary in which extensions can store thread-specific state
    information. Each extension should use a unique key to use to store state in
    the dictionary. It is okay to call this function when no current thread state
    is available. If this function returns `NULL`, no exception has been raised and
    the caller should assume no current thread state is available.

int PyThreadState\_SetAsyncExc(unsigned long id, [PyObject](structures.html#c.PyObject "PyObject") \*exc)
:   *Part of the [Stable ABI](stable.html#stable).*

    Asynchronously raise an exception in a thread. The *id* argument is the thread
    id of the target thread; *exc* is the exception object to be raised. This
    function does not steal any references to *exc*. To prevent naive misuse, you
    must write your own C extension to call this. Must be called with the GIL held.
    Returns the number of thread states modified; this is normally one, but will be
    zero if the thread id isn’t found. If *exc* is `NULL`, the pending
    exception (if any) for the thread is cleared. This raises no exceptions.

    Changed in version 3.7: The type of the *id* parameter changed from long to
    unsigned long.

void PyEval\_AcquireThread([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   *Part of the [Stable ABI](stable.html#stable).*

    Acquire the global interpreter lock and set the current thread state to
    *tstate*, which must not be `NULL`. The lock must have been created earlier.
    If this thread already has the lock, deadlock ensues.

    Note

    Calling this function from a thread when the runtime is finalizing
    will terminate the thread, even if the thread was not created by Python.
    You can use `_Py_IsFinalizing()` or [`sys.is_finalizing()`](../library/sys.html#sys.is_finalizing "sys.is_finalizing") to
    check if the interpreter is in process of being finalized before calling
    this function to avoid unwanted termination.

    Changed in version 3.8: Updated to be consistent with [`PyEval_RestoreThread()`](#c.PyEval_RestoreThread "PyEval_RestoreThread"),
    [`Py_END_ALLOW_THREADS()`](#c.Py_END_ALLOW_THREADS "Py_END_ALLOW_THREADS"), and [`PyGILState_Ensure()`](#c.PyGILState_Ensure "PyGILState_Ensure"),
    and terminate the current thread if called while the interpreter is finalizing.

    [`PyEval_RestoreThread()`](#c.PyEval_RestoreThread "PyEval_RestoreThread") is a higher-level function which is always
    available (even when threads have not been initialized).

void PyEval\_ReleaseThread([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   *Part of the [Stable ABI](stable.html#stable).*

    Reset the current thread state to `NULL` and release the global interpreter
    lock. The lock must have been created earlier and must be held by the current
    thread. The *tstate* argument, which must not be `NULL`, is only used to check
    that it represents the current thread state — if it isn’t, a fatal error is
    reported.

    [`PyEval_SaveThread()`](#c.PyEval_SaveThread "PyEval_SaveThread") is a higher-level function which is always
    available (even when threads have not been initialized).

void PyEval\_AcquireLock()
:   *Part of the [Stable ABI](stable.html#stable).*

    Acquire the global interpreter lock. The lock must have been created earlier.
    If this thread already has the lock, a deadlock ensues.

    Deprecated since version 3.2: This function does not update the current thread state. Please use
    [`PyEval_RestoreThread()`](#c.PyEval_RestoreThread "PyEval_RestoreThread") or [`PyEval_AcquireThread()`](#c.PyEval_AcquireThread "PyEval_AcquireThread")
    instead.

    Note

    Calling this function from a thread when the runtime is finalizing
    will terminate the thread, even if the thread was not created by Python.
    You can use `_Py_IsFinalizing()` or [`sys.is_finalizing()`](../library/sys.html#sys.is_finalizing "sys.is_finalizing") to
    check if the interpreter is in process of being finalized before calling
    this function to avoid unwanted termination.

    Changed in version 3.8: Updated to be consistent with [`PyEval_RestoreThread()`](#c.PyEval_RestoreThread "PyEval_RestoreThread"),
    [`Py_END_ALLOW_THREADS()`](#c.Py_END_ALLOW_THREADS "Py_END_ALLOW_THREADS"), and [`PyGILState_Ensure()`](#c.PyGILState_Ensure "PyGILState_Ensure"),
    and terminate the current thread if called while the interpreter is finalizing.

void PyEval\_ReleaseLock()
:   *Part of the [Stable ABI](stable.html#stable).*

    Release the global interpreter lock. The lock must have been created earlier.

    Deprecated since version 3.2: This function does not update the current thread state. Please use
    [`PyEval_SaveThread()`](#c.PyEval_SaveThread "PyEval_SaveThread") or [`PyEval_ReleaseThread()`](#c.PyEval_ReleaseThread "PyEval_ReleaseThread")
    instead.

## Sub-interpreter support

While in most uses, you will only embed a single Python interpreter, there
are cases where you need to create several independent interpreters in the
same process and perhaps even in the same thread. Sub-interpreters allow
you to do that.

The “main” interpreter is the first one created when the runtime initializes.
It is usually the only Python interpreter in a process. Unlike sub-interpreters,
the main interpreter has unique process-global responsibilities like signal
handling. It is also responsible for execution during runtime initialization and
is usually the active interpreter during runtime finalization. The
[`PyInterpreterState_Main()`](#c.PyInterpreterState_Main "PyInterpreterState_Main") function returns a pointer to its state.

You can switch between sub-interpreters using the [`PyThreadState_Swap()`](#c.PyThreadState_Swap "PyThreadState_Swap")
function. You can create and destroy them using the following functions:

type PyInterpreterConfig
:   Structure containing most parameters to configure a sub-interpreter.
    Its values are used only in [`Py_NewInterpreterFromConfig()`](#c.Py_NewInterpreterFromConfig "Py_NewInterpreterFromConfig") and
    never modified by the runtime.

    Added in version 3.12.

    Structure fields:

    int use\_main\_obmalloc
    :   If this is `0` then the sub-interpreter will use its own
        “object” allocator state.
        Otherwise it will use (share) the main interpreter’s.

        If this is `0` then
        [`check_multi_interp_extensions`](#c.PyInterpreterConfig.check_multi_interp_extensions "PyInterpreterConfig.check_multi_interp_extensions")
        must be `1` (non-zero).
        If this is `1` then [`gil`](#c.PyInterpreterConfig.gil "PyInterpreterConfig.gil")
        must not be [`PyInterpreterConfig_OWN_GIL`](#c.PyInterpreterConfig_OWN_GIL "PyInterpreterConfig_OWN_GIL").

    int allow\_fork
    :   If this is `0` then the runtime will not support forking the
        process in any thread where the sub-interpreter is currently active.
        Otherwise fork is unrestricted.

        Note that the [`subprocess`](../library/subprocess.html#module-subprocess "subprocess: Subprocess management.") module still works
        when fork is disallowed.

    int allow\_exec
    :   If this is `0` then the runtime will not support replacing the
        current process via exec (e.g. [`os.execv()`](../library/os.html#os.execv "os.execv")) in any thread
        where the sub-interpreter is currently active.
        Otherwise exec is unrestricted.

        Note that the [`subprocess`](../library/subprocess.html#module-subprocess "subprocess: Subprocess management.") module still works
        when exec is disallowed.

    int allow\_threads
    :   If this is `0` then the sub-interpreter’s [`threading`](../library/threading.html#module-threading "threading: Thread-based parallelism.") module
        won’t create threads.
        Otherwise threads are allowed.

    int allow\_daemon\_threads
    :   If this is `0` then the sub-interpreter’s [`threading`](../library/threading.html#module-threading "threading: Thread-based parallelism.") module
        won’t create daemon threads.
        Otherwise daemon threads are allowed (as long as
        [`allow_threads`](#c.PyInterpreterConfig.allow_threads "PyInterpreterConfig.allow_threads") is non-zero).

    int check\_multi\_interp\_extensions
    :   If this is `0` then all extension modules may be imported,
        including legacy (single-phase init) modules,
        in any thread where the sub-interpreter is currently active.
        Otherwise only multi-phase init extension modules
        (see [**PEP 489**](https://peps.python.org/pep-0489/)) may be imported.
        (Also see [`Py_mod_multiple_interpreters`](module.html#c.Py_mod_multiple_interpreters "Py_mod_multiple_interpreters").)

        This must be `1` (non-zero) if
        [`use_main_obmalloc`](#c.PyInterpreterConfig.use_main_obmalloc "PyInterpreterConfig.use_main_obmalloc") is `0`.

    int gil
    :   This determines the operation of the GIL for the sub-interpreter.
        It may be one of the following:

        PyInterpreterConfig\_DEFAULT\_GIL
        :   Use the default selection ([`PyInterpreterConfig_SHARED_GIL`](#c.PyInterpreterConfig_SHARED_GIL "PyInterpreterConfig_SHARED_GIL")).

        PyInterpreterConfig\_SHARED\_GIL
        :   Use (share) the main interpreter’s GIL.

        PyInterpreterConfig\_OWN\_GIL
        :   Use the sub-interpreter’s own GIL.

        If this is [`PyInterpreterConfig_OWN_GIL`](#c.PyInterpreterConfig_OWN_GIL "PyInterpreterConfig_OWN_GIL") then
        [`PyInterpreterConfig.use_main_obmalloc`](#c.PyInterpreterConfig.use_main_obmalloc "PyInterpreterConfig.use_main_obmalloc") must be `0`.

[PyStatus](init_config.html#c.PyStatus "PyStatus") Py\_NewInterpreterFromConfig([PyThreadState](#c.PyThreadState "PyThreadState") \*\*tstate\_p, const [PyInterpreterConfig](#c.PyInterpreterConfig "PyInterpreterConfig") \*config)
:   Create a new sub-interpreter. This is an (almost) totally separate environment
    for the execution of Python code. In particular, the new interpreter has
    separate, independent versions of all imported modules, including the
    fundamental modules [`builtins`](../library/builtins.html#module-builtins "builtins: The module that provides the built-in namespace."), [`__main__`](../library/__main__.html#module-__main__ "__main__: The environment where top-level code is run. Covers command-line interfaces, import-time behavior, and ``__name__ == '__main__'``.") and [`sys`](../library/sys.html#module-sys "sys: Access system-specific parameters and functions."). The
    table of loaded modules (`sys.modules`) and the module search path
    (`sys.path`) are also separate. The new environment has no `sys.argv`
    variable. It has new standard I/O stream file objects `sys.stdin`,
    `sys.stdout` and `sys.stderr` (however these refer to the same underlying
    file descriptors).

    The given *config* controls the options with which the interpreter
    is initialized.

    Upon success, *tstate\_p* will be set to the first thread state
    created in the new
    sub-interpreter. This thread state is made in the current thread state.
    Note that no actual thread is created; see the discussion of thread states
    below. If creation of the new interpreter is unsuccessful,
    *tstate\_p* is set to `NULL`;
    no exception is set since the exception state is stored in the
    current thread state and there may not be a current thread state.

    Like all other Python/C API functions, the global interpreter lock
    must be held before calling this function and is still held when it
    returns. Likewise a current thread state must be set on entry. On
    success, the returned thread state will be set as current. If the
    sub-interpreter is created with its own GIL then the GIL of the
    calling interpreter will be released. When the function returns,
    the new interpreter’s GIL will be held by the current thread and
    the previously interpreter’s GIL will remain released here.

    Added in version 3.12.

    Sub-interpreters are most effective when isolated from each other,
    with certain functionality restricted:

    ```
    PyInterpreterConfig config = {
        .use_main_obmalloc = 0,
        .allow_fork = 0,
        .allow_exec = 0,
        .allow_threads = 1,
        .allow_daemon_threads = 0,
        .check_multi_interp_extensions = 1,
        .gil = PyInterpreterConfig_OWN_GIL,
    };
    PyThreadState *tstate = NULL;
    PyStatus status = Py_NewInterpreterFromConfig(&tstate, &config);
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
    }
    ```

    Note that the config is used only briefly and does not get modified.
    During initialization the config’s values are converted into various
    [`PyInterpreterState`](#c.PyInterpreterState "PyInterpreterState") values. A read-only copy of the config
    may be stored internally on the [`PyInterpreterState`](#c.PyInterpreterState "PyInterpreterState").

    Extension modules are shared between (sub-)interpreters as follows:

    - For modules using multi-phase initialization,
      e.g. [`PyModule_FromDefAndSpec()`](module.html#c.PyModule_FromDefAndSpec "PyModule_FromDefAndSpec"), a separate module object is
      created and initialized for each interpreter.
      Only C-level static and global variables are shared between these
      module objects.
    - For modules using single-phase initialization,
      e.g. [`PyModule_Create()`](module.html#c.PyModule_Create "PyModule_Create"), the first time a particular extension
      is imported, it is initialized normally, and a (shallow) copy of its
      module’s dictionary is squirreled away.
      When the same extension is imported by another (sub-)interpreter, a new
      module is initialized and filled with the contents of this copy; the
      extension’s `init` function is not called.
      Objects in the module’s dictionary thus end up shared across
      (sub-)interpreters, which might cause unwanted behavior (see
      [Bugs and caveats](#bugs-and-caveats) below).

      Note that this is different from what happens when an extension is
      imported after the interpreter has been completely re-initialized by
      calling [`Py_FinalizeEx()`](#c.Py_FinalizeEx "Py_FinalizeEx") and [`Py_Initialize()`](#c.Py_Initialize "Py_Initialize"); in that
      case, the extension’s `initmodule` function *is* called again.
      As with multi-phase initialization, this means that only C-level static
      and global variables are shared between these modules.

[PyThreadState](#c.PyThreadState "PyThreadState") \*Py\_NewInterpreter(void)
:   *Part of the [Stable ABI](stable.html#stable).*

    Create a new sub-interpreter. This is essentially just a wrapper
    around [`Py_NewInterpreterFromConfig()`](#c.Py_NewInterpreterFromConfig "Py_NewInterpreterFromConfig") with a config that
    preserves the existing behavior. The result is an unisolated
    sub-interpreter that shares the main interpreter’s GIL, allows
    fork/exec, allows daemon threads, and allows single-phase init
    modules.

void Py\_EndInterpreter([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   *Part of the [Stable ABI](stable.html#stable).*

    Destroy the (sub-)interpreter represented by the given thread state.
    The given thread state must be the current thread state. See the
    discussion of thread states below. When the call returns,
    the current thread state is `NULL`. All thread states associated
    with this interpreter are destroyed. The global interpreter lock
    used by the target interpreter must be held before calling this
    function. No GIL is held when it returns.

    [`Py_FinalizeEx()`](#c.Py_FinalizeEx "Py_FinalizeEx") will destroy all sub-interpreters that
    haven’t been explicitly destroyed at that point.

### A Per-Interpreter GIL

Using [`Py_NewInterpreterFromConfig()`](#c.Py_NewInterpreterFromConfig "Py_NewInterpreterFromConfig") you can create
a sub-interpreter that is completely isolated from other interpreters,
including having its own GIL. The most important benefit of this
isolation is that such an interpreter can execute Python code without
being blocked by other interpreters or blocking any others. Thus a
single Python process can truly take advantage of multiple CPU cores
when running Python code. The isolation also encourages a different
approach to concurrency than that of just using threads.
(See [**PEP 554**](https://peps.python.org/pep-0554/).)

Using an isolated interpreter requires vigilance in preserving that
isolation. That especially means not sharing any objects or mutable
state without guarantees about thread-safety. Even objects that are
otherwise immutable (e.g. `None`, `(1, 5)`) can’t normally be shared
because of the refcount. One simple but less-efficient approach around
this is to use a global lock around all use of some state (or object).
Alternately, effectively immutable objects (like integers or strings)
can be made safe in spite of their refcounts by making them “immortal”.
In fact, this has been done for the builtin singletons, small integers,
and a number of other builtin objects.

If you preserve isolation then you will have access to proper multi-core
computing without the complications that come with free-threading.
Failure to preserve isolation will expose you to the full consequences
of free-threading, including races and hard-to-debug crashes.

Aside from that, one of the main challenges of using multiple isolated
interpreters is how to communicate between them safely (not break
isolation) and efficiently. The runtime and stdlib do not provide
any standard approach to this yet. A future stdlib module would help
mitigate the effort of preserving isolation and expose effective tools
for communicating (and sharing) data between interpreters.

Added in version 3.12.

### Bugs and caveats

Because sub-interpreters (and the main interpreter) are part of the same
process, the insulation between them isn’t perfect — for example, using
low-level file operations like [`os.close()`](../library/os.html#os.close "os.close") they can
(accidentally or maliciously) affect each other’s open files. Because of the
way extensions are shared between (sub-)interpreters, some extensions may not
work properly; this is especially likely when using single-phase initialization
or (static) global variables.
It is possible to insert objects created in one sub-interpreter into
a namespace of another (sub-)interpreter; this should be avoided if possible.

Special care should be taken to avoid sharing user-defined functions,
methods, instances or classes between sub-interpreters, since import
operations executed by such objects may affect the wrong (sub-)interpreter’s
dictionary of loaded modules. It is equally important to avoid sharing
objects from which the above are reachable.

Also note that combining this functionality with `PyGILState_*` APIs
is delicate, because these APIs assume a bijection between Python thread states
and OS-level threads, an assumption broken by the presence of sub-interpreters.
It is highly recommended that you don’t switch sub-interpreters between a pair
of matching [`PyGILState_Ensure()`](#c.PyGILState_Ensure "PyGILState_Ensure") and [`PyGILState_Release()`](#c.PyGILState_Release "PyGILState_Release") calls.
Furthermore, extensions (such as [`ctypes`](../library/ctypes.html#module-ctypes "ctypes: A foreign function library for Python.")) using these APIs to allow calling
of Python code from non-Python created threads will probably be broken when using
sub-interpreters.

## Asynchronous Notifications

A mechanism is provided to make asynchronous notifications to the main
interpreter thread. These notifications take the form of a function
pointer and a void pointer argument.

int Py\_AddPendingCall(int (\*func)(void\*), void \*arg)
:   *Part of the [Stable ABI](stable.html#stable).*

    Schedule a function to be called from the main interpreter thread. On
    success, `0` is returned and *func* is queued for being called in the
    main thread. On failure, `-1` is returned without setting any exception.

    When successfully queued, *func* will be *eventually* called from the
    main interpreter thread with the argument *arg*. It will be called
    asynchronously with respect to normally running Python code, but with
    both these conditions met:

    - on a [bytecode](../glossary.html#term-bytecode) boundary;
    - with the main thread holding the [global interpreter lock](../glossary.html#term-global-interpreter-lock)
      (*func* can therefore use the full C API).

    *func* must return `0` on success, or `-1` on failure with an exception
    set. *func* won’t be interrupted to perform another asynchronous
    notification recursively, but it can still be interrupted to switch
    threads if the global interpreter lock is released.

    This function doesn’t need a current thread state to run, and it doesn’t
    need the global interpreter lock.

    To call this function in a subinterpreter, the caller must hold the GIL.
    Otherwise, the function *func* can be scheduled to be called from the wrong
    interpreter.

    Warning

    This is a low-level function, only useful for very special cases.
    There is no guarantee that *func* will be called as quick as
    possible. If the main thread is busy executing a system call,
    *func* won’t be called before the system call returns. This
    function is generally **not** suitable for calling Python code from
    arbitrary C threads. Instead, use the [PyGILState API](#gilstate).

    Added in version 3.1.

    Changed in version 3.9: If this function is called in a subinterpreter, the function *func* is
    now scheduled to be called from the subinterpreter, rather than being
    called from the main interpreter. Each subinterpreter now has its own
    list of scheduled calls.

## Profiling and Tracing

The Python interpreter provides some low-level support for attaching profiling
and execution tracing facilities. These are used for profiling, debugging, and
coverage analysis tools.

This C interface allows the profiling or tracing code to avoid the overhead of
calling through Python-level callable objects, making a direct C function call
instead. The essential attributes of the facility have not changed; the
interface allows trace functions to be installed per-thread, and the basic
events reported to the trace function are the same as had been reported to the
Python-level trace functions in previous versions.

typedef int (\*Py\_tracefunc)([PyObject](structures.html#c.PyObject "PyObject") \*obj, [PyFrameObject](frame.html#c.PyFrameObject "PyFrameObject") \*frame, int what, [PyObject](structures.html#c.PyObject "PyObject") \*arg)
:   The type of the trace function registered using [`PyEval_SetProfile()`](#c.PyEval_SetProfile "PyEval_SetProfile") and
    [`PyEval_SetTrace()`](#c.PyEval_SetTrace "PyEval_SetTrace"). The first parameter is the object passed to the
    registration function as *obj*, *frame* is the frame object to which the event
    pertains, *what* is one of the constants [`PyTrace_CALL`](#c.PyTrace_CALL "PyTrace_CALL"),
    [`PyTrace_EXCEPTION`](#c.PyTrace_EXCEPTION "PyTrace_EXCEPTION"), [`PyTrace_LINE`](#c.PyTrace_LINE "PyTrace_LINE"), [`PyTrace_RETURN`](#c.PyTrace_RETURN "PyTrace_RETURN"),
    [`PyTrace_C_CALL`](#c.PyTrace_C_CALL "PyTrace_C_CALL"), [`PyTrace_C_EXCEPTION`](#c.PyTrace_C_EXCEPTION "PyTrace_C_EXCEPTION"), [`PyTrace_C_RETURN`](#c.PyTrace_C_RETURN "PyTrace_C_RETURN"),
    or [`PyTrace_OPCODE`](#c.PyTrace_OPCODE "PyTrace_OPCODE"), and *arg* depends on the value of *what*:

    | Value of *what* | Meaning of *arg* |
    | --- | --- |
    | [`PyTrace_CALL`](#c.PyTrace_CALL "PyTrace_CALL") | Always [`Py_None`](none.html#c.Py_None "Py_None"). |
    | [`PyTrace_EXCEPTION`](#c.PyTrace_EXCEPTION "PyTrace_EXCEPTION") | Exception information as returned by [`sys.exc_info()`](../library/sys.html#sys.exc_info "sys.exc_info"). |
    | [`PyTrace_LINE`](#c.PyTrace_LINE "PyTrace_LINE") | Always [`Py_None`](none.html#c.Py_None "Py_None"). |
    | [`PyTrace_RETURN`](#c.PyTrace_RETURN "PyTrace_RETURN") | Value being returned to the caller, or `NULL` if caused by an exception. |
    | [`PyTrace_C_CALL`](#c.PyTrace_C_CALL "PyTrace_C_CALL") | Function object being called. |
    | [`PyTrace_C_EXCEPTION`](#c.PyTrace_C_EXCEPTION "PyTrace_C_EXCEPTION") | Function object being called. |
    | [`PyTrace_C_RETURN`](#c.PyTrace_C_RETURN "PyTrace_C_RETURN") | Function object being called. |
    | [`PyTrace_OPCODE`](#c.PyTrace_OPCODE "PyTrace_OPCODE") | Always [`Py_None`](none.html#c.Py_None "Py_None"). |

int PyTrace\_CALL
:   The value of the *what* parameter to a [`Py_tracefunc`](#c.Py_tracefunc "Py_tracefunc") function when a new
    call to a function or method is being reported, or a new entry into a generator.
    Note that the creation of the iterator for a generator function is not reported
    as there is no control transfer to the Python bytecode in the corresponding
    frame.

int PyTrace\_EXCEPTION
:   The value of the *what* parameter to a [`Py_tracefunc`](#c.Py_tracefunc "Py_tracefunc") function when an
    exception has been raised. The callback function is called with this value for
    *what* when after any bytecode is processed after which the exception becomes
    set within the frame being executed. The effect of this is that as exception
    propagation causes the Python stack to unwind, the callback is called upon
    return to each frame as the exception propagates. Only trace functions receives
    these events; they are not needed by the profiler.

int PyTrace\_LINE
:   The value passed as the *what* parameter to a [`Py_tracefunc`](#c.Py_tracefunc "Py_tracefunc") function
    (but not a profiling function) when a line-number event is being reported.
    It may be disabled for a frame by setting [`f_trace_lines`](../reference/datamodel.html#frame.f_trace_lines "frame.f_trace_lines") to
    *0* on that frame.

int PyTrace\_RETURN
:   The value for the *what* parameter to [`Py_tracefunc`](#c.Py_tracefunc "Py_tracefunc") functions when a
    call is about to return.

int PyTrace\_C\_CALL
:   The value for the *what* parameter to [`Py_tracefunc`](#c.Py_tracefunc "Py_tracefunc") functions when a C
    function is about to be called.

int PyTrace\_C\_EXCEPTION
:   The value for the *what* parameter to [`Py_tracefunc`](#c.Py_tracefunc "Py_tracefunc") functions when a C
    function has raised an exception.

int PyTrace\_C\_RETURN
:   The value for the *what* parameter to [`Py_tracefunc`](#c.Py_tracefunc "Py_tracefunc") functions when a C
    function has returned.

int PyTrace\_OPCODE
:   The value for the *what* parameter to [`Py_tracefunc`](#c.Py_tracefunc "Py_tracefunc") functions (but not
    profiling functions) when a new opcode is about to be executed. This event is
    not emitted by default: it must be explicitly requested by setting
    [`f_trace_opcodes`](../reference/datamodel.html#frame.f_trace_opcodes "frame.f_trace_opcodes") to *1* on the frame.

void PyEval\_SetProfile([Py\_tracefunc](#c.Py_tracefunc "Py_tracefunc") func, [PyObject](structures.html#c.PyObject "PyObject") \*obj)
:   Set the profiler function to *func*. The *obj* parameter is passed to the
    function as its first parameter, and may be any Python object, or `NULL`. If
    the profile function needs to maintain state, using a different value for *obj*
    for each thread provides a convenient and thread-safe place to store it. The
    profile function is called for all monitored events except [`PyTrace_LINE`](#c.PyTrace_LINE "PyTrace_LINE")
    [`PyTrace_OPCODE`](#c.PyTrace_OPCODE "PyTrace_OPCODE") and [`PyTrace_EXCEPTION`](#c.PyTrace_EXCEPTION "PyTrace_EXCEPTION").

    See also the [`sys.setprofile()`](../library/sys.html#sys.setprofile "sys.setprofile") function.

    The caller must hold the [GIL](../glossary.html#term-GIL).

void PyEval\_SetProfileAllThreads([Py\_tracefunc](#c.Py_tracefunc "Py_tracefunc") func, [PyObject](structures.html#c.PyObject "PyObject") \*obj)
:   Like [`PyEval_SetProfile()`](#c.PyEval_SetProfile "PyEval_SetProfile") but sets the profile function in all running threads
    belonging to the current interpreter instead of the setting it only on the current thread.

    The caller must hold the [GIL](../glossary.html#term-GIL).

    As [`PyEval_SetProfile()`](#c.PyEval_SetProfile "PyEval_SetProfile"), this function ignores any exceptions raised while
    setting the profile functions in all threads.

Added in version 3.12.

void PyEval\_SetTrace([Py\_tracefunc](#c.Py_tracefunc "Py_tracefunc") func, [PyObject](structures.html#c.PyObject "PyObject") \*obj)
:   Set the tracing function to *func*. This is similar to
    [`PyEval_SetProfile()`](#c.PyEval_SetProfile "PyEval_SetProfile"), except the tracing function does receive line-number
    events and per-opcode events, but does not receive any event related to C function
    objects being called. Any trace function registered using [`PyEval_SetTrace()`](#c.PyEval_SetTrace "PyEval_SetTrace")
    will not receive [`PyTrace_C_CALL`](#c.PyTrace_C_CALL "PyTrace_C_CALL"), [`PyTrace_C_EXCEPTION`](#c.PyTrace_C_EXCEPTION "PyTrace_C_EXCEPTION") or
    [`PyTrace_C_RETURN`](#c.PyTrace_C_RETURN "PyTrace_C_RETURN") as a value for the *what* parameter.

    See also the [`sys.settrace()`](../library/sys.html#sys.settrace "sys.settrace") function.

    The caller must hold the [GIL](../glossary.html#term-GIL).

void PyEval\_SetTraceAllThreads([Py\_tracefunc](#c.Py_tracefunc "Py_tracefunc") func, [PyObject](structures.html#c.PyObject "PyObject") \*obj)
:   Like [`PyEval_SetTrace()`](#c.PyEval_SetTrace "PyEval_SetTrace") but sets the tracing function in all running threads
    belonging to the current interpreter instead of the setting it only on the current thread.

    The caller must hold the [GIL](../glossary.html#term-GIL).

    As [`PyEval_SetTrace()`](#c.PyEval_SetTrace "PyEval_SetTrace"), this function ignores any exceptions raised while
    setting the trace functions in all threads.

Added in version 3.12.

## Advanced Debugger Support

These functions are only intended to be used by advanced debugging tools.

[PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*PyInterpreterState\_Head()
:   Return the interpreter state object at the head of the list of all such objects.

[PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*PyInterpreterState\_Main()
:   Return the main interpreter state object.

[PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*PyInterpreterState\_Next([PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*interp)
:   Return the next interpreter state object after *interp* from the list of all
    such objects.

[PyThreadState](#c.PyThreadState "PyThreadState") \*PyInterpreterState\_ThreadHead([PyInterpreterState](#c.PyInterpreterState "PyInterpreterState") \*interp)
:   Return the pointer to the first [`PyThreadState`](#c.PyThreadState "PyThreadState") object in the list of
    threads associated with the interpreter *interp*.

[PyThreadState](#c.PyThreadState "PyThreadState") \*PyThreadState\_Next([PyThreadState](#c.PyThreadState "PyThreadState") \*tstate)
:   Return the next thread state object after *tstate* from the list of all such
    objects belonging to the same [`PyInterpreterState`](#c.PyInterpreterState "PyInterpreterState") object.

## Thread Local Storage Support

The Python interpreter provides low-level support for thread-local storage
(TLS) which wraps the underlying native TLS implementation to support the
Python-level thread local storage API ([`threading.local`](../library/threading.html#threading.local "threading.local")). The
CPython C level APIs are similar to those offered by pthreads and Windows:
use a thread key and functions to associate a void\* value per
thread.

The GIL does *not* need to be held when calling these functions; they supply
their own locking.

Note that `Python.h` does not include the declaration of the TLS APIs,
you need to include `pythread.h` to use thread-local storage.

Note

None of these API functions handle memory management on behalf of the
void\* values. You need to allocate and deallocate them yourself.
If the void\* values happen to be [PyObject](structures.html#c.PyObject "PyObject")\*, these
functions don’t do refcount operations on them either.

### Thread Specific Storage (TSS) API

TSS API is introduced to supersede the use of the existing TLS API within the
CPython interpreter. This API uses a new type [`Py_tss_t`](#c.Py_tss_t "Py_tss_t") instead of
int to represent thread keys.

Added in version 3.7.

See also

“A New C-API for Thread-Local Storage in CPython” ([**PEP 539**](https://peps.python.org/pep-0539/))

type Py\_tss\_t
:   This data structure represents the state of a thread key, the definition of
    which may depend on the underlying TLS implementation, and it has an
    internal field representing the key’s initialization state. There are no
    public members in this structure.

    When [Py\_LIMITED\_API](stable.html#stable) is not defined, static allocation of
    this type by [`Py_tss_NEEDS_INIT`](#c.Py_tss_NEEDS_INIT "Py_tss_NEEDS_INIT") is allowed.

Py\_tss\_NEEDS\_INIT
:   This macro expands to the initializer for [`Py_tss_t`](#c.Py_tss_t "Py_tss_t") variables.
    Note that this macro won’t be defined with [Py\_LIMITED\_API](stable.html#stable).

#### Dynamic Allocation

Dynamic allocation of the [`Py_tss_t`](#c.Py_tss_t "Py_tss_t"), required in extension modules
built with [Py\_LIMITED\_API](stable.html#stable), where static allocation of this type
is not possible due to its implementation being opaque at build time.

[Py\_tss\_t](#c.Py_tss_t "Py_tss_t") \*PyThread\_tss\_alloc()
:   *Part of the [Stable ABI](stable.html#stable) since version 3.7.*

    Return a value which is the same state as a value initialized with
    [`Py_tss_NEEDS_INIT`](#c.Py_tss_NEEDS_INIT "Py_tss_NEEDS_INIT"), or `NULL` in the case of dynamic allocation
    failure.

void PyThread\_tss\_free([Py\_tss\_t](#c.Py_tss_t "Py_tss_t") \*key)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.7.*

    Free the given *key* allocated by [`PyThread_tss_alloc()`](#c.PyThread_tss_alloc "PyThread_tss_alloc"), after
    first calling [`PyThread_tss_delete()`](#c.PyThread_tss_delete "PyThread_tss_delete") to ensure any associated
    thread locals have been unassigned. This is a no-op if the *key*
    argument is `NULL`.

    Note

    A freed key becomes a dangling pointer. You should reset the key to
    `NULL`.

#### Methods

The parameter *key* of these functions must not be `NULL`. Moreover, the
behaviors of [`PyThread_tss_set()`](#c.PyThread_tss_set "PyThread_tss_set") and [`PyThread_tss_get()`](#c.PyThread_tss_get "PyThread_tss_get") are
undefined if the given [`Py_tss_t`](#c.Py_tss_t "Py_tss_t") has not been initialized by
[`PyThread_tss_create()`](#c.PyThread_tss_create "PyThread_tss_create").

int PyThread\_tss\_is\_created([Py\_tss\_t](#c.Py_tss_t "Py_tss_t") \*key)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.7.*

    Return a non-zero value if the given [`Py_tss_t`](#c.Py_tss_t "Py_tss_t") has been initialized
    by [`PyThread_tss_create()`](#c.PyThread_tss_create "PyThread_tss_create").

int PyThread\_tss\_create([Py\_tss\_t](#c.Py_tss_t "Py_tss_t") \*key)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.7.*

    Return a zero value on successful initialization of a TSS key. The behavior
    is undefined if the value pointed to by the *key* argument is not
    initialized by [`Py_tss_NEEDS_INIT`](#c.Py_tss_NEEDS_INIT "Py_tss_NEEDS_INIT"). This function can be called
    repeatedly on the same key – calling it on an already initialized key is a
    no-op and immediately returns success.

void PyThread\_tss\_delete([Py\_tss\_t](#c.Py_tss_t "Py_tss_t") \*key)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.7.*

    Destroy a TSS key to forget the values associated with the key across all
    threads, and change the key’s initialization state to uninitialized. A
    destroyed key is able to be initialized again by
    [`PyThread_tss_create()`](#c.PyThread_tss_create "PyThread_tss_create"). This function can be called repeatedly on
    the same key – calling it on an already destroyed key is a no-op.

int PyThread\_tss\_set([Py\_tss\_t](#c.Py_tss_t "Py_tss_t") \*key, void \*value)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.7.*

    Return a zero value to indicate successfully associating a void\*
    value with a TSS key in the current thread. Each thread has a distinct
    mapping of the key to a void\* value.

void \*PyThread\_tss\_get([Py\_tss\_t](#c.Py_tss_t "Py_tss_t") \*key)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.7.*

    Return the void\* value associated with a TSS key in the current
    thread. This returns `NULL` if no value is associated with the key in the
    current thread.

### Thread Local Storage (TLS) API

Deprecated since version 3.7: This API is superseded by
[Thread Specific Storage (TSS) API](#thread-specific-storage-api).

Note

This version of the API does not support platforms where the native TLS key
is defined in a way that cannot be safely cast to `int`. On such platforms,
[`PyThread_create_key()`](#c.PyThread_create_key "PyThread_create_key") will return immediately with a failure status,
and the other TLS functions will all be no-ops on such platforms.

Due to the compatibility problem noted above, this version of the API should not
be used in new code.

int PyThread\_create\_key()
:   *Part of the [Stable ABI](stable.html#stable).*

void PyThread\_delete\_key(int key)
:   *Part of the [Stable ABI](stable.html#stable).*

int PyThread\_set\_key\_value(int key, void \*value)
:   *Part of the [Stable ABI](stable.html#stable).*

void \*PyThread\_get\_key\_value(int key)
:   *Part of the [Stable ABI](stable.html#stable).*

void PyThread\_delete\_key\_value(int key)
:   *Part of the [Stable ABI](stable.html#stable).*

void PyThread\_ReInitTLS()
:   *Part of the [Stable ABI](stable.html#stable).*
