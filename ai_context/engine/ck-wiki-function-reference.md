---
source_url: https://fallout.wiki/index.php?title=Resource:Creation_Kit/Function_Reference&action=raw
title: Resource:Creation Kit/Function Reference (Fallout 4 Creation Kit Wiki archive)
retrieved_utc: 2026-09-30T21:31:10Z
content_kind: upstream-documentation-verbatim
trust: upstream community reference, quoted verbatim. NOT verified against a compiler.
---

{{Creation Kit}}
Functions are units of work that are larger then a single expression, and may take various parameters and return a value to their caller.

== Function Definition ==
 <function> ::= <function header>
                [<function block>
                'endFunction']

Function headers must always be followed by a block and an "EndFunction" [[Resource:Creation Kit/Keyword Reference|keyword]], unless they are native functions (which are exposed by the game).

=== Function Header ===
 <function header> ::= [<type>] 'Function' <identifier> '(' [<parameters>] ')' ('global' | 'native')* <flags>*

A function header starts (optionally) with the return type of the function, and is then followed by the name of the function, its parameters (if any), and any modifiers and flags.

The [[Resource:Creation Kit/Identifier Reference|identifier]] used to name the function cannot conflict with any other function in the current script. If the identifier matches a function in the parent script, then the return type and parameters much match the parent script's version of the function - and the function will override the parent's function.

The "Global" flag indicates a function that does not actually run on an in-game object, and has no "Self" variable. The "Native" flag indicates a function that does not have a function body, because the function is implemented by the game itself. If you add the native flag to a function the game does not expose, the compiler won't complain, but the game will error at you. The same flag cannot be specified more then once.

Native functions may not be defined in non-native scripts

Debug-only functions may be defined by adding "DebugOnly" to the end of the function definition line. Any calls to these functions will be removed in release script builds.

Beta-only functions may be defined by adding "BetaOnly" to the end of the function definition line. Any calls to these functions will be removed in final script builds.

=== Parameters ===
 <parameters> ::= <parameter> (',' <parameter>)*
 <parameter>  ::= <type> <identifier> ['=' <constant>]

The parameter list is a comma-separated list of types and identifiers that indicate the various parameters that a function takes. Each parameter may be optionally followed by an equals sign and a constant, which indicates that the parameter has a default value. If a parameter has a default value, every parameter after it must also have a default value.

Parameters are essentially [[Resource:Creation Kit/Variable Reference|variables]] the function has access to that the caller gives initial values to.

==== Special Parameter Types ====
All three of these "types" will only accept raw string literals and no variables. The compiler will then check the value against some part of the type passed as the previous parameter or, if there is no previous parameter, the type the function was called on.
* ScriptEventName: The compiler will check the string against the list of events that could be sent by the object.
* CustomEventName: The compiler will check the string against the list of custom events that could be sent by the object.
* StructVarName: The compiler will check the string against the list of variable names in the struct.

=== Function Block ===
 <function block> ::= <statement>*

The function block contains zero or more [[Resource:Creation Kit/Statement Reference|statements]]. This performs the actual work of the function.

=== Examples ===
<pre>
; A simple function that adds the two values together and returns the result
; Global, because it doesn't need a self variable
int Function AddTwo(int a, int b) global
  return a + b
endFunction
</pre>
<br>
<pre>
; A function that increments a value on this script by the specified amount.
; The amount has a default value of 1 (so the caller doesn't have to pass it)
Function IncrementValue(int howMuch = 1)
  myValue += howMuch
endFunction
</pre>

== Special Variables ==
There are two special variables in a function, but only in a non-global one. "Self" refers to the instance of the script that the function is running on, and is useful if you want to pass yourself off to another function somewhere else.

"Parent" is only used to call a parent script's version of a function, in the case where you extend the parent.

=== Examples ===
<pre>
; Pass our self off to another function
SomeObject.OtherFunction(self)
</pre>
<br>
<pre>
; Call the parent's version of DoStuff, ignoring our local definition
Parent.DoStuff()
</pre>

== Calling Functions ==
Global function:
 [<scriptType> '.'] <identifier> '(' [<parameters>] ')'
Non-global function:
 [<expression> '.'] <identifier> '(' [<parameters>] ')'

Calling a function simply involves using the function's [[Resource:Creation Kit/Identifier Reference|identifier]], followed by parenthesis, and any parameters that the function takes. The return value of the function is the result of the function call and can be assigned to a variable, or used to call another function or property.

If you are calling a global function and the function's owning script isn't the current script or isn't [[Resource:Creation Kit/Script File Structure#Imports|imported]], then you must prefix it with the name of the script the function resides in.

If you are calling a non-global function and it isn't on yourself, then you must prefix it with the object you want to call it on.

=== Parameters ===
 <parameters> ::= <parameter> (',' <parameter>)*
 <parameter>  ::= [<identifier> '='] <expression>

The parameter list is a comma-separated list of expressions in the same order as the parameters are listed in the function definition. If a parameter is optional, it does not have to be passed (the default value is inserted by the compiler into the call location). You may specify parameters out of order by prefixing the expression with the identifier of the parameter (matching the name of the parameter in the definition) followed by an equals sign.

=== Examples ===
<pre>
; Call the function: MyFunction(int a, int b) and get the result and put it in x
x = MyFunction(1, 2)
</pre>
<br>
<pre>
; Call the function DefaultFunction(float a, float b, float c = 0.0, float d = 1.0) on MyObject,
; but only pass in the first three parameters
MyObject.DefaultFunction(4.0, 2.0, 1.0)
</pre>
<br>
<pre>
; Call the function DefaultFunction(float a, float b, float c = 0.0, float d = 1.0), but specify
; argument d out of order because we want c to keep the default it has
DefaultFunction(5.0, 2.4, d = 2.0)
</pre>
<br>
<pre>
; Call the global function MyGlobal() in the Utility script
Utility.MyGlobal()
; Call the global function MyGlobal() in the Utility script in the MyMod namespace
MyResource:Utility.MyGlobal()
</pre>

[[Category:Scripting]]
[[Category:Papyrus]]
[[Category:Papyrus Language Reference]]
