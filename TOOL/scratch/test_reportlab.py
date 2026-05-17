from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

fonts_dir = Path("fonts").absolute()
regular_path = str(fonts_dir / "Montserrat-Regular.ttf")

pdfmetrics.registerFont(TTFont('Montserrat', regular_path))

c = canvas.Canvas("scratch/test_reportlab.pdf")
c.setFont('Montserrat', 12)
c.drawString(100, 700, "Tiếng Việt: á à ả ã ạ, đ, ê ế ề ể ễ ệ")
c.save()
print("ReportLab PDF generated.")
