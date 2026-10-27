import os
from typing import Optional
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None
try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None
from .models import AIExplanation
from .prompts import get_reasoning_prompt

def message_text(res) -> str:
    """Newer Gemini integrations return content as a list of blocks; flatten to a string."""
    content = getattr(res, "content", res)
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type", "text") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)

class LLMService:
    def __init__(self):
        # Groq is preferred when GROQ_API_KEY is set; otherwise fall back to Gemini via GOOGLE_API_KEY
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.api_key = os.getenv("GOOGLE_API_KEY")

        if self.groq_key and ChatGroq:
            self.model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
            self.llm = ChatGroq(
                model=self.model_name,
                temperature=0.2,
                api_key=self.groq_key,
                timeout=60.0,
                max_retries=2
            )
        elif self.api_key and ChatGoogleGenerativeAI:
            self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=0.2,
                google_api_key=self.api_key,
                timeout=60.0,
                max_retries=2
            )
        else:
            self.llm = None

        self.structured_llm = self.llm.with_structured_output(AIExplanation) if self.llm else None

    def generate_reasoning(self, context: str) -> Optional[AIExplanation]:
        if not self.structured_llm:
            return None # Fail gracefully if provider is unavailable
            
        prompt = get_reasoning_prompt()
        chain = prompt | self.structured_llm
        
        try:
            res = chain.invoke({"context": context})
            return res
        except Exception as e:
            print(f"LLM Reasoning Error: {e}")
            return None
