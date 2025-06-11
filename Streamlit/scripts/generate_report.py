from xhtml2pdf import pisa

def convert_html_to_pdf(html_path, pdf_path):
    with open(html_path, "r") as html_file:
        html_string = html_file.read()
    with open(pdf_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)
    return not pisa_status.err
if convert_html_to_pdf("mlb_daily_leaders_2025-05-09.html", "example.pdf"):
    print("PDF generated and saved at example.pdf")
else:
    print("PDF generation failed")
