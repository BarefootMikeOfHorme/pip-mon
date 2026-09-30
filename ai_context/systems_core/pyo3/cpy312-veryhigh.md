---
source_url: https://docs.python.org/3.12/c-api/veryhigh.html
title: The Very High Level Layer — Python 3.12.14 documentation
retrieved_utc: 2026-09-30T22:25:56Z
content_kind: upstream-documentation-verbatim
trust: >
  Official upstream documentation, quoted verbatim. NOT paraphrased. PyO3 is
  NOT installed in this project; this is reference for a planned bridge, not
  documentation of existing code.
---

# The Very High Level Layer

The functions in this chapter will let you execute Python source code given in a
file or a buffer, but they will not let you interact in a more detailed way with
the interpreter.

Several of these functions accept a start symbol from the grammar as a
parameter. The available start symbols are [`Py_eval_input`](#c.Py_eval_input "Py_eval_input"),
[`Py_file_input`](#c.Py_file_input "Py_file_input"), and [`Py_single_input`](#c.Py_single_input "Py_single_input"). These are described
following the functions which accept them as parameters.

Note also that several of these functions take FILE\* parameters. One
particular issue which needs to be handled carefully is that the `FILE`
structure for different C libraries can be different and incompatible. Under
Windows (at least), it is possible for dynamically linked extensions to actually
use different libraries, so care should be taken that FILE\* parameters
are only passed to these functions if it is certain that they were created by
the same library that the Python runtime is using.

int Py\_Main(int argc, wchar\_t \*\*argv)
:   *Part of the [Stable ABI](stable.html#stable).*

    The main program for the standard interpreter. This is made available for
    programs which embed Python. The *argc* and *argv* parameters should be
    prepared exactly as those which are passed to a C program’s `main()`
    function (converted to wchar\_t according to the user’s locale). It is
    important to note that the argument list may be modified (but the contents of
    the strings pointed to by the argument list are not). The return value will
    be `0` if the interpreter exits normally (i.e., without an exception),
    `1` if the interpreter exits due to an exception, or `2` if the parameter
    list does not represent a valid Python command line.

    Note that if an otherwise unhandled [`SystemExit`](../library/exceptions.html#SystemExit "SystemExit") is raised, this
    function will not return `1`, but exit the process, as long as
    [`PyConfig.inspect`](init_config.html#c.PyConfig.inspect "PyConfig.inspect") is zero.

int Py\_BytesMain(int argc, char \*\*argv)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.8.*

    Similar to [`Py_Main()`](#c.Py_Main "Py_Main") but *argv* is an array of bytes strings.

    Added in version 3.8.

int PyRun\_AnyFile(FILE \*fp, const char \*filename)
:   This is a simplified interface to [`PyRun_AnyFileExFlags()`](#c.PyRun_AnyFileExFlags "PyRun_AnyFileExFlags") below, leaving
    *closeit* set to `0` and *flags* set to `NULL`.

int PyRun\_AnyFileFlags(FILE \*fp, const char \*filename, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags)
:   This is a simplified interface to [`PyRun_AnyFileExFlags()`](#c.PyRun_AnyFileExFlags "PyRun_AnyFileExFlags") below, leaving
    the *closeit* argument set to `0`.

int PyRun\_AnyFileEx(FILE \*fp, const char \*filename, int closeit)
:   This is a simplified interface to [`PyRun_AnyFileExFlags()`](#c.PyRun_AnyFileExFlags "PyRun_AnyFileExFlags") below, leaving
    the *flags* argument set to `NULL`.

int PyRun\_AnyFileExFlags(FILE \*fp, const char \*filename, int closeit, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags)
:   If *fp* refers to a file associated with an interactive device (console or
    terminal input or Unix pseudo-terminal), return the value of
    [`PyRun_InteractiveLoop()`](#c.PyRun_InteractiveLoop "PyRun_InteractiveLoop"), otherwise return the result of
    [`PyRun_SimpleFile()`](#c.PyRun_SimpleFile "PyRun_SimpleFile"). *filename* is decoded from the filesystem
    encoding ([`sys.getfilesystemencoding()`](../library/sys.html#sys.getfilesystemencoding "sys.getfilesystemencoding")). If *filename* is `NULL`, this
    function uses `"???"` as the filename.
    If *closeit* is true, the file is closed before
    `PyRun_SimpleFileExFlags()` returns.

int PyRun\_SimpleString(const char \*command)
:   This is a simplified interface to [`PyRun_SimpleStringFlags()`](#c.PyRun_SimpleStringFlags "PyRun_SimpleStringFlags") below,
    leaving the [`PyCompilerFlags`](#c.PyCompilerFlags "PyCompilerFlags")\* argument set to `NULL`.

int PyRun\_SimpleStringFlags(const char \*command, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags)
:   Executes the Python source code from *command* in the [`__main__`](../library/__main__.html#module-__main__ "__main__: The environment where top-level code is run. Covers command-line interfaces, import-time behavior, and ``__name__ == '__main__'``.") module
    according to the *flags* argument. If [`__main__`](../library/__main__.html#module-__main__ "__main__: The environment where top-level code is run. Covers command-line interfaces, import-time behavior, and ``__name__ == '__main__'``.") does not already exist, it
    is created. Returns `0` on success or `-1` if an exception was raised. If
    there was an error, there is no way to get the exception information. For the
    meaning of *flags*, see below.

    Note that if an otherwise unhandled [`SystemExit`](../library/exceptions.html#SystemExit "SystemExit") is raised, this
    function will not return `-1`, but exit the process, as long as
    [`PyConfig.inspect`](init_config.html#c.PyConfig.inspect "PyConfig.inspect") is zero.

int PyRun\_SimpleFile(FILE \*fp, const char \*filename)
:   This is a simplified interface to [`PyRun_SimpleFileExFlags()`](#c.PyRun_SimpleFileExFlags "PyRun_SimpleFileExFlags") below,
    leaving *closeit* set to `0` and *flags* set to `NULL`.

int PyRun\_SimpleFileEx(FILE \*fp, const char \*filename, int closeit)
:   This is a simplified interface to [`PyRun_SimpleFileExFlags()`](#c.PyRun_SimpleFileExFlags "PyRun_SimpleFileExFlags") below,
    leaving *flags* set to `NULL`.

int PyRun\_SimpleFileExFlags(FILE \*fp, const char \*filename, int closeit, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags)
:   Similar to [`PyRun_SimpleStringFlags()`](#c.PyRun_SimpleStringFlags "PyRun_SimpleStringFlags"), but the Python source code is read
    from *fp* instead of an in-memory string. *filename* should be the name of
    the file, it is decoded from [filesystem encoding and error handler](../glossary.html#term-filesystem-encoding-and-error-handler).
    If *closeit* is true, the file is closed before
    `PyRun_SimpleFileExFlags()` returns.

    Note

    On Windows, *fp* should be opened as binary mode (e.g. `fopen(filename, "rb")`).
    Otherwise, Python may not handle script file with LF line ending correctly.

int PyRun\_InteractiveOne(FILE \*fp, const char \*filename)
:   This is a simplified interface to [`PyRun_InteractiveOneFlags()`](#c.PyRun_InteractiveOneFlags "PyRun_InteractiveOneFlags") below,
    leaving *flags* set to `NULL`.

int PyRun\_InteractiveOneFlags(FILE \*fp, const char \*filename, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags)
:   Read and execute a single statement from a file associated with an
    interactive device according to the *flags* argument. The user will be
    prompted using `sys.ps1` and `sys.ps2`. *filename* is decoded from the
    [filesystem encoding and error handler](../glossary.html#term-filesystem-encoding-and-error-handler).

    Returns `0` when the input was
    executed successfully, `-1` if there was an exception, or an error code
    from the `errcode.h` include file distributed as part of Python if
    there was a parse error. (Note that `errcode.h` is not included by
    `Python.h`, so must be included specifically if needed.)

int PyRun\_InteractiveLoop(FILE \*fp, const char \*filename)
:   This is a simplified interface to [`PyRun_InteractiveLoopFlags()`](#c.PyRun_InteractiveLoopFlags "PyRun_InteractiveLoopFlags") below,
    leaving *flags* set to `NULL`.

int PyRun\_InteractiveLoopFlags(FILE \*fp, const char \*filename, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags)
:   Read and execute statements from a file associated with an interactive device
    until EOF is reached. The user will be prompted using `sys.ps1` and
    `sys.ps2`. *filename* is decoded from the [filesystem encoding and
    error handler](../glossary.html#term-filesystem-encoding-and-error-handler). Returns `0` at EOF or a negative number upon failure.

int (\*PyOS\_InputHook)(void)
:   *Part of the [Stable ABI](stable.html#stable).*

    Can be set to point to a function with the prototype
    `int func(void)`. The function will be called when Python’s
    interpreter prompt is about to become idle and wait for user input
    from the terminal. The return value is ignored. Overriding this
    hook can be used to integrate the interpreter’s prompt with other
    event loops, as done in the `Modules/_tkinter.c` in the
    Python source code.

    Changed in version 3.12: This function is only called from the
    [main interpreter](init.html#sub-interpreter-support).

char \*(\*PyOS\_ReadlineFunctionPointer)(FILE\*, FILE\*, const char\*)
:   Can be set to point to a function with the prototype
    `char *func(FILE *stdin, FILE *stdout, char *prompt)`,
    overriding the default function used to read a single line of input
    at the interpreter’s prompt. The function is expected to output
    the string *prompt* if it’s not `NULL`, and then read a line of
    input from the provided standard input file, returning the
    resulting string. For example, The [`readline`](../library/readline.html#module-readline "readline: GNU readline support for Python. (Unix)") module sets
    this hook to provide line-editing and tab-completion features.

    The result must be a string allocated by [`PyMem_RawMalloc()`](memory.html#c.PyMem_RawMalloc "PyMem_RawMalloc") or
    [`PyMem_RawRealloc()`](memory.html#c.PyMem_RawRealloc "PyMem_RawRealloc"), or `NULL` if an error occurred.

    Changed in version 3.4: The result must be allocated by [`PyMem_RawMalloc()`](memory.html#c.PyMem_RawMalloc "PyMem_RawMalloc") or
    [`PyMem_RawRealloc()`](memory.html#c.PyMem_RawRealloc "PyMem_RawRealloc"), instead of being allocated by
    [`PyMem_Malloc()`](memory.html#c.PyMem_Malloc "PyMem_Malloc") or [`PyMem_Realloc()`](memory.html#c.PyMem_Realloc "PyMem_Realloc").

    Changed in version 3.12: This function is only called from the
    [main interpreter](init.html#sub-interpreter-support).

[PyObject](structures.html#c.PyObject "PyObject") \*PyRun\_String(const char \*str, int start, [PyObject](structures.html#c.PyObject "PyObject") \*globals, [PyObject](structures.html#c.PyObject "PyObject") \*locals)
:   *Return value: New reference.*

    This is a simplified interface to [`PyRun_StringFlags()`](#c.PyRun_StringFlags "PyRun_StringFlags") below, leaving
    *flags* set to `NULL`.

[PyObject](structures.html#c.PyObject "PyObject") \*PyRun\_StringFlags(const char \*str, int start, [PyObject](structures.html#c.PyObject "PyObject") \*globals, [PyObject](structures.html#c.PyObject "PyObject") \*locals, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags)
:   *Return value: New reference.*

    Execute Python source code from *str* in the context specified by the
    objects *globals* and *locals* with the compiler flags specified by
    *flags*. *globals* must be a dictionary; *locals* can be any object
    that implements the mapping protocol. The parameter *start* specifies
    the start token that should be used to parse the source code.

    Returns the result of executing the code as a Python object, or `NULL` if an
    exception was raised.

[PyObject](structures.html#c.PyObject "PyObject") \*PyRun\_File(FILE \*fp, const char \*filename, int start, [PyObject](structures.html#c.PyObject "PyObject") \*globals, [PyObject](structures.html#c.PyObject "PyObject") \*locals)
:   *Return value: New reference.*

    This is a simplified interface to [`PyRun_FileExFlags()`](#c.PyRun_FileExFlags "PyRun_FileExFlags") below, leaving
    *closeit* set to `0` and *flags* set to `NULL`.

[PyObject](structures.html#c.PyObject "PyObject") \*PyRun\_FileEx(FILE \*fp, const char \*filename, int start, [PyObject](structures.html#c.PyObject "PyObject") \*globals, [PyObject](structures.html#c.PyObject "PyObject") \*locals, int closeit)
:   *Return value: New reference.*

    This is a simplified interface to [`PyRun_FileExFlags()`](#c.PyRun_FileExFlags "PyRun_FileExFlags") below, leaving
    *flags* set to `NULL`.

[PyObject](structures.html#c.PyObject "PyObject") \*PyRun\_FileFlags(FILE \*fp, const char \*filename, int start, [PyObject](structures.html#c.PyObject "PyObject") \*globals, [PyObject](structures.html#c.PyObject "PyObject") \*locals, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags)
:   *Return value: New reference.*

    This is a simplified interface to [`PyRun_FileExFlags()`](#c.PyRun_FileExFlags "PyRun_FileExFlags") below, leaving
    *closeit* set to `0`.

[PyObject](structures.html#c.PyObject "PyObject") \*PyRun\_FileExFlags(FILE \*fp, const char \*filename, int start, [PyObject](structures.html#c.PyObject "PyObject") \*globals, [PyObject](structures.html#c.PyObject "PyObject") \*locals, int closeit, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags)
:   *Return value: New reference.*

    Similar to [`PyRun_StringFlags()`](#c.PyRun_StringFlags "PyRun_StringFlags"), but the Python source code is read from
    *fp* instead of an in-memory string. *filename* should be the name of the file,
    it is decoded from the [filesystem encoding and error handler](../glossary.html#term-filesystem-encoding-and-error-handler).
    If *closeit* is true, the file is closed before [`PyRun_FileExFlags()`](#c.PyRun_FileExFlags "PyRun_FileExFlags")
    returns.

[PyObject](structures.html#c.PyObject "PyObject") \*Py\_CompileString(const char \*str, const char \*filename, int start)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    This is a simplified interface to [`Py_CompileStringFlags()`](#c.Py_CompileStringFlags "Py_CompileStringFlags") below, leaving
    *flags* set to `NULL`.

[PyObject](structures.html#c.PyObject "PyObject") \*Py\_CompileStringFlags(const char \*str, const char \*filename, int start, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags)
:   *Return value: New reference.*

    This is a simplified interface to [`Py_CompileStringExFlags()`](#c.Py_CompileStringExFlags "Py_CompileStringExFlags") below, with
    *optimize* set to `-1`.

[PyObject](structures.html#c.PyObject "PyObject") \*Py\_CompileStringObject(const char \*str, [PyObject](structures.html#c.PyObject "PyObject") \*filename, int start, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags, int optimize)
:   *Return value: New reference.*

    Parse and compile the Python source code in *str*, returning the resulting code
    object. The start token is given by *start*; this can be used to constrain the
    code which can be compiled and should be [`Py_eval_input`](#c.Py_eval_input "Py_eval_input"),
    [`Py_file_input`](#c.Py_file_input "Py_file_input"), or [`Py_single_input`](#c.Py_single_input "Py_single_input"). The filename specified by
    *filename* is used to construct the code object and may appear in tracebacks or
    [`SyntaxError`](../library/exceptions.html#SyntaxError "SyntaxError") exception messages. This returns `NULL` if the code
    cannot be parsed or compiled.

    The integer *optimize* specifies the optimization level of the compiler; a
    value of `-1` selects the optimization level of the interpreter as given by
    [`-O`](../using/cmdline.html#cmdoption-O) options. Explicit levels are `0` (no optimization;
    `__debug__` is true), `1` (asserts are removed, `__debug__` is false)
    or `2` (docstrings are removed too).

    Added in version 3.4.

[PyObject](structures.html#c.PyObject "PyObject") \*Py\_CompileStringExFlags(const char \*str, const char \*filename, int start, [PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*flags, int optimize)
:   *Return value: New reference.*

    Like [`Py_CompileStringObject()`](#c.Py_CompileStringObject "Py_CompileStringObject"), but *filename* is a byte string
    decoded from the [filesystem encoding and error handler](../glossary.html#term-filesystem-encoding-and-error-handler).

    Added in version 3.2.

[PyObject](structures.html#c.PyObject "PyObject") \*PyEval\_EvalCode([PyObject](structures.html#c.PyObject "PyObject") \*co, [PyObject](structures.html#c.PyObject "PyObject") \*globals, [PyObject](structures.html#c.PyObject "PyObject") \*locals)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    This is a simplified interface to [`PyEval_EvalCodeEx()`](#c.PyEval_EvalCodeEx "PyEval_EvalCodeEx"), with just
    the code object, and global and local variables. The other arguments are
    set to `NULL`.

[PyObject](structures.html#c.PyObject "PyObject") \*PyEval\_EvalCodeEx([PyObject](structures.html#c.PyObject "PyObject") \*co, [PyObject](structures.html#c.PyObject "PyObject") \*globals, [PyObject](structures.html#c.PyObject "PyObject") \*locals, [PyObject](structures.html#c.PyObject "PyObject") \*const \*args, int argcount, [PyObject](structures.html#c.PyObject "PyObject") \*const \*kws, int kwcount, [PyObject](structures.html#c.PyObject "PyObject") \*const \*defs, int defcount, [PyObject](structures.html#c.PyObject "PyObject") \*kwdefs, [PyObject](structures.html#c.PyObject "PyObject") \*closure)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    Evaluate a precompiled code object, given a particular environment for its
    evaluation. This environment consists of a dictionary of global variables,
    a mapping object of local variables, arrays of arguments, keywords and
    defaults, a dictionary of default values for [keyword-only](../glossary.html#keyword-only-parameter) arguments and a closure tuple of cells.

[PyObject](structures.html#c.PyObject "PyObject") \*PyEval\_EvalFrame([PyFrameObject](frame.html#c.PyFrameObject "PyFrameObject") \*f)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    Evaluate an execution frame. This is a simplified interface to
    [`PyEval_EvalFrameEx()`](#c.PyEval_EvalFrameEx "PyEval_EvalFrameEx"), for backward compatibility.

[PyObject](structures.html#c.PyObject "PyObject") \*PyEval\_EvalFrameEx([PyFrameObject](frame.html#c.PyFrameObject "PyFrameObject") \*f, int throwflag)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    This is the main, unvarnished function of Python interpretation. The code
    object associated with the execution frame *f* is executed, interpreting
    bytecode and executing calls as needed. The additional *throwflag*
    parameter can mostly be ignored - if true, then it causes an exception
    to immediately be thrown; this is used for the [`throw()`](../reference/expressions.html#generator.throw "generator.throw")
    methods of generator objects.

    Changed in version 3.4: This function now includes a debug assertion to help ensure that it
    does not silently discard an active exception.

int PyEval\_MergeCompilerFlags([PyCompilerFlags](#c.PyCompilerFlags "PyCompilerFlags") \*cf)
:   This function changes the flags of the current evaluation frame, and returns
    true on success, false on failure.

int Py\_eval\_input
:   The start symbol from the Python grammar for isolated expressions; for use with
    [`Py_CompileString()`](#c.Py_CompileString "Py_CompileString").

int Py\_file\_input
:   The start symbol from the Python grammar for sequences of statements as read
    from a file or other source; for use with [`Py_CompileString()`](#c.Py_CompileString "Py_CompileString"). This is
    the symbol to use when compiling arbitrarily long Python source code.

int Py\_single\_input
:   The start symbol from the Python grammar for a single statement; for use with
    [`Py_CompileString()`](#c.Py_CompileString "Py_CompileString"). This is the symbol used for the interactive
    interpreter loop.

struct PyCompilerFlags
:   This is the structure used to hold compiler flags. In cases where code is only
    being compiled, it is passed as `int flags`, and in cases where code is being
    executed, it is passed as `PyCompilerFlags *flags`. In this case, `from
    __future__ import` can modify *flags*.

    Whenever `PyCompilerFlags *flags` is `NULL`, [`cf_flags`](#c.PyCompilerFlags.cf_flags "PyCompilerFlags.cf_flags") is treated as
    equal to `0`, and any modification due to `from __future__ import` is
    discarded.

    int cf\_flags
    :   Compiler flags.

    int cf\_feature\_version
    :   *cf\_feature\_version* is the minor Python version. It should be
        initialized to `PY_MINOR_VERSION`.

        The field is ignored by default, it is used if and only if
        `PyCF_ONLY_AST` flag is set in [`cf_flags`](#c.PyCompilerFlags.cf_flags "PyCompilerFlags.cf_flags").

    Changed in version 3.8: Added *cf\_feature\_version* field.

int CO\_FUTURE\_DIVISION
:   This bit can be set in *flags* to cause division operator `/` to be
    interpreted as “true division” according to [**PEP 238**](https://peps.python.org/pep-0238/).
