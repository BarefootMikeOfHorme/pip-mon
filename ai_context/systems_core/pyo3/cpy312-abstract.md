---
source_url: https://docs.python.org/3.12/c-api/abstract.html
title: Abstract Objects Layer — Python 3.12.14 documentation
retrieved_utc: 2026-09-30T22:16:43Z
content_kind: upstream-documentation-verbatim
trust: >
  Official upstream documentation, quoted verbatim. NOT paraphrased. PyO3 is
  NOT installed in this project; this is reference for a planned bridge, not
  documentation of existing code.
---

# Abstract Objects Layer

The functions in this chapter interact with Python objects regardless of their
type, or with wide classes of object types (e.g. all numerical types, or all
sequence types). When used on object types for which they do not apply, they
will raise a Python exception.

It is not possible to use these functions on objects that are not properly
initialized, such as a list object that has been created by [`PyList_New()`](list.html#c.PyList_New "PyList_New"),
but whose items have not been set to some non-`NULL` value yet.

- [Object Protocol](object.html)
- [Call Protocol](call.html)
  - [The *tp\_call* Protocol](call.html#the-tp-call-protocol)
  - [The Vectorcall Protocol](call.html#the-vectorcall-protocol)
    - [Recursion Control](call.html#recursion-control)
    - [Vectorcall Support API](call.html#vectorcall-support-api)
  - [Object Calling API](call.html#object-calling-api)
  - [Call Support API](call.html#call-support-api)
- [Number Protocol](number.html)
- [Sequence Protocol](sequence.html)
- [Mapping Protocol](mapping.html)
- [Iterator Protocol](iter.html)
- [Buffer Protocol](buffer.html)
  - [Buffer structure](buffer.html#buffer-structure)
  - [Buffer request types](buffer.html#buffer-request-types)
    - [request-independent fields](buffer.html#request-independent-fields)
    - [readonly, format](buffer.html#readonly-format)
    - [shape, strides, suboffsets](buffer.html#shape-strides-suboffsets)
    - [contiguity requests](buffer.html#contiguity-requests)
    - [compound requests](buffer.html#compound-requests)
  - [Complex arrays](buffer.html#complex-arrays)
    - [NumPy-style: shape and strides](buffer.html#numpy-style-shape-and-strides)
    - [PIL-style: shape, strides and suboffsets](buffer.html#pil-style-shape-strides-and-suboffsets)
  - [Buffer-related functions](buffer.html#buffer-related-functions)
- [Old Buffer Protocol](objbuffer.html)
