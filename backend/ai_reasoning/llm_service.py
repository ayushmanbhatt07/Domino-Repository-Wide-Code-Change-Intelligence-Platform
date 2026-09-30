import os
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from .models import AIExplanation
from .prompts import get_reasoning_prompt

class LLMService:
    def __init__(self):
        # We assume GOOGLE_API_KEY is in the environment
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        if self.api_key:
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=0.2,
                google_api_key=self.api_key,
                timeout=30.0,
                max_retries=2
            )
            self.structured_llm = self.llm.with_structured_output(AIExplanation)
        else:
            self.llm = None
            self.structured_llm = None

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
