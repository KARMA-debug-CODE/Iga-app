"""Santa's defences against prompt injection.

Everything Santa's model reads besides its fixed system prompt is data: the student's message and earlier
turns, passages quoted from lessons, quiz questions, options and explanations written by teachers, and the
student's own answers. Any of it may try to steer the model ("ignore your rules", a fake "system:" line, a
chat-template control token, a forged end of a block). No filter can recognise every such attempt, so Santa
uses several layers, each of which helps on its own:

1. What the model may see is decided by the server (services.build_context): an answer key is in the prompt
   only once the student may see it, nothing at all is sent during an exam, and no other user's data or any
   secret is ever put in a prompt. Whatever the model is talked into, it can't reveal what it was never given.
2. Data goes in clearly named blocks, and the system prompt says that only its own rules count and that
   nothing inside a block is an instruction. Whether a quiz answer may be discussed is an attribute of the
   app's own <quiz_question> tag, which no data can write.
3. `neutralise` makes data unable to pose as structure: chat-template control tokens are removed, the
   app's block tags are rewritten so data can't open or close a block, "system:"-style role labels at the
   start of a line lose their colon, and invisible characters used to hide text are dropped. Text authored
   for lessons and quizzes also has instruction-like phrases ("ignore previous instructions") removed.
4. The student's message is checked for such phrases; when one is found the turn says so, and the attempt
   is recorded as a security event.
5. Earlier turns come from the browser, so a reply "from Santa" is believed only when Santa really wrote
   it for this student (services.clean_history checks the exchange log).
6. The model has one tool, a side-effect-free calculator, with a few calls per round and a few rounds.
7. An answer that repeats the system prompt is replaced by a refusal (`LeakCheck`); while an answer is
   streamed, the end that could be the start of such a copy waits, so none of it reaches the student.
"""

import re
import unicodedata

# The blocks the app writes in the student's turn. Data may never open or close one of them.
BLOCKS = (
    "context",
    "open_lesson",
    "lesson_passages",
    "passage",
    "quiz_question",
    "student_answer",
    "student_message",
    "system",
    "instructions",
)

_BLOCK_TAG = re.compile(r"<\s*(/?)\s*(" + "|".join(BLOCKS) + r")\b[^<>]{0,200}>", re.I)

# Control tokens of the chat templates open models use (ChatML, Llama, Gemma, Mistral, Phi and others). A
# model server may read them in a message as the real thing, so a message could end its turn and start a
# "system" one. They are removed.
_CONTROL_TOKENS = re.compile(
    r"<\|[^<>|\n]{0,40}\|>"  # <|im_start|>, <|eot_id|>, <|start_header_id|>, <|system|>
    r"|<\|[a-z_]{1,30}>|<[a-z_]{1,30}\|>"  # <|turn>, <turn|>
    r"|</?\s*(?:start_of_turn|end_of_turn|start_of_image|end_of_image|bos|eos|pad|unk|mask|s)\s*>"
    r"|\[/?\s*(?:INST|SYS|SYSTEM_PROMPT|TOOL_CALLS|AVAILABLE_TOOLS|TOOL_RESULTS)\s*\]"
    r"|<</?\s*SYS\s*>>",
    re.I,
)

# "System:", "### Assistant:", "[user]:" at the start of a line look like a new turn of the conversation.
_ROLE_LABEL = re.compile(
    r"^([ \t>*_#-]*\[?)(system|syst[eè]me|assistant|developer|d[ée]veloppeur|user|utilisateur|tool|santa|human)"
    r"(\]?[ \t*_]*)(:)",
    re.I | re.M,
)

# Phrases that address the model instead of teaching anything, in English and French. They are kept narrow so
# lesson language ("don't forget the rules of indices", "you are now able to", "pretend to be a shopkeeper")
# never matches: each one needs words that only make sense when talking to an AI.
_RULES = r"(?:instructions?|rules?|prompts?|directions?|guidelines?|guardrails?|restrictions?|messages?|context)"
_REGLES = r"(?:instructions?|r[eè]gles?|consignes?|directives?|messages?)"
_INSTRUCTION_PHRASES = re.compile(
    r"\b(?:ignore|disregard|forget|override|bypass)\s+(?:(?:all|any|every|of|the|these|those)\s+){0,3}"
    r"(?:previous|prior|above|earlier|preceding|original|initial|former|system|safety|your|santa'?s)\s+(?:\w+\s+){0,2}"
    + _RULES
    + r"\b"
    r"|\b(?:ignore|disregard)\s+(?:all|any)\s+(?:\w+\s+)?(?:instructions|prompts|guidelines)\b"
    r"|\bsystem\s+prompt\b"
    r"|\bnew\s+system\s+(?:prompt|instructions|rules)\b"
    r"|\b(?:reveal|print|repeat|output|leak|show|tell)\s+(?:me\s+|us\s+)?your\s+(?:\w+\s+)?(?:instructions|prompt|rules)\b"
    r"|\b(?:you\s+are|you're)\s+now\s+(?:dan\b|free\b|not\s+santa\b|an?\s+(?:unrestricted|unfiltered|uncensored|different|new)\b)"
    r"|\byou\s+are\s+no\s+longer\s+(?:santa\b|bound\b|restricted\b|limited\b|an?\s+(?:ai|assistant|tutor)\b)"
    r"|\b(?:developer|god|dan|jailbreak|unrestricted|unfiltered)\s+mode\b"
    r"|\bjailbr(?:eak|oken)\w*"
    r"|\b(?:act|behave|respond)\s+as\s+(?:an?\s+)?(?:unrestricted|unfiltered|uncensored|evil)\b"
    # French
    r"|\b(?:ignore[rz]?|oublie[rz]?|n[ée]glige[rz]?|contourne[rz]?)\s+(?:toutes?\s+|tous\s+)?"
    r"(?:(?:tes|vos)\s+(?:\w+\s+)?"
    + _REGLES
    + r"|(?:les|ces)\s+"
    + _REGLES
    + r"\s+(?:pr[ée]c[ée]dentes?|ant[ée]rieures?|initiales?|du\s+syst[eè]me|de\s+santa))\b"
    r"|\b(?:prompt|invite)\s+(?:du\s+)?syst[eè]me\b"
    r"|\b(?:r[ée]v[eè]le[rz]?|affiche[rz]?|montre[rz]?|r[ée]p[eè]te[rz]?)[\s-]+(?:moi\s+|nous\s+)?"
    r"(?:tes|vos|ton|votre)\s+(?:\w+\s+)?(?:instructions?|consignes?|prompt|r[eè]gles?)\b"
    r"|\b(?:tu\s+es|vous\s+[eê]tes)\s+(?:maintenant|d[ée]sormais)\s+(?:dan\b|libre|une?\s+(?:ia|intelligence)\s+sans|"
    r"sans\s+(?:r[eè]gles|limites|restrictions?))"
    r"|\bmode\s+(?:d[ée]veloppeur|dan|jailbreak|sans\s+(?:restrictions?|limites?|filtres?))\b",
    re.I,
)

REMOVED = "[removed]"


def _visible(text):
    """Without invisible format characters (zero-width spaces, direction overrides) that can hide or reorder
    text; line breaks and tabs stay."""
    return "".join(c for c in text if c in "\n\t" or unicodedata.category(c) not in ("Cf", "Cc", "Co", "Cs"))


def neutralise(text, *, authored=False):
    """`text` made unable to pose as instructions or structure in Santa's prompt.

    `authored` is for text written for lessons and quizzes (by teachers and editors), which has no reason to
    address the model: instruction-like phrases are removed from it too. The student's own words keep them
    (they are checked with `looks_like_injection` instead), so a question about such a phrase still reads."""
    if not text:
        return ""
    text = _visible(unicodedata.normalize("NFKC", str(text)))
    text = _CONTROL_TOKENS.sub(" ", text)
    text = _BLOCK_TAG.sub(lambda m: f"[{m.group(1)}{m.group(2).lower()}]", text)
    text = _ROLE_LABEL.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)} -", text)
    if authored:
        text = _INSTRUCTION_PHRASES.sub(REMOVED, text)
    return text


def looks_like_injection(text):
    """True when the text tries to give the model instructions or to pose as the app."""
    if not text:
        return False
    plain = _visible(unicodedata.normalize("NFKC", str(text)))
    return bool(
        _INSTRUCTION_PHRASES.search(plain)
        or _CONTROL_TOKENS.search(plain)
        or _BLOCK_TAG.search(plain)
        or _ROLE_LABEL.search(plain)
    )


# --- The system prompt must not come back out ---------------------------------------------------

LEAK_WINDOW = 60


def _squash(text):
    return re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", text.lower())).strip()


def _counts(char):
    """True for a character that is a letter or digit once squashed (so it counts towards a window)."""
    return char.isalnum() and (char.isascii() or unicodedata.normalize("NFKD", char)[:1].isascii())


class LeakCheck:
    """Finds a run of LEAK_WINDOW characters (letters and digits, spacing and punctuation ignored) of the
    system prompt in an answer. Common phrases are much shorter, so an ordinary answer never trips it."""

    def __init__(self, secret_text):
        self.squashed = _squash(secret_text)
        self.windows = {self.squashed[i : i + LEAK_WINDOW] for i in range(max(0, len(self.squashed) - LEAK_WINDOW + 1))}

    def __call__(self, answer):
        squashed = _squash(answer or "")
        return any(squashed[i : i + LEAK_WINDOW] in self.windows for i in range(max(0, len(squashed) - LEAK_WINDOW + 1)))

    def held(self, text):
        """How many characters at the end of `text` (an answer being written) to hold back: the longest end of it
        that is also a piece of the system prompt, which may be the start of a copy. Passing on only the rest
        means no part of a copy reaches the student before it is caught. In an ordinary answer this is a few
        letters (the end of a common word), so the text still appears as it is written."""
        tail = text[-4 * LEAK_WINDOW :]
        squashed = _squash(tail)
        # A piece of a piece is a piece, so the longest matching end can be found by halving.
        low, high = 0, min(len(squashed), LEAK_WINDOW)
        while low < high:
            middle = (low + high + 1) // 2
            if squashed[-middle:] in self.squashed:
                low = middle
            else:
                high = middle - 1
        if not low:
            return 0
        letters = 0
        for i in range(len(tail) - 1, -1, -1):
            letters += _counts(tail[i])
            if letters >= low:
                return len(tail) - i
        return len(tail)
