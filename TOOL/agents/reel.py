from __future__ import annotations
import config
from agents.base import BaseAgent

class ReelAgent(BaseAgent):
    """Expert in short-form video scripts (Reels/TikTok/Shorts)."""
    
    def __init__(self):
        super().__init__(
            model=config.REEL_MODEL,
            system_prompt_path=config.PROMPTS_DIR / "reel_system.md",
            temperature=0.8,
            max_tokens=3000,
        )

    def generate_script(self, topic: str, core_story: str = "Chữa lành", tone: str = "Hóm hỉnh") -> str:
        """Generates a detailed reel script based on topic and style."""
        user_prompt = (
            f"Chủ đề: {topic}\n"
            f"Core Story: {core_story}\n"
            f"Tone: {tone}\n"
        )
        response = self.complete(user_prompt)
        return response.content
