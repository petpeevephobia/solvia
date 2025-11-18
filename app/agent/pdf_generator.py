"""
PDF Report Generator for SEO Audits - Gamified 2-Page Report
Creates professional 2-page PDF reports with progress bars, SEO stages, and motivational quotes
"""
import os
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Brand colors
SOLVIA_ORANGE = HexColor('#EC6019')
SOLVIA_DARK = HexColor('#1F2937')
SOLVIA_GRAY = HexColor('#6B7280')
SOLVIA_LIGHT_GRAY = HexColor('#F3F4F6')
SOLVIA_LIGHT_GRAY_BG = HexColor('#EEEEEE')
SOLVIA_GREEN = HexColor('#16A34A')  # PIXEL-PERFECT: Exact Figma green for positive changes
SOLVIA_RED = HexColor('#EF4444')
SOLVIA_YELLOW = HexColor('#F59E0B')
SOLVIA_BLACK = HexColor('#000000')
SOLVIA_WHITE = HexColor('#FFFFFF')

# Helper function to get hex string from HexColor
def get_hex_string(color):
    """Get hex string from HexColor object"""
    if hasattr(color, 'hexval'):
        # HexColor stores the value as a list of RGB values
        return f"#{int(color.red*255):02x}{int(color.green*255):02x}{int(color.blue*255):02x}"
    return "#000000"


class ProgressBarFlowable(Flowable):
    """
    Custom flowable for drawing SEO stage progress bar with 3 visual states

    Visual States:
    1. Current Stage: Solid orange fill (#EC6019), white text, 0.5px black border
    2. Next Target Stage: Orange border (#EC6019), orange text, white fill, 0.5px border
    3. Future Stages: Black border (#000000), black text, white fill, 0.5px border

    Layout: 4 connected boxes (Hidden, Emerging, Discoverable, Trusted)
    """

    def __init__(self, current_stage: str, current_impressions: int, width=500, height=60):
        """
        Initialize progress bar

        Args:
            current_stage: One of 'hidden', 'emerging', 'discoverable', 'trusted'
            current_impressions: Current impression count (for threshold display)
            width: Total width of progress bar
            height: Total height of progress bar
        """
        Flowable.__init__(self)
        self.current_stage = current_stage.lower()
        self.current_impressions = current_impressions
        self.width = width
        self.height = height

        # Define stages in order
        self.stages = [
            {'key': 'hidden', 'name': 'Hidden', 'threshold': '1 impression'},
            {'key': 'emerging', 'name': 'Emerging', 'threshold': '50 impressions'},
            {'key': 'discoverable', 'name': 'Discoverable', 'threshold': '300 impressions'},
            {'key': 'trusted', 'name': 'Trusted', 'threshold': '2000+ impressions'}
        ]

        # Box dimensions with spacing
        self.gap = 8  # Gap between boxes
        self.box_width = (width - (3 * self.gap)) / 4  # Divide space for 4 boxes + 3 gaps
        self.box_height = height

    def draw(self):
        """Draw the progress bar with 4 separated boxes and current position indicator"""
        canvas = self.canv

        # Find current stage index
        current_index = next((i for i, s in enumerate(self.stages) if s['key'] == self.current_stage), 0)

        # Draw each box
        for i, stage in enumerate(self.stages):
            # Calculate x position with gaps
            x = i * (self.box_width + self.gap)
            y = 0

            # Determine visual state
            if i == current_index:
                # Current stage: Solid orange fill, white text
                fill_color = SOLVIA_ORANGE
                border_color = SOLVIA_BLACK
                text_color = SOLVIA_WHITE
                border_width = 0.5
            elif i == current_index + 1:
                # Next target stage: Orange border, orange text, white fill
                fill_color = SOLVIA_WHITE
                border_color = SOLVIA_ORANGE
                text_color = SOLVIA_ORANGE
                border_width = 0.5
            else:
                # Future stages: Black border, black text, white fill
                fill_color = SOLVIA_WHITE
                border_color = SOLVIA_BLACK
                text_color = SOLVIA_BLACK
                border_width = 0.5

            # Draw box with fill
            canvas.setFillColor(fill_color)
            canvas.setStrokeColor(border_color)
            canvas.setLineWidth(border_width)

            # ULTRATHINK FIX: Rounded corners on first and last boxes only (4px radius)
            if i == 0 or i == 3:  # First or last box
                canvas.roundRect(x, y, self.box_width, self.box_height, 4, stroke=1, fill=1)
            else:  # Middle boxes stay square
                canvas.rect(x, y, self.box_width, self.box_height, stroke=1, fill=1)

            # Draw stage name (11px Arial Bold)
            canvas.setFillColor(text_color)
            canvas.setFont("Helvetica-Bold", 11)
            stage_name = stage['name']
            text_width = canvas.stringWidth(stage_name, "Helvetica-Bold", 11)
            canvas.drawString(x + (self.box_width - text_width) / 2, y + self.box_height - 20, stage_name)

            # Draw threshold (9px Arial Italic per Figma)
            canvas.setFont("Helvetica-Oblique", 9)
            threshold_text = stage['threshold']
            threshold_width = canvas.stringWidth(threshold_text, "Helvetica-Oblique", 9)
            canvas.drawString(x + (self.box_width - threshold_width) / 2, y + 10, threshold_text)

        # Draw "You are here" indicator below current stage
        current_x = current_index * (self.box_width + self.gap)
        indicator_text = f"You are here: {self.current_impressions} impressions"

        # Arrow position (centered below current box)
        arrow_x = current_x + (self.box_width / 2)
        arrow_y = -10

        # Draw small arrow pointing up to current box
        canvas.setStrokeColor(SOLVIA_ORANGE)
        canvas.setFillColor(SOLVIA_ORANGE)
        canvas.setLineWidth(1.5)

        # Draw arrow line pointing up
        canvas.line(arrow_x, arrow_y, arrow_x, -2)

        # Draw arrow head (small triangle) using path
        path = canvas.beginPath()
        path.moveTo(arrow_x - 3, -2)
        path.lineTo(arrow_x, 0)
        path.lineTo(arrow_x + 3, -2)
        path.close()
        canvas.drawPath(path, stroke=0, fill=1)

        # Draw indicator text (8px, orange)
        canvas.setFont("Helvetica-Bold", 8)
        text_width = canvas.stringWidth(indicator_text, "Helvetica-Bold", 8)
        canvas.drawString(arrow_x - (text_width / 2), arrow_y - 12, indicator_text)


class ScoreCircle(Flowable):
    """Custom flowable for drawing SEO score circle with 48/100 format"""

    def __init__(self, score, size=100):
        Flowable.__init__(self)
        self.score = score
        self.size = size
        self.width = size
        self.height = size

    def draw(self):
        # Determine color based on score
        if self.score >= 80:
            color = SOLVIA_GREEN
        elif self.score >= 60:
            color = SOLVIA_YELLOW
        elif self.score >= 40:
            color = SOLVIA_ORANGE
        else:
            color = SOLVIA_RED

        # Draw circle
        self.canv.setStrokeColor(color)
        self.canv.setLineWidth(8)
        self.canv.circle(self.size/2, self.size/2, self.size/2 - 10, stroke=1, fill=0)

        # PIXEL-PERFECT FIX: Draw score as TWO separate text elements per Figma
        # "48" in 36pt bold (top)
        self.canv.setFillColor(SOLVIA_DARK)
        self.canv.setFont("Helvetica-Bold", 36)
        score_text = f"{int(self.score)}"
        score_width = self.canv.stringWidth(score_text, "Helvetica-Bold", 36)
        score_x = (self.size - score_width) / 2
        score_y = self.size/2 + 2  # Positioned above center
        self.canv.drawString(score_x, score_y, score_text)

        # "/100" in 14pt regular (bottom, with 8px gap)
        self.canv.setFont("Helvetica", 14)
        suffix_text = "/100"
        suffix_width = self.canv.stringWidth(suffix_text, "Helvetica", 14)
        suffix_x = (self.size - suffix_width) / 2
        suffix_y = self.size/2 - 18  # 8px gap below score (converted to points)
        self.canv.drawString(suffix_x, suffix_y, suffix_text)


class PDFReportGenerator:
    """Generate professional 2-page gamified PDF reports for SEO audits"""

    def __init__(self):
        self.styles = self._create_styles()

    def _create_styles(self):
        """Create custom styles matching Solvia brand"""
        styles = getSampleStyleSheet()

        # Title style (PIXEL-PERFECT: 32pt per Figma)
        styles.add(ParagraphStyle(
            name='SolviaTitle',
            parent=styles['Title'],
            fontSize=32,
            textColor=SOLVIA_DARK,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Heading styles (PIXEL-PERFECT: 21pt per Figma for "Summary", "Health Score")
        styles.add(ParagraphStyle(
            name='SolviaHeading1',
            parent=styles['Heading1'],
            fontSize=21,
            textColor=SOLVIA_DARK,
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            name='SolviaHeading2',
            parent=styles['Heading2'],
            fontSize=12,  # PIXEL-PERFECT: 12pt per Figma for "Your Next Steps"
            textColor=SOLVIA_DARK,
            spaceAfter=8,  # Reduced from 10 to 8 to match Figma gap
            spaceBefore=0,  # No extra space before (table provides spacing)
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            name='SolviaHeading3',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=SOLVIA_DARK,
            spaceAfter=8,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))

        # Body text
        styles.add(ParagraphStyle(
            name='SolviaBody',
            parent=styles['Normal'],
            fontSize=11,
            textColor=SOLVIA_GRAY,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=14
        ))

        # Quote style (for motivational quotes) - PIXEL-PERFECT: 11pt per Figma
        styles.add(ParagraphStyle(
            name='SolviaQuote',
            parent=styles['Normal'],
            fontSize=11,
            textColor=SOLVIA_DARK,
            alignment=TA_LEFT,  # Changed from CENTER to LEFT per Figma
            spaceAfter=0,
            spaceBefore=0,
            fontName='Helvetica',  # Changed from Helvetica-Oblique to regular
            leading=13  # 1.149 line height at 11pt = ~13pt
        ))

        return styles

    def generate_report(self, audit_data: Dict[str, Any], output_path: str,
                       website_url: str, audit_id: str):
        """
        Generate the complete 2-page gamified PDF report

        Args:
            audit_data: Dictionary containing all audit data including gamified_pdf_data
            output_path: Path where PDF will be saved
            website_url: Website URL being audited
            audit_id: Unique audit identifier
        """

        # ULTRATHINK FIX: Handle both direct audit_result and database record formats
        # If audit_data contains an 'audit_data' field (database record), parse it
        if 'audit_data' in audit_data and isinstance(audit_data['audit_data'], str):
            import json
            print(f"[PDF GEN] 🔄 Parsing audit_data from database record (JSON string)")
            audit_data = json.loads(audit_data['audit_data'])
        elif 'audit_data' in audit_data and isinstance(audit_data['audit_data'], dict):
            print(f"[PDF GEN] 🔄 Extracting audit_data from database record (already parsed)")
            audit_data = audit_data['audit_data']

        # Store motivational quotes for footer rendering (separate for Page 1 and Page 2)
        gamified_data = audit_data.get('gamified_pdf_data', {})
        self.motivational_quote_page1 = gamified_data.get('motivational_quote_page1', "It's okay to be early! Every great site starts in the shadows before it shines. This is where your foundation is built.")
        self.motivational_quote_page2 = gamified_data.get('motivational_quote_page2', "Your next step is clarity. Make Google's job easier by showing it what each page is about. That's how visibility starts to grow.")

        # Track current page for footer rendering
        self.current_page_num = 0

        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        # Build story
        story = []

        # ================== PAGE 1 ==================
        story.extend(self._create_page1_header(audit_data, website_url, audit_id))
        story.extend(self._create_page1_summary(audit_data))
        story.extend(self._create_page1_progress_bar(audit_data))
        story.extend(self._create_page1_stage_description(audit_data))
        # ULTRATHINK FIX: Add motivational quote gray bubble ON page (not just footer as per Figma)
        story.extend(self._create_page1_motivational_quote(audit_data))
        # Footer removed - now handled in page template

        # Page break to Page 2
        story.append(PageBreak())

        # ================== PAGE 2 ==================
        story.extend(self._create_page2_health_score(audit_data))
        story.extend(self._create_page2_metrics_table(audit_data))
        story.extend(self._create_page2_next_steps(audit_data))
        # ULTRATHINK FIX: Add progress bar and motivational quote to Page 2 as per Figma
        story.extend(self._create_page1_progress_bar(audit_data))  # Reuse Page 1 progress bar
        story.extend(self._create_page2_motivational_quote(audit_data))  # Page 2-specific quote
        # Footer removed - now handled in page template

        # Build PDF with page numbers
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

    def _add_page_number(self, canvas, doc):
        """Add footer with generation date, motivational quote, and page number to every page"""
        canvas.saveState()

        # Footer line (orange horizontal line)
        canvas.setStrokeColor(SOLVIA_ORANGE)
        canvas.setLineWidth(1)
        canvas.line(50, 100, letter[0] - 50, 100)

        # Footer text: "Generated by Solvia on [date]"
        generation_date = datetime.now().strftime('%B %d, %Y')  # "November 13, 2025"
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(SOLVIA_GRAY)

        # "Generated on" text
        footer_text = f"Generated on "
        text_width = canvas.stringWidth(footer_text, 'Helvetica', 10)
        x_position = (letter[0] - text_width - canvas.stringWidth(generation_date, 'Helvetica', 10) - canvas.stringWidth(" with ", 'Helvetica', 10) - canvas.stringWidth("Solvia", 'Helvetica-Bold', 10)) / 2
        canvas.drawString(x_position, 80, footer_text)
        x_position += text_width

        # "[date]" text
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(SOLVIA_GRAY)
        date_width = canvas.stringWidth(generation_date, 'Helvetica', 10)
        canvas.drawString(x_position, 80, generation_date)
        x_position += date_width

        # " with " text
        with_text = " with "
        with_width = canvas.stringWidth(with_text, 'Helvetica', 10)
        canvas.drawString(x_position, 80, with_text)
        x_position += with_width

        # "Solvia" text (orange, bold)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(SOLVIA_ORANGE)
        solvia_text = "Solvia"
        canvas.drawString(x_position, 80, solvia_text)

        # Motivational quote with sun icon (below "Generated by Solvia")
        # Use different quotes for Page 1 and Page 2
        sun_icon_path = '/Users/jarotekosaputra/Documents/SOLVIA/App/solvia/app/static/images/orange-emblem.png'
        page_num = canvas.getPageNumber()

        if page_num == 1:
            quote_text = getattr(self, 'motivational_quote_page1', "It's okay to be early! Every great site starts in the shadows before it shines. This is where your foundation is built.")
        else:  # Page 2
            quote_text = getattr(self, 'motivational_quote_page2', "Your next step is clarity. Make Google's job easier by showing it what each page is about. That's how visibility starts to grow.")

        # Remove quotes from the quote text for rendering (if present)
        quote_display = quote_text.strip('"')

        if os.path.exists(sun_icon_path):
            # Calculate total width for centering (icon + spacing + text)
            canvas.setFont('Helvetica-Oblique', 10)
            quote_width = canvas.stringWidth(quote_display, 'Helvetica-Oblique', 10)
            icon_width = 16
            spacing = 4
            total_width = icon_width + spacing + quote_width

            # Calculate starting X position to center the entire group
            start_x = (letter[0] - total_width) / 2

            # Draw sun icon (16x16px for footer) - centered
            canvas.drawImage(sun_icon_path, start_x, 55, width=16, height=16, mask='auto')

            # Draw quote text next to icon (italic, dark gray) - centered
            canvas.setFillColor(SOLVIA_DARK)
            canvas.drawString(start_x + icon_width + spacing, 60, quote_display)
        else:
            # Quote only (no icon) - centered
            canvas.setFont('Helvetica-Oblique', 10)
            canvas.setFillColor(SOLVIA_DARK)
            quote_width = canvas.stringWidth(quote_display, 'Helvetica-Oblique', 10)
            canvas.drawString((letter[0] - quote_width) / 2, 60, quote_display)

        # Page number (bottom right corner)
        page_num = canvas.getPageNumber()
        page_text = f"Page {page_num}"
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(SOLVIA_GRAY)
        canvas.drawRightString(letter[0] - 50, 30, page_text)

        canvas.restoreState()

    # ==================== PAGE 1 METHODS ====================

    def _create_page1_header(self, audit_data: Dict[str, Any], website_url: str, audit_id: str):
        """Create Page 1 header with title, website, report ID, date range (NO time)"""
        elements = []

        # Title (updated to match Figma: "Your SEO Audit Report")
        elements.append(Paragraph(
            "Your SEO Audit Report",
            self.styles['SolviaTitle']
        ))

        elements.append(Spacer(1, 10))

        # Get date range from gamified_pdf_data
        gamified_data = audit_data.get('gamified_pdf_data', {})
        date_range = gamified_data.get('date_range', {})
        start_display = date_range.get('start_display', 'N/A')
        end_display = date_range.get('end_display', 'N/A')

        # Website info (NO time in generated date)
        # Updated to match Figma: "Data from:" instead of "Data Range:"
        info_text = f"""
        <para align="center">
        <font color="{get_hex_string(SOLVIA_GRAY)}">Website:</font>
        <font color="{get_hex_string(SOLVIA_ORANGE)}"><b>{website_url}</b></font><br/>
        <font color="{get_hex_string(SOLVIA_GRAY)}">Report ID:</font> {audit_id}<br/>
        <font color="{get_hex_string(SOLVIA_GRAY)}">Data from:</font> {start_display} to {end_display}
        </para>
        """
        elements.append(Paragraph(info_text, self.styles['SolviaBody']))

        elements.append(Spacer(1, 30))

        return elements

    def _create_page1_summary(self, audit_data: Dict[str, Any]):
        """Create Page 1 summary section with 3 rule-based paragraphs"""
        elements = []

        elements.append(Paragraph("Summary", self.styles['SolviaHeading1']))

        # Get summary paragraphs from gamified data (rule-based conditional text)
        gamified_data = audit_data.get('gamified_pdf_data', {})
        summary_paragraphs = gamified_data.get('summary_paragraphs', {})

        # DEBUG: Log what we're receiving
        print(f"[PDF SUMMARY DEBUG] 🔍 Checking summary paragraphs:")
        print(f"[PDF SUMMARY DEBUG]    Has gamified_pdf_data: {'gamified_pdf_data' in audit_data}")
        print(f"[PDF SUMMARY DEBUG]    gamified_data keys: {list(gamified_data.keys())}")
        print(f"[PDF SUMMARY DEBUG]    Has summary_paragraphs: {'summary_paragraphs' in gamified_data}")
        print(f"[PDF SUMMARY DEBUG]    summary_paragraphs type: {type(summary_paragraphs)}")
        print(f"[PDF SUMMARY DEBUG]    summary_paragraphs keys: {list(summary_paragraphs.keys()) if isinstance(summary_paragraphs, dict) else 'NOT A DICT'}")

        if summary_paragraphs:
            for key, value in summary_paragraphs.items():
                print(f"[PDF SUMMARY DEBUG]    {key}: {value[:80] if value else 'EMPTY'}...")
        else:
            print(f"[PDF SUMMARY DEBUG]    ⚠️ summary_paragraphs is empty or None!")

        # Get the 3 rule-based paragraphs
        impressions_para = summary_paragraphs.get('impressions_para', 'No data available.')
        clicks_ctr_para = summary_paragraphs.get('clicks_ctr_para', 'No data available.')
        position_para = summary_paragraphs.get('position_para', 'No data available.')

        print(f"[PDF SUMMARY DEBUG] 📝 Final paragraphs to render:")
        print(f"[PDF SUMMARY DEBUG]    impressions_para: {impressions_para[:80] if len(impressions_para) > 80 else impressions_para}")
        print(f"[PDF SUMMARY DEBUG]    clicks_ctr_para: {clicks_ctr_para[:80] if len(clicks_ctr_para) > 80 else clicks_ctr_para}")
        print(f"[PDF SUMMARY DEBUG]    position_para: {position_para[:80] if len(position_para) > 80 else position_para}")

        # Replace **text** with bold formatting for HTML rendering
        impressions_para_html = impressions_para.replace('**', '<b>').replace('</b>', '</b>', 1) if '**' in impressions_para else impressions_para
        clicks_ctr_para_html = clicks_ctr_para.replace('**', '<b>').replace('</b>', '</b>', 1) if '**' in clicks_ctr_para else clicks_ctr_para
        position_para_html = position_para.replace('**', '<b>').replace('</b>', '</b>', 1) if '**' in position_para else position_para

        # Convert markdown bold (**text**) to HTML bold (<b>text</b>)
        import re
        impressions_para_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', impressions_para)
        clicks_ctr_para_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clicks_ctr_para)
        position_para_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', position_para)

        # Add the 3 paragraphs (PIXEL-PERFECT: 8px gap per Figma)
        elements.append(Paragraph(impressions_para_html, self.styles['SolviaBody']))
        elements.append(Spacer(1, 8))  # Changed from 10 to 8 per Figma
        elements.append(Paragraph(clicks_ctr_para_html, self.styles['SolviaBody']))
        elements.append(Spacer(1, 8))  # Changed from 10 to 8 per Figma
        elements.append(Paragraph(position_para_html, self.styles['SolviaBody']))

        elements.append(Spacer(1, 30))

        return elements

    def _create_page1_progress_bar(self, audit_data: Dict[str, Any]):
        """Create Page 1 progress bar with 3 visual states"""
        elements = []

        # Get current stage and impressions
        gamified_data = audit_data.get('gamified_pdf_data', {})
        current_stage = gamified_data.get('seo_stage', 'hidden')
        # Get current impressions (use correct key name from AuditResult.to_dict())
        metrics = audit_data.get('metrics', {})
        current_impressions = metrics.get('total_impressions', metrics.get('impressions', 0))

        # Create progress bar flowable
        progress_bar = ProgressBarFlowable(
            current_stage=current_stage,
            current_impressions=current_impressions,
            width=500,
            height=60
        )

        # Center the progress bar
        center_table = Table([[progress_bar]], colWidths=[6.5*inch])
        center_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ]))
        elements.append(center_table)

        elements.append(Spacer(1, 30))

        return elements

    def _create_page1_stage_description(self, audit_data: Dict[str, Any]):
        """Create Page 1 SEO stage description paragraph"""
        elements = []

        # Get stage info
        gamified_data = audit_data.get('gamified_pdf_data', {})
        seo_stage_info = gamified_data.get('seo_stage_info', {})
        description = seo_stage_info.get('description', 'No description available.')

        # ULTRATHINK FIX: Just description paragraph below progress bar (no heading as per Figma)
        elements.append(Paragraph(description, self.styles['SolviaBody']))

        elements.append(Spacer(1, 30))

        return elements

    def _create_page1_motivational_quote(self, audit_data: Dict[str, Any]):
        """Create Page 1 motivational quote with sun icon and gray bubble"""
        elements = []

        # ULTRATHINK FIX: Get Page 1-specific motivational quote
        gamified_data = audit_data.get('gamified_pdf_data', {})
        quote = gamified_data.get('motivational_quote_page1', '"It\'s okay to be early! Every great site starts in the shadows before it shines. This is where your foundation is built."')

        # Load sun icon (PNG format for ReportLab compatibility)
        sun_icon_path = '/Users/jarotekosaputra/Documents/SOLVIA/App/solvia/app/static/images/orange-emblem.png'

        # Create gray bubble with quote and sun icon
        quote_data = []

        # Check if sun icon exists
        if os.path.exists(sun_icon_path):
            # Add sun icon (32x32px) and quote text side by side
            sun_icon = Image(sun_icon_path, width=32, height=32)
            quote_paragraph = Paragraph(
                f'<font color="{get_hex_string(SOLVIA_DARK)}"><i>{quote}</i></font>',
                self.styles['SolviaQuote']
            )
            quote_data = [[sun_icon, quote_paragraph]]
        else:
            # Quote only (no icon)
            quote_paragraph = Paragraph(
                f'<font color="{get_hex_string(SOLVIA_DARK)}"><i>{quote}</i></font>',
                self.styles['SolviaQuote']
            )
            quote_data = [[quote_paragraph]]

        # Create table for gray bubble effect (PIXEL-PERFECT: 8px top/bottom, 12px left/right per Figma)
        quote_table = Table(quote_data, colWidths=[0.5*inch, 5.5*inch] if os.path.exists(sun_icon_path) else [6*inch])
        quote_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), SOLVIA_LIGHT_GRAY_BG),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),  # PIXEL-PERFECT: 12px per Figma
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),  # PIXEL-PERFECT: 12px per Figma
            ('TOPPADDING', (0, 0), (-1, -1), 8),     # PIXEL-PERFECT: 8px per Figma
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),  # PIXEL-PERFECT: 8px per Figma
            ('BOX', (0, 0), (-1, -1), 0, SOLVIA_LIGHT_GRAY),  # No border per Figma
            ('ROUNDEDCORNERS', (0, 0), (-1, -1), 8),  # 8px border radius per Figma
        ]))

        elements.append(quote_table)
        elements.append(Spacer(1, 20))

        return elements

    def _create_page1_footer(self, audit_data: Dict[str, Any]):
        """Create Page 1 footer with generation date (NO time) and page number"""
        elements = []

        elements.append(Spacer(1, 30))

        # Footer line
        elements.append(Paragraph(
            '<font color="#EC6019">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</font>',
            self.styles['SolviaBody']
        ))

        # Footer text (date NO time)
        generation_date = datetime.now().strftime('%B %d, %Y')  # "November 13, 2025"
        footer_text = f"""
        <para align="center">
        <font color="#6B7280">Generated by</font>
        <font color="#EC6019"><b>Solvia</b></font>
        <font color="#6B7280">on {generation_date}</font>
        </para>
        """
        elements.append(Paragraph(footer_text, self.styles['SolviaBody']))

        return elements

    # ==================== PAGE 2 METHODS ====================

    def _create_page2_health_score(self, audit_data: Dict[str, Any]):
        """Create Page 2 health score circle (48/100 format)"""
        elements = []

        # Title - ULTRATHINK FIX: Changed from "SEO Health Score" to "Health Score" as per Figma
        elements.append(Paragraph("Health Score", self.styles['SolviaHeading1']))

        # Create score circle (reduced size to save space)
        score = audit_data.get('seo_score', 0)
        score_circle = ScoreCircle(score, size=100)

        # Center the score circle
        center_table = Table([[score_circle]], colWidths=[6.5*inch])
        center_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ]))
        elements.append(center_table)

        elements.append(Spacer(1, 8))  # Reduced from 15 to 8 to save space

        return elements

    def _create_page2_metrics_table(self, audit_data: Dict[str, Any]):
        """
        Create Page 2 metrics table with 4 columns: Metric, Current Value, 28-Day Change, Notes

        CRITICAL: Fix CTR display bug by multiplying by 100 to show as percentage
        """
        elements = []

        # PIXEL-PERFECT FIX: No heading above table per Figma - goes directly from score circle to table

        # Get metrics and gamified data
        metrics = audit_data.get('metrics', {})
        gamified_data = audit_data.get('gamified_pdf_data', {})
        changes = gamified_data.get('changes_28day', {})

        # ULTRATHINK DEBUG: Log what we received
        print(f"[PDF GEN] 🔍 Received audit_data keys: {list(audit_data.keys())}")
        print(f"[PDF GEN] 📊 Metrics keys: {list(metrics.keys())}")
        print(f"[PDF GEN] 🎯 Gamified data keys: {list(gamified_data.keys())}")
        print(f"[PDF GEN] 📈 Changes keys: {list(changes.keys())}")
        if not gamified_data:
            print(f"[PDF GEN] ⚠️  WARNING: gamified_pdf_data is EMPTY!")
        if not changes:
            print(f"[PDF GEN] ⚠️  WARNING: changes_28day is EMPTY!")

        # Import pdf_data_processor for notes generation
        try:
            from app.agent.pdf_data_processor import generate_metric_notes, format_ctr_display

            # Get SEO stage for context
            seo_stage = gamified_data.get('seo_stage', 'hidden')

            # Extract current values (use correct key names from AuditResult.to_dict())
            current_impressions = metrics.get('total_impressions', metrics.get('impressions', 0))
            current_clicks = metrics.get('total_clicks', metrics.get('clicks', 0))
            current_ctr = metrics.get('average_ctr', metrics.get('ctr', 0))  # Decimal format from API
            current_position = metrics.get('average_position', metrics.get('avg_position', 0))

            # Extract 28-day changes
            impressions_change = changes.get('impressions_change', 'N/A')
            clicks_change = changes.get('clicks_change', 'N/A')
            ctr_change = changes.get('ctr_change', 'N/A')
            position_change = changes.get('position_change', 'N/A')

            # Format CTR display (CRITICAL FIX: multiply by 100)
            current_ctr_display = format_ctr_display(current_ctr)

            # Generate notes
            impressions_note = generate_metric_notes('impressions', current_impressions, impressions_change, seo_stage)
            clicks_note = generate_metric_notes('clicks', current_clicks, clicks_change, seo_stage)
            ctr_note = generate_metric_notes('ctr', current_ctr * 100, ctr_change, seo_stage)  # Pass as percentage
            position_note = generate_metric_notes('position', current_position, position_change, seo_stage)

        except ImportError:
            # Fallback if pdf_data_processor is unavailable (use correct key names)
            current_impressions = metrics.get('total_impressions', metrics.get('impressions', 0))
            current_clicks = metrics.get('total_clicks', metrics.get('clicks', 0))
            current_ctr = metrics.get('average_ctr', metrics.get('ctr', 0))
            current_position = metrics.get('average_position', metrics.get('avg_position', 0))

            impressions_change = changes.get('impressions_change', 'N/A')
            clicks_change = changes.get('clicks_change', 'N/A')
            ctr_change = changes.get('ctr_change', 'N/A')
            position_change = changes.get('position_change', 'N/A')

            # Format CTR display (CRITICAL FIX: multiply by 100)
            current_ctr_display = f"{current_ctr * 100:.2f}%"

            # Generic notes
            impressions_note = "Monitor visibility trends"
            clicks_note = "Track click performance"
            ctr_note = "Optimize for better engagement"
            position_note = "Improve search rankings"

        # Get indexed pages from metrics
        indexed_pages = metrics.get('indexed_pages', metrics.get('total_pages', 5))
        indexed_pages_change = changes.get('indexed_pages_change', 'N/A')

        # Generate indexed pages note using rule-based function
        try:
            from app.agent.pdf_text_constants import get_indexed_pages_note
            # Calculate unindexed count (default to 1 if indexed pages < 10)
            unindexed_count = 1 if indexed_pages < 10 else 0
            indexed_pages_note = get_indexed_pages_note(unindexed_count, indexed_pages_change if isinstance(indexed_pages_change, int) else 0)
        except ImportError:
            indexed_pages_note = "Indexing status stable"

        # Create metrics table data (5 rows total)
        metrics_data = [
            ['Metric', 'Current Value', '28-Day Change', 'Notes'],
            [
                'Total Impressions',
                f"{current_impressions:,}",
                f"{impressions_change:+.1f}%" if isinstance(impressions_change, (int, float)) else impressions_change,
                Paragraph(impressions_note, self.styles['SolviaBody'])
            ],
            [
                'Total Clicks',
                f"{current_clicks:,}",
                f"{clicks_change:+.1f}%" if isinstance(clicks_change, (int, float)) else clicks_change,
                Paragraph(clicks_note, self.styles['SolviaBody'])
            ],
            [
                'Click-Through Rate',
                current_ctr_display,  # Already formatted as percentage
                f"{ctr_change:+.2f}pp" if isinstance(ctr_change, (int, float)) else ctr_change,  # pp = percentage points
                Paragraph(ctr_note, self.styles['SolviaBody'])
            ],
            [
                'Average Position',
                f"{current_position:.1f}",
                f"{position_change:+.1f}" if isinstance(position_change, (int, float)) else position_change,
                Paragraph(position_note, self.styles['SolviaBody'])
            ],
            [
                'Indexed Pages',
                f"{indexed_pages}",
                f"{indexed_pages_change:+d}" if isinstance(indexed_pages_change, int) else indexed_pages_change,
                Paragraph(indexed_pages_note, self.styles['SolviaBody'])
            ],
        ]

        # Create table (PIXEL-PERFECT per Figma specifications)
        table = Table(metrics_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2.6*inch])
        table.setStyle(TableStyle([
            # Header row styling (PIXEL-PERFECT: 11pt bold, 4px top/bottom, 12px left/right)
            ('BACKGROUND', (0, 0), (-1, 0), SOLVIA_ORANGE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),  # PIXEL-PERFECT: 11pt per Figma
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),  # PIXEL-PERFECT: 4px per Figma
            ('TOPPADDING', (0, 0), (-1, 0), 4),      # PIXEL-PERFECT: 4px per Figma
            ('LEFTPADDING', (0, 0), (-1, 0), 12),    # PIXEL-PERFECT: 12px per Figma
            ('RIGHTPADDING', (0, 0), (-1, 0), 12),   # PIXEL-PERFECT: 12px per Figma
            # Body rows styling (PIXEL-PERFECT: 11pt regular, 4px top/bottom)
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, SOLVIA_LIGHT_GRAY),  # PIXEL-PERFECT: 0.5px border
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, SOLVIA_LIGHT_GRAY_BG]),
            ('FONTSIZE', (0, 1), (-1, -1), 11),  # PIXEL-PERFECT: 11pt per Figma
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),  # PIXEL-PERFECT: 4px per Figma
            ('TOPPADDING', (0, 1), (-1, -1), 4),     # PIXEL-PERFECT: 4px per Figma
            ('LEFTPADDING', (0, 1), (2, -1), 0),     # 0px for centered columns (Metric, Value, Change)
            ('RIGHTPADDING', (0, 1), (2, -1), 0),    # 0px for centered columns
            ('LEFTPADDING', (3, 1), (3, -1), 12),    # PIXEL-PERFECT: 12px for Notes column per Figma
            ('RIGHTPADDING', (3, 1), (3, -1), 12),   # PIXEL-PERFECT: 12px for Notes column per Figma
            ('ALIGN', (3, 0), (3, -1), 'LEFT'),      # Notes column left-aligned per Figma
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 8))  # Reduced from 15 to 8 to save space

        return elements

    def _create_page2_next_steps(self, audit_data: Dict[str, Any]):
        """Create Page 2 next steps list (3-5 conditional items)"""
        elements = []

        elements.append(Paragraph("Your Next Steps", self.styles['SolviaHeading2']))

        # Get next steps from gamified data
        gamified_data = audit_data.get('gamified_pdf_data', {})
        next_steps = gamified_data.get('next_steps', [])

        if next_steps:
            for i, step in enumerate(next_steps[:5], 1):  # Max 5 steps
                step_text = f"<b>{i}.</b> {step}"
                elements.append(Paragraph(step_text, self.styles['SolviaBody']))
                elements.append(Spacer(1, 2))  # Reduced from 4 to 2 to save space
        else:
            # Fallback generic next steps
            default_steps = [
                "Review and fix any critical SEO issues identified in this report.",
                "Monitor your search performance trends weekly.",
                "Optimize underperforming pages for better rankings.",
                "Continue building high-quality backlinks.",
                "Keep your content fresh and relevant to your audience."
            ]
            for i, step in enumerate(default_steps, 1):
                step_text = f"<b>{i}.</b> {step}"
                elements.append(Paragraph(step_text, self.styles['SolviaBody']))
                elements.append(Spacer(1, 2))  # Reduced from 4 to 2 to save space

        elements.append(Spacer(1, 5))  # Reduced from 10 to 5 to save space

        return elements

    def _create_page2_progress_bar(self, audit_data: Dict[str, Any]):
        """Create Page 2 progress bar with threshold labels"""
        elements = []

        # Get current stage and impressions
        gamified_data = audit_data.get('gamified_pdf_data', {})
        current_stage = gamified_data.get('seo_stage', 'hidden')
        # Get current impressions (use correct key name from AuditResult.to_dict())
        metrics = audit_data.get('metrics', {})
        current_impressions = metrics.get('total_impressions', metrics.get('impressions', 0))

        # Create progress bar flowable (same as Page 1)
        progress_bar = ProgressBarFlowable(
            current_stage=current_stage,
            current_impressions=current_impressions,
            width=500,
            height=60
        )

        # Center the progress bar
        center_table = Table([[progress_bar]], colWidths=[6.5*inch])
        center_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ]))
        elements.append(center_table)

        elements.append(Spacer(1, 10))  # Reduced from 20 to 10 to save space

        return elements

    def _create_page2_motivational_quote(self, audit_data: Dict[str, Any]):
        """Create Page 2 motivational quote section (Page 2-specific quote)"""
        elements = []

        # ULTRATHINK FIX: Get Page 2-specific motivational quote (different from Page 1)
        gamified_data = audit_data.get('gamified_pdf_data', {})
        quote = gamified_data.get('motivational_quote_page2', '"Your next step is clarity. Make Google\'s job easier by showing it what each page is about. That\'s how visibility starts to grow."')

        # Load sun icon (PNG format for ReportLab compatibility)
        sun_icon_path = '/Users/jarotekosaputra/Documents/SOLVIA/App/solvia/app/static/images/orange-emblem.png'

        # Create gray bubble with quote and sun icon
        quote_data = []

        # Check if sun icon exists
        if os.path.exists(sun_icon_path):
            # Add sun icon (32x32px) and quote text side by side
            sun_icon = Image(sun_icon_path, width=32, height=32)
            quote_paragraph = Paragraph(
                f'<font color="{get_hex_string(SOLVIA_DARK)}"><i>{quote}</i></font>',
                self.styles['SolviaQuote']
            )
            quote_data = [[sun_icon, quote_paragraph]]
        else:
            # Quote only (no icon)
            quote_paragraph = Paragraph(
                f'<font color="{get_hex_string(SOLVIA_DARK)}"><i>{quote}</i></font>',
                self.styles['SolviaQuote']
            )
            quote_data = [[quote_paragraph]]

        # Create table for gray bubble effect (PIXEL-PERFECT: 8px top/bottom, 12px left/right per Figma)
        quote_table = Table(quote_data, colWidths=[0.5*inch, 5.5*inch] if os.path.exists(sun_icon_path) else [6*inch])
        quote_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), SOLVIA_LIGHT_GRAY_BG),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),  # PIXEL-PERFECT: 12px per Figma
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),  # PIXEL-PERFECT: 12px per Figma
            ('TOPPADDING', (0, 0), (-1, -1), 8),     # PIXEL-PERFECT: 8px per Figma
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),  # PIXEL-PERFECT: 8px per Figma
            ('BOX', (0, 0), (-1, -1), 0, SOLVIA_LIGHT_GRAY),  # No border per Figma
            ('ROUNDEDCORNERS', (0, 0), (-1, -1), 8),  # 8px border radius per Figma
        ]))

        elements.append(quote_table)
        elements.append(Spacer(1, 5))  # Reduced from 10 to 5 to save space

        return elements

    def _create_page2_footer(self, audit_data: Dict[str, Any]):
        """Create Page 2 footer (remove copyright, keep generation info)"""
        elements = []

        elements.append(Spacer(1, 30))

        # Footer line
        elements.append(Paragraph(
            '<font color="#EC6019">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</font>',
            self.styles['SolviaBody']
        ))

        # Footer text (NO copyright)
        generation_date = datetime.now().strftime('%B %d, %Y')  # "November 13, 2025"
        footer_text = f"""
        <para align="center">
        <font color="#6B7280">Generated by</font>
        <font color="#EC6019"><b>Solvia</b></font>
        <font color="#6B7280">on {generation_date}</font>
        </para>
        """
        elements.append(Paragraph(footer_text, self.styles['SolviaBody']))

        return elements
