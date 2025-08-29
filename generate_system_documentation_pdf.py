#!/usr/bin/env python3
"""
Generate PDF documentation for QuantROI System Components
"""

import os
import subprocess
import sys
from pathlib import Path

def generate_pdf_documentation():
    """Generate PDF from markdown documentation"""
    
    try:
        subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
        print("✅ Pandoc is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Pandoc not found. Installing...")
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'pandoc', 'texlive-latex-base', 'texlive-fonts-recommended'], check=True)
            print("✅ Pandoc installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install pandoc: {e}")
            return False
    
    docs_dir = Path(__file__).parent / 'docs'
    input_file = docs_dir / 'QuantROI_System_Components_Documentation.md'
    output_file = docs_dir / 'QuantROI_System_Components_Documentation.pdf'
    
    docs_dir.mkdir(exist_ok=True)
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return False
    
    try:
        cmd = [
            'pandoc',
            str(input_file),
            '-o', str(output_file),
            '--pdf-engine=pdflatex',
            '--variable', 'geometry:margin=0.8in',
            '--variable', 'fontsize=10pt',
            '--variable', 'documentclass=article',
            '--variable', 'colorlinks=true',
            '--variable', 'linkcolor=blue',
            '--variable', 'urlcolor=blue',
            '--toc',
            '--toc-depth=4',
            '--number-sections',
            '--highlight-style=github'
        ]
        
        print(f"🔄 Generating comprehensive PDF: {output_file}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Comprehensive PDF generated successfully: {output_file}")
            print(f"📄 File size: {output_file.stat().st_size / 1024:.1f} KB")
            return True
        else:
            print(f"❌ PDF generation failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return generate_alternative_pdf()
            
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        return generate_alternative_pdf()

def generate_alternative_pdf():
    """Generate PDF using Python libraries as fallback"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import black, blue, red
        
        print("🔄 Generating PDF using ReportLab...")
        
        docs_dir = Path(__file__).parent / 'docs'
        input_file = docs_dir / 'QuantROI_System_Components_Documentation.md'
        output_file = docs_dir / 'QuantROI_System_Components_Documentation.pdf'
        
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc = SimpleDocTemplate(str(output_file), pagesize=A4)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=blue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=black
        )
        
        story = []
        
        story.append(Paragraph("QuantROI System Components Documentation", title_style))
        story.append(Spacer(1, 20))
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
            elif line.startswith('# '):
                story.append(Paragraph(line[2:], title_style))
                story.append(Spacer(1, 12))
            elif line.startswith('## '):
                story.append(Paragraph(line[3:], heading_style))
                story.append(Spacer(1, 8))
            elif line.startswith('### '):
                story.append(Paragraph(line[4:], styles['Heading3']))
                story.append(Spacer(1, 6))
            elif line.startswith('**') and line.endswith('**'):
                story.append(Paragraph(f"<b>{line[2:-2]}</b>", styles['Normal']))
            elif line.startswith('- '):
                story.append(Paragraph(f"• {line[2:]}", styles['Normal']))
            else:
                if line:
                    story.append(Paragraph(line, styles['Normal']))
        
        doc.build(story)
        
        print(f"✅ PDF generated successfully using ReportLab: {output_file}")
        print(f"📄 File size: {output_file.stat().st_size / 1024:.1f} KB")
        return True
        
    except ImportError:
        print("❌ ReportLab not available. Installing...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'reportlab'], check=True)
            print("✅ ReportLab installed. Retrying...")
            return generate_alternative_pdf()
        except subprocess.CalledProcessError:
            print("❌ Failed to install ReportLab")
            return False
    except Exception as e:
        print(f"❌ Error generating PDF with ReportLab: {e}")
        return False

def main():
    """Main function to generate PDF documentation"""
    print("=== QuantROI System Documentation PDF Generator ===")
    
    if generate_pdf_documentation():
        return True
    
    print("\n🔄 Pandoc failed, trying alternative method...")
    
    if generate_alternative_pdf():
        return True
    
    print("\n❌ All PDF generation methods failed")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
