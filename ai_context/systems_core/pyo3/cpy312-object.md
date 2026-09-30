---
source_url: https://docs.python.org/3.12/c-api/object.html
title: Object Protocol — Python 3.12.14 documentation
retrieved_utc: 2026-09-30T22:25:56Z
content_kind: upstream-documentation-verbatim
trust: >
  Official upstream documentation, quoted verbatim. NOT paraphrased. PyO3 is
  NOT installed in this project; this is reference for a planned bridge, not
  documentation of existing code.
---

# Object Protocol

[PyObject](structures.html#c.PyObject "PyObject") \*Py\_NotImplemented
:   The `NotImplemented` singleton, used to signal that an operation is
    not implemented for the given type combination.

Py\_RETURN\_NOTIMPLEMENTED
:   Properly handle returning [`Py_NotImplemented`](#c.Py_NotImplemented "Py_NotImplemented") from within a C
    function (that is, create a new [strong reference](../glossary.html#term-strong-reference)
    to [`NotImplemented`](../library/constants.html#NotImplemented "NotImplemented") and return it).

Py\_PRINT\_RAW
:   Flag to be used with multiple functions that print the object (like
    [`PyObject_Print()`](#c.PyObject_Print "PyObject_Print") and [`PyFile_WriteObject()`](file.html#c.PyFile_WriteObject "PyFile_WriteObject")).
    If passed, these function would use the [`str()`](../library/stdtypes.html#str "str") of the object
    instead of the [`repr()`](../library/functions.html#repr "repr").

int PyObject\_Print([PyObject](structures.html#c.PyObject "PyObject") \*o, FILE \*fp, int flags)
:   Print an object *o*, on file *fp*. Returns `-1` on error. The flags argument
    is used to enable certain printing options. The only option currently supported
    is [`Py_PRINT_RAW`](#c.Py_PRINT_RAW "Py_PRINT_RAW"); if given, the [`str()`](../library/stdtypes.html#str "str") of the object is written
    instead of the [`repr()`](../library/functions.html#repr "repr").

int PyObject\_HasAttr([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyObject](structures.html#c.PyObject "PyObject") \*attr\_name)
:   *Part of the [Stable ABI](stable.html#stable).*

    Returns `1` if *o* has the attribute *attr\_name*, and `0` otherwise. This
    is equivalent to the Python expression `hasattr(o, attr_name)`. This function
    always succeeds.

    Note

    Exceptions that occur when this calls [`__getattr__()`](../reference/datamodel.html#object.__getattr__ "object.__getattr__") and
    [`__getattribute__()`](../reference/datamodel.html#object.__getattribute__ "object.__getattribute__") methods are silently ignored.
    For proper error handling, use [`PyObject_GetAttr()`](#c.PyObject_GetAttr "PyObject_GetAttr") instead.

int PyObject\_HasAttrString([PyObject](structures.html#c.PyObject "PyObject") \*o, const char \*attr\_name)
:   *Part of the [Stable ABI](stable.html#stable).*

    This is the same as [`PyObject_HasAttr()`](#c.PyObject_HasAttr "PyObject_HasAttr"), but *attr\_name* is
    specified as a const char\* UTF-8 encoded bytes string,
    rather than a [PyObject](structures.html#c.PyObject "PyObject")\*.

    Note

    Exceptions that occur when this calls [`__getattr__()`](../reference/datamodel.html#object.__getattr__ "object.__getattr__") and
    [`__getattribute__()`](../reference/datamodel.html#object.__getattribute__ "object.__getattribute__") methods or while creating the temporary
    [`str`](../library/stdtypes.html#str "str") object are silently ignored.
    For proper error handling, use [`PyObject_GetAttrString()`](#c.PyObject_GetAttrString "PyObject_GetAttrString") instead.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_GetAttr([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyObject](structures.html#c.PyObject "PyObject") \*attr\_name)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    Retrieve an attribute named *attr\_name* from object *o*. Returns the attribute
    value on success, or `NULL` on failure. This is the equivalent of the Python
    expression `o.attr_name`.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_GetAttrString([PyObject](structures.html#c.PyObject "PyObject") \*o, const char \*attr\_name)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    This is the same as [`PyObject_GetAttr()`](#c.PyObject_GetAttr "PyObject_GetAttr"), but *attr\_name* is
    specified as a const char\* UTF-8 encoded bytes string,
    rather than a [PyObject](structures.html#c.PyObject "PyObject")\*.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_GenericGetAttr([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyObject](structures.html#c.PyObject "PyObject") \*name)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    Generic attribute getter function that is meant to be put into a type
    object’s `tp_getattro` slot. It looks for a descriptor in the dictionary
    of classes in the object’s MRO as well as an attribute in the object’s
    [`__dict__`](../reference/datamodel.html#object.__dict__ "object.__dict__") (if present). As outlined in [Implementing Descriptors](../reference/datamodel.html#descriptors),
    data descriptors take preference over instance attributes, while non-data
    descriptors don’t. Otherwise, an [`AttributeError`](../library/exceptions.html#AttributeError "AttributeError") is raised.

int PyObject\_SetAttr([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyObject](structures.html#c.PyObject "PyObject") \*attr\_name, [PyObject](structures.html#c.PyObject "PyObject") \*v)
:   *Part of the [Stable ABI](stable.html#stable).*

    Set the value of the attribute named *attr\_name*, for object *o*, to the value
    *v*. Raise an exception and return `-1` on failure;
    return `0` on success. This is the equivalent of the Python statement
    `o.attr_name = v`.

    If *v* is `NULL`, the attribute is deleted. This behaviour is deprecated
    in favour of using [`PyObject_DelAttr()`](#c.PyObject_DelAttr "PyObject_DelAttr"), but there are currently no
    plans to remove it.

int PyObject\_SetAttrString([PyObject](structures.html#c.PyObject "PyObject") \*o, const char \*attr\_name, [PyObject](structures.html#c.PyObject "PyObject") \*v)
:   *Part of the [Stable ABI](stable.html#stable).*

    This is the same as [`PyObject_SetAttr()`](#c.PyObject_SetAttr "PyObject_SetAttr"), but *attr\_name* is
    specified as a const char\* UTF-8 encoded bytes string,
    rather than a [PyObject](structures.html#c.PyObject "PyObject")\*.

    If *v* is `NULL`, the attribute is deleted, but this feature is
    deprecated in favour of using [`PyObject_DelAttrString()`](#c.PyObject_DelAttrString "PyObject_DelAttrString").

    The number of different attribute names passed to this function
    should be kept small, usually by using a statically allocated string
    as *attr\_name*.
    For attribute names that aren’t known at compile time, prefer calling
    [`PyUnicode_FromString()`](unicode.html#c.PyUnicode_FromString "PyUnicode_FromString") and [`PyObject_SetAttr()`](#c.PyObject_SetAttr "PyObject_SetAttr") directly.
    For more details, see [`PyUnicode_InternFromString()`](unicode.html#c.PyUnicode_InternFromString "PyUnicode_InternFromString"), which may be
    used internally to create a key object.

int PyObject\_GenericSetAttr([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyObject](structures.html#c.PyObject "PyObject") \*name, [PyObject](structures.html#c.PyObject "PyObject") \*value)
:   *Part of the [Stable ABI](stable.html#stable).*

    Generic attribute setter and deleter function that is meant
    to be put into a type object’s [`tp_setattro`](typeobj.html#c.PyTypeObject.tp_setattro "PyTypeObject.tp_setattro")
    slot. It looks for a data descriptor in the
    dictionary of classes in the object’s MRO, and if found it takes preference
    over setting or deleting the attribute in the instance dictionary. Otherwise, the
    attribute is set or deleted in the object’s [`__dict__`](../reference/datamodel.html#object.__dict__ "object.__dict__") (if present).
    On success, `0` is returned, otherwise an [`AttributeError`](../library/exceptions.html#AttributeError "AttributeError")
    is raised and `-1` is returned.

int PyObject\_DelAttr([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyObject](structures.html#c.PyObject "PyObject") \*attr\_name)
:   Delete attribute named *attr\_name*, for object *o*. Returns `-1` on failure.
    This is the equivalent of the Python statement `del o.attr_name`.

int PyObject\_DelAttrString([PyObject](structures.html#c.PyObject "PyObject") \*o, const char \*attr\_name)
:   This is the same as [`PyObject_DelAttr()`](#c.PyObject_DelAttr "PyObject_DelAttr"), but *attr\_name* is
    specified as a const char\* UTF-8 encoded bytes string,
    rather than a [PyObject](structures.html#c.PyObject "PyObject")\*.

    The number of different attribute names passed to this function
    should be kept small, usually by using a statically allocated string
    as *attr\_name*.
    For attribute names that aren’t known at compile time, prefer calling
    [`PyUnicode_FromString()`](unicode.html#c.PyUnicode_FromString "PyUnicode_FromString") and [`PyObject_DelAttr()`](#c.PyObject_DelAttr "PyObject_DelAttr") directly.
    For more details, see [`PyUnicode_InternFromString()`](unicode.html#c.PyUnicode_InternFromString "PyUnicode_InternFromString"), which may be
    used internally to create a key object for lookup.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_GenericGetDict([PyObject](structures.html#c.PyObject "PyObject") \*o, void \*context)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable) since version 3.10.*

    A generic implementation for the getter of a `__dict__` descriptor. It
    creates the dictionary if necessary.

    This function may also be called to get the [`__dict__`](../reference/datamodel.html#object.__dict__ "object.__dict__")
    of the object *o*. Pass `NULL` for *context* when calling it.
    Since this function may need to allocate memory for the
    dictionary, it may be more efficient to call [`PyObject_GetAttr()`](#c.PyObject_GetAttr "PyObject_GetAttr")
    when accessing an attribute on the object.

    On failure, returns `NULL` with an exception set.

    Added in version 3.3.

int PyObject\_GenericSetDict([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyObject](structures.html#c.PyObject "PyObject") \*value, void \*context)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.7.*

    A generic implementation for the setter of a `__dict__` descriptor. This
    implementation does not allow the dictionary to be deleted.

    Added in version 3.3.

[PyObject](structures.html#c.PyObject "PyObject") \*\*\_PyObject\_GetDictPtr([PyObject](structures.html#c.PyObject "PyObject") \*obj)
:   Return a pointer to [`__dict__`](../reference/datamodel.html#object.__dict__ "object.__dict__") of the object *obj*.
    If there is no `__dict__`, return `NULL` without setting an exception.

    This function may need to allocate memory for the
    dictionary, so it may be more efficient to call [`PyObject_GetAttr()`](#c.PyObject_GetAttr "PyObject_GetAttr")
    when accessing an attribute on the object.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_RichCompare([PyObject](structures.html#c.PyObject "PyObject") \*o1, [PyObject](structures.html#c.PyObject "PyObject") \*o2, int opid)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    Compare the values of *o1* and *o2* using the operation specified by *opid*,
    which must be one of [`Py_LT`](typeobj.html#c.Py_LT "Py_LT"), [`Py_LE`](typeobj.html#c.Py_LE "Py_LE"), [`Py_EQ`](typeobj.html#c.Py_EQ "Py_EQ"),
    [`Py_NE`](typeobj.html#c.Py_NE "Py_NE"), [`Py_GT`](typeobj.html#c.Py_GT "Py_GT"), or [`Py_GE`](typeobj.html#c.Py_GE "Py_GE"), corresponding to `<`,
    `<=`, `==`, `!=`, `>`, or `>=` respectively. This is the equivalent of
    the Python expression `o1 op o2`, where `op` is the operator corresponding
    to *opid*. Returns the value of the comparison on success, or `NULL` on failure.

int PyObject\_RichCompareBool([PyObject](structures.html#c.PyObject "PyObject") \*o1, [PyObject](structures.html#c.PyObject "PyObject") \*o2, int opid)
:   *Part of the [Stable ABI](stable.html#stable).*

    Compare the values of *o1* and *o2* using the operation specified by *opid*,
    like [`PyObject_RichCompare()`](#c.PyObject_RichCompare "PyObject_RichCompare"), but returns `-1` on error, `0` if
    the result is false, `1` otherwise.

Note

If *o1* and *o2* are the same object, [`PyObject_RichCompareBool()`](#c.PyObject_RichCompareBool "PyObject_RichCompareBool")
will always return `1` for [`Py_EQ`](typeobj.html#c.Py_EQ "Py_EQ") and `0` for [`Py_NE`](typeobj.html#c.Py_NE "Py_NE").

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_Format([PyObject](structures.html#c.PyObject "PyObject") \*obj, [PyObject](structures.html#c.PyObject "PyObject") \*format\_spec)
:   *Part of the [Stable ABI](stable.html#stable).*

    Format *obj* using *format\_spec*. This is equivalent to the Python
    expression `format(obj, format_spec)`.

    *format\_spec* may be `NULL`. In this case the call is equivalent
    to `format(obj)`.
    Returns the formatted string on success, `NULL` on failure.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_Repr([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    Compute a string representation of object *o*. Returns the string
    representation on success, `NULL` on failure. This is the equivalent of the
    Python expression `repr(o)`. Called by the [`repr()`](../library/functions.html#repr "repr") built-in function.

    Changed in version 3.4: This function now includes a debug assertion to help ensure that it
    does not silently discard an active exception.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_ASCII([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    As [`PyObject_Repr()`](#c.PyObject_Repr "PyObject_Repr"), compute a string representation of object *o*, but
    escape the non-ASCII characters in the string returned by
    [`PyObject_Repr()`](#c.PyObject_Repr "PyObject_Repr") with `\x`, `\u` or `\U` escapes. This generates
    a string similar to that returned by [`PyObject_Repr()`](#c.PyObject_Repr "PyObject_Repr") in Python 2.
    Called by the [`ascii()`](../library/functions.html#ascii "ascii") built-in function.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_Str([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    Compute a string representation of object *o*. Returns the string
    representation on success, `NULL` on failure. This is the equivalent of the
    Python expression `str(o)`. Called by the [`str()`](../library/stdtypes.html#str "str") built-in function
    and, therefore, by the [`print()`](../library/functions.html#print "print") function.

    Changed in version 3.4: This function now includes a debug assertion to help ensure that it
    does not silently discard an active exception.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_Bytes([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    Compute a bytes representation of object *o*. `NULL` is returned on
    failure and a bytes object on success. This is equivalent to the Python
    expression `bytes(o)`, when *o* is not an integer. Unlike `bytes(o)`,
    a TypeError is raised when *o* is an integer instead of a zero-initialized
    bytes object.

int PyObject\_IsSubclass([PyObject](structures.html#c.PyObject "PyObject") \*derived, [PyObject](structures.html#c.PyObject "PyObject") \*cls)
:   *Part of the [Stable ABI](stable.html#stable).*

    Return `1` if the class *derived* is identical to or derived from the class
    *cls*, otherwise return `0`. In case of an error, return `-1`.

    If *cls* is a tuple, the check will be done against every entry in *cls*.
    The result will be `1` when at least one of the checks returns `1`,
    otherwise it will be `0`.

    If *cls* has a [`__subclasscheck__()`](../reference/datamodel.html#type.__subclasscheck__ "type.__subclasscheck__") method, it will be called to
    determine the subclass status as described in [**PEP 3119**](https://peps.python.org/pep-3119/). Otherwise,
    *derived* is a subclass of *cls* if it is a direct or indirect subclass,
    i.e. contained in [`cls.__mro__`](../reference/datamodel.html#type.__mro__ "type.__mro__").

    Normally only class objects, i.e. instances of [`type`](../library/functions.html#type "type") or a derived
    class, are considered classes. However, objects can override this by having
    a [`__bases__`](../reference/datamodel.html#type.__bases__ "type.__bases__") attribute (which must be a tuple of base classes).

int PyObject\_IsInstance([PyObject](structures.html#c.PyObject "PyObject") \*inst, [PyObject](structures.html#c.PyObject "PyObject") \*cls)
:   *Part of the [Stable ABI](stable.html#stable).*

    Return `1` if *inst* is an instance of the class *cls* or a subclass of
    *cls*, or `0` if not. On error, returns `-1` and sets an exception.

    If *cls* is a tuple, the check will be done against every entry in *cls*.
    The result will be `1` when at least one of the checks returns `1`,
    otherwise it will be `0`.

    If *cls* has a [`__instancecheck__()`](../reference/datamodel.html#type.__instancecheck__ "type.__instancecheck__") method, it will be called to
    determine the subclass status as described in [**PEP 3119**](https://peps.python.org/pep-3119/). Otherwise, *inst*
    is an instance of *cls* if its class is a subclass of *cls*.

    An instance *inst* can override what is considered its class by having a
    [`__class__`](../reference/datamodel.html#object.__class__ "object.__class__") attribute.

    An object *cls* can override if it is considered a class, and what its base
    classes are, by having a [`__bases__`](../reference/datamodel.html#type.__bases__ "type.__bases__") attribute (which must be a tuple
    of base classes).

[Py\_hash\_t](hash.html#c.Py_hash_t "Py_hash_t") PyObject\_Hash([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Part of the [Stable ABI](stable.html#stable).*

    Compute and return the hash value of an object *o*. On failure, return `-1`.
    This is the equivalent of the Python expression `hash(o)`.

    Changed in version 3.2: The return type is now Py\_hash\_t. This is a signed integer the same size
    as [`Py_ssize_t`](intro.html#c.Py_ssize_t "Py_ssize_t").

[Py\_hash\_t](hash.html#c.Py_hash_t "Py_hash_t") PyObject\_HashNotImplemented([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Part of the [Stable ABI](stable.html#stable).*

    Set a [`TypeError`](../library/exceptions.html#TypeError "TypeError") indicating that `type(o)` is not [hashable](../glossary.html#term-hashable) and return `-1`.
    This function receives special treatment when stored in a `tp_hash` slot,
    allowing a type to explicitly indicate to the interpreter that it is not
    hashable.

int PyObject\_IsTrue([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Part of the [Stable ABI](stable.html#stable).*

    Returns `1` if the object *o* is considered to be true, and `0` otherwise.
    This is equivalent to the Python expression `not not o`. On failure, return
    `-1`.

int PyObject\_Not([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Part of the [Stable ABI](stable.html#stable).*

    Returns `0` if the object *o* is considered to be true, and `1` otherwise.
    This is equivalent to the Python expression `not o`. On failure, return
    `-1`.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_Type([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    When *o* is non-`NULL`, returns a type object corresponding to the object type
    of object *o*. On failure, raises [`SystemError`](../library/exceptions.html#SystemError "SystemError") and returns `NULL`. This
    is equivalent to the Python expression `type(o)`.
    This function creates a new [strong reference](../glossary.html#term-strong-reference) to the return value.
    There’s really no reason to use this
    function instead of the [`Py_TYPE()`](structures.html#c.Py_TYPE "Py_TYPE") function, which returns a
    pointer of type [PyTypeObject](type.html#c.PyTypeObject "PyTypeObject")\*, except when a new
    [strong reference](../glossary.html#term-strong-reference) is needed.

int PyObject\_TypeCheck([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyTypeObject](type.html#c.PyTypeObject "PyTypeObject") \*type)
:   Return non-zero if the object *o* is of type *type* or a subtype of *type*, and
    `0` otherwise. Both parameters must be non-`NULL`.

[Py\_ssize\_t](intro.html#c.Py_ssize_t "Py_ssize_t") PyObject\_Size([PyObject](structures.html#c.PyObject "PyObject") \*o)

[Py\_ssize\_t](intro.html#c.Py_ssize_t "Py_ssize_t") PyObject\_Length([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Part of the [Stable ABI](stable.html#stable).*

    Return the length of object *o*. If the object *o* provides either the sequence
    and mapping protocols, the sequence length is returned. On error, `-1` is
    returned. This is the equivalent to the Python expression `len(o)`.

[Py\_ssize\_t](intro.html#c.Py_ssize_t "Py_ssize_t") PyObject\_LengthHint([PyObject](structures.html#c.PyObject "PyObject") \*o, [Py\_ssize\_t](intro.html#c.Py_ssize_t "Py_ssize_t") defaultvalue)
:   Return an estimated length for the object *o*. First try to return its
    actual length, then an estimate using [`__length_hint__()`](../reference/datamodel.html#object.__length_hint__ "object.__length_hint__"), and
    finally return the default value. On error return `-1`. This is the
    equivalent to the Python expression `operator.length_hint(o, defaultvalue)`.

    Added in version 3.4.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_GetItem([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyObject](structures.html#c.PyObject "PyObject") \*key)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    Return element of *o* corresponding to the object *key* or `NULL` on failure.
    This is the equivalent of the Python expression `o[key]`.

int PyObject\_SetItem([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyObject](structures.html#c.PyObject "PyObject") \*key, [PyObject](structures.html#c.PyObject "PyObject") \*v)
:   *Part of the [Stable ABI](stable.html#stable).*

    Map the object *key* to the value *v*. Raise an exception and
    return `-1` on failure; return `0` on success. This is the
    equivalent of the Python statement `o[key] = v`. This function *does
    not* steal a reference to *v*.

int PyObject\_DelItem([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyObject](structures.html#c.PyObject "PyObject") \*key)
:   *Part of the [Stable ABI](stable.html#stable).*

    Remove the mapping for the object *key* from the object *o*. Return `-1`
    on failure. This is equivalent to the Python statement `del o[key]`.

int PyObject\_DelItemString([PyObject](structures.html#c.PyObject "PyObject") \*o, const char \*key)
:   *Part of the [Stable ABI](stable.html#stable).*

    This is the same as [`PyObject_DelItem()`](#c.PyObject_DelItem "PyObject_DelItem"), but *key* is
    specified as a const char\* UTF-8 encoded bytes string,
    rather than a [PyObject](structures.html#c.PyObject "PyObject")\*.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_Dir([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    This is equivalent to the Python expression `dir(o)`, returning a (possibly
    empty) list of strings appropriate for the object argument, or `NULL` if there
    was an error. If the argument is `NULL`, this is like the Python `dir()`,
    returning the names of the current locals; in this case, if no execution frame
    is active then `NULL` is returned but [`PyErr_Occurred()`](exceptions.html#c.PyErr_Occurred "PyErr_Occurred") will return false.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_GetIter([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    This is equivalent to the Python expression `iter(o)`. It returns a new
    iterator for the object argument, or the object itself if the object is already
    an iterator. Raises [`TypeError`](../library/exceptions.html#TypeError "TypeError") and returns `NULL` if the object cannot be
    iterated.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_SelfIter([PyObject](structures.html#c.PyObject "PyObject") \*obj)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable).*

    This is equivalent to the Python `__iter__(self): return self` method.
    It is intended for [iterator](../glossary.html#term-iterator) types, to be used in the [`PyTypeObject.tp_iter`](typeobj.html#c.PyTypeObject.tp_iter "PyTypeObject.tp_iter") slot.

[PyObject](structures.html#c.PyObject "PyObject") \*PyObject\_GetAIter([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Return value: New reference.* *Part of the [Stable ABI](stable.html#stable) since version 3.10.*

    This is the equivalent to the Python expression `aiter(o)`. Takes an
    `AsyncIterable` object and returns an `AsyncIterator` for it.
    This is typically a new iterator but if the argument is an
    `AsyncIterator`, this returns itself. Raises [`TypeError`](../library/exceptions.html#TypeError "TypeError") and
    returns `NULL` if the object cannot be iterated.

    Added in version 3.10.

void \*PyObject\_GetTypeData([PyObject](structures.html#c.PyObject "PyObject") \*o, [PyTypeObject](type.html#c.PyTypeObject "PyTypeObject") \*cls)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.12.*

    Get a pointer to subclass-specific data reserved for *cls*.

    The object *o* must be an instance of *cls*, and *cls* must have been
    created using negative [`PyType_Spec.basicsize`](type.html#c.PyType_Spec.basicsize "PyType_Spec.basicsize").
    Python does not check this.

    On error, set an exception and return `NULL`.

    Added in version 3.12.

[Py\_ssize\_t](intro.html#c.Py_ssize_t "Py_ssize_t") PyType\_GetTypeDataSize([PyTypeObject](type.html#c.PyTypeObject "PyTypeObject") \*cls)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.12.*

    Return the size of the instance memory space reserved for *cls*, i.e. the size of the
    memory [`PyObject_GetTypeData()`](#c.PyObject_GetTypeData "PyObject_GetTypeData") returns.

    This may be larger than requested using [`-PyType_Spec.basicsize`](type.html#c.PyType_Spec.basicsize "PyType_Spec.basicsize");
    it is safe to use this larger size (e.g. with `memset()`).

    The type *cls* **must** have been created using
    negative [`PyType_Spec.basicsize`](type.html#c.PyType_Spec.basicsize "PyType_Spec.basicsize").
    Python does not check this.

    On error, set an exception and return a negative value.

    Added in version 3.12.

void \*PyObject\_GetItemData([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   Get a pointer to per-item data for a class with
    [`Py_TPFLAGS_ITEMS_AT_END`](typeobj.html#c.Py_TPFLAGS_ITEMS_AT_END "Py_TPFLAGS_ITEMS_AT_END").

    On error, set an exception and return `NULL`.
    [`TypeError`](../library/exceptions.html#TypeError "TypeError") is raised if *o* does not have
    [`Py_TPFLAGS_ITEMS_AT_END`](typeobj.html#c.Py_TPFLAGS_ITEMS_AT_END "Py_TPFLAGS_ITEMS_AT_END") set.

    Added in version 3.12.
