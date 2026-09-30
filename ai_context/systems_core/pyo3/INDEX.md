---
title: PyO3 + CPython 3.12 C-API reference corpus - index
generated_utc: 2026-09-30T22:25:56Z
content_kind: fetch-index-with-prose
trust: >
  This INDEX.md is the ONLY file in this directory containing authored prose.
  Every other .md file here is an unmodified capture of upstream documentation
  and must be quoted, not summarized. PyO3 is NOT installed in this project;
  this material is reference for a PLANNED bridge, not documentation of
  existing code. Nothing here describes working, verified code.
---

# PyO3 / CPython 3.12 C-API reference corpus

## prose

This directory holds verbatim captures of upstream reference documentation for a
**planned** Rust/Python bridge. It was assembled by fetching the URLs listed below
and converting each page's HTML body to Markdown without editing, reordering,
correcting, or paraphrasing any text.

This is the **second** capture pass. The first pass fetched ten URLs; five of them
returned HTTP 404 upstream and were never captured. A follow-up pass resolved the
corrected PyO3 book paths (the book was restructured and is now served per-version
under `/main/...`) and captured the missing chapters, plus two CPython pages. The
14 documentation files below are therefore the union of all three passes. No
placeholder file was ever created for a failed URL.

A **third pass** attempted to close the type-conversion gap and to answer the
GIL question. One of its two URLs was dead: the presumed `gil.html` chapter does
not exist at `/main/gil.html` or at `/gil.html`. The other, `conversions.html`,
was captured but turned out to be a landing page rather than the conversion
reference, so that gap is **still open** - see the gap status update below.

A later session must not infer API details from this index, and must not assume
that a page listed here has been read: each file is the authoritative source.

### Method notes

- Bodies were rendered from the page's main content container, excluding
  navigation, scripts, styles and header anchor links. For `docs.python.org` that
  container is `div[role=main]` (which excludes the right-hand sidebar); for the
  PyO3 book it is `main`.
- HTML was fetched as **raw bytes and decoded as UTF-8 explicitly**, never via a
  client's own charset guess. The `docs.python.org` server returns
  `Content-Type: text/html` with **no `charset` parameter** and only declares
  UTF-8 via a `<meta charset>` tag, so a naive text fetch decodes as latin-1 and
  produces mojibake: the apostrophe in "don't hold the GIL" becomes a three-byte
  sequence misread as the single character U+00E2 (a-circumflex) followed by
  U+0080 and U+0099. Every saved file was audited
  afterwards for U+FFFD and for those U+00E2-based byte-sequence families;
  all are clean.
- Rust code samples were re-verified byte-for-byte against the `<pre>` text of the
  source HTML. The HTML-to-Markdown converter re-indents `<pre>` elements nested
  inside list items, which silently corrupts Rust samples; `pyo3-function.md` was
  affected and every fenced block in it was restored to its exact source bytes.
- `bytes` below is the on-disk size of the saved file, which includes the YAML
  frontmatter in addition to the verbatim body.

## files

| file | source URL | what it covers | bytes |
| --- | --- | --- | --- |
| `pyo3-index.md` | https://pyo3.rs/ | PyO3 user guide landing page and project README: stated Rust/Python version requirements, supported Python distributions, first-steps `maturin` workflow for calling Rust from Python, embedding Python into a Rust binary via `Python::attach`, `auto-initialize` feature, tools/libraries and examples lists, license | 21376 |
| `pyo3-class.md` | https://pyo3.rs/main/class.html | **The `#[pyclass]` reference.** Defining a class, the requirement that classes be `Send` + `Sync`, constructor via `#[new]`, initializer `__init__`, `frozen` classes and opting out of interior mutability, the full `#[pyclass(...)]` parameter table, adding the class to a module via `#[pymodule]`, inheritance and `extends`, object properties via `#[pyo3(get, set)]`, instance/class/static methods, class attributes, classes as function arguments, `#[pyclass]` enums, implementation details | 56833 |
| `pyo3-python-from-rust.md` | https://pyo3.rs/main/python-from-rust.html | Calling Python from Rust: the `'py` lifetime and Python's memory model | 4385 |
| `pyo3-rust-from-python.md` | https://pyo3.rs/main/rust-from-python.html | Short by-design chapter landing page introducing the `#[pymodule]` / `#[pyfunction]` / `#[pyclass]` (+ `#[pymethods]`) macros and listing the subchapters. By design only a few sentences; not a stub and not truncated | 987 |
| `pyo3-types.md` | https://pyo3.rs/main/types.html | Python object **types** (not the conversion table): PyO3's three smart pointers `Py<T>`, `Bound<'py, T>` and `Borrowed<'a, 'py, T>`, when to use each, function-argument lifetimes, casting between smart pointer types; then the concrete Python types that fill in the `T` parameter (`PyAny`, `PyList`, `PyDict`, `PyTuple`, user `#[pyclass]` types), using APIs for concrete types, casting between Python object types, and extracting Rust data from Python objects | 17856 |
| `pyo3-function.md` | https://pyo3.rs/main/function.html | Python functions: defining functions with `#[pyfunction]`, returning `PyResult`, function options (`#[pyo3(...)]`), per-argument options, `#[pyo3(signature = ...)]`, and advanced function patterns | 10983 |
| `pyo3-features.md` | https://pyo3.rs/main/features.html | Cargo feature reference: features selecting the target ABI (`abi3`, `Py_LIMITED_API`), features for embedding Python in Rust, advanced features (e.g. `multiple-pymethods`), optional dependencies, and deprecated features for extension-module authors | 20976 |
| `cpy312-init.md` | https://docs.python.org/3.12/c-api/init.html | Interpreter initialization/finalization, `Py_Initialize`/`Py_Finalize`, thread state and the GIL, releasing the GIL from extension code, the PyGILState API, sub-interpreters, per-interpreter GIL configuration, `PyConfig` | 103347 |
| `cpy312-intro.md` | https://docs.python.org/3.12/c-api/intro.html | C-API introduction: headers, conventions, return/error handling, `PyDoc_STRVAR` and friends, inclusion/linking macros, examples | 37057 |
| `cpy312-object.md` | https://docs.python.org/3.12/c-api/object.html | Object Protocol: `Py_NotImplemented` / `Py_RETURN_NOTIMPLEMENTED` / `Py_PRINT_RAW` / `PyObject_Print`, the generic attribute functions (`PyObject_GetAttr`/`SetAttr`/`DelAttr`/`HasAttr` and their `String` and `Generic` variants, plus the `__dict__` functions), comparison (`PyObject_RichCompare`, `PyObject_RichCompareBool`), `PyObject_Format`, `PyObject_Repr`/`ASCII`/`Str`/`Bytes`, type checks (`PyObject_Type`, `PyObject_TypeCheck`, `PyObject_IsInstance`, `PyObject_IsSubclass`), hashing (`PyObject_Hash`, `PyObject_HashNotImplemented`), truth tests (`PyObject_IsTrue`, `PyObject_Not`), `PyObject_Length`/`LengthHint`, item access (`PyObject_GetItem`/`SetItem`/`DelItem`/`DelItemString`), `PyObject_Dir`, the iteration functions, and type-data accessors | 28276 |
| `cpy312-abstract.md` | https://docs.python.org/3.12/c-api/abstract.html | Abstract Objects Layer chapter landing page: the introductory note that these functions work across object types and raise for inapplicable types, plus the index of object/call/number/sequence/mapping/iterator/buffer protocol chapters (a short by-design index page, not a stub) | 2319 |
| `cpy312-refcounting.md` | https://docs.python.org/3.12/c-api/refcounting.html | Reference counting: reference counts, `Py_INCREF`/`Py_DECREF`/`Py_XDECREF`, `Py_REFCNT`, weak references, immortal objects, debug and free-threading notes | 9140 |
| `pyo3-conversions.md` | https://pyo3.rs/main/conversions.html | Chapter landing page for the type-conversion section of the guide. Short by design: one paragraph stating the section covers the mapping of Python types to Rust types and the traits for converting between them, then a pointer to the conversion `tables` and `traits` pages. **The `IntoPy`/`FromPyObject`/`IntoPyObject` rules are NOT in this file** - the book moved them to the two sub-pages it links (see the gap note) | 697 |
| `cpy312-veryhigh.md` | https://docs.python.org/3.12/c-api/veryhigh.html | The Very High Level Layer: embedding and driving the interpreter from a host program - `Py_Main` and `Py_BytesMain`, the `PyRun_AnyFile*` / `PyRun_SimpleString*` / `PyRun_SimpleFile*` / `PyRun_InteractiveOne*` / `PyRun_InteractiveLoop*` families, the `PyOS_InputHook` and `PyOS_ReadlineFunctionPointer` globals, the older `PyRun_String*` / `PyRun_File*` family, `Py_CompileString*`, `PyEval_EvalCode`/`PyEval_EvalCodeEx`/`PyEval_EvalFrame`/`PyEval_EvalFrameEx`, `PyEval_MergeCompilerFlags`, the `Py_eval_input` / `Py_file_input` / `Py_single_input` start symbols, and the `PyCompilerFlags` struct with its `CO_*` flags | 21654 |

`INDEX.md` is this file and is deliberately omitted from the table above: its own
size cannot be stated inside itself. Its size on disk is whatever `ls` reports.

## original-404-urls (IMPORTANT - do not retry these)

This section records **which of the ORIGINAL ten requested URLs were genuinely
gone upstream**, so a later session does not rediscover this by trial and error.
All five were re-verified as HTTP 404 on 2026-09-30 with `curl -L` following
redirects, so the failures are upstream and permanent, not client artifacts.

| original URL | status | replacement that now works | captured as |
| --- | --- | --- | --- |
| https://pyo3.rs/pyclass.html | **404 Not Found** | https://pyo3.rs/main/class.html | `pyo3-class.md` |
| https://pyo3.rs/misc.html | **404 Not Found** | *no single replacement* - the chapter was split up. The relevant pieces are now `class.html`, `types.html`, `function.html`, `python-from-rust.html`, `rust-from-python.html` and `features.html`, all under `/main/` | see `files` table above |
| https://pyo3.rs/conversions/table.html | **404 Not Found** | https://pyo3.rs/main/conversions.html (page title "Type conversions - PyO3 user guide") - **not captured here**, see the gap note below | *not captured* |
| https://pyo3.rs/features.html | **404 Not Found** | https://pyo3.rs/main/features.html | `pyo3-features.md` |
| https://docs.python.org/3.12/c-api/obj.html | **404 Not Found** | https://docs.python.org/3.12/c-api/object.html | `cpy312-object.md` |

### third-pass 404: `gil.html` is dead too

Requested in the third pass on the belief that a GIL chapter existed at
`https://pyo3.rs/main/gil.html`. It does not:

| URL | status | what replaced it | captured as |
| --- | --- | --- | --- |
| https://pyo3.rs/main/gil.html | **404 Not Found** | https://pyo3.rs/main/class/thread-safety.html ("Thread safety - PyO3 user guide") - the thread-safety chapter is about `#[pyclass]` thread safety, **not** a GIL chapter | *not captured* |
| https://pyo3.rs/gil.html | **404 Not Found** | same as above | *not captured* |

No placeholder file was written for `gil.html`, and
`class/thread-safety.html` was **not** fetched in its place, because that page
does not answer the question the request was aimed at. `pyo3-class.md:154`
defers to it with "There is a [detailed discussion on
thread-safety](/main/class/thread-safety) later in the guide", and that
discussion is about making `#[pyclass]` types `Send`/`Sync` and locking. Its
only two occurrences of "GIL" are a passing mention of
`MutexGuardMixin::lock_py_attached` "that avoids deadlocks with the GIL". The
page contains no occurrence of `detach` or `allow_threads`, and never states
whether PyO3 releases the GIL automatically.

**Do not conclude from this corpus that PyO3 does or does not release the GIL.**
This corpus contains no authoritative statement about it. The PyO3 guide's
`/main/python-from-rust/calling-existing-code` sub-chapter (linked as the
*previous* chapter of `conversions.html`, and therefore the likely home of
`detach`/`allow_threads` documentation) is live but **not captured**.

Why they are gone, in short:

- The PyO3 book was restructured and is now served **per version under a
  `/main/` prefix**. Bare paths like `pyo3.rs/pyclass.html` no longer exist; the
  version must be in the path. `pyclass.html` also gained the `class/` chapter
  family (e.g. `class/thread-safety`, `class/protocols.html`) referenced from
  the pages captured here.
- On `docs.python.org` the chapter is named `object.html`, not `obj.html`.
  (`objbuffer.html` is a genuinely different, still-live chapter - the old
  buffer protocol - and must not be confused with it.)

Consequences for a future session:

- Do **not** retry the five URLs in the table above; they will 404 again.
- If a PyO3 page 404s, check whether the correct form is
  `https://pyo3.rs/main/<chapter>.html` before concluding the page is missing.
- Note that internal links inside the captured PyO3 files mix `/main/...`,
  `/latest/...` and relative forms, because the book rewrites them per version.
  Resolve them against `/main/`, not `/latest/`.
- Re-verify before trusting this table: upstream docs move, and a future session
  should not treat a URL as permanently dead if it 404s today.

### gap STATUS UPDATE: `conversions.html` fetched, but the gap is only half closed

`pyo3-types.md` was initially assumed to be the replacement for the dead
`conversions/table.html`. **It is not.** `types.html` covers Python object types
and PyO3's smart pointers; the conversion reference is a different page.

`https://pyo3.rs/main/conversions.html` was fetched in the third pass and is
captured as `pyo3-conversions.md`. **However, that page is a two-paragraph
chapter landing page, not the conversion reference.** Its entire body is a
heading, one sentence of prose, and this link pair:

> See also the conversion [tables](/main/conversions/tables) and [traits](/main/conversions/traits).

The book was split again: the actual reference now lives one level down, at two
URLs verified live (HTTP 200) on 2026-09-30 but **not captured**:

- **https://pyo3.rs/main/conversions/traits** - "Conversion traits - PyO3 user guide".
  This is the page expected to hold the `IntoPy` / `FromPyObject` /
  `IntoPyObject` trait rules, lifetimes and `Borrow`.
- **https://pyo3.rs/main/conversions/tables** - "Mapping of Rust types to
  Python types - PyO3 user guide". The Rust-type-to-Python-type mapping table.

So **this corpus still cannot answer questions about the Rust <-> Python
`IntoPy`/`FromPyObject`/`IntoPyObject` conversion rules.** `pyo3-types.md` only
touches conversion indirectly, in its closing section "Extracting Rust data from
Python objects", and `pyo3-conversions.md` contains no trait rules at all.
Do not reconstruct the conversion table or the trait rules from memory; fetch
`/main/conversions/traits`.

Two other pages referenced from the captured material were verified live but are
also **not captured**: `https://pyo3.rs/main/class/thread-safety.html` (see the
third-pass 404 entry above for why it was not fetched) and
`https://pyo3.rs/main/class/protocols.html`.

## failures

No fetch in the second pass failed. All eight URLs requested in the second pass
returned HTTP 200 and were captured. The five failures belong to the first pass
and are recorded in the `original-404-urls` section above rather than duplicated
here.

In the **third pass**, 1 of the 2 requested URLs failed:
`https://pyo3.rs/main/gil.html` returned **404 Not Found** (verified twice with
redirects followed; `https://pyo3.rs/gil.html` also 404s). It is recorded under
the third-pass 404 entry above. No placeholder file was created for it.
`https://pyo3.rs/main/conversions.html` returned HTTP 200 and was captured as
`pyo3-conversions.md`.

## truncation

No page was truncated. The largest body, `cpy312-init.md` at 102920 bytes, is
well under the 400 KB limit, so no file carries a truncation marker. Every saved
file is complete. Two pages are short by design rather than truncated:
`pyo3-rust-from-python.md` (987 bytes) is a chapter landing page, and
`cpy312-abstract.md` (2319 bytes) is an index page.
