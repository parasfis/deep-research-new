"""PDF generator for Deep Research Assistant.

This module provides functionality for generating PDF reports from research results.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import PDF generation libraries
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
    from reportlab.platypus.flowables import HRFlowable
except ImportError:
    # Fallback to fpdf2 if reportlab is not available
    from fpdf import FPDF

import config

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Class for generating PDF reports from research results."""

    def __init__(self, output_dir: str = None):
        """Initialize the PDF generator.

        Args:
            output_dir: Directory to save PDF reports. Defaults to config.PDF_OUTPUT_DIR.
        """
        self.output_dir = output_dir or config.PDF_OUTPUT_DIR
        Path(self.output_dir).mkdir(exist_ok=True)
        
        # Check which PDF library is available
        self.use_reportlab = 'reportlab.platypus' in globals()

    def generate_pdf(self, research_data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Generate a PDF report from research data.

        Args:
            research_data: Research data containing topic, context, and results.
            filename: Optional filename for the PDF. If not provided, a filename will be
                generated based on the topic and timestamp.

        Returns:
            Path to the generated PDF file.
        """
        topic = research_data.get("topic", "Research Report")
        
        if not filename:
            # Generate a filename based on the topic and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sanitized_topic = "".join(c if c.isalnum() else "_" for c in topic)
            filename = f"{sanitized_topic}_{timestamp}.pdf"
        
        # Ensure the filename has a .pdf extension
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
            
        filepath = os.path.join(self.output_dir, filename)
        
        # Generate the PDF using the appropriate library
        if self.use_reportlab:
            self._generate_with_reportlab(research_data, filepath)
        else:
            self._generate_with_fpdf(research_data, filepath)
            
        logger.info(f"Generated PDF report: {filepath}")
        return filepath

    def _generate_with_reportlab(self, research_data: Dict[str, Any], filepath: str):
        """Generate a PDF report using ReportLab.

        Args:
            research_data: Research data containing topic, context, and results.
            filepath: Path to save the PDF file.
        """
        topic = research_data.get("topic", "Research Report")
        context = research_data.get("context", "")
        results = research_data.get("results", {})
        report = results.get("report", "No report generated.")
        analyzed_sources = results.get("analyzed_sources", [])
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='Heading1',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12
        ))
        styles.add(ParagraphStyle(
            name='Heading2',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10
        ))
        styles.add(ParagraphStyle(
            name='Heading3',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=8
        ))
        styles.add(ParagraphStyle(
            name='BodyText',
            parent=styles['BodyText'],
            fontSize=10,
            spaceAfter=6
        ))
        
        # Build the document content
        content = []
        
        # Title
        title = f"{config.PDF_TITLE_PREFIX}{topic}"
        content.append(Paragraph(title, styles['Heading1']))
        content.append(Spacer(1, 0.25 * inch))
        
        # Metadata
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content.append(Paragraph(f"Generated: {timestamp}", styles['BodyText']))
        content.append(Paragraph(f"Author: {config.PDF_AUTHOR}", styles['BodyText']))
        content.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=0.1*inch, spaceAfter=0.1*inch))
        
        # Context (if provided)
        if context:
            content.append(Paragraph("Research Context", styles['Heading2']))
            content.append(Paragraph(context, styles['BodyText']))
            content.append(Spacer(1, 0.2 * inch))
        
        # Convert markdown report to ReportLab paragraphs
        content.extend(self._convert_markdown_to_reportlab(report, styles))
        
        # Sources
        if analyzed_sources:
            content.append(Paragraph("Sources", styles['Heading2']))
            sources_list = []
            
            for i, source in enumerate(analyzed_sources):
                source_text = f"<b>{i+1}. {source.get('title', 'Untitled')}</b><br/>"
                source_text += f"URL: {source.get('url', 'No URL')}<br/>"
                source_text += f"Relevance: {source.get('relevance', 0):.2f}"
                
                sources_list.append(ListItem(Paragraph(source_text, styles['BodyText'])))
            
            content.append(ListFlowable(sources_list, bulletType='bullet', leftIndent=20))
        
        # Build the PDF
        doc.build(content)

    def _convert_markdown_to_reportlab(self, markdown_text: str, styles):
        """Convert markdown text to ReportLab flowables.

        Args:
            markdown_text: Markdown formatted text.
            styles: ReportLab styles.

        Returns:
            List of ReportLab flowables.
        """
        flowables = []
        current_list_items = []
        in_list = False
        
        for line in markdown_text.split('\n'):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                if in_list and current_list_items:
                    # End the current list
                    flowables.append(ListFlowable(current_list_items, bulletType='bullet', leftIndent=20))
                    current_list_items = []
                    in_list = False
                flowables.append(Spacer(1, 0.1 * inch))
                continue
            
            # Headings
            if line.startswith('# '):
                if in_list and current_list_items:
                    flowables.append(ListFlowable(current_list_items, bulletType='bullet', leftIndent=20))
                    current_list_items = []
                    in_list = False
                flowables.append(Paragraph(line[2:], styles['Heading1']))
            elif line.startswith('## '):
                if in_list and current_list_items:
                    flowables.append(ListFlowable(current_list_items, bulletType='bullet', leftIndent=20))
                    current_list_items = []
                    in_list = False
                flowables.append(Paragraph(line[3:], styles['Heading2']))
            elif line.startswith('### '):
                if in_list and current_list_items:
                    flowables.append(ListFlowable(current_list_items, bulletType='bullet', leftIndent=20))
                    current_list_items = []
                    in_list = False
                flowables.append(Paragraph(line[4:], styles['Heading3']))
            
            # List items
            elif line.startswith('- ') or line.startswith('* '):
                in_list = True
                item_text = line[2:]
                current_list_items.append(ListItem(Paragraph(item_text, styles['BodyText'])))
            
            # Regular paragraph
            else:
                if in_list and current_list_items:
                    flowables.append(ListFlowable(current_list_items, bulletType='bullet', leftIndent=20))
                    current_list_items = []
                    in_list = False
                flowables.append(Paragraph(line, styles['BodyText']))
        
        # Add any remaining list items
        if in_list and current_list_items:
            flowables.append(ListFlowable(current_list_items, bulletType='bullet', leftIndent=20))
        
        return flowables

    def _generate_with_fpdf(self, research_data: Dict[str, Any], filepath: str):
        """Generate a PDF report using FPDF.

        Args:
            research_data: Research data containing topic, context, and results.
            filepath: Path to save the PDF file.
        """
        topic = research_data.get("topic", "Research Report")
        context = research_data.get("context", "")
        results = research_data.get("results", {})
        report = results.get("report", "No report generated.")
        analyzed_sources = results.get("analyzed_sources", [])
        
        # Create PDF object
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Set font
        pdf.set_font("Arial", "B", 16)
        
        # Title
        title = f"{config.PDF_TITLE_PREFIX}{topic}"
        pdf.cell(0, 10, title, ln=True)
        pdf.ln(5)
        
        # Metadata
        pdf.set_font("Arial", "", 10)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.cell(0, 5, f"Generated: {timestamp}", ln=True)
        pdf.cell(0, 5, f"Author: {config.PDF_AUTHOR}", ln=True)
        pdf.line(10, pdf.get_y() + 5, 200, pdf.get_y() + 5)
        pdf.ln(10)
        
        # Context (if provided)
        if context:
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Research Context", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 5, context)
            pdf.ln(5)
        
        # Convert markdown report to FPDF
        self._convert_markdown_to_fpdf(report, pdf)
        
        # Sources
        if analyzed_sources:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Sources", ln=True)
            pdf.set_font("Arial", "", 10)
            
            for i, source in enumerate(analyzed_sources):
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 5, f"{i+1}. {source.get('title', 'Untitled')}", ln=True)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 5, f"URL: {source.get('url', 'No URL')}", ln=True)
                pdf.cell(0, 5, f"Relevance: {source.get('relevance', 0):.2f}", ln=True)
                pdf.ln(5)
        
        # Save the PDF
        pdf.output(filepath)

    def _convert_markdown_to_fpdf(self, markdown_text: str, pdf):
        """Convert markdown text to FPDF.

        Args:
            markdown_text: Markdown formatted text.
            pdf: FPDF object.
        """
        for line in markdown_text.split('\n'):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                pdf.ln(5)
                continue
            
            # Headings
            if line.startswith('# '):
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 10, line[2:], ln=True)
                pdf.set_font("Arial", "", 10)
            elif line.startswith('## '):
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, line[3:], ln=True)
                pdf.set_font("Arial", "", 10)
            elif line.startswith('### '):
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, line[4:], ln=True)
                pdf.set_font("Arial", "", 10)
            
            # List items
            elif line.startswith('- ') or line.startswith('* '):
                pdf.cell(5, 5, "•", 0, 0)
                pdf.multi_cell(0, 5, line[2:])
            
            # Regular paragraph
            else:
                pdf.multi_cell(0, 5, line)