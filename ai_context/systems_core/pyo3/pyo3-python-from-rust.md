---
source_url: https://pyo3.rs/main/python-from-rust.html
title: Calling Python from Rust - PyO3 user guide
retrieved_utc: 2026-09-30T22:25:56Z
content_kind: upstream-documentation-verbatim
trust: >
  Official upstream documentation, quoted verbatim. NOT paraphrased. PyO3 is
  NOT installed in this project; this is reference for a planned bridge, not
  documentation of existing code.
---

# [Calling Python in Rust code](#calling-python-in-rust-code)

This chapter of the guide documents some ways to interact with Python code from Rust.

Below is an introduction to the `'py` lifetime and some general remarks about how PyO3’s API reasons about Python code.

The subchapters also cover the following topics:

* Python object types available in PyO3’s API
* How to work with Python exceptions
* How to call Python functions
* How to execute existing Python code

## [The `'py` lifetime](#the-py-lifetime)

To safely interact with the Python interpreter a Rust thread must be [[attached](/main/glossary#attached)] to the Python interpreter.
PyO3 has a `Python<'py>` token that is used to prove that these conditions are met.
Its lifetime `'py` is a central part of PyO3’s API.

The `Python<'py>` token serves three purposes:

* It provides global APIs for the Python interpreter, such as [`py.eval()`](https://pyo3.rs/main/doc/pyo3/marker/struct.python#method.eval) and [`py.import()`](https://pyo3.rs/main/doc/pyo3/marker/struct.python#method.import).
* It can be passed to functions that require a proof of attachment, such as [`Py::clone_ref`](https://pyo3.rs/main/doc/pyo3/prelude/struct.py#method.clone_ref).
* Its lifetime `'py` is used to bind many of PyO3’s types to the Python interpreter, such as [`Bound<'py, T>`](https://pyo3.rs/main/doc/pyo3/struct.bound).

PyO3’s types that are bound to the `'py` lifetime, for example `Bound<'py, T>`, all contain a `Python<'py>` token.
This means they have full access to the Python interpreter and offer a complete API for interacting with Python objects.

Consult [PyO3’s API documentation](https://pyo3.rs/main/doc/pyo3/marker/struct.python#obtaining-a-python-token) to learn how to acquire one of these tokens.

### [The Global Interpreter Lock](#the-global-interpreter-lock)

Prior to the introduction of [free-threaded Python](https://docs.python.org/3/glossary.html#term-free-threaded-build) (first available in 3.13, fully supported in 3.14), the Python interpreter was made thread-safe by the [global interpreter lock](https://docs.python.org/3/glossary.html#term-global-interpreter-lock).
This ensured that only one Python thread can use the Python interpreter and its API at the same time.
Historically, Rust code was able to use the [GIL](https://docs.python.org/3/glossary.html#term-GIL) as a synchronization guarantee, but the introduction of free-threaded Python removed this possibility.

The [`pyo3::sync`](https://pyo3.rs/main/doc/pyo3/sync/) module offers synchronization tools which abstract over both Python builds.

To enable any parallelism on the GIL-enabled build, and best throughput on the free-threaded build, non-Python operations (system calls and native Rust code) should consider detaching from the Python interpreter to allow other work to proceed.
See [the section on parallelism](/main/parallelism) for how to do that using PyO3’s API.

## [Python’s memory model](#pythons-memory-model)

Python’s memory model differs from Rust’s memory model in two key ways:

* There is no concept of ownership; all Python objects are shared and usually implemented via reference counting
* There is no concept of exclusive (`&mut`) references; any reference can mutate a Python object

PyO3’s API reflects this by providing [smart pointer](/main/glossary#smart-pointer) types, `Py<T>`, `Bound<'py, T>`, and (the very rarely used) `Borrowed<'a, 'py, T>`.
These smart pointers all use Python reference counting.
See the [subchapter on types](/main/types) for more detail on these types.

Because of the lack of exclusive `&mut` references, PyO3’s APIs for Python objects, for example [`PyListMethods::append`](https://pyo3.rs/main/doc/pyo3/types/trait.pylistmethods#tymethod.append), use shared references.
This is safe because Python objects have internal mechanisms to prevent [data races](https://docs.python.org/3/glossary.html#term-data-race) (as of time of writing, the Python GIL).
