from __future__ import annotations
import json
from pathlib import Path
import config
from agents.base import BaseAgent
from litellm import completion

class SocialAdvisorAgent(BaseAgent):
    """AI Advisor for social media strategy and audience growth."""
    
    def __init__(self):
        super().__init__(
            model=config.ADVISOR_MODEL,
            system_prompt_path=config.PROMPTS_DIR / "advisor_system.md",
            temperature=0.7,
            max_tokens=2000,
        )

    def get_advice(self, user_query: str, history: list[dict[str, str]] = None) -> str:
        """Generates strategic advice for social media growth."""
        
        api_key = config.require_gemini_key()

        # Load real-time context if available
        context_path = config.DATA_DIR / "facebook_context.json"
        fb_context = ""
        if context_path.exists():
            try:
                data = json.loads(context_path.read_text(encoding="utf-8"))
                fb_context = f"\n\n[DỮ LIỆU THỰC TẾ TỪ FACEBOOK - CẬP NHẬT {data.get('timestamp', 'N/A')}]\n{data.get('summary', '')}"
            except:
                pass

        messages = [
            {"role": "system", "content": self.system_prompt + fb_context}
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_query})
        
        try:
            response = completion(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=api_key,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Lỗi cố vấn: {e}"
