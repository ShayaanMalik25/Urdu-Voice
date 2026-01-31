from dotenv import load_dotenv
load_dotenv()

import logging

# Suppress verbose audio logs
logging.getLogger("livekit.agents").setLevel(logging.INFO)
logging.getLogger("livekit.plugins").setLevel(logging.WARNING)

logger = logging.getLogger("agent")

from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions, JobProcess, MetricsCollectedEvent, metrics, function_tool, RunContext, AgentFalseInterruptionEvent
from livekit.plugins import (
    openai,
    noise_cancellation,
    silero,
    elevenlabs,
    cartesia
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from models.stt import WhisperSTT
from models.llm import OllamaLLM
import json
import os


def prewarm(proc: JobProcess):
    """Pre-warm VAD model for faster startup."""
    proc.userdata["vad"] = silero.VAD.load(
        min_silence_duration=0.12,  # Slightly increased to reduce false interruptions
        prefix_padding_duration=0.05,  # Reduced from 0.08 to reduce audio buffering delay
        activation_threshold=0.65,  # Increased from 0.60 to reduce false interruptions (less sensitive)
        # deactivation_threshold=0.25,
        sample_rate=8000,
    )


class Assistant(Agent):
    def __init__(self) -> None:
        self._room = None
        
        # Create function tools using decorator pattern
        # Access room through ctx.session.room (available when function is called)
        @function_tool()
        async def scroll_to_section(ctx: RunContext, section_id: str) -> str:
            """
            Website پر کسی specific section تک scroll کریں۔ جب user pricing، features، about، agents، demo، ya contact sections دیکھنا چاہے تو یہ use کریں۔
            
            Args:
                section_id: Section ID جہاں scroll کرنا ہے: home، about، agents، features، plans (pricing)، demo، ya contact
            """
            # Try multiple ways to access the room
            room = None
            # Method 1: Try self._room (set via set_room() in entrypoint)
            if self._room:
                room = self._room
            # Method 2: Try ctx.session.room
            elif hasattr(ctx.session, 'room'):
                room = ctx.session.room
            # Method 3: Try session's internal _room
            elif hasattr(ctx.session, '_room'):
                room = ctx.session._room
            
            if room:
                command = {
                    "type": "scroll",
                    "target": section_id
                }
                try:
                    command_json = json.dumps(command)
                    command_bytes = command_json.encode("utf-8")
                    
                    # Send navigation command via LiveKit data channel
                    await room.local_participant.publish_data(
                        command_bytes,
                        topic="navigation",
                        reliable=True
                    )
                    print(f"✅ Navigation command sent via data channel: {command_json}")
                    
                    print(f"   Room name: {room.name}")
                    print(f"   Remote participants: {len(room.remote_participants)}")
                    return f"Scrolled to {section_id} section"
                except Exception as e:
                    error_msg = f"Error scrolling: {str(e)}"
                    print(f"❌ {error_msg}")
                    import traceback
                    print(f"   Traceback: {traceback.format_exc()}")
                    return error_msg
            print(f"⚠️ Room not available for scrolling to {section_id}")
            print(f"   self._room is: {self._room}")
            return f"Would scroll to {section_id} section (room not available)"
        
        @function_tool()
        async def navigate_to_page(ctx: RunContext, page_path: str) -> str:
            """
            Website پر کسی different page پر navigate کریں۔ جب user use cases page ya koi aur page پر jana chahe تو یہ use کریں۔
            
            Args:
                page_path: Page path جہاں navigate کرنا ہے، مثال: /use-cases
            """
            # Try multiple ways to access the room
            room = None
            # Method 1: Try self._room (set via set_room() in entrypoint)
            if self._room:
                room = self._room
            # Method 2: Try ctx.session.room
            elif hasattr(ctx.session, 'room'):
                room = ctx.session.room
            # Method 3: Try session's internal _room
            elif hasattr(ctx.session, '_room'):
                room = ctx.session._room
            
            if room:
                command = {
                    "type": "navigate",
                    "target": page_path
                }
                try:
                    command_json = json.dumps(command)
                    command_bytes = command_json.encode("utf-8")
                    
                    # Send navigation command via LiveKit data channel
                    await room.local_participant.publish_data(
                        command_bytes,
                        topic="navigation",
                        reliable=True
                    )
                    print(f"✅ Navigation command sent via data channel: {command_json}")
                    
                    return f"Navigated to {page_path}"
                except Exception as e:
                    error_msg = f"Error navigating: {str(e)}"
                    print(f"❌ {error_msg}")
                    import traceback
                    print(f"   Traceback: {traceback.format_exc()}")
                    return error_msg
            print(f"⚠️ Room not available for navigating to {page_path}")
            return f"Would navigate to {page_path} (room not available)"
        
        @function_tool()
        async def get_section_info(ctx: RunContext, section_id: str) -> str:
            """
            Website section کے بارے میں معلومات حاصل کریں۔ جب user کسی section کے بارے میں پوچھے تو یہ use کریں تاکہ پتہ چل سکے کہ اس section میں کیا content ہے۔
            
            Args:
                section_id: Section ID جس کے بارے میں معلومات چاہیے
            """
            section_info_map = {
                "home": "Main landing page with hero section introducing Urdu AI Voice Agents",
                "about": "Information about our AI Voice Agent - natural conversations in Urdu and English, 24/7 available for customer support, sales, and business needs",
                "agents": "Three use cases: WhatsApp Inbound Calling (restaurants, order taking), WhatsApp Outbound Calling (sales, healthcare reminders), Web Voice Widget (website integration, database connectivity)",
                "features": "Key features: Multilingual support (Urdu + English), Natural conversation, Real-time processing, Analytics, Customizable, Scalable",
                "plans": "Three pricing tiers: Basic ($99/month, 500 calls), Pro ($299/month, 5,000 calls, most popular), Enterprise ($999/month, unlimited calls)",
                "demo": "Interactive live demo where users can test the AI Voice Agent directly by speaking in Urdu or English",
                "contact": "Contact information for inquiries and support"
            }
            return section_info_map.get(section_id, "Section information not available")
        
        super().__init__(
            instructions="""
# ویب ویجیٹ اسسٹنٹ - جنریشن زی (Gen Z) لاہوری

## بنیادی شناخت
آپ ایک ویب ویجیٹ اسسٹنٹ ہیں جو website visitors کی مدد کرتی ہیں۔ آپ ایک 20 سالہ نوجوان پاکستانی لڑکی ہیں جو لاہور سے تعلق رکھتی ہے۔ آپ کا انداز دوستانہ، جدید اور 'Gen Z' والا ہے۔ آپ روبوٹ کی طرح نہیں بلکہ ایک سمجھدار دوست کی طرح بات کرتی ہیں جو website navigation میں مدد کرتی ہے۔

## آپ کا کام
- Website navigation میں مدد کریں - users کو مختلف sections تک لے جائیں
- Page content کے بارے میں معلومات دیں
- Natural conversation کریں جب users sections کے بارے میں پوچھیں
- Voice commands کو understand کریں اور navigation actions perform کریں

## زبان اور گفتگو کا انداز (Minglish)
- **اردو اور انگریزی کا ملاپ:** آپ پکی اردو نہیں بولتیں، بلکہ قدرتی طور پر اردو اور انگریزی مکس کرتی ہیں۔
- **الفاظ کا استعمال:** مشکل اردو الفاظ کی جگہ عام انگریزی الفاظ استعمال کریں (مثال: "مسئلہ" کی جگہ "Issue"، "انتظار" کی جگہ "Wait"، "پریشان" کی جگہ "Tension")۔
- **ٹکیہ کلام (Fillers):** جملوں میں "Actually", "Basically", "You know", "Honestly", "Like" جیسے الفاظ کا استعمال قدرتی انداز میں کریں۔
- **لہجہ:** آپ کا لہجہ بہت 'Cool'، شائستہ اور یقین دلانے والا ہے۔

## جواب کا طریقہ
- لمبی تقریریں نہیں کرنی، بات چیت conversational رکھنی ہے۔
- اگر صارف پریشان ہو تو کہیں: "Don't worry, hum fix kar lein ge"۔
- بہت زیادہ formal نہیں ہونا، "آپ" کا استعمال کریں لیکن لہجہ دوستانہ رکھیں۔

## Website Sections کے بارے میں معلومات

### Home Section (id: "home")
- Main landing page with hero section
- Headline: "اردو AI Voice Agents" / "Intelligent Conversational AI for Voice"
- Subtitle: "24/7 AI Voice Support in Urdu & English"

### About Section (id: "about")
- Title: "ہمارا پروڈکٹ"
- Description: AI Voice Agent جو اردو اور انگریزی دونوں میں natural conversations کر سکتا ہے
- 24/7 available ہے customer support، sales، اور business needs کے لیے
- Intelligent، context-aware responses دیتا ہے

### Agents/Use Cases Section (id: "agents")
- Title: "استعمال کی مثالیں"
- تین main types:
  1. WhatsApp Inbound Calling - incoming calls handle کرتا ہے، restaurants کے لیے perfect (order taking، menu info، booking confirmation)
  2. WhatsApp Outbound Calling - automated calls sales کے لیے، follow-ups، healthcare reminders
  3. Web Voice Widget - websites پر embed کیا جا سکتا ہے، databases سے connect ہوتا ہے، real-time information access

### Features Section (id: "features")
- Multilingual support (Urdu + English)
- Natural conversation
- Real-time processing
- Analytics
- Customizable
- Scalable

### Pricing Section (id: "plans")
- تین tiers:
  - Basic: $99/month - 500 calls/month، small businesses کے لیے
  - Pro: $299/month - 5,000 calls/month، growing businesses کے لیے (most popular)
  - Enterprise: $999/month - Unlimited calls، large enterprises کے لیے

### Demo Section (id: "demo")
- Interactive live demo
- Users یہاں AI Voice Agent test کر سکتے ہیں directly
- Urdu یا English میں بات کر سکتے ہیں

### Contact Section (id: "contact")
- Contact information
- Inquiries اور support کے لیے email اور phone

## Navigation Commands Examples

جب user کہے:
- "pricing dikhao" یا "Show me pricing" → scroll_to_section("plans") use کریں
- "features ke bare mein batao" یا "Tell me about features" → scroll_to_section("features") use کریں پھر content discuss کریں
- "use cases page par jao" یا "Go to use cases" → navigate_to_page("/use-cases") use کریں
- "aap kya agents offer karte hain?" یا "What agents do you offer?" → scroll_to_section("agents") use کریں پھر discuss کریں
- "about dikhao" یا "About section" → scroll_to_section("about") use کریں
- "demo dikhao" یا "Show demo" → scroll_to_section("demo") use کریں

## اہم ہدایات
- جب بھی user navigate کرنا چاہے یا کسی section دیکھنا چاہے تو function tools ضرور use کریں
- Scrolling/navigating کے بعد naturally اس section کا content discuss کریں
- Conversational اور helpful رہیں
- Tools proactively use کریں - explicit "scroll" command کا wait نہ کریں اگر user کچھ دیکھنا چاہتا ہے
            """,
            tools=[scroll_to_section, navigate_to_page, get_section_info]
        )
    
    def set_room(self, room: rtc.Room):
        """Set the room for sending data messages"""
        self._room = room


async def entrypoint(ctx: agents.JobContext):
    
    # tts = upliftai.TTS(
    #     voice_id="v_meklc281", 
    #     output_format="MP3_22050_32",
    # )
    # Try your original voice first, but fallback to Sarah if it doesn't work
    # voice_id="m5qndnI7u4OAdXhH0Mr5" - your original voice
    # voice_id="EXAVITQu4vr4xnSDxMaL" - Sarah (well-tested multilingual fallback)
    # Try Krishna voice (was working before) or Monika Sogam
    tts=elevenlabs.TTS(
        # voice_id="m5qndnI7u4OAdXhH0Mr5",  # Krishna - was working before with Urdu
        voice_id="zmh5xhBvMzqR4ZlXgcgL",  # Monika Sogam - alternative
        model="eleven_turbo_v2_5",
        language="hi"
        # No language parameter - let ElevenLabs auto-detect
        # Hindi voices can handle Urdu text when language is auto-detected
    )
    # tts=cartesia.TTS(
    #         model="sonic-3",
    #         voice="b7d50908-b17c-442d-ad8d-810c63997ed9",
    #         sample_rate=16000
    #     )
    
    # Use cache key for prompt caching (enables faster responses with cached prompts)
    cache_key = "web_voice_agent_default"
    
    # In-process STT using Faster Whisper
    stt_model = WhisperSTT(
        language="ur",  # Urdu
        model=os.getenv("WHISPER_MODEL", "base"),  # base, small, medium, large-v2, large-v3
        device=os.getenv("WHISPER_DEVICE", "cuda"),  # cuda or cpu
        compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "float16"),  # float16, float32, int8
        model_cache_directory=os.getenv("WHISPER_CACHE_DIR", "/workspace/models/whisper"),
    )
    
    # Self-hosted LLM using Ollama
    llm_model = OllamaLLM(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key="NULL",  # Ollama doesn't need API key
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        temperature=0.4,
        top_p=0.9,
    )
    
    session = AgentSession(
        stt=stt_model,  # In-process STT
        llm=llm_model,  # Self-hosted LLM (Ollama)
        tts=tts,  # ElevenLabs TTS (API)
        turn_detection=MultilingualModel(),  # Multilingual turn detector for Urdu/English support
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        resume_false_interruption=True,
        false_interruption_timeout=0.5  # Reduced from 1.0s for faster recovery from false interruptions
    )

    @session.on("agent_false_interruption")
    def _on_agent_false_interruption(ev: AgentFalseInterruptionEvent):
        """Log false interruptions to monitor VAD aggressiveness."""
        logger.info(
            "False interruption detected - auto-resuming (timeout: 0.5s). "
            "Monitor frequency to assess VAD aggressiveness."
        )
        # System will auto-resume with resume_false_interruption=True

    # Usage collector for summary at end
    usage_collector = metrics.UsageCollector()

    # Metrics tracking - same as production
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        print(f"\n📊 Session usage summary: {summary}\n")

    ctx.add_shutdown_callback(log_usage)

    assistant = Assistant()
    assistant.set_room(ctx.room)
    
    await session.start(
        room=ctx.room,
        agent=assistant,
        room_input_options=RoomInputOptions(
            # noise_cancellation=noise_cancellation.BVC(), 
        ),
    )

    await session.generate_reply(
        instructions="""صارف کو گرمجوشی سے خوش آمدید کہیں۔ مختصر تعارف: 'السلام علیکم! میں آپ کی ویب سائٹ اسسٹنٹ ہوں۔ آپ مجھے voice commands دے سکتے ہیں - جیسے pricing دکھاؤ۔ کیا آپ help چاہتے ہیں؟'"""
    )
#     await session.generate_reply(
#     instructions="""Greet the user warmly. Short intro: 'Hello! I am your website assistant. You can give me voice commands - like show pricing. Do you need help?'"""
# )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        initialize_process_timeout=60,
        prewarm_fnc=prewarm,
        port=8082,  # Use port 8082 to avoid conflict with nginx on 8081
    ))