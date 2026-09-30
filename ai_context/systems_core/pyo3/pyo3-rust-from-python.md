---
source_url: https://pyo3.rs/main/rust-from-python.html
title: Using Rust from Python - PyO3 user guide
retrieved_utc: 2026-09-30T22:25:56Z
content_kind: upstream-documentation-verbatim
trust: >
  Official upstream documentation, quoted verbatim. NOT paraphrased. PyO3 is
  NOT installed in this project; this is reference for a planned bridge, not
  documentation of existing code.
---

# [Using Rust from Python](#using-rust-from-python)

This chapter of the guide is dedicated to explaining how to wrap Rust code into Python objects.

PyO3 uses Rust’s “procedural macros” to provide a powerful yet simple API to denote what Rust code should map into Python objects.

PyO3 can create three types of Python objects:

* Python modules, via the `#[pymodule]` macro
* Python functions, via the `#[pyfunction]` macro
* Python classes, via the `#[pyclass]` macro (plus `#[pymethods]` to define methods for those classes)

The following subchapters go through each of these in turn.
