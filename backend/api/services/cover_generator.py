from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CoverArtGenerator:
    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir
        self.base_image_path = assets_dir / "listenbrainz_cover_base.png"
        
        # Ensure assets dir exists
        if not self.assets_dir.exists():
            self.assets_dir.mkdir(parents=True, exist_ok=True)

    def generate_cover(self, title: str, subtitle: str = "") -> bytes:
        """
        Generates a cover image with title overlay.
        Returns bytes of the JPEG image.
        """
        try:
            if not self.base_image_path.exists():
                logger.error(f"Base image not found at {self.base_image_path}")
                return None

            # Open base image
            with Image.open(self.base_image_path) as img:
                img = img.convert("RGB")
                draw = ImageDraw.Draw(img)
                width, height = img.size

                # Improved Font Sizing & Layout
                # Goal: 
                # Title: Large, Multiline if needed, Top/Center
                # User: Large, Distinct color/weight, Bottom/Center

                # Font Sizes (Scale relative to width=640 usually)
                title_size = int(width / 7)    # Slightly smaller to fit words
                subtitle_size = int(width / 9) # MUCH larger than before (was /15)

                font_path = self.assets_dir / "font.ttf"
                if font_path.exists():
                    font = ImageFont.truetype(str(font_path), title_size)
                    sub_font = ImageFont.truetype(str(font_path), subtitle_size)
                else:
                    # Try linux paths
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_size)
                        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", subtitle_size) # Bold for user too
                    except:
                        font = ImageFont.load_default()
                        sub_font = ImageFont.load_default()

                # --- Draw Title (Multiline) ---
                import textwrap
                # Wrap text to ~10-12 chars per line roughly? Or measure it?
                # Pillow doesn't auto-wrap. Let's wrap fairly aggressively for "Weekly Exploration" -> 2 lines
                lines = textwrap.wrap(title, width=10) 
                
                # Calculate total height of title block
                line_heights = []
                line_spacing = 10
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_heights.append(bbox[3] - bbox[1])
                
                total_title_h = sum(line_heights) + (len(lines) - 1) * line_spacing
                
                # --- Draw Subtitle (User) ---
                sub_w = 0
                sub_h = 0
                if subtitle:
                    sbbox = draw.textbbox((0, 0), subtitle, font=sub_font)
                    sub_w = sbbox[2] - sbbox[0]
                    sub_h = sbbox[3] - sbbox[1]

                # --- Positioning ---
                # Layout:
                # [ Spacer ]
                # [ Title Block ]
                # [ Spacer ]
                # [ User Block ]
                # [ Spacer ]
                
                # Total content height
                content_gap = 50 # Gap between title and user
                total_content_h = total_title_h + content_gap + sub_h
                
                start_y = (height - total_content_h) / 2
                
                # Draw Title Lines
                current_y = start_y
                for i, line in enumerate(lines):
                    lbbox = draw.textbbox((0, 0), line, font=font)
                    lw = lbbox[2] - lbbox[0]
                    lx = (width - lw) / 2
                    
                    # Shadow
                    shadow = 4
                    draw.text((lx+shadow, current_y+shadow), line, font=font, fill=(0,0,0))
                    draw.text((lx, current_y), line, font=font, fill=(255, 255, 255))
                    
                    current_y += line_heights[i] + line_spacing
                
                # Draw User
                if subtitle:
                    user_y = current_y + content_gap - line_spacing # Adjust for last spacing
                    sx = (width - sub_w) / 2
                    
                    # User: Yellow/Gold or just distinct White? 
                    # Let's keep white but maybe a different opacity or just BRIGHT
                    # Shadow
                    draw.text((sx+3, user_y+3), subtitle, font=sub_font, fill=(0,0,0))
                    # Text
                    draw.text((sx, user_y), subtitle, font=sub_font, fill=(255, 220, 100)) # Slight Gold tint for User

                # Save to bytes
                from io import BytesIO
                out_buffer = BytesIO()
                img.save(out_buffer, format="JPEG", quality=90)
                return out_buffer.getvalue()

        except Exception as e:
            logger.error(f"Failed to generate cover: {e}")
            return None
