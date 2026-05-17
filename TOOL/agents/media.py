"""MediaAgent: generate Facebook posts from an approved chapter."""

from __future__ import annotations

import config
from agents.base import BaseAgent
from db.schemas import PostDraft, PostType


class MediaAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model=config.MEDIA_MODEL,
            system_prompt_path=config.PROMPTS_DIR / "media_system.md",
            temperature=0.7,
            max_tokens=2000,
        )

    def generate_posts(self, chapter_id: str, chapter_content: str) -> list[PostDraft]:
        user_prompt = f"Hãy tạo nội dung marketing cho chapter sau:\n\n---\n\n{chapter_content}"
        response = self.complete(user_prompt)
        
        # Split by --- to get parts
        parts = [p.strip() for p in response.content.split("---") if p.strip()]
        
        posts = []
        # Mapping keywords to PostType
        type_keywords = {
            PostType.SHORT: ["SHORT POST", "BÀI VIẾT NGẮN"],
            PostType.INFORMATIVE: ["INFORMATIVE", "CHUYÊN SÂU", "THÔNG TIN"],
        }
        
        for part in parts:
            content = part
            hero_object = "Một quyển sách bay bổng"
            color_palette = "Neon Blue & Purple"
            detected_type = None
            
            # Detect type by looking at the first few lines or headers
            upper_part = part.upper()
            for p_type, keywords in type_keywords.items():
                if any(kw in upper_part[:100] for kw in keywords):
                    detected_type = p_type
                    break
            
            # Fallback to order if not detected
            if not detected_type:
                index = len(posts)
                fallbacks = [PostType.SHORT, PostType.INFORMATIVE]
                if index < len(fallbacks):
                    detected_type = fallbacks[index]
                else:
                    continue # Skip extra parts

            # Extract HERO_OBJECT and COLOR_PALETTE
            if "HERO_OBJECT:" in part:
                p_parts = part.split("HERO_OBJECT:")
                content = p_parts[0].strip()
                meta_section = p_parts[1].strip()
                if "COLOR_PALETTE:" in meta_section:
                    m_parts = meta_section.split("COLOR_PALETTE:")
                    hero_object = m_parts[0].strip()
                    color_palette = m_parts[1].strip()
                else:
                    hero_object = meta_section

            # Assemble the final poster prompt
            image_prompt = self._assemble_poster_prompt(hero_object, color_palette)
            
            # Strip the header
            content = self._strip_header(content)
            
            posts.append(PostDraft(
                chapter_id=chapter_id,
                type=detected_type,
                content=content,
                image_prompt=image_prompt
            ))
            
        return posts

    def generate_single_post(self, chapter_id: str, chapter_content: str, post_type: PostType) -> PostDraft:
        type_labels = {
            PostType.SHORT: "Short Post (bài viết ngắn kèm emoji)",
            PostType.INFORMATIVE: "Informative Post (bài viết chuyên sâu)",
            PostType.PROMO: "Promo Post (bài viết quảng bá dự án)",
        }
        label = type_labels.get(post_type, post_type.value)
        
        user_prompt = (
            f"Hãy tạo DUY NHẤT một bài viết loại **{label}** cho chapter sau:\n\n"
            f"---\n\n{chapter_content}\n\n"
            f"Đảm bảo kết thúc bằng:\n"
            f"HERO_OBJECT: [mô tả]\n"
            f"COLOR_PALETTE: [mô tả]"
        )
        response = self.complete(user_prompt)
        
        content = response.content
        hero_object = "Một đối tượng siêu thực"
        color_palette = "Vibrant Neon"
        
        if "HERO_OBJECT:" in content:
            p_parts = content.split("HERO_OBJECT:")
            content = p_parts[0].strip()
            meta_section = p_parts[1].strip()
            if "COLOR_PALETTE:" in meta_section:
                m_parts = meta_section.split("COLOR_PALETTE:")
                hero_object = m_parts[0].strip()
                color_palette = m_parts[1].strip()
            else:
                hero_object = meta_section

        image_prompt = self._assemble_poster_prompt(hero_object, color_palette)
        content = self._strip_header(content)
        
        return PostDraft(
            chapter_id=chapter_id,
            type=post_type,
            content=content,
            image_prompt=image_prompt
        )

    def generate_project_promo(self, project_id: int, project_name: str, project_desc: str) -> PostDraft:
        """Generates a promotional post for the project itself."""
        user_prompt = (
            f"Hãy tạo một bài viết quảng bá (PROMO POST) cho dự án sau:\n\n"
            f"Tên dự án: {project_name}\n"
            f"Mô tả: {project_desc}\n\n"
            f"Hãy nhấn mạnh sứ mệnh giáo dục và mục đích thiện nguyện của dự án.\n"
            f"Đảm bảo kết thúc bằng:\n"
            f"HERO_OBJECT: [mô tả]\n"
            f"COLOR_PALETTE: [mô tả]"
        )
        response = self.complete(user_prompt)
        
        content = response.content
        hero_object = "Biểu tượng của sự sẻ chia và tri thức"
        color_palette = "Deep Navy & Golden Yellow"
        
        if "HERO_OBJECT:" in content:
            p_parts = content.split("HERO_OBJECT:")
            content = p_parts[0].strip()
            meta_section = p_parts[1].strip()
            if "COLOR_PALETTE:" in meta_section:
                m_parts = meta_section.split("COLOR_PALETTE:")
                hero_object = m_parts[0].strip()
                color_palette = m_parts[1].strip()
            else:
                hero_object = meta_section

        image_prompt = self._assemble_poster_prompt(hero_object, color_palette)
        content = self._strip_header(content)
        
        return PostDraft(
            project_id=project_id,
            type=PostType.PROMO,
            content=content,
            image_prompt=image_prompt
        )

    def _assemble_poster_prompt(self, hero_object: str, color_palette: str) -> str:
        return (
            f"A professional digital collage poster featuring a central, surreal {hero_object}.\n\n"
            f"Surface & Texture: The image must exhibit a heavy, tactile Risograph print texture with visible film grain and coarse noise. "
            f"It should look like it was printed on uncoated, matte art paper with a slight yellowish off-white base. No smooth digital gradients or plastic-looking surfaces.\n\n"
            f"Lighting & Color: Vibrant but distressed dithered gradients. Light must bleed using soft aura glows and inner glows that soften the edges of all shapes. "
            f"Use a high-contrast, neon {color_palette} that feels like ink soaking into paper fibers.\n\n"
            f"Compositional Layers: A deep, multi-layered layout. Background: A faint, distressed isometric grid mixed with blurred abstract silhouettes. "
            f"Middle-ground: The main hero object with a subtle soft-focus glow. Foreground: Floating dust particles, geometric sparkles, and motion-blurred abstract blobs to create immense atmospheric depth.\n\n"
            f"Design Constraint: Strategic negative space must be preserved for typography: a dedicated zone for a heavy, blocky Sans-Serif title at the top, and a contrasting area for an elegant, thin flowing Script accent. "
            f"Objects must have a soft glass drop shadow or a subtle glowing aura to pop from the background.\n\n"
            f"Vibe: Surreal, nostalgic, lo-fi aesthetic with a deep depth of field. --ar 2:3"
        )

    @staticmethod
    def _strip_header(text: str) -> str:
        import re
        # Remove lines like "### 1. CAROUSEL" or "### 2. SHORT POST"
        return re.sub(r"^###\s*\d+\..*?\n", "", text, flags=re.MULTILINE).strip()
