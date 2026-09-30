---
source_url: https://fallout.wiki/index.php?title=Resource:Creation_Kit/Events_Reference&action=raw
title: Resource:Creation Kit/Events Reference (Fallout 4 Creation Kit Wiki archive)
retrieved_utc: 2026-09-30T21:31:10Z
content_kind: upstream-documentation-verbatim
trust: upstream community reference, quoted verbatim. NOT verified against a compiler.
---

{{Creation Kit}}
Events are special [[Resource:Creation Kit/Function Reference|functions]] that the game will call when something happens. Note that simply defining an event won't make the game call it, you must follow the name and argument list of an event that the game [[Category:CK Events|already sends you]]

New events may not be defined in non-native objects to avoid typos being recognized as new events.

== Event Definition ==
 <event> ::= (<event header> | <remote event header>)
             [<function block>
             'endEvent']

Function headers must always be followed by a standard [[Resource:Creation Kit/Function Reference#Function Block|function block]] and "EndEvent", unless they are native (which are handled by the game).

=== Event Header ===
 <event header> ::= 'Event' <identifier> '(' [<parameters>] ')' ['Native'] <flags>*

The event header is identical to the [[Resource:Creation Kit/Function Reference#Function Header|function header]], but does not allow for return types or allow for the "Global" flag.

=== Remote Event Header ===

 <remote event header> ::= 'Event' <object type> '.' <identifier> '(' <sender parameter> [',' <parameters>] ')' ['Native'] <flags>*

The sender parameter must be the same type as the type specified in the event name, and it is followed by the parameters that the event on the remote object sends. The identifier must be the name of an event defined on the object type, and it must not be defined in a parent object type. In other words, the object type must be the least-derived type that contains the event.

=== Custom Event Header ===

 <custom event header> ::= 'Event' <object type> '.' <identifier> '(' <sender parameter> ',' <args parameter> ')' ['Native'] <flags>*

The sender parameter must be the same type as the type specified in the event name, and must be followed by an arguments parameter of type "Var[]". The identifier must be the name of the custom event defined in the object type.

=== Parameters ===
The parameters are identical to the [[Resource:Creation Kit/Function Reference#Parameters|function parameter list]], but should match the data that the game will send to the event.

=== Examples ===
<pre>
; A simple activate event handler 
Event OnActivate(ObjectReference akActivator)
  PlayAnimation("CoolStuff")
endEvent
</pre>

An example of a remote event handler:
<pre>
Event ObjectReference.OnActivate(ObjectReference akSender, ObjectReference akActivator)
  PlayAnimation("CoolStuff")
endEvent
</pre>

An example of a custom event handler:
<pre>
Event MyQuestScript.MyCustomEvent(MyQuestScript akSender, Var[] akArgs)
  Debug.Trace("Got MyCustomEvent from " + akSender + " with arguments " + akArgs)
endEvent
</pre>

== Creating a Custom Event ==
 'CustomEvent' <identifier>

The "CustomEvent" keyword defines a new custom event that this script can send, kind of like a variable. Whenever someone defines a custom event receiver function, or passes a custom event name to a function, it is checked against this particular element. You cannot define a custom event with the same name as any other function or event in your script, or your parent script.

=== Examples ===
<pre>
; Define a MyCustomEvent event
CustomEvent MyCustomEvent
</pre>

== Special Variables ==
Event special variables are identical to a non-global [[Resource:Creation Kit/Function Reference#Special Variables|function's]].

== Calling Events ==
Calling events is identical to calling a [[Resource:Creation Kit/Function Reference#Calling Functions|function]].

Remote and custom events may not be directly called. Directly calling an event will not trigger remote events on other scripts.

[[Category:Scripting]]
[[Category:Papyrus Language Reference]]
[[Category:CK Events]]
