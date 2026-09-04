import json
import logging
import os
import re
import threading
import time
from dotenv import load_dotenv

# Load environment variables first so logging config and API keys are available.
load_dotenv()

from crewai import Agent, Task, Crew, Process, LLM
from fallback_responses import generate_fallback_reply
from scholarship_kb import get_rag_context_for_query, load_scholarships

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from google import genai
except ImportError:  # pragma: no cover
    genai = None

# Production logging: default to WARNING unless LOG_LEVEL is set.
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.WARNING))
# Suppress noisy third-party logs in the terminal; our own logger still reports errors.
logging.getLogger("crewai.flow.runtime").setLevel(logging.CRITICAL)
logging.getLogger("crewai").setLevel(logging.CRITICAL)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Global lock to prevent concurrent CrewAI executor usage.
# CrewAI does not allow the same executor instance to run concurrently.
_crew_lock = threading.Lock()

# Workaround for CrewAI 1.15.x + Groq: CrewAI unconditionally injects a
# cache_breakpoint field into messages, which Groq's API rejects.
# This monkey-patch disables that behavior for non-Anthropic providers.
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()


def _collect_env_keys(prefix: str) -> list[str]:
    """Collect all non-empty API keys for a given prefix.
    Supports GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... and legacy GROQ_API_KEY, HF_TOKEN.
    """
    keys = []
    # Numbered keys: PREFIX_1, PREFIX_2, ...
    for i in range(1, 10):
        value = os.getenv(f"{prefix}_{i}")
        if value and not value.lower().startswith("your_"):
            keys.append(value)
    # Legacy single key without suffix.
    legacy = os.getenv(prefix)
    if legacy and not legacy.lower().startswith("your_") and legacy not in keys:
        keys.append(legacy)
    return keys


def _collect_groq_keys() -> list[str]:
    """Collect all Groq keys including the legacy GROQ_API_KEY and fresh GROQ_API_KEY_NEW."""
    keys = _collect_env_keys("GROQ_API_KEY")
    new_key = os.getenv("GROQ_API_KEY_NEW")
    if new_key and not new_key.lower().startswith("your_") and new_key not in keys:
        keys.append(new_key)
    return keys


# Startup diagnostics: print how many keys were loaded so operators can verify .env is read.
_gemini_keys = _collect_env_keys("GEMINI_API_KEY")
_groq_keys = _collect_groq_keys()
_hf_tokens = _collect_env_keys("HF_TOKEN")
print(f"[startup] Loaded {len(_gemini_keys)} Gemini key(s), {len(_groq_keys)} Groq key(s), {len(_hf_tokens)} Hugging Face token(s)")
print(f"[startup] LLM_PROVIDER={LLM_PROVIDER}, GEMINI_MODEL={os.getenv('GEMINI_MODEL', 'not set')}, GROQ_MODEL={os.getenv('GROQ_MODEL', 'not set')}, HF_MODEL={os.getenv('HF_MODEL', 'not set')}")

# Print the exact key routing order that will be used for fallback.
_routing_order = []
if LLM_PROVIDER == "gemini":
    for i in range(len(_gemini_keys)):
        _routing_order.append(f"Gemini key {i + 1} ({os.getenv('GEMINI_MODEL', 'gemini/gemini-3.6-flash')})")
for i in range(len(_groq_keys)):
    _routing_order.append(f"Groq key {i + 1} ({os.getenv('GROQ_MODEL', 'groq/openai/gpt-oss-120b')})")
for i in range(len(_hf_tokens)):
    _routing_order.append(f"Hugging Face token {i + 1} ({os.getenv('HF_MODEL', 'mistralai/Mistral-7B-Instruct-v0.2')})")
if _routing_order:
    print("[startup] Key routing order:")
    for idx, route in enumerate(_routing_order, start=1):
        print(f"  {idx}. {route}")
else:
    print("[startup] WARNING: No API keys loaded. Check your .env file.")

# Verify local scholarship knowledge base is available for RAG.
_scholarship_kb_count = len(load_scholarships())
print(f"[startup] Scholarship knowledge base loaded: {_scholarship_kb_count} entries")


def _test_key(provider: str, key_index: int) -> dict:
    """Quickly test a single API key with a small 'Hello' prompt."""
    try:
        if provider == "gemini":
            _gemini_chat_completion([{"role": "user", "content": "Hello"}], key_index=key_index, max_tokens=50)
            return {"ok": True}
        if provider == "groq":
            keys = _collect_groq_keys()
            api_key = keys[key_index] if key_index < len(keys) else (keys[0] if keys else None)
            # Use the primary active Groq model; strip provider prefix for direct Groq API.
            model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").replace("groq/", "")
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 50,
                    "temperature": 0.7,
                },
                timeout=15,
            )
            if res.status_code != 200:
                return {"ok": False, "error": f"{res.status_code}: {res.text}"}
            return {"ok": True}
        if provider == "huggingface":
            _hf_chat_completion([{"role": "user", "content": "Hello"}], key_index=key_index, max_tokens=50, timeout=10)
            return {"ok": True}
        return {"ok": False, "error": "unknown provider"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def create_llm(provider: str, key_index: int = 0, model: str | None = None):
    """Create an LLM instance for the given provider and key index.
    key_index selects the N-th configured key for that provider.
    model overrides the default model name when provided.
    """
    provider = provider.lower()
    if provider == "gemini":
        keys = _collect_env_keys("GEMINI_API_KEY")
        api_key = keys[key_index] if key_index < len(keys) else (keys[0] if keys else None)
        return LLM(
            model=model or os.getenv("GEMINI_MODEL", "gemini/gemini-3.6-flash"),
            api_key=api_key,
            temperature=0.7,
            max_tokens=512,
        )
    if provider == "huggingface":
        keys = _collect_env_keys("HF_TOKEN")
        api_key = keys[key_index] if key_index < len(keys) else (keys[0] if keys else None)
        return LLM(
            model=model or os.getenv("HF_MODEL", "huggingface/mistralai/Mistral-7B-Instruct-v0.2"),
            api_key=api_key,
            temperature=0.7,
            max_tokens=512,
        )
    # Groq
    keys = _collect_groq_keys()
    api_key = keys[key_index] if key_index < len(keys) else (keys[0] if keys else None)
    return LLM(
        model=model or os.getenv("GROQ_MODEL", "groq/openai/gpt-oss-120b"),
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.7,
        max_tokens=512,
    )


def _gemini_chat_completion(messages, key_index: int = 0, max_tokens: int = 2048, model: str | None = None) -> str:
    """Call the Gemini API directly using the official google-genai SDK.
    This bypasses LiteLLM/CrewAI model-name issues and uses the configured model.
    """
    if genai is None:
        raise RuntimeError("google-genai SDK is not available")

    keys = _collect_env_keys("GEMINI_API_KEY")
    api_key = keys[key_index] if key_index < len(keys) else (keys[0] if keys else None)
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    model = (model or os.getenv("GEMINI_MODEL", "gemini/gemini-3.6-flash"))
    # Strip any provider prefix so we pass only the model name to the SDK.
    model = model.replace("gemini/", "")

    client = genai.Client(api_key=api_key)
    # Convert messages to google-genai Content format.
    contents = []
    for m in messages:
        role = m.get("role", "user")
        text = m.get("content", "")
        if role == "system":
            # Google GenAI supports a system instruction via config; prepend for simplicity.
            contents.append({"role": "user", "parts": [{"text": f"System instruction: {text}"}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": text}]})
        else:
            contents.append({"role": "user", "parts": [{"text": text}]})

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=genai.types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=0.7,
        ),
    )
    if response.candidates and response.candidates[0].content.parts:
        return response.candidates[0].content.parts[0].text.strip()
    raise RuntimeError("Empty response from Gemini API")


def _hf_chat_completion(messages, key_index: int = 0, max_tokens: int = 1024, timeout: int = 10, model: str | None = None) -> str:
    """Call the Hugging Face Inference API serverless endpoint directly.
    This is used as a tertiary fallback when Gemini and Groq both fail.
    Uses the legacy text-generation endpoint which works with free HF tokens.
    """
    if requests is None:
        raise RuntimeError("requests library is not available")

    keys = _collect_env_keys("HF_TOKEN")
    token = keys[key_index] if key_index < len(keys) else (keys[0] if keys else None)
    if not token:
        raise RuntimeError("HF_TOKEN is not set")

    model = model or os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    # Keep only the model name if the user included a provider prefix.
    model = model.replace("huggingface/", "")

    # Build a simple prompt from messages.
    system_msg = ""
    user_msgs = []
    for m in messages:
        if m.get("role") == "system":
            system_msg += m.get("content", "") + "\n"
        elif m.get("role") == "user":
            user_msgs.append(m.get("content", ""))
    user_prompt = "\n\n".join(user_msgs)

    # Mistral Instruct format. Meta-Llama-3 uses the same generic [INST] wrapper
    # for simple single-turn prompts and responds correctly.
    prompt = f"<s>[INST] {system_msg}{user_prompt} [/INST]"

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": 0.7,
            "return_full_text": False,
        },
        "options": {"wait_for_model": True},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    # HF serverless text-generation returns a list of dicts: [{"generated_text": "..."}]
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"].strip()
    if isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"].strip()
    raise RuntimeError(f"Unexpected Hugging Face response format: {json.dumps(data)[:200]}")


def _groq_chat_completion(messages, key_index: int = 0, model: str | None = None, max_tokens: int = 2048, timeout: int = 10) -> str:
    """Call Groq REST API directly — bypasses CrewAI overhead for sub-3-second responses."""
    if requests is None:
        raise RuntimeError("requests library is not available")

    keys = _collect_groq_keys()
    api_key = keys[key_index] if key_index < len(keys) else (keys[0] if keys else None)
    if not api_key:
        raise RuntimeError("No GROQ_API_KEY is set")

    model = (model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")).replace("groq/", "")

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        },
        timeout=timeout,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text[:200]}")

    data = response.json()
    choices = data.get("choices", [])
    if choices and choices[0].get("message", {}).get("content"):
        return choices[0]["message"]["content"].strip()
    raise RuntimeError("Empty response from Groq API")


def create_chat_advisor(llm_instance):
    """Create the conversational advisor agent with the given LLM."""
    return Agent(
        role="Conversational Career Advisor",
        goal="Have a natural, helpful conversation to understand the user and give useful career and scholarship advice.",
        backstory=(
            "You are a helpful career and scholarship advisor, similar to ChatGPT or Claude. "
            "You advise on scholarships at ALL levels: Bachelor's/Undergraduate, Master's, and PhD. "
            "Many users are beginners and do not know how to write detailed prompts. They may say simple things like "
            "'I am studying this, I want a scholarship for this' or 'I want to do a book for this.' "
            "ALWAYS respond to what the user just said first. Give useful information, guidance, or a direct answer. "
            "If the user's request is clear enough, help them directly without asking extra questions. "
            "Only if you genuinely need more information to give better advice, ask ONE short follow-up question at the very end. "
            "Use [[FINAL]] at the start of your response ONLY when you are giving the complete final recommendation AND the conversation should end. "
            "If you ask ANY question, do NOT use [[FINAL]]. "
            "Respond in Chinese (中文) if the user writes in Chinese. "
            "When generating personal documents (CV, cover letter, SOP, email), use ONLY facts the user provided; "
            "do NOT invent universities, companies, skills, projects, or achievements. Use placeholders like [Your Phone] for missing details. "
            "Keep replies concise, friendly, and easy to read."
        ),
        verbose=False,
        allow_delegation=False,
        llm=llm_instance
    )


# Primary LLM and agent for the legacy career-scholarship pipeline.
llm = create_llm(LLM_PROVIDER)
chat_advisor = create_chat_advisor(llm)

# Career Counselor Agent - concise, focused advice
career_counselor = Agent(
    role="Senior Career Counselor",
    goal="Provide a brief, actionable career recommendation with 2-3 tailored paths.",
    backstory="You give concise, high-value career advice. Avoid long essays. Use bullet points and short sentences.",
    verbose=False,
    allow_delegation=False,
    llm=llm
)

# Scholarship Matcher Agent - concise scholarship matches
scholarship_matcher = Agent(
    role="Global Scholarship & Grant Specialist",
    goal="List 2-3 highly relevant scholarships with eligibility and next steps, briefly.",
    backstory="You match students to scholarships efficiently. Keep outputs short, scannable, and actionable.",
    verbose=False,
    allow_delegation=False,
    llm=llm
)


def detect_language(text: str) -> str:
    """Detect the dominant script/language of the text."""
    if not text:
        return "English"

    total = len(text)
    if total == 0:
        return "English"

    chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
    devanagari = sum(1 for c in text if "\u0900" <= c <= "\u097f")

    if chinese / total > 0.1:
        return "Chinese (中文)"
    if arabic / total > 0.1:
        return "Urdu/Arabic (اردو)"
    if devanagari / total > 0.1:
        return "Hindi (हिन्दी)"

    # Default to English for Latin script and mixed Roman text
    return "English"


def format_chat_history(messages: list[dict], max_messages: int = 4) -> str:
    """Convert a list of {role, content} messages into a conversation string.
    Only keep the most recent messages to stay within token limits."""
    recent = messages[-max_messages:] if len(messages) > max_messages else messages
    lines = []
    for msg in recent:
        role = "User" if msg.get("role") == "user" else "Advisor"
        content = msg.get("content", "")
        # Truncate very long messages to keep token usage low
        if len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _extract_wait_seconds(error_text: str) -> float:
    """Extract suggested wait time in seconds from Groq rate-limit error."""
    match = re.search(r"try again in ([0-9]+(?:\.[0-9]+)?)s", error_text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 0.0


def _is_rate_limit_error(error_text: str) -> bool:
    return "rate_limit" in error_text.lower() or "rate limit" in error_text.lower()


def kickoff_with_retries(crew: Crew, max_retries: int = 2):
    """Run crew.kickoff() with retries on transient errors.
    Retries on rate-limit errors and empty LLM responses."""
    last_error = None
    for attempt in range(max_retries):
        try:
            result = crew.kickoff()
            if result is None or str(result).strip() == "":
                raise ValueError("LLM returned an empty response")
            return result
        except Exception as e:
            last_error = e
            error_text = str(e)
            if _is_rate_limit_error(error_text) or "empty" in error_text.lower():
                wait = 2 + attempt * 2
                concise = "rate limit" if _is_rate_limit_error(error_text) else "empty response"
                logger.warning("Transient LLM error (attempt %d/%d): %s. Retrying in %ds...", attempt + 1, max_retries, concise, wait)
                time.sleep(wait)
                continue
            raise
    raise last_error


def _fallback_reply(user_message: str, language: str) -> str:
    """Return a helpful fallback reply when the LLM is unavailable due to rate limits."""
    return generate_fallback_reply(user_message, language)


def _deterministic_offline_reply(user_message: str, language: str) -> str:
    """Return a polite, structured message when all online LLM providers are unavailable.
    This prevents 500 crashes and tells the user to retry briefly.
    For scholarship-related queries, we still return curated RAG context so the user gets value even when all LLMs are down."""
    is_urdu = "Urdu" in language or "Arabic" in language
    is_hindi = "Hindi" in language
    is_chinese = "Chinese" in language

    # Zero-failure RAG: if this is a scholarship query, return retrieved KB results even when LLMs fail.
    if _is_scholarship_query(user_message):
        rag_context = get_rag_context_for_query(user_message, top_k=5)
        prefix = "Here is what I found in our curated scholarship knowledge base:\n\n"
        suffix = "\n\n(The AI summarizer is temporarily offline due to high demand; the details above are from our verified local dataset.)"
        if is_chinese:
            prefix = "以下是我从我们整理的奖学金知识库中找到的内容：\n\n"
            suffix = "\n\n（AI 总结器因需求较高暂时离线；以上信息来自我们验证过的本地数据集。）"
        elif is_urdu:
            prefix = "یہ ہماری تیار کردہ اسکالرشپ نالج بیس سے ملنے والی معلومات ہے:\n\n"
            suffix = "\n\n(AI خلاصہ ساز عارضی طور پر آف لائن ہے؛ اوپر دی گئی تفصیلات ہماری تصدیق شدہ مقامی ڈیٹا سیٹ سے ہیں۔)"
        elif is_hindi:
            prefix = "यह हमारे क्यूरेटेड स्कॉलरशिप नॉलेज बेस से मिली जानकारी है:\n\n"
            suffix = "\n\n(AI सारांशक अस्थायी रूप से ऑफ़लाइन है; उपरोक्त विवरण हमारे सत्यापित स्थानीय डेटासेट से हैं।)"
        return prefix + rag_context + suffix

    # Zero-failure local fallback: even when every online LLM provider is down,
    # return a helpful career-advisor response instead of a generic "busy" message.
    if is_chinese:
        return (
            "感谢你的消息！我目前暂时无法调用在线 AI 模型，但我仍然可以帮你规划。\n\n"
            "请告诉我更多信息，这样我能给你更精准的建议：\n"
            "- 你当前的教育背景和专业\n"
            "- 你感兴趣的职业方向或国家\n"
            "- 你想申请的项目类型（本科 / 硕士 / 博士）\n\n"
            "Follow-up questions:\n"
            "1. 你目前是在读学生还是已经工作？\n"
            "2. 你未来 3-5 年的职业目标是什么？"
        )
    if is_urdu:
        return (
            "آپ کے پیغام کا شکریہ! میں اس وقت آن لائن AI ماڈلز نہیں بلا سکتا، لیکن میں پھر بھی آپ کی منصوبہ بندی میں مدد کر سکتا ہوں۔\n\n"
            "براہ کرم مزید معلومات شیئر کریں تاکہ بہتر مشورہ دیا جا سکے:\n"
            "- آپ کی موجودہ تعلیمی سطح اور مضمون\n"
            "- وہ شعبہ یا ملک جس میں آپ دلچسپی رکھتے ہیں\n"
            "- آپ کس قسم کے پروگرام کے لیے درخواست دینا چاہتے ہیں\n\n"
            "Follow-up questions:\n"
            "1. کیا آپ ابھی طالب علم ہیں یا کام کر رہے ہیں؟\n"
            "2. آپ کے اگلے 3-5 سال کے کیریئر مقاصد کیا ہیں؟"
        )
    if is_hindi:
        return (
            "आपके संदेश के लिए धन्यवाद! मैं इस समय ऑनलाइन AI मॉडल का उपयोग नहीं कर सकता, लेकिन फिर भी मैं आपकी योजना बनाने में मदद कर सकता हूँ।\n\n"
            "कृपया और जानकारी साझा करें ताकि बेहतर सलाह दे सकूँ:\n"
            "- आपकी वर्तमान शैक्षिक योग्यता और विषय\n"
            "- वह क्षेत्र या देश जिसमें आप रुचि रखते हैं\n"
            "- आप किस प्रकार के कार्यक्रम के लिए आवेदन करना चाहते हैं\n\n"
            "Follow-up questions:\n"
            "1. क्या आप अभी छात्र हैं या नौकरी कर रहे हैं?\n"
            "2. आपके अगले 3-5 साल के करियर लक्ष्य क्या हैं?"
        )
    return (
        "Thanks for your message! I'm currently unable to reach the online AI models, "
        "but I'm still here to help you plan your next steps.\n\n"
        "To give you the most relevant guidance, please share a bit more:\n"
        "- Your current education level and field of study\n"
        "- The career direction or country you're interested in\n"
        "- The type of program you want to apply for (bachelor's / master's / PhD)\n\n"
        "Follow-up questions:\n"
        "1. Are you currently a student or working professional?\n"
        "2. What are your career goals for the next 3-5 years?"
    )


MIN_TURNS_FOR_FINAL = 10  # at least 10 user answers before final recommendation
MAX_TURNS = 18  # force final recommendation after 18 user answers


def _is_scholarship_query(text: str) -> bool:
    """Detect if the user is asking about scholarships, funding, or financial aid."""
    keywords = [
        "scholarship", "scholarships", "funding", "grant", "financial aid", "tuition fee",
        "study abroad", "fully funded", "phd funding", "masters funding", "bachelor funding",
        "undergraduate", "bachelor", "bachelors", "fellowship",
        "bursary", "burslari", "stipend", "scholar",
        "mext", "csc", "pearson scholarship", "stamps scholarship",
        "turkiye", "japan scholarship", "china scholarship", "canada scholarship"
    ]
    lowered = text.lower()
    return any(k in lowered for k in keywords)


def _is_on_topic(text: str) -> bool:
    """Check if the user's message is related to education, career, or scholarships."""
    keywords = [
        "scholarship", "scholarships", "funding", "grant", "financial aid", "tuition",
        "study abroad", "fully funded", "fellowship", "bursary", "stipend",
        "undergraduate", "bachelor", "masters", "phd", "doctorate",
        "university", "college", "school", "degree", "program", "course", "major",
        "career", "job", "work", "profession", "internship", "field",
        "cv", "resume", "sop", "personal statement", "essay", "cover letter",
        "ielts", "toefl", "gre", "sat", "gmat", "test",
        "apply", "application", "admission", "enroll", "enrol",
        "visa", "study", "abroad", "education", "academic",
        "recommend", "suggestion", "advice", "guidance", "help",
        "mext", "csc", "chevening", "fulbright", "erasmus", "daad", "kaist",
        "turkiye", "burslari", "pearson",
        # Chinese keywords
        "大学", "奖学金", "留学", "学习", "专业", "职业", "学位", "研究", "申请", "录取",
        # Urdu / Arabic keywords
        "تعلیم", "تعلیمات", "اسکالرشپ", "اسکالرشب", "یونیورسٹی",
        "کیریئر", "مستقبل", "داخلہ", "ترکی", "چین", "جاپان", "کینیڈا",
        "مدد", "بتائیں", "برس", "فنڈنگ",
        # Hindi (Devanagari) keywords
        "शिक्षा", "करियर", "यूनिवर्सिटी", "स्कॉलरशिप", "पढ़ाई", "प्रवेश", "मदद",
        # Turkish keywords
        "merhaba", "selam", "burs", "eğitim", "üniversite",
        "hello", "hi", "hey", "salam", "namaste",
    ]
    lowered = text.lower()
    return any(k in lowered for k in keywords)


def _off_topic_redirect(language: str) -> str:
    """Return a polite domain-restriction message in the detected language."""
    if "Chinese" in language:
        return "\u6211\u662f\u4e13\u4e1a\u7684 AI \u804c\u4e1a\u4e0e\u5956\u5b66\u91d1\u987e\u95ee\u3002\u6211\u53ea\u80fd\u4e3a\u60a8\u63d0\u4f9b\u6559\u80b2\u8def\u5f84\u3001\u5f55\u53d6\u548c\u5956\u5b66\u91d1\u673a\u4f1a\u65b9\u9762\u7684\u5e2e\u52a9\u3002\u8bf7\u968f\u65f6\u5411\u6211\u54a8\u8be2\u76f8\u5173\u95ee\u9898\uff01"
    if "Urdu" in language or "Arabic" in language:
        return "\u0645\u06cc\u06ba \u0627\u06cc\u06a9 \u0645\u062e\u0635\u0648\u0635 AI \u06a9\u06cc\u0631\u06cc\u0626\u0631 \u0627\u0648\u0631 \u0627\u0633\u06a9\u0648\u0644\u0631\u0634\u0628 \u0645\u0634\u06cc\u0631 \u06c1\u0648\u06ba\u06d4 \u0645\u06cc\u06ba \u0635\u0631\u0641 \u062a\u0639\u0644\u06cc\u0645\u06cc \u0631\0627\u0633\u062a\u0648\u06ba\u060c \062f\0627\062e\0644\0648\u06ba \u0627\0648\0631 \0627\0633\06a9\0648\0644\0631\0634\0628 \06a9\06d2 \0645\0648\0627\0642\0639\0648\06ba \0645\06cc\06ba \0622\067e \06a9\06cc \0645\062f\062f \06a9\0631 \0633\06a9\062a\0627 \06c1\0648\06ba\u06d4"
    if "Hindi" in language:
        return "\u092e\u0948\u0902 \u090f\u0915 \u0938\u092e\u0930\u094d\u092a\u093f\u0924 AI \u0915\u0930\u093f\u092f\u0930 \u0914\u0930 \u0938\u094d\u0915\u0949\u0932\u0930\u0936\u093f\u092a \u0938\u0932\u093e\u0939\u0915\093e\0930 \u0939\0942\u0901\u0964 \u092e\u0948\u0902 \u0915\u0947\u0935\u0932 \u0936\u0948\u0915\্\u0937\u093f\u0915 \u092e\u093e\u0930\्\u0917\u094b\u0902, \u092a\्\u0930\u0935\े\u0936 \u0914\u0930 \स\्\u0915\u0949\u0932\u0930\u0936\u093f\प \u0905\u0935\u0938\u0930\ो\u0902 \u092e\u0947\ं \u0906\u092a\u0915\u0940 \u0938\ह\ा\u092f\u0924\u093e \u0915\u0930 \u0938\u0915\u0924\u093e \u0939\u0942\u0901\u0964"
    if "Turk" in language:
        return "Ben kariyer ve burs konusunda uzmanla\u015fm\u0131\u015f bir yapay zeka dan\u0131\u015fman\u0131y\u0131m. Yaln\u0131zca e\u011fitim yollar\u0131, kabul ve burs f\u0131rsatlar\u0131 konusunda yard\u0131mc\u0131 olabilirim."
    return "I am a dedicated AI Career & Scholarship Advisor. I can only assist you with educational pathways, admissions, and scholarship opportunities. Please ask me about scholarships, careers, or study abroad!"


def _build_rag_context(user_message: str) -> str:
    """Retrieve and format scholarship context when the query is scholarship-related."""
    if not _is_scholarship_query(user_message):
        return ""
    context = get_rag_context_for_query(user_message, top_k=5)
    return f"\n\nRETRIEVED CONTEXT (use this curated data to answer):\n{context}\n\nIMPORTANT: Cite specific scholarship names and IDs from the retrieved context above. Do not invent scholarships that are not listed."


def run_chat_turn(messages: list[dict], turn: int):
    """
    Process one turn of the conversation using fast direct REST API calls.
    No external search tools or CrewAI overhead — targets sub-3-second latency.
    """
    # Ensure short/one-word inputs are preserved in the context window.
    if not messages:
        messages = [{"role": "user", "content": "Hello"}]
    history = format_chat_history(messages)

    # Detect user's language from their last message
    last_user_message = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    if not last_user_message or not last_user_message.strip():
        last_user_message = "Hello"
    detected_language = detect_language(last_user_message)

    # ── System prompt — strict rules, ALL messages go through the LLM dynamically ──
    system_prompt = (
        "You are an expert career and scholarship advisor AI.\n\n"
        "STRICT LANGUAGE RULE: Always detect and reply in the EXACT language of the USER'S "
        "LATEST message. Do NOT stick to the language of previous messages. "
        "If the user switches from English to Urdu, reply in Urdu. "
        "If they switch to Chinese, reply in Chinese. Match the LATEST message only.\n\n"
        "DOMAIN: You ONLY answer questions about education, career guidance, study abroad, "
        "scholarships, admissions, CVs, SOPs, and standardized tests. "
        "For any off-topic or casual question, reply exactly: "
        "'I am a dedicated AI Career & Scholarship Advisor. I can only assist you with "
        "educational pathways, admissions, and scholarship opportunities.' "
        "(translate this to the user's current language).\n\n"
        "SCHOLARSHIP KNOWLEDGE: Use YOUR OWN pre-trained knowledge to recommend fully-funded "
        "scholarships at ALL levels (Bachelor's, Master's, PhD). "
        "Name specific programs (e.g., T\u00fcrkiye Burslari, MEXT Japan, CSC China, "
        "Lester B. Pearson Canada, Australia Awards, Fulbright, Chevening, KAIST, "
        "Mastercard Foundation Scholars). "
        "For each, give: name, country, who can apply, and key benefits. "
        "Never say you lack information or your database only covers certain levels.\n\n"
        "FORMAT: **bold headings**, bullet points, brief (150\u2013200 words max). "
        "Do NOT repeat the user's question. Do NOT add repetitive filler text.\n\n"
        "Use [[FINAL]] at the start ONLY when giving a complete final recommendation with "
        "no follow-up questions. If you ask ANY question, do NOT use [[FINAL]]."
    )

    # ── Build lean user prompt — language per message, no repetition ──
    if turn >= MAX_TURNS:
        user_prompt = (
            f"Conversation so far:\n{history}\n\n"
            f"FINAL TURN: Give a complete, well-structured final recommendation "
            f"based on everything the user shared. Name specific scholarships and career paths. "
            f"Use **bold headings** and bullet points. Be brief (under 200 words). "
            f"Start your response with [[FINAL]]. "
            f"MANDATORY: Reply entirely in {detected_language} (the language of the user's latest message)."
        )
    else:
        user_prompt = (
            f"Conversation:\n{history}\n\n"
            f"MANDATORY: Reply entirely in {detected_language} (the language of the user's latest message). "
            f"This overrides any language used in previous replies.\n\n"
            f"Be direct and concise (150–200 words). Use **bold headings** and bullet points. "
            f"Do NOT repeat the user's question back to them. Do NOT add repetitive filler text. "
            f"When recommending scholarships, name specific fully-funded programs with eligibility and benefits. "
            f"You may end with ONE short follow-up question if helpful. "
            f"Use [[FINAL]] only if turn >= {MIN_TURNS_FOR_FINAL} AND you are giving a final recommendation. "
            f"This is turn {turn} of {MAX_TURNS}."
        )

    # Build fast fallback chain: Groq direct REST first (fastest), then Gemini.
    # HuggingFace skipped (DNS unavailable in this environment).
    groq_models = [
        m.strip().replace("groq/", "")
        for m in os.getenv("GROQ_MODELS", "groq/openai/gpt-oss-120b,llama-3.1-8b-instant").split(",")
        if m.strip()
    ]
    attempts: list[dict] = []

    # Groq keys first — direct REST, no CrewAI overhead, sub-3s latency.
    for idx in range(len(_collect_groq_keys())):
        for model in groq_models:
            attempts.append({"provider": "groq", "key_index": idx, "model": model})

    # Gemini as secondary fallback.
    gemini_models = [
        m.strip()
        for m in os.getenv("GEMINI_MODELS", "gemini-3.6-flash,gemini-2.0-flash").split(",")
        if m.strip()
    ]
    for idx in range(len(_collect_env_keys("GEMINI_API_KEY"))):
        for model in gemini_models:
            attempts.append({"provider": "gemini", "key_index": idx, "model": model})

    print(f"[chat] turn={turn}, attempts={len(attempts)}, lang={detected_language}")

    raw_result = ""
    last_error = None
    t0 = time.time()
    for attempt in attempts:
        provider = attempt["provider"]
        key_index = attempt["key_index"]
        model = attempt["model"]
        try:
            if provider == "groq":
                # Direct Groq REST API — no CrewAI, no LiteLLM, sub-3s.
                groq_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                raw_result = _groq_chat_completion(groq_messages, key_index=key_index, model=model, max_tokens=2048, timeout=10)
                elapsed = time.time() - t0
                logger.info("Groq direct (key %d, model %s) succeeded in %.2fs", key_index + 1, model, elapsed)
                break

            if provider == "gemini":
                gemini_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                raw_result = _gemini_chat_completion(gemini_messages, key_index=key_index, model=model, max_tokens=2048)
                elapsed = time.time() - t0
                logger.info("Gemini SDK (key %d, model %s) succeeded in %.2fs", key_index + 1, model, elapsed)
                break
        except Exception as e:
            last_error = e
            elapsed = time.time() - t0
            print(f"[chat] attempt failed ({elapsed:.2f}s): {provider} key={key_index} model={model} err={e}")
            continue
    else:
        # All online providers failed: return a structured, polite message.
        logger.error("All LLM providers failed. Returning deterministic offline message.")
        raw_result = _deterministic_offline_reply(last_user_message, detected_language)

    elapsed = time.time() - t0
    print(f"[chat] Response returned in {elapsed:.2f}s")

    is_final = raw_result.strip().startswith("[[FINAL]]")
    reply = raw_result.replace("[[FINAL]]", "").strip()

    # Enforce minimum conversation length: ignore early [[FINAL]] markers.
    if turn < MIN_TURNS_FOR_FINAL:
        is_final = False

    # Force final if maximum turns reached.
    if turn >= MAX_TURNS:
        is_final = True

    return reply, is_final


def run_career_scholarship_crew(user_profile: str, answers: str = ""):
    """Legacy endpoint helper: generate concise career and scholarship advice."""
    context = f"User profile:\n{user_profile}\n\nClarifying answers:\n{answers}" if answers else user_profile

    task1 = Task(
        description=(
            f"Based on the context below, suggest 2-3 best career paths. "
            f"For each path, give: role name, why it fits, and 2 key skills to build. "
            f"Keep it short and scannable.\n\n{context}"
        ),
        expected_output="Concise list of 2-3 career paths with fit and key skills.",
        agent=career_counselor
    )

    task2 = Task(
        description=(
            f"Based on the context below, list 2-3 relevant scholarships or funding programs. "
            f"For each: name, eligibility, and one clear next step. "
            f"Keep it short and actionable.\n\n{context}"
        ),
        expected_output="Concise list of 2-3 scholarships with eligibility and next steps.",
        agent=scholarship_matcher
    )

    crew = Crew(
        agents=[career_counselor, scholarship_matcher],
        tasks=[task1, task2],
        process=Process.sequential
    )

    with _crew_lock:
        result = kickoff_with_retries(crew)
    return str(result)


# Startup smoke test: verify which keys are actively returning responses.
# This runs after all helper functions are defined.
print("[startup] Running key smoke tests with 'Hello' prompt...")
for idx in range(len(_gemini_keys)):
    result = _test_key("gemini", idx)
    status = "OK" if result["ok"] else f"FAIL: {result.get('error', 'unknown')}"
    print(f"  Gemini key {idx + 1}: {status}")
for idx in range(len(_groq_keys)):
    result = _test_key("groq", idx)
    status = "OK" if result["ok"] else f"FAIL: {result.get('error', 'unknown')}"
    print(f"  Groq key {idx + 1}: {status}")
for idx in range(len(_hf_tokens)):
    result = _test_key("huggingface", idx)
    status = "OK" if result["ok"] else f"FAIL: {result.get('error', 'unknown')}"
    print(f"  Hugging Face token {idx + 1}: {status}")
