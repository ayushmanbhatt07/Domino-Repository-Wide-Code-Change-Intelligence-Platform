import os
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from .models import ChangePlan
from .prompts import get_planner_prompt, get_patch_prompt

class ChangePlannerLLMService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        if self.api_key:
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=0.1,
                google_api_key=self.api_key,
                timeout=60.0,
                max_retries=2
            )
            self.structured_llm = self.llm.with_structured_output(ChangePlan)
        else:
            self.llm = None
            self.structured_llm = None

    def generate_plan(self, request: str, context: str) -> Optional[ChangePlan]:
        if not self.structured_llm:
            return None
            
        prompt = get_planner_prompt()
        chain = prompt | self.structured_llm
        
        try:
            return chain.invoke({"request": request, "context": context})
        except Exception as e:
            print(f"Change Planning Error: {e}")
            return None

    def generate_patch(self, request: str, plan_json: str, context: str) -> Optional[str]:
        if not self.llm:
            return None
            
        prompt = get_patch_prompt()
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            return chain.invoke({
                "request": request,
                "plan": plan_json,
                "context": context
            })
        except Exception as e:
            print(f"Patch Generation Error: {e}")
            return None
