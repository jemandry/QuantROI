#!/usr/bin/env python3
"""
Convert CAUSAL_AI_SYSTEM_ANALYSIS.md to PDF format
"""

import markdown
from weasyprint import HTML, CSS
from pathlib import Path

def convert_md_to_pdf(md_file_path, pdf_file_path):
    """Convert markdown file to PDF with proper styling"""
    
    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    css_style = """
    @page {
        size: A4;
        margin: 1in;
    }
    
    body {
        font-family: 'Arial', sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 100%;
    }
    
    h1 {
        color: #2c3e50;
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
        margin-top: 30px;
        font-size: 24px;
    }
    
    h2 {
        color: #34495e;
        border-bottom: 2px solid #95a5a6;
        padding-bottom: 8px;
        margin-top: 25px;
        font-size: 20px;
    }
    
    h3 {
        color: #2c3e50;
        margin-top: 20px;
        font-size: 16px;
    }
    
    h4 {
        color: #7f8c8d;
        margin-top: 15px;
        font-size: 14px;
    }
    
    p {
        margin-bottom: 12px;
        text-align: justify;
    }
    
    ul, ol {
        margin-bottom: 15px;
        padding-left: 25px;
    }
    
    li {
        margin-bottom: 5px;
    }
    
    code {
        background-color: #f8f9fa;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
    }
    
    pre {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #3498db;
        overflow-x: auto;
        margin: 15px 0;
    }
    
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 15px 0;
    }
    
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    
    th {
        background-color: #f2f2f2;
        font-weight: bold;
    }
    
    .success {
        color: #27ae60;
        font-weight: bold;
    }
    
    .warning {
        color: #f39c12;
        font-weight: bold;
    }
    
    .error {
        color: #e74c3c;
        font-weight: bold;
    }
    
    .highlight {
        background-color: #fff3cd;
        padding: 10px;
        border-left: 4px solid #ffc107;
        margin: 10px 0;
    }
    
    blockquote {
        border-left: 4px solid #3498db;
        margin: 15px 0;
        padding-left: 15px;
        color: #7f8c8d;
        font-style: italic;
    }
    
    hr {
        border: none;
        border-top: 2px solid #ecf0f1;
        margin: 25px 0;
    }
    """
    
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Causal AI Trading System Analysis</title>
        <style>{css_style}</style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    html_doc = HTML(string=full_html)
    html_doc.write_pdf(pdf_file_path)
    
    print(f"Successfully converted {md_file_path} to {pdf_file_path}")

if __name__ == "__main__":
    md_file = Path("CAUSAL_AI_SYSTEM_ANALYSIS.md")
    pdf_file = Path("CAUSAL_AI_SYSTEM_ANALYSIS.pdf")
    
    if not md_file.exists():
        print(f"Error: {md_file} not found!")
        exit(1)
    
    try:
        convert_md_to_pdf(md_file, pdf_file)
        print(f"PDF created successfully: {pdf_file}")
    except Exception as e:
        print(f"Error converting to PDF: {e}")
        exit(1)
