"""
Natural Language Action Parser for KantorKu contracts.

Parses user natural language input to detect contract actions (accept, revise, interrupt).
This is business logic, not UI — extracted from the deprecated Textual TUI.
"""

import re
from enum import Enum


# Patterns that map to contract actions
ACCEPT_PATTERNS = re.compile(
    r"^(yes|yeah|yep|ok|okay|accept|approve|go ahead|go for it|do it|"
    r"let'?s go|sure|sounds good|perfect|lg|lfg|ship it|"
    r"looks good|agree|confirmed|confirm|proceed|execute)\s*[!.!]*$",
    re.IGNORECASE,
)

REVISE_PATTERNS = re.compile(
    r"^(no|nope|nah|revise|change|modify|update|alter|redo|reject|deny|"
    r"not quite|not really|i want|i need|i prefer|instead|"
    r"could you|can you|please change|please update|but)\b",
    re.IGNORECASE,
)

INTERRUPT_PATTERNS = re.compile(
    r"^(stop|halt|pause|wait|hold on|hold up|interrupt|disrupt|break|cancel)\b",
    re.IGNORECASE,
)


class NLAction(str, Enum):
    """Possible natural language actions."""
    ACCEPT = "accept"
    REVISE = "revise"
    INTERRUPT = "interrupt"


def parse_nl_action(text: str, contract_state: str) -> str | None:
    """
    Parse natural language input to detect contract actions.

    Args:
        text: User input text
        contract_state: Current contract state string

    Returns:
        "accept" if user wants to accept the contract
        "revise" if user wants to revise the contract (remaining text = feedback)
        "interrupt" if user wants to interrupt work
        None if no action detected (regular chat message)
    """
    stripped = text.strip()
    if not stripped:
        return None

    # Only parse accept/revise when contract is presented or awaiting revision
    if contract_state in ("contract_presented", "awaiting_revision"):
        if ACCEPT_PATTERNS.match(stripped):
            return NLAction.ACCEPT
        if REVISE_PATTERNS.match(stripped):
            return NLAction.REVISE

    # Only parse interrupt when work is in progress
    if contract_state == "working":
        if INTERRUPT_PATTERNS.match(stripped):
            return NLAction.INTERRUPT

    return None
