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


class RoundedQuoteBox(Flowable):
    """
    Custom flowable for motivational quote with rounded gray background

    PIXEL-PERFECT SPECS:
    - Rounded corners (8px radius)
    - Gray background (#F3F4F6)
    - Sun icon outside the box (32×32px)
    - Quote text inside box with padding
    """

    def __init__(self, quote_text: str, icon_path: str, width=472, style=None):
        """
        Initialize rounded quote box

        Args:
            quote_text: The motivational quote text
            icon_path: Path to sun icon PNG
            width: Width of the quote bubble (not including icon)
            style: ParagraphStyle for text formatting
        """
        Flowable.__init__(self)
        self.quote_text = quote_text
        self.icon_path = icon_path
        self.bubble_width = width
        self.style = style
        self.icon_size = 32
        self.gap = 8  # Gap between icon and bubble
        self.padding = 12  # Internal padding
        self.radius = 8  # Corner radius

    def wrap(self, availWidth, availHeight):
        """Calculate required space"""
        # Create paragraph to measure text height
        from reportlab.platypus import Paragraph
        p = Paragraph(f'<font color="#6B7280">{self.quote_text}</font>', self.style)
        text_width = self.bubble_width - (self.padding * 2)
        text_width, text_height = p.wrap(text_width, availHeight)

        # Total height is max of icon height or text height + padding
        content_height = max(self.icon_size, text_height + (self.padding * 2))
        total_width = self.icon_size + self.gap + self.bubble_width

        # CRITICAL FIX: Store height for use in draw() method
        self.height = content_height
        self.width = total_width

        return (total_width, content_height)

    def draw(self):
        """Draw icon and rounded quote box"""
        canvas = self.canv

        # Draw sun icon
        if os.path.exists(self.icon_path):
            from reportlab.platypus import Image as RLImage
            icon = RLImage(self.icon_path, width=self.icon_size, height=self.icon_size)
            icon.drawOn(canvas, 0, 0)

        # Draw rounded rectangle background
        bubble_x = self.icon_size + self.gap
        canvas.setFillColor(SOLVIA_LIGHT_GRAY_BG)
        canvas.setStrokeColor(SOLVIA_LIGHT_GRAY_BG)
        canvas.roundRect(bubble_x, 0, self.bubble_width, self.height, self.radius, stroke=0, fill=1)

        # Draw text
        from reportlab.platypus import Paragraph
        p = Paragraph(f'<font color="#6B7280">{self.quote_text}</font>', self.style)
        text_width = self.bubble_width - (self.padding * 2)
        text_width, text_height = p.wrap(text_width, self.height)

        # Center text vertically in bubble
        text_y = (self.height - text_height) / 2
        p.drawOn(canvas, bubble_x + self.padding, text_y)


class ProgressBarFlowable(Flowable):
    """
    Custom flowable for drawing SEO stage progress bar as connected pill shape

    PIXEL-PERFECT SPECS:
    - Total 4 boxes connected (no gaps)
    - Each box: 136.75 × 36 pixels
    - Rounded left end (first box) and right end (last box) only
    - Middle boxes have square corners where they connect
    - Gap between stage name and threshold text

    Visual States:
    1. Current Stage: Solid orange fill (#EC6019), white text
    2. Next Target Stage: Orange border, orange text, white fill
    3. Future Stages: Black border, black text, white fill
    """

    def __init__(self, current_stage: str, current_impressions: int, width=547, height=36):
        """
        Initialize progress bar

        Args:
            current_stage: One of 'hidden', 'emerging', 'discoverable', 'trusted'
            current_impressions: Current impression count
            width: Total width (136.75 × 4 = 547)
            height: Height (36 pixels)
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

        # PIXEL-PERFECT FIX: Calculate box width dynamically based on total width
        # Box dimensions (NO GAPS - connected pill)
        self.box_width = width / 4  # Dynamic calculation (512 / 4 = 128pt per box)
        self.box_height = height     # Use provided height

    def draw(self):
        """Draw the progress bar as connected pill shape (NO gaps between boxes)"""
        canvas = self.canv

        # Find current stage index
        current_index = next((i for i, s in enumerate(self.stages) if s['key'] == self.current_stage), 0)

        # CRITICAL FIX: Draw fills first WITHOUT borders to avoid white gaps
        radius = 18
        for i, stage in enumerate(self.stages):
            x = i * self.box_width
            y = 0

            # PIXEL-PERFECT FIX: Only current stage has orange fill, all others are white
            if i == current_index:
                fill_color = SOLVIA_ORANGE
            else:
                fill_color = SOLVIA_WHITE

            # Draw box fill only (no stroke)
            canvas.setFillColor(fill_color)

            if i == 0:
                # First box: Left rounded corners
                canvas.roundRect(x, y, self.box_width, self.box_height, radius, stroke=0, fill=1)
                # Square off right side
                canvas.rect(x + self.box_width - radius, y, radius, self.box_height, stroke=0, fill=1)
            elif i == 3:
                # Last box: Right rounded corners
                canvas.roundRect(x, y, self.box_width, self.box_height, radius, stroke=0, fill=1)
                # Square off left side
                canvas.rect(x, y, radius, self.box_height, stroke=0, fill=1)
            else:
                # Middle boxes: Square corners
                canvas.rect(x, y, self.box_width, self.box_height, stroke=0, fill=1)

        # CRITICAL FIX: Draw borders using proper rounded rectangle outline
        # Draw the complete outer border as one rounded rectangle
        total_width = self.width
        canvas.setStrokeColor(SOLVIA_BLACK)
        canvas.setLineWidth(1)
        canvas.roundRect(0, 0, total_width, self.box_height, radius, stroke=1, fill=0)

        # Draw vertical separators between all boxes
        for i in range(3):  # Only between boxes, not at edges
            x = (i + 1) * self.box_width

            # Check if we're at the boundary of the current stage
            is_left_current = (i == current_index)
            is_right_current = (i + 1 == current_index)

            if is_left_current or is_right_current:
                # Orange separator when one side is current stage
                canvas.setStrokeColor(SOLVIA_ORANGE)
            else:
                # Black separator between non-current stages
                canvas.setStrokeColor(SOLVIA_BLACK)

            canvas.line(x, y, x, y + self.box_height)

        # Draw text labels
        for i, stage in enumerate(self.stages):
            x = i * self.box_width
            y = 0

            # PIXEL-PERFECT FIX: Only current stage has special color, all others are black
            if i == current_index:
                # Current stage: White text on orange background
                text_color = SOLVIA_WHITE
            else:
                # All other stages: Black text on white background
                text_color = SOLVIA_BLACK

            # Draw stage name (11px Bold)
            canvas.setFillColor(text_color)
            canvas.setFont("Helvetica-Bold", 11)
            stage_name = stage['name']
            name_width = canvas.stringWidth(stage_name, "Helvetica-Bold", 11)
            canvas.drawString(x + (self.box_width - name_width) / 2, y + 22, stage_name)

            # Draw threshold (9px Italic)
            canvas.setFont("Helvetica-Oblique", 9)
            threshold_text = stage['threshold']
            threshold_width = canvas.stringWidth(threshold_text, "Helvetica-Oblique", 9)
            canvas.drawString(x + (self.box_width - threshold_width) / 2, y + 8, threshold_text)


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
        # PIXEL-PERFECT FIX: Add progress bar and motivational quote (NO stage description per user feedback)
        story.extend(self._create_page2_progress_bar(audit_data))
        story.extend(self._create_page2_motivational_quote(audit_data))
        # Footer handled in page template

        # Build PDF with page numbers
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

    def _add_page_number(self, canvas, doc):
        """Add simple footer with generation date on left and page number on right"""
        canvas.saveState()

        # PIXEL-PERFECT FIX: Simple footer per user feedback
        # Left side: "Generated on [date] with Solvia" (gray font, small)
        # Right side: Just number "1" or "2" (no "Page" prefix)

        generation_date = datetime.now().strftime('%B %d, %Y')  # "November 18, 2025"
        canvas.setFont('Helvetica', 9)  # Small font per user request
        canvas.setFillColor(SOLVIA_GRAY)

        # Left side: "Generated on [date] with Solvia"
        footer_left = f"Generated on {generation_date} with Solvia"
        canvas.drawString(50, 30, footer_left)

        # Right side: Just page number (no "Page" prefix)
        page_num = str(canvas.getPageNumber())
        canvas.drawRightString(letter[0] - 50, 30, page_num)

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

        # PIXEL-PERFECT FIX: Spacing before progress bar (match with spacing after)
        elements.append(Spacer(1, 8))

        return elements

    def _create_page1_progress_bar(self, audit_data: Dict[str, Any]):
        """Create Page 1 progress bar with 3 visual states - FULL WIDTH aligned with summary"""
        elements = []

        # Get current stage and impressions
        gamified_data = audit_data.get('gamified_pdf_data', {})
        current_stage = gamified_data.get('seo_stage', 'hidden')
        # Get current impressions (use correct key name from AuditResult.to_dict())
        metrics = audit_data.get('metrics', {})
        current_impressions = metrics.get('total_impressions', metrics.get('impressions', 0))

        # PIXEL-PERFECT FIX: Full content width progress bar (512 points = page width - margins)
        # Page: 612pt, Margins: 50pt left + 50pt right = 512pt content area
        # This aligns with summary paragraph starting point
        progress_bar = ProgressBarFlowable(
            current_stage=current_stage,
            current_impressions=current_impressions,
            width=512,  # Exact content area width
            height=36
        )

        # PIXEL-PERFECT FIX: Left-align instead of center to match summary paragraph
        elements.append(progress_bar)

        # PIXEL-PERFECT FIX: Spacing after progress bar (match with spacing before: 8px)
        elements.append(Spacer(1, 8))

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

        # PIXEL-PERFECT FIX: Small gap before motivational quote (12px)
        elements.append(Spacer(1, 12))

        return elements

    def _create_page1_motivational_quote(self, audit_data: Dict[str, Any]):
        """Create Page 1 motivational quote with sun icon left-aligned, gray text (#6B7280), rounded gray box, full width"""
        elements = []

        # PIXEL-PERFECT FIX: Get Page 1-specific motivational quote
        gamified_data = audit_data.get('gamified_pdf_data', {})
        quote = gamified_data.get('motivational_quote_page1', '"It\'s okay to be early! Every great site starts in the shadows before it shines. This is where your foundation is built."')

        # Load sun icon (PNG format for ReportLab compatibility)
        sun_icon_path = '/Users/jarotekosaputra/Documents/SOLVIA/App/solvia/app/static/images/orange-emblem.png'

        # PIXEL-PERFECT FIX: Use custom RoundedQuoteBox for proper rounded corners
        # Bubble width: 472pt (512pt content - 32pt icon - 8pt gap)
        quote_box = RoundedQuoteBox(
            quote_text=quote,
            icon_path=sun_icon_path,
            width=472,
            style=self.styles['SolviaQuote']
        )

        elements.append(quote_box)
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
        """Create Page 2 health score circle (48/100 format) - 109×109 pixels"""
        elements = []

        # Title - PIXEL-PERFECT: "Health Score" as per Figma
        elements.append(Paragraph("Health Score", self.styles['SolviaHeading1']))

        # PIXEL-PERFECT FIX: Enlarge score circle to 109×109 per user request
        score = audit_data.get('seo_score', 0)
        score_circle = ScoreCircle(score, size=109)

        # Center the score circle
        center_table = Table([[score_circle]], colWidths=[6.5*inch])
        center_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ]))
        elements.append(center_table)

        # PIXEL-PERFECT FIX: Reduced spacing to prevent Page 3 overflow (was 8, now 4)
        elements.append(Spacer(1, 4))

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

        # PIXEL-PERFECT FIX: Helper function to colorize 28-Day Change values
        def colorize_change(value, formatted_text):
            """Colorize change values: green for positive, red for negative, gray for N/A"""
            if isinstance(value, (int, float)):
                if value > 0:
                    color = "#16A34A"  # Green for positive changes
                elif value < 0:
                    color = "#EF4444"  # Red for negative changes
                else:
                    color = "#6B7280"  # Gray for zero
                return Paragraph(f'<font color="{color}">{formatted_text}</font>', self.styles['SolviaBody'])
            else:
                # N/A or other non-numeric values
                return Paragraph(f'<font color="#6B7280">{formatted_text}</font>', self.styles['SolviaBody'])

        # Create metrics table data (5 rows total) with colorized 28-Day Change column
        metrics_data = [
            ['Metric', 'Current Value', '28-Day Change', 'Notes'],
            [
                'Total Impressions',
                f"{current_impressions:,}",
                colorize_change(impressions_change, f"{impressions_change:+.1f}%" if isinstance(impressions_change, (int, float)) else impressions_change),
                Paragraph(impressions_note, self.styles['SolviaBody'])
            ],
            [
                'Total Clicks',
                f"{current_clicks:,}",
                colorize_change(clicks_change, f"{clicks_change:+.1f}%" if isinstance(clicks_change, (int, float)) else clicks_change),
                Paragraph(clicks_note, self.styles['SolviaBody'])
            ],
            [
                'Click-Through Rate',
                current_ctr_display,  # Already formatted as percentage
                colorize_change(ctr_change, f"{ctr_change:+.2f}pp" if isinstance(ctr_change, (int, float)) else ctr_change),
                Paragraph(ctr_note, self.styles['SolviaBody'])
            ],
            [
                'Average Position',
                f"{current_position:.1f}",
                # Note: For position, NEGATIVE is GOOD (moved up), so invert the color logic
                colorize_change(-position_change if isinstance(position_change, (int, float)) else position_change, f"{position_change:+.1f}" if isinstance(position_change, (int, float)) else position_change),
                Paragraph(position_note, self.styles['SolviaBody'])
            ],
            [
                'Indexed Pages',
                f"{indexed_pages}",
                colorize_change(indexed_pages_change, f"{indexed_pages_change:+d}" if isinstance(indexed_pages_change, int) else indexed_pages_change),
                Paragraph(indexed_pages_note, self.styles['SolviaBody'])
            ],
        ]

        # Create table (PIXEL-PERFECT per user feedback)
        table = Table(metrics_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2.6*inch])
        table.setStyle(TableStyle([
            # PIXEL-PERFECT FIX: Header row color #6B7280 (gray) with white font per user feedback
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#6B7280')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('LEFTPADDING', (0, 0), (-1, 0), 12),
            ('RIGHTPADDING', (0, 0), (-1, 0), 12),
            # PIXEL-PERFECT FIX: Alternating row colors (white and #F3F4F6) per user feedback
            ('GRID', (0, 0), (-1, -1), 0.5, SOLVIA_LIGHT_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#F3F4F6')]),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING', (0, 1), (2, -1), 0),
            ('RIGHTPADDING', (0, 1), (2, -1), 0),
            ('LEFTPADDING', (3, 1), (3, -1), 12),
            ('RIGHTPADDING', (3, 1), (3, -1), 12),
            ('ALIGN', (3, 0), (3, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)
        # PIXEL-PERFECT FIX: Reduced spacing to prevent Page 3 overflow (was 8, now 4)
        elements.append(Spacer(1, 4))

        return elements

    def _create_page2_next_steps(self, audit_data: Dict[str, Any]):
        """Create Page 2 next steps list (3-5 conditional items) with BULLET POINTS"""
        elements = []

        # PIXEL-PERFECT FIX: Add margin-top before section per user feedback
        elements.append(Spacer(1, 12))

        elements.append(Paragraph("Your Next Steps", self.styles['SolviaHeading2']))

        # Get next steps from gamified data
        gamified_data = audit_data.get('gamified_pdf_data', {})
        next_steps = gamified_data.get('next_steps', [])

        # PIXEL-PERFECT FIX: Use bullet points (•) with MINIMAL spacing per user feedback
        if next_steps:
            for i, step in enumerate(next_steps[:5]):  # Max 5 steps
                step_text = f"• {step}"  # Bullet point instead of number
                elements.append(Paragraph(step_text, self.styles['SolviaBody']))
                # PIXEL-PERFECT FIX: Minimal gap (2px) between list items, not 4px
                if i < len(next_steps) - 1:  # No spacer after last item
                    elements.append(Spacer(1, 2))
        else:
            # Fallback generic next steps
            default_steps = [
                "Review and fix any critical SEO issues identified in this report.",
                "Monitor your search performance trends weekly.",
                "Optimize underperforming pages for better rankings.",
                "Continue building high-quality backlinks.",
                "Keep your content fresh and relevant to your audience."
            ]
            for i, step in enumerate(default_steps):
                step_text = f"• {step}"  # Bullet point instead of number
                elements.append(Paragraph(step_text, self.styles['SolviaBody']))
                # PIXEL-PERFECT FIX: Minimal gap (2px) between list items
                if i < len(default_steps) - 1:  # No spacer after last item
                    elements.append(Spacer(1, 2))

        # Reduced spacing after section (was 10, now 8)
        elements.append(Spacer(1, 8))

        return elements

    def _create_page2_stage_description(self, audit_data: Dict[str, Any]):
        """Create Page 2 SEO stage description paragraph (same as Page 1)"""
        elements = []

        # Get stage info
        gamified_data = audit_data.get('gamified_pdf_data', {})
        seo_stage_info = gamified_data.get('seo_stage_info', {})
        description = seo_stage_info.get('description', 'No description available.')

        # Same description paragraph as Page 1
        elements.append(Paragraph(description, self.styles['SolviaBody']))

        # Minimum gap before progress bar
        elements.append(Spacer(1, 8))

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

        # Create progress bar flowable with full content width (same as Page 1)
        # Page: 612pt, Margins: 50pt left + 50pt right = 512pt content area
        progress_bar = ProgressBarFlowable(
            current_stage=current_stage,
            current_impressions=current_impressions,
            width=512,  # Full content width (same as Page 1)
            height=36   # Same height as Page 1
        )

        # Center the progress bar in content area
        center_table = Table([[progress_bar]], colWidths=[512])
        center_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ]))
        elements.append(center_table)

        # PIXEL-PERFECT FIX: Add gap before motivational quote per user feedback (was 4, now 8)
        elements.append(Spacer(1, 8))

        return elements

    def _create_page2_motivational_quote(self, audit_data: Dict[str, Any]):
        """Create Page 2 motivational quote - DIFFERENT from Page 1, full width, sun icon left-aligned, rounded gray box"""
        elements = []

        # PIXEL-PERFECT FIX: Get Page 2-specific motivational quote (DIFFERENT from Page 1)
        gamified_data = audit_data.get('gamified_pdf_data', {})
        quote = gamified_data.get('motivational_quote_page2', '"Your next step is clarity. Make Google\'s job easier by showing it what each page is about. That\'s how visibility starts to grow."')

        # Load sun icon (PNG format for ReportLab compatibility)
        sun_icon_path = '/Users/jarotekosaputra/Documents/SOLVIA/App/solvia/app/static/images/orange-emblem.png'

        # PIXEL-PERFECT FIX: Use custom RoundedQuoteBox for proper rounded corners (same as Page 1)
        # Bubble width: 472pt (512pt content - 32pt icon - 8pt gap)
        quote_box = RoundedQuoteBox(
            quote_text=quote,
            icon_path=sun_icon_path,
            width=472,
            style=self.styles['SolviaQuote']
        )

        elements.append(quote_box)
        elements.append(Spacer(1, 10))

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
