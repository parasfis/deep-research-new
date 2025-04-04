"""PDF generator for Deep Research Assistant.

This module provides functionality for generating PDF reports from research results.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# --- Try importing ReportLab ---
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
    from reportlab.platypus.flowables import HRFlowable
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    # Define dummy classes if reportlab is not available to avoid NameErrors later if needed
    # Although the logic should prevent using them if unavailable
    class SimpleDocTemplate: pass
    class Paragraph: pass
    class Spacer: pass
    class Table: pass
    class TableStyle: pass
    class ListFlowable: pass
    class ListItem: pass
    class HRFlowable: pass
    class colors: pass
    def getSampleStyleSheet(): return {}
    letter, A4 = None, None
    inch = 0


# --- Try importing FPDF ---
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    # Define dummy class if fpdf is not available
    class FPDF: pass


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

        # Set flags based on available libraries
        self.reportlab_available = REPORTLAB_AVAILABLE
        self.fpdf_available = FPDF_AVAILABLE

        if not self.reportlab_available and not self.fpdf_available:
            logger.error("Neither ReportLab nor FPDF is installed. PDF generation will fail.")
            # Optionally raise an error here if PDF generation is critical
            # raise ImportError("Required PDF library (ReportLab or FPDF) not found.")

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

        # Generate the PDF using the preferred library (ReportLab) if available
        if self.reportlab_available:
            try:
                self._generate_with_reportlab(research_data, filepath)
                logger.info(f"Generated PDF report using ReportLab: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Error generating PDF with ReportLab: {e}", exc_info=True)
                # Optionally fallback to FPDF if ReportLab fails mid-generation
                if self.fpdf_available:
                    logger.warning("ReportLab generation failed. Attempting fallback with FPDF.")
                else:
                    raise # Re-raise exception if FPDF is not available

        # Fallback to FPDF if ReportLab is not available or failed
        if self.fpdf_available:
            try:
                self._generate_with_fpdf(research_data, filepath)
                logger.info(f"Generated PDF report using FPDF: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Error generating PDF with FPDF: {e}", exc_info=True)
                raise # Re-raise FPDF generation error

        # If neither library worked or was available
        error_message = "Failed to generate PDF. Neither ReportLab nor FPDF is available or generation failed."
        logger.error(error_message)
        raise RuntimeError(error_message)

    def _generate_with_reportlab(self, research_data: Dict[str, Any], filepath: str):
        """Generate a PDF report using ReportLab.

        Args:
            research_data: Research data containing topic, context, and results.
            filepath: Path to save the PDF file.
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab library is not available, cannot generate PDF with this method.")
            
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
        
        # Create new styles instead of modifying existing ones
        styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12
        ))
        styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10
        ))
        styles.add(ParagraphStyle(
            name='CustomHeading3',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=8
        ))
        styles.add(ParagraphStyle(
            name='CustomBodyText',
            parent=styles['BodyText'],
            fontSize=10,
            spaceAfter=6
        ))
        
        # Build the document content
        content = []
        
        # Title
        title = f"{config.PDF_TITLE_PREFIX}{topic}"
        content.append(Paragraph(title, styles['CustomHeading1']))
        content.append(Spacer(1, 0.25 * inch))
        
        # Metadata
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content.append(Paragraph(f"Generated: {timestamp}", styles['CustomBodyText']))
        content.append(Paragraph(f"Author: {config.PDF_AUTHOR}", styles['CustomBodyText']))
        content.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=0.1*inch, spaceAfter=0.1*inch))
        
        # Context (if provided)
        if context:
            content.append(Paragraph("Research Context", styles['CustomHeading2']))
            content.append(Paragraph(context, styles['CustomBodyText']))
            content.append(Spacer(1, 0.2 * inch))
        
        # Convert markdown report to ReportLab paragraphs
        content.extend(self._convert_markdown_to_reportlab(report, styles))
        
        # Sources
        if analyzed_sources:
            content.append(Paragraph("Sources", styles['CustomHeading2']))
            sources_list = []
            
            for i, source in enumerate(analyzed_sources):
                source_text = f"<b>{i+1}. {source.get('title', 'Untitled')}</b><br/>"
                source_text += f"URL: {source.get('url', 'No URL')}<br/>"
                source_text += f"Relevance: {source.get('relevance', 0):.2f}"
                
                sources_list.append(ListItem(Paragraph(source_text, styles['CustomBodyText'])))
            
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
        
        # Create a link style based on BodyText
        if 'CustomLink' not in styles:
            styles.add(ParagraphStyle(
                name='CustomLink',
                parent=styles['CustomBodyText'],
                textColor=colors.blue,
                underline=True
            ))
        
        import re
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        url_pattern = r'https?://[^\s)>]+'
        
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
            
            # First, escape any < and > characters to prevent XML parsing issues
            line = line.replace('<', '&lt;').replace('>', '&gt;')
            
            # Process markdown links [text](url) to HTML links
            line = re.sub(link_pattern, r'<a href="\2">\1</a>', line)
            
            # Process bare URLs to HTML links (but avoid creating nested links)
            # Don't wrap URLs that are already inside an href attribute
            def replace_url(match):
                url = match.group(0)
                # Check if this URL is already part of an href attribute
                start_pos = match.start()
                # Look for 'href=' within 10 characters before the URL
                context_before = line[max(0, start_pos-10):start_pos]
                if 'href=' in context_before:
                    # Already in an href, return as is
                    return url
                else:
                    # Wrap in an anchor tag
                    return f'<a href="{url}">{url}</a>'
            
            line = re.sub(url_pattern, replace_url, line)
            
            # Headings
            if line.startswith('# '):
                if in_list and current_list_items:
                    flowables.append(ListFlowable(current_list_items, bulletType='bullet', leftIndent=20))
                    current_list_items = []
                    in_list = False
                flowables.append(Paragraph(line[2:], styles['CustomHeading1']))
            elif line.startswith('## '):
                if in_list and current_list_items:
                    flowables.append(ListFlowable(current_list_items, bulletType='bullet', leftIndent=20))
                    current_list_items = []
                    in_list = False
                flowables.append(Paragraph(line[3:], styles['CustomHeading2']))
            elif line.startswith('### '):
                if in_list and current_list_items:
                    flowables.append(ListFlowable(current_list_items, bulletType='bullet', leftIndent=20))
                    current_list_items = []
                    in_list = False
                flowables.append(Paragraph(line[4:], styles['CustomHeading3']))
            
            # List items
            elif line.startswith('- ') or line.startswith('* '):
                in_list = True
                item_text = line[2:]
                # For safety, wrap in a try-except in case HTML parsing fails
                try:
                    current_list_items.append(ListItem(Paragraph(item_text, styles['CustomBodyText'])))
                except ValueError as e:
                    logger.warning(f"Error processing list item with links: {e}")
                    # Fallback: strip HTML tags
                    clean_text = re.sub(r'<.*?>', '', item_text)
                    current_list_items.append(ListItem(Paragraph(clean_text, styles['CustomBodyText'])))
            
            # Regular paragraph
            else:
                if in_list and current_list_items:
                    flowables.append(ListFlowable(current_list_items, bulletType='bullet', leftIndent=20))
                    current_list_items = []
                    in_list = False
                # For safety, wrap in a try-except in case HTML parsing fails
                try:
                    flowables.append(Paragraph(line, styles['CustomBodyText']))
                except ValueError as e:
                    logger.warning(f"Error processing paragraph with links: {e}")
                    # Fallback: strip HTML tags
                    clean_text = re.sub(r'<.*?>', '', line)
                    flowables.append(Paragraph(clean_text, styles['CustomBodyText']))
        
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
        if not FPDF_AVAILABLE:
             raise RuntimeError("FPDF library is not available, cannot generate PDF with this method.")
             
        topic = research_data.get("topic", "Research Report")
        context = research_data.get("context", "")
        results = research_data.get("results", {})
        report = results.get("report", "No report generated.")
        analyzed_sources = results.get("analyzed_sources", [])
        
        # Create PDF object with Unicode support
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Try to set up Unicode font support
        unicode_font_added = False
        try:
            # Try multiple potential locations for Unicode fonts
            font_paths = [
                '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',  # macOS
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',       # Linux
                'C:\\Windows\\Fonts\\arial.ttf'                         # Windows
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdf.add_font('DejaVu', '', font_path, uni=True)
                    pdf.set_font('DejaVu', '', 10)
                    unicode_font_added = True
                    # Store this flag on the pdf object for use in other methods
                    pdf._unicode_font_added = True
                    logger.info(f"Using Unicode font: {font_path}")
                    break
                    
            if not unicode_font_added:
                # Fallback to default font
                logger.warning("No Unicode font found. Using default font with limited character support.")
                pdf.set_font("Arial", "", 10)
                pdf._unicode_font_added = False
        except Exception as e:
            logger.warning(f"Error adding Unicode font: {e}. Using default font.")
            pdf.set_font("Arial", "", 10)
            pdf._unicode_font_added = False
        
        pdf.add_page()
        
        # Set font for title
        if unicode_font_added:
            pdf.set_font('DejaVu', 'B', 16)
        else:
            pdf.set_font("Arial", "B", 16)
        
        # Title
        title = f"{config.PDF_TITLE_PREFIX}{topic}"
        pdf.cell(0, 10, title, ln=True)
        pdf.ln(5)
        
        # Metadata
        if unicode_font_added:
            pdf.set_font('DejaVu', '', 10)
        else:
            pdf.set_font("Arial", "", 10)
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.cell(0, 5, f"Generated: {timestamp}", ln=True)
        pdf.cell(0, 5, f"Author: {config.PDF_AUTHOR}", ln=True)
        pdf.line(10, pdf.get_y() + 5, 200, pdf.get_y() + 5)
        pdf.ln(10)
        
        # Context (if provided)
        if context:
            if unicode_font_added:
                pdf.set_font('DejaVu', 'B', 14)
            else:
                pdf.set_font("Arial", "B", 14)
                
            pdf.cell(0, 10, "Research Context", ln=True)
            
            if unicode_font_added:
                pdf.set_font('DejaVu', '', 10)
            else:
                pdf.set_font("Arial", "", 10)
                
            pdf.multi_cell(0, 5, context)
            pdf.ln(5)
        
        # Convert markdown report to FPDF
        self._convert_markdown_to_fpdf(report, pdf)
        
        # Sources
        if analyzed_sources:
            pdf.add_page()
            
            if unicode_font_added:
                pdf.set_font('DejaVu', 'B', 14)
            else:
                pdf.set_font("Arial", "B", 14)
                
            pdf.cell(0, 10, "Sources", ln=True)
            
            if unicode_font_added:
                pdf.set_font('DejaVu', '', 10)
            else:
                pdf.set_font("Arial", "", 10)
            
            for i, source in enumerate(analyzed_sources):
                if unicode_font_added:
                    pdf.set_font('DejaVu', 'B', 10)
                else:
                    pdf.set_font("Arial", "B", 10)
                    
                pdf.cell(0, 5, f"{i+1}. {source.get('title', 'Untitled')}", ln=True)
                
                if unicode_font_added:
                    pdf.set_font('DejaVu', '', 10)
                else:
                    pdf.set_font("Arial", "", 10)
                
                # Make URL clickable
                url = source.get('url', 'No URL')
                if url.startswith('http'):
                    pdf.set_text_color(0, 0, 255)  # Blue color for links
                    pdf.cell(0, 5, f"URL: ", 0, 0)
                    pdf.cell(0, 5, url, 0, 1, link=url)
                    pdf.set_text_color(0, 0, 0)    # Reset to black
                else:
                    pdf.cell(0, 5, f"URL: {url}", ln=True)
                    
                pdf.cell(0, 5, f"Relevance: {source.get('relevance', 0):.2f}", ln=True)
                pdf.ln(5)
        
        # Save the PDF
        try:
            pdf.output(filepath)
        except UnicodeEncodeError:
            logger.warning("Unicode encoding error with default FPDF output. Trying alternate approach.")
            # If we hit Unicode encoding issues, try a different approach
            self._generate_basic_fpdf(research_data, filepath)
    
    def _generate_basic_fpdf(self, research_data: Dict[str, Any], filepath: str):
        """Generate a simplified PDF report using FPDF when Unicode support fails.
        
        This is a fallback method that avoids special characters and formatting.
        
        Args:
            research_data: Research data containing topic, context, and results.
            filepath: Path to save the PDF file.
        """
        topic = research_data.get("topic", "Research Report")
        results = research_data.get("results", {})
        report = results.get("report", "No report generated.")
        
        # Create basic PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Basic ASCII-only fonts
        pdf.set_font("Arial", "B", 16)
        
        # Title
        title = f"{config.PDF_TITLE_PREFIX}{topic}"
        pdf.cell(0, 10, title, ln=True)
        pdf.ln(5)
        
        # Simplified content - strip markdown and special characters
        pdf.set_font("Arial", "", 10)
        
        # Process report text - remove markdown and special characters
        import re
        
        # Remove markdown formatting and links
        report = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', report)  # Replace [text](url) with just text
        report = re.sub(r'[^\x00-\x7F]+', ' ', report)  # Remove non-ASCII chars
        
        # Remove markdown headings, bullet points, etc.
        lines = []
        for line in report.split('\n'):
            # Remove heading markers
            line = re.sub(r'^#+\s+', '', line)
            # Remove bullet points
            line = re.sub(r'^[\*\-]\s+', '', line)
            lines.append(line)
        
        # Join back and write text
        safe_report = '\n'.join(lines)
        
        # Write parts of the report in chunks to avoid overflow issues
        for chunk in [safe_report[i:i+1000] for i in range(0, len(safe_report), 1000)]:
            pdf.multi_cell(0, 5, chunk)
            pdf.ln(5)
        
        # Note about limitations
        pdf.ln(10)
        pdf.set_font("Arial", "I", 10)
        pdf.multi_cell(0, 5, "Note: This is a simplified version of the report due to character encoding limitations. Some formatting and special characters may have been removed.")
        
        # Save the PDF
        pdf.output(filepath)

    def _convert_markdown_to_fpdf(self, markdown_text: str, pdf):
        """Convert markdown text to FPDF.

        Args:
            markdown_text: Markdown formatted text.
            pdf: FPDF object.
        """
        import re
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        url_pattern = r'https?://[^\s)>]+'
        
        # Replace Unicode bullet character with ASCII alternative if needed
        bullet_char = '-'  # ASCII fallback
        try:
            # Test if we can use the Unicode bullet
            test_str = '•'
            test_str.encode('latin-1')
            bullet_char = '•'  # Use Unicode if encoding works
        except UnicodeEncodeError:
            # Stick with ASCII fallback
            pass
        
        # Check if we have Unicode font support
        unicode_font_added = hasattr(pdf, '_unicode_font_added') and pdf._unicode_font_added
        
        for line in markdown_text.split('\n'):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                pdf.ln(5)
                continue
            
            # Catch any encoding errors for each line
            try:
                # Headings
                if line.startswith('# '):
                    if unicode_font_added:
                        pdf.set_font('DejaVu', 'B', 16)
                    else:
                        pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, line[2:], ln=True)
                    if unicode_font_added:
                        pdf.set_font('DejaVu', '', 10)
                    else:
                        pdf.set_font("Arial", "", 10)
                elif line.startswith('## '):
                    if unicode_font_added:
                        pdf.set_font('DejaVu', 'B', 14)
                    else:
                        pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 10, line[3:], ln=True)
                    if unicode_font_added:
                        pdf.set_font('DejaVu', '', 10)
                    else:
                        pdf.set_font("Arial", "", 10)
                elif line.startswith('### '):
                    if unicode_font_added:
                        pdf.set_font('DejaVu', 'B', 12)
                    else:
                        pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 10, line[4:], ln=True)
                    if unicode_font_added:
                        pdf.set_font('DejaVu', '', 10)
                    else:
                        pdf.set_font("Arial", "", 10)
                
                # List items - handle with simpler approach to avoid encoding issues
                elif line.startswith('- ') or line.startswith('* '):
                    # Extract any links first
                    text = line[2:]
                    
                    # Replace markdown links with plain text equivalent
                    text = re.sub(link_pattern, r'\1 (\2)', text)
                    
                    # Write the list item with bullet char
                    pdf.cell(5, 5, bullet_char, 0, 0)
                    pdf.multi_cell(0, 5, text)
                
                # Regular paragraph - handle with simpler approach
                else:
                    # Replace markdown links with plain text equivalent
                    text = re.sub(link_pattern, r'\1 (\2)', line)
                    
                    # Handle URLs separately if needed
                    if 'http' in text and not re.search(link_pattern, line):
                        # Find all URLs
                        urls = re.finditer(url_pattern, text)
                        remaining_text = text
                        current_position = 0
                        
                        for match in urls:
                            # Text before the URL
                            pre_text = remaining_text[current_position:match.start()]
                            if pre_text:
                                pdf.write(5, pre_text)
                            
                            # Add the URL as a link
                            url = match.group(0)
                            try:
                                pdf.set_text_color(0, 0, 255)  # Blue color for links
                                pdf.write(5, url, link=url)
                                pdf.set_text_color(0, 0, 0)    # Reset to black
                            except Exception as e:
                                # If linking fails, just write the text
                                logger.warning(f"Failed to create link in FPDF: {e}")
                                pdf.write(5, url)
                            
                            current_position = match.end()
                        
                        # Text after all URLs
                        if current_position < len(remaining_text):
                            pdf.write(5, remaining_text[current_position:])
                        pdf.ln()
                    else:
                        # No URLs to handle specially, just write the text
                        pdf.multi_cell(0, 5, text)
            
            except Exception as e:
                # If we hit encoding or other issues, try a simpler approach
                logger.warning(f"FPDF rendering error, using fallback: {e}")
                try:
                    # Remove any special characters and just output plain text
                    clean_line = re.sub(r'[^\x00-\x7F]+', ' ', line)
                    if line.startswith('#'):
                        clean_line = clean_line.lstrip('#').strip()
                        pdf.set_font("Arial", "B", 12)
                        pdf.cell(0, 10, clean_line, ln=True)
                        pdf.set_font("Arial", "", 10)
                    elif line.startswith('-') or line.startswith('*'):
                        pdf.cell(5, 5, "-", 0, 0)
                        pdf.multi_cell(0, 5, clean_line[1:].strip())
                    else:
                        pdf.multi_cell(0, 5, clean_line)
                except Exception as inner_e:
                    # Last resort - skip this line
                    logger.error(f"Failed to render line even with fallback: {inner_e}")
                    continue