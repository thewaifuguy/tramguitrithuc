from __future__ import annotations
import config
from agents.base import BaseAgent
from db.schemas import RejectReason, RejectEntry

class CriticAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model=config.CRITIC_MODEL,
            system_prompt_path=config.PROMPTS_DIR / "critic_system.md",
            temperature=0.3, # Lower temperature for consistency
            max_tokens=1000,
        )

    def review_draft(self, topic: str, content: str) -> RejectEntry | None:
        """
        Reviews a chapter draft. 
        Returns RejectEntry if corrections are needed, else None (Approved).
        """
        user_prompt = f"Hãy đánh giá chapter về chủ đề: {topic}\n\nNội dung:\n{content}"
        response = self.complete(user_prompt)
        
        text = response.content.upper()
        
        # Look for [APPROVED]
        if "[APPROVED]" in text or "[DUYỆT]" in text:
            return None
            
        # Look for [REJECT] and reason
        reason = RejectReason.OTHER
        note = response.content
        
        for r in RejectReason:
            if f"[{r.value.upper()}]" in text:
                reason = r
                break
        
        # Clean up note if it has the code
        import re
        note = re.sub(r"\[.*?\]", "", note).strip()
        
        return RejectEntry(reason_code=reason, note=note)
