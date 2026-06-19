"""LiveKit voice worker for automated accounts-receivable collections."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    TurnHandlingOptions,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, google, silero

from database import get_invoice_details, init_db, update_invoice_status

load_dotenv()

# Support both names because the README previously used both conventions.
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

REQUIRED_KEYS = [
    "GOOGLE_API_KEY",
    "DEEPGRAM_API_KEY",
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
]

DIGIT_WORDS = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}

ONES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def validate_environment() -> None:
    """Fail fast with a readable error if required credentials are missing."""
    missing = [key for key in REQUIRED_KEYS if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill in your real keys."
        )


def number_to_words(number: int) -> str:
    """Convert a non-negative integer under one million to words."""
    if number < 0 or number >= 1_000_000:
        return str(number)
    if number < 20:
        return ONES[number]
    if number < 100:
        tens, remainder = divmod(number, 10)
        return TENS[tens] if remainder == 0 else f"{TENS[tens]} {ONES[remainder]}"
    if number < 1_000:
        hundreds, remainder = divmod(number, 100)
        suffix = "" if remainder == 0 else f" {number_to_words(remainder)}"
        return f"{ONES[hundreds]} hundred{suffix}"
    thousands, remainder = divmod(number, 1_000)
    suffix = "" if remainder == 0 else f" {number_to_words(remainder)}"
    return f"{number_to_words(thousands)} thousand{suffix}"


def money_to_speech(amount: float) -> str:
    """Format a money amount for TTS instead of using symbols."""
    cents_total = int(round(float(amount) * 100))
    dollars, cents = divmod(cents_total, 100)
    dollar_unit = "dollar" if dollars == 1 else "dollars"
    if cents == 0:
        return f"{number_to_words(dollars)} {dollar_unit}"
    cent_unit = "cent" if cents == 1 else "cents"
    return f"{number_to_words(dollars)} {dollar_unit} and {number_to_words(cents)} {cent_unit}"


def invoice_id_to_speech(invoice_id: str) -> str:
    """Spell invoice identifiers in a TTS-friendly way."""
    parts: list[str] = []
    for char in invoice_id:
        if char.isalpha():
            parts.append(char.upper())
        elif char.isdigit():
            parts.append(DIGIT_WORDS[char])
    return " ".join(parts)


def build_system_prompt(invoice: dict[str, Any]) -> str:
    spoken_amount = money_to_speech(float(invoice["amount_due"]))
    spoken_invoice_id = invoice_id_to_speech(invoice["invoice_id"])
    return f"""
You are Sarah, a polite, professional automated financial collections agent representing Peakflo.
You are calling to follow up on an overdue invoice with {invoice['customer_name']}.

Invoice details:
- Customer name: {invoice['customer_name']}
- Invoice number: {spoken_invoice_id}
- Total amount owed: {spoken_amount}
- Original due date: {invoice['due_date']}
- Current status: {invoice['status']}

Call rules:
1. Keep every reply short, conversational, and direct. Use one or two sentences.
2. Never speak raw symbols like $, ₹, INV-2026-001, or 06/01/2026. Use spoken words instead.
3. Ask when they can complete payment. Do not sound threatening or aggressive.
4. If the customer promises a payment date, call the record_payment_promise tool with that date.
5. If they ask for a payment link or email verification, say you will trigger confirmation to the registered email.
6. Stay calm, helpful, and businesslike.
""".strip()


class ARCollectionsAgent(Agent):
    """Agent with tools for updating invoice state during the call."""

    def __init__(self, invoice: dict[str, Any]) -> None:
        super().__init__(instructions=build_system_prompt(invoice))
        self.invoice = invoice

    @function_tool()
    async def record_payment_promise(self, context: RunContext, promise_date: str) -> str:
        """Record the date on which the customer promises to pay the invoice.

        Args:
            promise_date: The customer's promised payment date in natural language,
                for example "June 25, 2026" or "next Friday".
        """
        updated = update_invoice_status(
            self.invoice["invoice_id"],
            "PROMISED",
            promise_date=promise_date,
        )
        if updated:
            return f"Payment promise recorded for {promise_date}."
        return "I could not find the invoice record to update."


async def entrypoint(ctx: JobContext) -> None:
    """LiveKit worker entrypoint."""
    validate_environment()
    init_db(seed=True)

    await ctx.connect()

    invoice_id = os.getenv("TEST_INVOICE_ID", "INV-2026-001")
    invoice = get_invoice_details(invoice_id)
    if invoice is None:
        raise RuntimeError(f"Invoice {invoice_id} was not found in the local database.")

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en-IN"),
        llm=google.LLM(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash")),
        tts=deepgram.TTS(model=os.getenv("DEEPGRAM_TTS_MODEL", "aura-2-asteria-en")),
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(turn_detection="vad"),
    )

    agent = ARCollectionsAgent(invoice)
    await session.start(room=ctx.room, agent=agent)

    await session.generate_reply(
        instructions=(
            "Start the call with a brief greeting. Confirm you are speaking with the finance team at "
            f"{invoice['customer_name']}, mention invoice {invoice_id_to_speech(invoice['invoice_id'])}, "
            f"the due date {invoice['due_date']}, and ask if now is a good time."
        )
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, port=int(os.getenv("PORT", "8080"))))
