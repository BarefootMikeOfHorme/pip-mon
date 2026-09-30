"""Command dispatcher: OverseerCLI -> V-Probe control channel.

Rule 3 lives here on the consumer side too. The dashboard offers buttons like
"cancel this thread" and "force-kill", and the temptation is to fire them
straight down the pipe and report success. That would be a lie: V-Probe queues
every command and executes it on the next engine frame, so the dashboard cannot
know whether it worked.

So the API is shaped to make the lie impossible. Every send returns
``Dispatched``, never ``Succeeded``. The UI is written against that vocabulary
on purpose -- if the button said "Cancelled", users would believe it.

The one exception is :meth:`Dispatcher.ping`, which is a genuine round trip: the
probe echoes it back, so the result is real and is the only way to verify the
whole path end to end.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from .ipc_client import VLinkClient

log = logging.getLogger(__name__)

#: Bump when the control vocabulary changes. The probe reports its own version in
#: a PluginDiag handshake, and a mismatch is surfaced rather than tolerated.
CONTROL_PROTOCOL_VERSION: Final[int] = 1


class Outcome(Enum):
    """The honest set of possible results.

    ``Succeeded`` exists for exactly one operation -- :meth:`Dispatcher.ping` --
    because it is the only one with a real reply.
    """

    DISPATCHED = "dispatched"
    """Handed to the pipe. Will execute next engine frame. Outcome unknown."""

    TIMED_OUT = "timed_out"
    """The probe never echoed a ping within the timeout. Path is broken."""

    FAILED = "failed"
    """The send itself failed: not connected, or the pipe closed mid-write."""


class CommandKind(Enum):
    SOFT_CANCEL = "soft_cancel"
    FORCE_KILL = "force_kill"
    STACK_DUMP = "dump_stack"
    CANCEL_ALL = "cancel_all"
    SET_SAMPLING = "set_sampling"
    PING = "ping"
    CLEAN_TESTLAB = "clean_testlab"


@dataclass(frozen=True, slots=True)
class DispatchResult:
    kind: CommandKind
    outcome: Outcome
    detail: str = ""
    elapsed_ms: float = 0.0

    @property
    def ok(self) -> bool:
        """True when the operation is expected to have taken effect.

        For a DISPATCHED result this means "accepted for execution", never
        "confirmed". Only PING, which has a real reply, can be confirmed.
        """
        if self.outcome is Outcome.Succeeded:
            return True
        return self.outcome is Outcome.DISPATCHED


@dataclass(frozen=True, slots=True)
class SafetyWarning:
    """Shown before a destructive action. Force-kill always produces one."""

    title: str
    body: str
    requires_typed_confirmation: str | None = None

    @property
    def is_blocking(self) -> bool:
        return self.requires_typed_confirmation is not None


#: Force-kill warnings are defined here, in the consumer, because the consumer
#: is what the user is looking at. Defining them in the probe would mean the
#: safety copy lives somewhere the user never sees.
FORCE_KILL_WARNING = SafetyWarning(
    title="Force-kill VM thread?",
    body=(
        "This terminates a Papyrus thread WITHOUT unwinding it.\n\n"
        "Consequences:\n"
        "  • quest flags the script was writing may be left half-set\n"
        "  • workshop / object property changes may be inconsistent\n"
        "  • the script's cleanup code will NOT run\n\n"
        "A soft-cancel (Script.Cancel) is safe and releases the script's locals "
        "normally. Try that first.\n\n"
        "Save to a NEW slot if you need this save to stay valid."
    ),
    requires_typed_confirmation="force",
)

SOFT_CANCEL_WARNING = SafetyWarning(
    title="Soft-cancel VM thread?",
    body=(
        "Calls Script.Cancel() on the owning form. The script unwinds and "
        "releases its locals. This is the safe option and is what you usually want."
    ),
)

STACK_DUMP_WARNING = SafetyWarning(
    title="Request stack dump",
    body=(
        "Read-only. The probe re-reads the VM stack on the main thread and "
        "returns it. Safe."
    ),
)


class Dispatcher:
    """Sends control commands to V-Probe over the V-Link control channel."""

    def __init__(self, client: VLinkClient) -> None:
        self._client = client
        self._last_ping_ok: bool | None = None
        self._last_ping_at: float = 0.0
        #: Set by the app's frame-ingest loop. Kept as a callback rather than a
        #: queue read so that pinging can never steal a telemetry frame out from
        #: under the profiler -- a subtle and very annoying bug if the drain path
        #: is shared.
        self._echo_sink: list[bool] = []

    def note_diag(self, text: str) -> None:
        """Feed diag text in from the normal ingest path. Cheap string check."""
        if "vlink_ping" in text and self._echo_sink:
            self._echo_sink.pop(0)

    # -- safe operations ---------------------------------------------------

    async def ping(self, timeout: float = 1.5) -> DispatchResult:
        """Round-trip a ping. The only command with a verifiable outcome.

        Used by ``mon_ping`` in-game and by the dashboard's status bar to
        distinguish "probe not loaded" from "probe loaded, no consumer" from
        "consumer attached but not processing".
        """
        start = time.monotonic()
        self._echo_sink.append(False)
        try:
            await self._client.send_control(self._encode(CommandKind.PING, {}))
        except Exception as exc:  # noqa: BLE001
            self._last_ping_ok = False
            if self._echo_sink:
                self._echo_sink.pop()
            return DispatchResult(
                CommandKind.PING, Outcome.FAILED, f"{type(exc).__name__}: {exc}"
            )

        # The probe echoes a marker through the normal PluginDiag channel. We do
        # NOT read the client's queue here -- the ingest loop does that, and
        # competing for it would silently drop telemetry. Instead we poll our own
        # sink, which the ingest loop fills via note_diag().
        deadline = start + timeout
        while time.monotonic() < deadline:
            await _sleep(0.02)
            if self._echo_sink and self._echo_sink[0]:
                self._echo_sink.pop(0)
                rtt = (time.monotonic() - start) * 1000
                self._last_ping_ok = True
                self._last_ping_at = time.monotonic()
                return DispatchResult(
                    CommandKind.PING, Outcome.Succeeded, "echo received", rtt
                )

        if self._echo_sink:
            self._echo_sink.pop()
        self._last_ping_ok = False
        self._last_ping_at = time.monotonic()
        return DispatchResult(
            CommandKind.PING,
            Outcome.TIMED_OUT,
            "attached but no echo: the consumer is not processing frames",
        )

    @property
    def last_ping_ok(self) -> bool | None:
        return self._last_ping_ok

    async def request_stack_dump(self, vm_thread_id: int) -> DispatchResult:
        return await self._send(
            CommandKind.STACK_DUMP, {"threadId": vm_thread_id}, "stack dump"
        )

    async def cancel_all(self) -> DispatchResult:
        return await self._send(CommandKind.CANCEL_ALL, {}, "cancel all tracked threads")

    async def set_sampling(self, interval_ops: int) -> DispatchResult:
        if interval_ops < 1 or interval_ops > 65536:
            return DispatchResult(
                CommandKind.SET_SAMPLING, Outcome.FAILED, "interval must be 1..65536"
            )
        return await self._send(
            CommandKind.SET_SAMPLING, {"interval": interval_ops}, "set sampling"
        )

    async def clean_testlab(self) -> DispatchResult:
        return await self._send(CommandKind.CLEAN_TESTLAB, {}, "release TestLab references")

    # -- destructive -------------------------------------------------------

    async def soft_cancel(self, vm_thread_id: int) -> DispatchResult:
        """Safe. Unwinds the script, releases its locals. Always try this first."""
        return await self._send(
            CommandKind.SOFT_CANCEL, {"threadId": vm_thread_id}, "soft cancel"
        )

    async def force_kill(self, vm_thread_id: int) -> DispatchResult:
        """UNSAFE. Skips unwinding; can leave quest state half-written.

        No confirmation is enforced here because a library cannot ask a
        question. The caller must have shown FORCE_KILL_WARNING and obtained
        explicit confirmation first -- the UI is where that gate lives, and
        :meth:`safety_warning` exists so it can be fetched from one place.
        """
        return await self._send(
            CommandKind.FORCE_KILL, {"threadId": vm_thread_id}, "force kill"
        )

    @staticmethod
    def safety_warning(kind: CommandKind) -> SafetyWarning | None:
        return {
            CommandKind.FORCE_KILL: FORCE_KILL_WARNING,
            CommandKind.SOFT_CANCEL: SOFT_CANCEL_WARNING,
            CommandKind.STACK_DUMP: STACK_DUMP_WARNING,
        }.get(kind)

    # -- internals ---------------------------------------------------------

    async def _send(self, kind: CommandKind, params: dict, label: str) -> DispatchResult:
        start = time.monotonic()
        try:
            await self._client.send_control(self._encode(kind, params))
        except Exception as exc:  # noqa: BLE001
            return DispatchResult(
                kind, Outcome.FAILED, f"{label}: {type(exc).__name__}: {exc}"
            )
        return DispatchResult(
            kind,
            Outcome.DISPATCHED,
            f"{label} queued; executes on the next engine frame",
            (time.monotonic() - start) * 1000,
        )

    @staticmethod
    def _encode(kind: CommandKind, params: dict) -> bytes:
        return json.dumps(
            {
                "v": CONTROL_PROTOCOL_VERSION,
                "cmd": kind.value,
                **params,
            },
            separators=(",", ":"),
        ).encode("utf-8")


def proto_event_diag():  # noqa: ANN201
    """Late import to avoid a cycle between dispatcher and protocol."""
    from . import protocol

    return protocol.EventType.PLUGIN_DIAG


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
