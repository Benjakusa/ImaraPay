"""
conversation/parser.py
======================
Rule-based command grammar parser (§8.1).
This is intentionally NOT an LLM — determinism matters more than flexibility.
A merchant should be able to predict exactly what will and won't work.

Supported commands:
  request <amount> [for <reference>]
  today
  status <reference>
  last <N>
  cancel <reference>
  help
"""
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Command Types ─────────────────────────────────────────────────────────────

COMMAND_REQUEST = 'request'
COMMAND_TODAY = 'today'
COMMAND_STATUS = 'status'
COMMAND_LAST = 'last'
COMMAND_CANCEL = 'cancel'
COMMAND_HELP = 'help'
COMMAND_UNKNOWN = 'unknown'
COMMAND_CONFIRM = 'confirm'   # interactive button reply
COMMAND_EDIT = 'edit'         # interactive button reply

# Max N for "last N" command (§8.1 cap at 10)
LAST_N_MAX = 10


@dataclass
class ParsedCommand:
    command: str
    # request
    amount: Optional[int] = None
    reference: Optional[str] = None
    description: Optional[str] = None
    # last N
    n: Optional[int] = None
    # raw text for help/error messages
    raw: str = ''
    # True if the command was an interactive button/list reply
    is_interactive: bool = False
    # Interactive reply ID (e.g. "confirm", "edit", "help_create")
    interactive_id: Optional[str] = None


# ─── Patterns ─────────────────────────────────────────────────────────────────

# request 2500 [for INV-1002] or request 2500 [INV-1002]
_REQUEST_PATTERN = re.compile(
    r'^(?:request|req|pay)\s+'           # keyword
    r'(\d[\d,\.]*)'                        # amount (digits, optional commas/dots)
    r'(?:\s+(?:for\s+)?([A-Za-z0-9_\-]+))?'  # optional reference
    r'(?:\s+(.+))?$',                     # optional description
    re.IGNORECASE,
)

# today (and common variants)
_TODAY_PATTERN = re.compile(r'^(?:today|totals?|summary|overview)$', re.IGNORECASE)

# status INV-1002
_STATUS_PATTERN = re.compile(r'^status\s+([A-Za-z0-9_\-]+)$', re.IGNORECASE)

# last 5
_LAST_PATTERN = re.compile(r'^last\s+(\d+)$', re.IGNORECASE)

# cancel INV-1002
_CANCEL_PATTERN = re.compile(r'^cancel\s+([A-Za-z0-9_\-]+)$', re.IGNORECASE)

# help
_HELP_PATTERN = re.compile(r'^(?:help|menu|commands?|start|hi|hello|hey)$', re.IGNORECASE)


def parse_command(text: str) -> ParsedCommand:
    """
    Parse a raw WhatsApp message text into a ParsedCommand.
    Returns COMMAND_UNKNOWN for anything not in the grammar — never a guessed action.
    """
    text = text.strip()
    raw = text

    # ── interactive button/list reply ──────────────────────────────────────────
    # These come in as plain text from the button reply value
    if text.lower() in ('confirm', 'yes', 'y'):
        return ParsedCommand(command=COMMAND_CONFIRM, raw=raw, is_interactive=True, interactive_id='confirm')
    if text.lower() in ('edit', 'change', 'no'):
        return ParsedCommand(command=COMMAND_EDIT, raw=raw, is_interactive=True, interactive_id='edit')

    # ── help ──────────────────────────────────────────────────────────────────
    if _HELP_PATTERN.match(text):
        return ParsedCommand(command=COMMAND_HELP, raw=raw)

    # ── today ──────────────────────────────────────────────────────────────────
    if _TODAY_PATTERN.match(text):
        return ParsedCommand(command=COMMAND_TODAY, raw=raw)

    # ── status <ref> ──────────────────────────────────────────────────────────
    m = _STATUS_PATTERN.match(text)
    if m:
        return ParsedCommand(command=COMMAND_STATUS, reference=m.group(1), raw=raw)

    # ── last <N> ──────────────────────────────────────────────────────────────
    m = _LAST_PATTERN.match(text)
    if m:
        n = min(int(m.group(1)), LAST_N_MAX)
        return ParsedCommand(command=COMMAND_LAST, n=n, raw=raw)

    # ── cancel <ref> ─────────────────────────────────────────────────────────
    m = _CANCEL_PATTERN.match(text)
    if m:
        return ParsedCommand(command=COMMAND_CANCEL, reference=m.group(1), raw=raw)

    # ── request <amount> [for <ref>] [desc] ──────────────────────────────────
    m = _REQUEST_PATTERN.match(text)
    if m:
        raw_amount = m.group(1).replace(',', '').replace('.', '')
        try:
            amount = int(raw_amount)
        except ValueError:
            return ParsedCommand(command=COMMAND_UNKNOWN, raw=raw)
        reference = m.group(2) or None
        description = m.group(3) or None
        return ParsedCommand(
            command=COMMAND_REQUEST,
            amount=amount,
            reference=reference,
            description=description,
            raw=raw,
        )

    # ── fallthrough ───────────────────────────────────────────────────────────
    logger.debug(f"Unrecognized command: {text!r}")
    return ParsedCommand(command=COMMAND_UNKNOWN, raw=raw)


def parse_interactive_reply(interactive_payload: dict) -> ParsedCommand:
    """
    Parse a WhatsApp interactive button or list reply payload into a ParsedCommand.
    The 'id' field of the reply is used as the command key.
    """
    reply_type = interactive_payload.get('type')
    if reply_type == 'button_reply':
        reply_id = interactive_payload.get('button_reply', {}).get('id', '')
    elif reply_type == 'list_reply':
        reply_id = interactive_payload.get('list_reply', {}).get('id', '')
    else:
        return ParsedCommand(command=COMMAND_UNKNOWN, raw=str(interactive_payload), is_interactive=True)

    # Map interactive reply IDs to commands
    id_to_command = {
        'confirm': COMMAND_CONFIRM,
        'edit': COMMAND_EDIT,
        'help': COMMAND_HELP,
        'help_create': COMMAND_REQUEST,
        'help_today': COMMAND_TODAY,
        'help_last': COMMAND_LAST,
        'help_status': COMMAND_STATUS,
        'help_cancel': COMMAND_CANCEL,
    }
    command = id_to_command.get(reply_id, COMMAND_UNKNOWN)
    return ParsedCommand(
        command=command,
        raw=reply_id,
        is_interactive=True,
        interactive_id=reply_id,
    )
