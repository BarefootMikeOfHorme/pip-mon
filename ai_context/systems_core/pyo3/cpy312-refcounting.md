---
source_url: https://docs.python.org/3.12/c-api/refcounting.html
title: Reference Counting — Python 3.12.14 documentation
retrieved_utc: 2026-09-30T22:16:43Z
content_kind: upstream-documentation-verbatim
trust: >
  Official upstream documentation, quoted verbatim. NOT paraphrased. PyO3 is
  NOT installed in this project; this is reference for a planned bridge, not
  documentation of existing code.
---

# Reference Counting

The functions and macros in this section are used for managing reference counts
of Python objects.

[Py\_ssize\_t](intro.html#c.Py_ssize_t "Py_ssize_t") Py\_REFCNT([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   Get the reference count of the Python object *o*.

    Note that the returned value may not actually reflect how many
    references to the object are actually held. For example, some
    objects are “immortal” and have a very high refcount that does not
    reflect the actual number of references. Consequently, do not rely
    on the returned value to be accurate, other than a value of 0 or 1.

    Use the [`Py_SET_REFCNT()`](#c.Py_SET_REFCNT "Py_SET_REFCNT") function to set an object reference count.

    Changed in version 3.10: [`Py_REFCNT()`](#c.Py_REFCNT "Py_REFCNT") is changed to the inline static function.

    Changed in version 3.11: The parameter type is no longer const [PyObject](structures.html#c.PyObject "PyObject")\*.

void Py\_SET\_REFCNT([PyObject](structures.html#c.PyObject "PyObject") \*o, [Py\_ssize\_t](intro.html#c.Py_ssize_t "Py_ssize_t") refcnt)
:   Set the object *o* reference counter to *refcnt*.

    Note that this function has no effect on
    [immortal](https://peps.python.org/pep-0683/)
    objects.

    Added in version 3.9.

    Changed in version 3.12: Immortal objects are not modified.

void Py\_INCREF([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   Indicate taking a new [strong reference](../glossary.html#term-strong-reference) to object *o*,
    indicating it is in use and should not be destroyed.

    This function is usually used to convert a [borrowed reference](../glossary.html#term-borrowed-reference) to a
    [strong reference](../glossary.html#term-strong-reference) in-place. The [`Py_NewRef()`](#c.Py_NewRef "Py_NewRef") function can be
    used to create a new [strong reference](../glossary.html#term-strong-reference).

    When done using the object, release it by calling [`Py_DECREF()`](#c.Py_DECREF "Py_DECREF").

    The object must not be `NULL`; if you aren’t sure that it isn’t
    `NULL`, use [`Py_XINCREF()`](#c.Py_XINCREF "Py_XINCREF").

    Do not expect this function to actually modify *o* in any way.
    For at least [**some objects**](https://peps.python.org/pep-0683/),
    this function has no effect.

    Changed in version 3.12: Immortal objects are not modified.

void Py\_XINCREF([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   Similar to [`Py_INCREF()`](#c.Py_INCREF "Py_INCREF"), but the object *o* can be `NULL`,
    in which case this has no effect.

    See also [`Py_XNewRef()`](#c.Py_XNewRef "Py_XNewRef").

[PyObject](structures.html#c.PyObject "PyObject") \*Py\_NewRef([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.10.*

    Create a new [strong reference](../glossary.html#term-strong-reference) to an object:
    call [`Py_INCREF()`](#c.Py_INCREF "Py_INCREF") on *o* and return the object *o*.

    When the [strong reference](../glossary.html#term-strong-reference) is no longer needed, [`Py_DECREF()`](#c.Py_DECREF "Py_DECREF")
    should be called on it to release the reference.

    The object *o* must not be `NULL`; use [`Py_XNewRef()`](#c.Py_XNewRef "Py_XNewRef") if *o* can be
    `NULL`.

    For example:

    ```
    Py_INCREF(obj);
    self->attr = obj;
    ```

    can be written as:

    ```
    self->attr = Py_NewRef(obj);
    ```

    See also [`Py_INCREF()`](#c.Py_INCREF "Py_INCREF").

    Added in version 3.10.

[PyObject](structures.html#c.PyObject "PyObject") \*Py\_XNewRef([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Part of the [Stable ABI](stable.html#stable) since version 3.10.*

    Similar to [`Py_NewRef()`](#c.Py_NewRef "Py_NewRef"), but the object *o* can be NULL.

    If the object *o* is `NULL`, the function just returns `NULL`.

    Added in version 3.10.

void Py\_DECREF([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   Release a [strong reference](../glossary.html#term-strong-reference) to object *o*, indicating the
    reference is no longer used.

    Once the last [strong reference](../glossary.html#term-strong-reference) is released
    (i.e. the object’s reference count reaches 0),
    the object’s type’s deallocation
    function (which must not be `NULL`) is invoked.

    This function is usually used to delete a [strong reference](../glossary.html#term-strong-reference) before
    exiting its scope.

    The object must not be `NULL`; if you aren’t sure that it isn’t `NULL`,
    use [`Py_XDECREF()`](#c.Py_XDECREF "Py_XDECREF").

    Do not expect this function to actually modify *o* in any way.
    For at least [**some objects**](https://peps.python.org/pep-0683/),
    this function has no effect.

    Warning

    The deallocation function can cause arbitrary Python code to be invoked (e.g.
    when a class instance with a [`__del__()`](../reference/datamodel.html#object.__del__ "object.__del__") method is deallocated). While
    exceptions in such code are not propagated, the executed code has free access to
    all Python global variables. This means that any object that is reachable from
    a global variable should be in a consistent state before [`Py_DECREF()`](#c.Py_DECREF "Py_DECREF") is
    invoked. For example, code to delete an object from a list should copy a
    reference to the deleted object in a temporary variable, update the list data
    structure, and then call [`Py_DECREF()`](#c.Py_DECREF "Py_DECREF") for the temporary variable.

    Changed in version 3.12: Immortal objects are not modified.

void Py\_XDECREF([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   Similar to [`Py_DECREF()`](#c.Py_DECREF "Py_DECREF"), but the object *o* can be `NULL`,
    in which case this has no effect.
    The same warning from [`Py_DECREF()`](#c.Py_DECREF "Py_DECREF") applies here as well.

void Py\_CLEAR([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   Release a [strong reference](../glossary.html#term-strong-reference) for object *o*.
    The object may be `NULL`, in
    which case the macro has no effect; otherwise the effect is the same as for
    [`Py_DECREF()`](#c.Py_DECREF "Py_DECREF"), except that the argument is also set to `NULL`. The warning
    for [`Py_DECREF()`](#c.Py_DECREF "Py_DECREF") does not apply with respect to the object passed because
    the macro carefully uses a temporary variable and sets the argument to `NULL`
    before releasing the reference.

    It is a good idea to use this macro whenever releasing a reference
    to an object that might be traversed during garbage collection.

    Changed in version 3.12: The macro argument is now only evaluated once. If the argument has side
    effects, these are no longer duplicated.

void Py\_IncRef([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Part of the [Stable ABI](stable.html#stable).*

    Indicate taking a new [strong reference](../glossary.html#term-strong-reference) to object *o*.
    A function version of [`Py_XINCREF()`](#c.Py_XINCREF "Py_XINCREF").
    It can be used for runtime dynamic embedding of Python.

void Py\_DecRef([PyObject](structures.html#c.PyObject "PyObject") \*o)
:   *Part of the [Stable ABI](stable.html#stable).*

    Release a [strong reference](../glossary.html#term-strong-reference) to object *o*.
    A function version of [`Py_XDECREF()`](#c.Py_XDECREF "Py_XDECREF").
    It can be used for runtime dynamic embedding of Python.

Py\_SETREF(dst, src)
:   Macro safely releasing a [strong reference](../glossary.html#term-strong-reference) to object *dst*
    and setting *dst* to *src*.

    As in case of [`Py_CLEAR()`](#c.Py_CLEAR "Py_CLEAR"), “the obvious” code can be deadly:

    ```
    Py_DECREF(dst);
    dst = src;
    ```

    The safe way is:

    ```
    Py_SETREF(dst, src);
    ```

    That arranges to set *dst* to *src* \_before\_ releasing the reference
    to the old value of *dst*, so that any code triggered as a side-effect
    of *dst* getting torn down no longer believes *dst* points
    to a valid object.

    Added in version 3.6.

    Changed in version 3.12: The macro arguments are now only evaluated once. If an argument has side
    effects, these are no longer duplicated.

Py\_XSETREF(dst, src)
:   Variant of [`Py_SETREF`](#c.Py_SETREF "Py_SETREF") macro that uses [`Py_XDECREF()`](#c.Py_XDECREF "Py_XDECREF") instead
    of [`Py_DECREF()`](#c.Py_DECREF "Py_DECREF").

    Added in version 3.6.

    Changed in version 3.12: The macro arguments are now only evaluated once. If an argument has side
    effects, these are no longer duplicated.
