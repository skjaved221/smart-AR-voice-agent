import asyncio
import os
from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai
from database import get_invoice_details

# Load API keys from .env file
load_dotenv()

# Verify that credentials exist
required_keys = ["OPENAI_API_KEY", "DEEPGRAM_API_KEY", "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
missing_keys = [key for key in required_keys if not os.getenv(key)]
if missing_keys:
    print(f"\n[WARNING] Missing environment variables: {', '.join(missing_keys)}")
    print("Please configure your .env file before running this worker.\n")

async def entrypoint(ctx: JobContext):
    """
    Main entrypoint called by LiveKit when a user joins the WebRTC voice room.
    """
    print(f"Connecting to LiveKit room: {ctx.room.name}...")
    await ctx.connect()
    print("Successfully connected to room.")

    # 1. Fetch overdue invoice details from our SQLite database
    # We will use our mock record INV-2026-001 for testing
    invoice_id = "INV-2026-001"
    invoice = get_invoice_details(invoice_id)
    
    if not invoice:
        # Fallback details if db check fails
        invoice = {
            "customer_name": "Acme Corporation",
            "amount_due": 4500.50,
            "due_date": "June 1, 2026"
        }

    # 2. Build the System Prompt tailored for Voice Interactions
    # Rules: Short turns, phone-style call flow, phonetic formatting for numbers & letters.
    system_prompt = f"""
    You are "Sarah", a polite, professional, and automated financial collections agent representing Peakflo.
    You are calling to follow up on an overdue invoice with {invoice['customer_name']}.

    Invoice Details to Use:
    - Customer Name: {invoice['customer_name']}
    - Invoice Number: {invoice_id}
    - Total Amount Owed: {invoice['amount_due']} dollars
    - Original Due Date: June first, twenty twenty-six

    Rules for Voice Call flow:
    1. **Strict TTS formatting rule:** Text-to-speech engines mispronounce symbols.
       - NEVER write or output "$4500.50". Instead, ALWAYS write it out phonetically as: "four thousand five hundred dollars and fifty cents".
       - NEVER write "INV-2026-001". Instead, write it out letter-by-letter as: "I N V two zero two six zero zero one".
       - NEVER write dates like "06/01/2026". Write them as: "June first, twenty twenty-six".
    2. Keep responses brief, conversational, and direct (1-2 sentences). Do not speak in long paragraphs.
    3. If the customer asks for a payment link or email verification, say that you will trigger an email confirmation to their registered email address immediately.
    4. If the customer offers a specific promise date for the payment, thank them and state that you will record their payment promise for that date in the system.
    5. Always maintain a helpful, calm, and professional business tone.
    """

    # 3. Initialize the LiveKit Voice Pipeline Agent
    # VAD (Voice Activity Detection) is automatic from LiveKit SDK
    # STT: Deepgram (very fast real-time transcription)
    # LLM: OpenAI GPT-4o-mini (highly intelligent and fast response)
    # TTS: OpenAI voice synthesis
    agent = VoicePipelineAgent(
        vad=ctx.vad,
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(),
        chat_ctx=llm.ChatContext().append(role="system", text=system_prompt),
    )

    # 4. Start the agent worker in the WebRTC room
    agent.start(ctx.room)
    
    # Send a warm intro greeting to the user as they join the call
    await asyncio.sleep(1)  # small delay for connection stabilization
    await agent.say(
        f"Hello, is this the finance department at {invoice['customer_name']}? "
        f"I am calling from Peakflo regarding invoice number I N V two zero two six zero zero one, "
        f"which was due on June first."
    )

if __name__ == "__main__":
    # Start the LiveKit Agent worker process
    # The 'dev' or 'start' commands are passed via command-line args (e.g. python voice_agent.py dev)
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
