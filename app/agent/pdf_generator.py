"""
PDF Report Generator for SEO Audits
Creates beautiful, professional PDF reports matching the Solvia brand
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

# Brand colors
SOLVIA_ORANGE = HexColor('#EC6019')
SOLVIA_DARK = HexColor('#1F2937')
SOLVIA_GRAY = HexColor('#6B7280')
SOLVIA_LIGHT_GRAY = HexColor('#F3F4F6')
SOLVIA_GREEN = HexColor('#10B981')
SOLVIA_RED = HexColor('#EF4444')
SOLVIA_YELLOW = HexColor('#F59E0B')

# Helper function to get hex string from HexColor
def get_hex_string(color):
    """Get hex string from HexColor object"""
    if hasattr(color, 'hexval'):
        # HexColor stores the value as a list of RGB values
        return f"#{int(color.red*255):02x}{int(color.green*255):02x}{int(color.blue*255):02x}"
    return "#000000"

class ScoreCircle(Flowable):
    """Custom flowable for drawing SEO score circle"""
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
        
        # Draw score text
        self.canv.setFillColor(SOLVIA_DARK)
        self.canv.setFont("Helvetica-Bold", 32)
        text = str(int(self.score))
        self.canv.drawCentredString(self.size/2, self.size/2 - 10, text)
        
        # Draw "/100" text
        self.canv.setFont("Helvetica", 12)
        self.canv.setFillColor(SOLVIA_GRAY)
        self.canv.drawCentredString(self.size/2, self.size/2 - 25, "/100")

class PDFReportGenerator:
    """Generate professional PDF reports for SEO audits"""
    
    def __init__(self):
        self.styles = self._create_styles()
        
    def _create_styles(self):
        """Create custom styles matching Solvia brand"""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='SolviaTitle',
            parent=styles['Title'],
            fontSize=28,
            textColor=SOLVIA_DARK,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Heading styles
        styles.add(ParagraphStyle(
            name='SolviaHeading1',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=SOLVIA_DARK,
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            borderColor=SOLVIA_ORANGE,
            borderWidth=0,
            borderPadding=0
        ))
        
        styles.add(ParagraphStyle(
            name='SolviaHeading2',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=SOLVIA_DARK,
            spaceAfter=10,
            spaceBefore=15,
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
        
        # Metric style
        styles.add(ParagraphStyle(
            name='MetricValue',
            fontSize=24,
            textColor=SOLVIA_DARK,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Issue styles by severity
        styles.add(ParagraphStyle(
            name='CriticalIssue',
            parent=styles['Normal'],
            fontSize=11,
            textColor=SOLVIA_RED,
            leftIndent=20,
            bulletColor=SOLVIA_RED,
            bulletFontName='Symbol'
        ))
        
        styles.add(ParagraphStyle(
            name='HighIssue',
            parent=styles['Normal'],
            fontSize=11,
            textColor=SOLVIA_ORANGE,
            leftIndent=20
        ))
        
        styles.add(ParagraphStyle(
            name='MediumIssue',
            parent=styles['Normal'],
            fontSize=11,
            textColor=SOLVIA_YELLOW,
            leftIndent=20
        ))
        
        return styles
    
    def generate_report(self, audit_data: Dict[str, Any], output_path: str, 
                       website_url: str, audit_id: str):
        """Generate the complete PDF report"""
        
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
        
        # Add header
        story.extend(self._create_header(website_url, audit_id))
        
        # Add executive summary
        story.extend(self._create_executive_summary(audit_data))
        
        # Add SEO score section
        story.extend(self._create_score_section(audit_data))
        
        # Page break before metrics for full page 2
        story.append(PageBreak())
        
        # Add key metrics on page 2
        story.extend(self._create_metrics_section(audit_data))
        
        # Page break after metrics
        story.append(PageBreak())
        
        # Add issues section on page 3
        story.extend(self._create_issues_section(audit_data))
        
        # Page break before recommendations for new page
        story.append(PageBreak())
        
        # Add recommendations on new page
        story.extend(self._create_recommendations_section(audit_data))
        
        # Add footer
        story.extend(self._create_footer())
        
        # Build PDF
        doc.build(story)
        
    def _create_header(self, website_url: str, audit_id: str):
        """Create report header"""
        elements = []
        
        # Title
        elements.append(Paragraph(
            "SEO AUDIT REPORT",
            self.styles['SolviaTitle']
        ))
        
        elements.append(Spacer(1, 10))
        
        # Website info
        info_text = f"""
        <para align="center">
        <font color="{get_hex_string(SOLVIA_GRAY)}">Website:</font> 
        <font color="{get_hex_string(SOLVIA_ORANGE)}"><b>{website_url}</b></font><br/>
        <font color="{get_hex_string(SOLVIA_GRAY)}">Report ID:</font> {audit_id}<br/>
        <font color="{get_hex_string(SOLVIA_GRAY)}">Generated:</font> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        </para>
        """
        elements.append(Paragraph(info_text, self.styles['SolviaBody']))
        
        elements.append(Spacer(1, 30))
        
        return elements
    
    def _create_executive_summary(self, audit_data: Dict[str, Any]):
        """Create executive summary section"""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.styles['SolviaHeading1']))
        
        seo_score = audit_data.get('seo_score', 0)
        total_issues = audit_data.get('summary', {}).get('total_issues', 0)
        critical_issues = audit_data.get('summary', {}).get('critical_issues', 0)
        
        # Performance interpretation
        if seo_score >= 80:
            performance = "excellent"
            color = SOLVIA_GREEN
        elif seo_score >= 60:
            performance = "good"
            color = SOLVIA_YELLOW
        elif seo_score >= 40:
            performance = "needs improvement"
            color = SOLVIA_ORANGE
        else:
            performance = "poor"
            color = SOLVIA_RED
        
        summary_text = f"""
        Your website's SEO health score is <font color="{get_hex_string(color)}"><b>{seo_score}/100</b></font>, 
        which indicates <b>{performance}</b> overall performance. 
        We've identified <b>{total_issues} issues</b> that are impacting your search visibility"""
        
        if critical_issues > 0:
            summary_text += f""", including <font color="{get_hex_string(SOLVIA_RED)}"><b>{critical_issues} critical 
            issues</b></font> that require immediate attention"""
        
        summary_text += "."
        
        elements.append(Paragraph(summary_text, self.styles['SolviaBody']))
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_score_section(self, audit_data: Dict[str, Any]):
        """Create SEO score visualization"""
        elements = []
        
        elements.append(Paragraph("SEO Health Score", self.styles['SolviaHeading1']))
        
        # Create a centered table to hold the score circle
        score = audit_data.get('seo_score', 0)
        score_circle = ScoreCircle(score, size=120)
        
        # Use a table to center the score circle
        center_table = Table([[score_circle]], colWidths=[6.5*inch])
        center_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ]))
        elements.append(center_table)
        
        elements.append(Spacer(1, 20))
        
        # Score breakdown table
        breakdown_data = [
            ['Component', 'Score', 'Weight'],
            ['Traffic Performance', f"{audit_data.get('scores', {}).get('traffic_score', 0):.1f}", '30%'],
            ['Search Position', f"{audit_data.get('scores', {}).get('position_score', 0):.1f}", '25%'],
            ['Click-Through Rate', f"{audit_data.get('scores', {}).get('ctr_score', 0):.1f}", '25%'],
            ['Trend Analysis', f"{audit_data.get('scores', {}).get('trend_score', 0):.1f}", '20%']
        ]
        
        table = Table(breakdown_data, colWidths=[3.5*inch, 1.8*inch, 1.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), SOLVIA_LIGHT_GRAY),
            ('TEXTCOLOR', (0, 0), (-1, 0), SOLVIA_DARK),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, SOLVIA_LIGHT_GRAY),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        return elements
    
    def _create_metrics_section(self, audit_data: Dict[str, Any]):
        """Create key metrics section - Full Page 2"""
        elements = []
        
        # Page header
        elements.append(Paragraph("Key Performance Metrics", self.styles['SolviaTitle']))
        elements.append(Spacer(1, 10))
        
        # Add date range info
        date_range = audit_data.get('date_range', {})
        if date_range:
            elements.append(Paragraph(
                f'<font color="{get_hex_string(SOLVIA_GRAY)}">Analysis Period: {date_range.get("start", "N/A")} to {date_range.get("end", "N/A")} ({date_range.get("days", 30)} days)</font>',
                self.styles['SolviaBody']
            ))
        elements.append(Spacer(1, 30))
        
        metrics = audit_data.get('metrics', {})
        
        # Section 1: Primary Metrics
        elements.append(Paragraph("Primary Performance Indicators", self.styles['SolviaHeading1']))
        
        # Create primary metrics table with larger cells
        metrics_data = [
            ['Metric', 'Current Value', '30-Day Change', 'Status', 'Trend'],
            ['Total Impressions', f"{metrics.get('impressions', metrics.get('total_impressions', 0)):,}", 
             f"{metrics.get('impressions_change', 0):+.1f}%", 
             Paragraph(self._get_status_indicator(metrics.get('impressions_change', 0)), self.styles['SolviaBody']),
             self._get_trend_arrow(metrics.get('impressions_change', 0))],
            ['Total Clicks', f"{metrics.get('clicks', metrics.get('total_clicks', 0)):,}",
             f"{metrics.get('clicks_change', 0):+.1f}%", 
             Paragraph(self._get_status_indicator(metrics.get('clicks_change', 0)), self.styles['SolviaBody']),
             self._get_trend_arrow(metrics.get('clicks_change', 0))],
            ['Click-Through Rate', f"{metrics.get('ctr', metrics.get('average_ctr', 0)):.2f}%",
             f"{metrics.get('ctr_change', 0):+.1f}%", 
             Paragraph(self._get_status_indicator(metrics.get('ctr_change', 0)), self.styles['SolviaBody']),
             self._get_trend_arrow(metrics.get('ctr_change', 0))],
            ['Average Position', f"{metrics.get('avg_position', metrics.get('average_position', 0)):.1f}",
             f"{metrics.get('position_change', 0):+.1f}", 
             Paragraph(self._get_status_indicator(-metrics.get('position_change', 0)), self.styles['SolviaBody']),
             self._get_trend_arrow(-metrics.get('position_change', 0))],
        ]
        
        # Full width table for better presentation
        table = Table(metrics_data, colWidths=[2.2*inch, 1.4*inch, 1.3*inch, 1.1*inch, 1.1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), SOLVIA_ORANGE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, SOLVIA_LIGHT_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, SOLVIA_LIGHT_GRAY]),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 40))
        
        # Section 2: Additional Metrics
        elements.append(Paragraph("Additional SEO Metrics", self.styles['SolviaHeading1']))
        
        additional_data = [
            ['Metric', 'Value', 'Industry Benchmark', 'Performance'],
            ['Total Keywords', f"{metrics.get('total_queries', 0):,}", '100+', 
             self._get_performance_level(metrics.get('total_queries', 0), 100)],
            ['Indexed Pages', f"{metrics.get('total_pages', 0):,}", '50+',
             self._get_performance_level(metrics.get('total_pages', 0), 50)],
            ['Avg. Time on Site', f"{metrics.get('avg_time_on_site', 'N/A')}", '2+ min', 'N/A'],
            ['Bounce Rate', f"{metrics.get('bounce_rate', 'N/A')}", '<50%', 'N/A'],
        ]
        
        # Full width table matching primary table
        table2 = Table(additional_data, colWidths=[2.2*inch, 1.6*inch, 1.6*inch, 1.7*inch])
        table2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), SOLVIA_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, SOLVIA_LIGHT_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, SOLVIA_LIGHT_GRAY]),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
        ]))
        
        elements.append(table2)
        
        # Add page break before Performance Summary
        elements.append(PageBreak())
        
        # Section 3: Performance Summary (New Page)
        elements.append(Paragraph("Performance Summary", self.styles['SolviaHeading1']))
        
        # Create performance interpretation
        perf_summary = self._create_performance_summary(metrics)
        elements.append(Paragraph(perf_summary, self.styles['SolviaBody']))
        
        return elements
    
    def _get_trend_arrow(self, value: float) -> str:
        """Get trend arrow with actual values"""
        if value > 5:
            return f"↑↑ +{value:.1f}%"
        elif value > 0:
            return f"↑ +{value:.1f}%"
        elif value == 0:
            return "→ 0.0%"
        elif value > -5:
            return f"↓ {value:.1f}%"
        else:
            return f"↓↓ {value:.1f}%"
    
    def _get_performance_level(self, actual: float, benchmark: float) -> str:
        """Get performance level compared to benchmark"""
        if actual >= benchmark:
            return "Good"
        elif actual >= benchmark * 0.5:
            return "Fair"
        else:
            return "Poor"
    
    def _create_performance_summary(self, metrics: Dict) -> str:
        """Create a performance summary text"""
        impressions = metrics.get('impressions', metrics.get('total_impressions', 0))
        clicks = metrics.get('clicks', metrics.get('total_clicks', 0))
        ctr = metrics.get('ctr', metrics.get('average_ctr', 0))
        position = metrics.get('avg_position', metrics.get('average_position', 0))
        
        summary = f"""
        <b>Overall Performance Analysis:</b><br/>
        <br/>
        """
        
        if impressions == 0:
            summary += f'• <font color="{get_hex_string(SOLVIA_RED)}">Your website currently has no search visibility</font>, which is a critical issue requiring immediate attention.<br/>'
        elif impressions < 100:
            summary += f'• Your website has <font color="{get_hex_string(SOLVIA_ORANGE)}">very limited search visibility</font> with only {impressions:,} impressions.<br/>'
        elif impressions < 1000:
            summary += f'• Your website has <font color="{get_hex_string(SOLVIA_YELLOW)}">moderate search visibility</font> with {impressions:,} impressions.<br/>'
        else:
            summary += f'• Your website has <font color="{get_hex_string(SOLVIA_GREEN)}">good search visibility</font> with {impressions:,} impressions.<br/>'
        
        if ctr < 2:
            summary += f'• Your click-through rate of {ctr:.2f}% is <font color="{get_hex_string(SOLVIA_RED)}">below industry standards</font> and needs improvement.<br/>'
        elif ctr < 5:
            summary += f'• Your click-through rate of {ctr:.2f}% is <font color="{get_hex_string(SOLVIA_YELLOW)}">average</font> with room for optimization.<br/>'
        else:
            summary += f'• Your click-through rate of {ctr:.2f}% is <font color="{get_hex_string(SOLVIA_GREEN)}">performing well</font>.<br/>'
        
        if position > 20:
            summary += f'• Average position of {position:.1f} indicates your pages typically appear on <font color="{get_hex_string(SOLVIA_RED)}">page {int(position/10)+1} of search results</font>.<br/>'
        elif position > 10:
            summary += f'• Average position of {position:.1f} indicates your pages typically appear on <font color="{get_hex_string(SOLVIA_ORANGE)}">page 2 of search results</font>.<br/>'
        else:
            summary += f'• Average position of {position:.1f} indicates your pages typically appear on <font color="{get_hex_string(SOLVIA_GREEN)}">page 1 of search results</font>.<br/>'
        
        return summary
    
    def _create_issues_section(self, audit_data: Dict[str, Any]):
        """Create issues section"""
        elements = []
        
        elements.append(Paragraph("Issues Detected", self.styles['SolviaHeading1']))
        
        issues = audit_data.get('issues', [])
        
        if not issues:
            elements.append(Paragraph(
                "No significant issues detected. Your website is performing well!",
                self.styles['SolviaBody']
            ))
        else:
            # Group issues by severity
            critical = [i for i in issues if i.get('severity') == 'critical']
            high = [i for i in issues if i.get('severity') == 'high']
            medium = [i for i in issues if i.get('severity') == 'medium']
            low = [i for i in issues if i.get('severity') == 'low']
            
            # Add critical issues
            if critical:
                elements.append(Paragraph(
                    f'<font color="{get_hex_string(SOLVIA_RED)}"><b>Critical Issues ({len(critical)})</b></font>',
                    self.styles['SolviaHeading2']
                ))
                for issue in critical:
                    elements.extend(self._format_issue(issue, SOLVIA_RED))
                elements.append(Spacer(1, 15))
            
            # Add high priority issues
            if high:
                elements.append(Paragraph(
                    f'<font color="{get_hex_string(SOLVIA_ORANGE)}"><b>High Priority Issues ({len(high)})</b></font>',
                    self.styles['SolviaHeading2']
                ))
                for issue in high:
                    elements.extend(self._format_issue(issue, SOLVIA_ORANGE))
                elements.append(Spacer(1, 15))
            
            # Add medium priority issues
            if medium:
                elements.append(Paragraph(
                    f'<font color="{get_hex_string(SOLVIA_YELLOW)}"><b>Medium Priority Issues ({len(medium)})</b></font>',
                    self.styles['SolviaHeading2']
                ))
                for issue in medium:
                    elements.extend(self._format_issue(issue, SOLVIA_YELLOW))
                elements.append(Spacer(1, 15))
        
        return elements
    
    def _format_issue(self, issue: Dict[str, Any], color: HexColor):
        """Format a single issue"""
        elements = []
        
        # Issue title
        elements.append(Paragraph(
            f'<font color="{get_hex_string(color)}">• <b>{issue.get("title", "Unknown Issue")}</b></font>',
            self.styles['SolviaBody']
        ))
        
        # Issue description
        if issue.get('description'):
            elements.append(Paragraph(
                f'  {issue["description"]}',
                self.styles['SolviaBody']
            ))
        
        # Business impact
        if issue.get('business_impact'):
            elements.append(Paragraph(
                f'  <font color="{get_hex_string(SOLVIA_GRAY)}"><i>Impact: {issue["business_impact"]}</i></font>',
                self.styles['SolviaBody']
            ))
        
        # Recommendation
        if issue.get('recommendation'):
            elements.append(Paragraph(
                f'  <font color="{get_hex_string(SOLVIA_GREEN)}">✓ {issue["recommendation"]}</font>',
                self.styles['SolviaBody']
            ))
        
        elements.append(Spacer(1, 10))
        
        return elements
    
    def _create_recommendations_section(self, audit_data: Dict[str, Any]):
        """Create recommendations section"""
        elements = []
        
        elements.append(Paragraph("Recommended Actions", self.styles['SolviaHeading1']))
        
        recommendations = audit_data.get('recommendations', [])
        
        if recommendations:
            for i, rec in enumerate(recommendations[:5], 1):  # Top 5 recommendations
                elements.append(Paragraph(
                    f"<b>{i}. {rec.get('title', '')}</b>",
                    self.styles['SolviaHeading3']
                ))
                
                if rec.get('description'):
                    elements.append(Paragraph(
                        rec['description'],
                        self.styles['SolviaBody']
                    ))
                
                if rec.get('priority'):
                    priority_color = {
                        'high': SOLVIA_RED,
                        'medium': SOLVIA_ORANGE,
                        'low': SOLVIA_YELLOW
                    }.get(rec['priority'].lower(), SOLVIA_GRAY)
                    
                    elements.append(Paragraph(
                        f'<font color="{get_hex_string(priority_color)}">Priority: {rec["priority"].upper()}</font>',
                        self.styles['SolviaBody']
                    ))
                
                elements.append(Spacer(1, 10))
        else:
            elements.append(Paragraph(
                "Continue monitoring your SEO metrics and maintain current best practices.",
                self.styles['SolviaBody']
            ))
        
        return elements
    
    def _create_footer(self):
        """Create report footer"""
        elements = []
        
        elements.append(Spacer(1, 30))
        
        # Footer line
        elements.append(Paragraph(
            '<font color="#EC6019">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</font>',
            self.styles['SolviaBody']
        ))
        
        # Footer text
        footer_text = """
        <para align="center">
        <font color="#6B7280">Generated by</font> 
        <font color="#EC6019"><b>Solvia</b></font> 
        <font color="#6B7280">- Your AI-Powered SEO Assistant</font><br/>
        <font color="#6B7280" size="9">© 2025 Solvia. All rights reserved.</font>
        </para>
        """
        elements.append(Paragraph(footer_text, self.styles['SolviaBody']))
        
        return elements
    
    def _get_status_indicator(self, change: float) -> str:
        """Get colorized status indicator with icons"""
        if change > 5:
            return '<font color="#10B981">🟢 Good</font>'
        elif change > 0:
            return '<font color="#F59E0B">🟡 Improving</font>'
        elif change == 0:
            return '<font color="#6B7280">⚪ Stable</font>'
        elif change > -5:
            return '<font color="#F59E0B">🟠 Declining</font>'
        else:
            return '<font color="#EF4444">🔴 Poor</font>'