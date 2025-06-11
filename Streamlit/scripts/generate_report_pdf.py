# Requires: pip install weasyprint
from weasyprint import HTML

html_path = "mlb_daily_leaders_2025-05-09.html"
pdf_path = "example.pdf"

HTML(html_path).write_pdf(pdf_path)
print(f"PDF generated and saved at {pdf_path}") 