import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), '../reports/templates')
        self.static_dir = os.path.join(os.path.dirname(__file__), '../reports/static')
        self.output_dir = os.path.join(os.path.dirname(__file__), '../reports/generated')
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load email configuration
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.email_from = os.getenv('EMAIL_FROM')

    def generate_report(self, website_data, openai_analysis):
        """Generate PDF report from website data and OpenAI analysis."""
        try:
            # Debug logging
            logger.info("Starting report generation...")
            logger.info(f"Website data keys: {website_data.keys()}")
            logger.info(f"OpenAI analysis keys: {openai_analysis.keys()}")
            logger.info(f"OpenAI analysis content: {json.dumps(openai_analysis, indent=2)}")
            
            # Create PDF document
            pdf_path = os.path.join(self.output_dir, f"seo_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            
            # Get styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30
            ))
            
            # Create content
            content = []
            
            # Title
            content.append(Paragraph(f"SEO Audit Report - {website_data['url']}", styles['CustomTitle']))
            content.append(Spacer(1, 20))
            
            # Executive Summary
            content.append(Paragraph("Executive Summary", styles['Heading1']))
            if 'executive_summary' in openai_analysis and openai_analysis['executive_summary']:
                content.append(Paragraph(openai_analysis['executive_summary'], styles['Normal']))
            else:
                content.append(Paragraph("No executive summary available.", styles['Normal']))
            content.append(Spacer(1, 20))
            
            # Core Metrics
            content.append(Paragraph("Core Metrics", styles['Heading1']))
            metrics_data = [
                ['Metric', 'Value'],
                ['Impressions', str(website_data.get('impressions', 'N/A'))],
                ['Clicks', str(website_data.get('clicks', 'N/A'))],
                ['CTR', f"{website_data.get('ctr', 0):.2f}%"],
                ['Average Position', f"{website_data.get('average_position', 0):.2f}"]
            ]
            metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            content.append(metrics_table)
            content.append(Spacer(1, 20))
            
            # Technical Metrics
            content.append(Paragraph("Technical Analysis", styles['Heading1']))
            tech_data = [
                ['Metric', 'Value'],
                ['Performance Score', f"{website_data.get('performance_score', 0)}%"],
                ['First Contentful Paint', f"{website_data.get('first_contentful_paint', 0):.2f}s"],
                ['Largest Contentful Paint', f"{website_data.get('largest_contentful_paint', 0):.2f}s"],
                ['Cumulative Layout Shift', f"{website_data.get('cumulative_layout_shift', 0):.2f}"]
            ]
            tech_table = Table(tech_data, colWidths=[3*inch, 2*inch])
            tech_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            content.append(tech_table)
            content.append(Spacer(1, 20))
            
            # Recommendations
            content.append(Paragraph("Automated Recommendations", styles['Heading1']))
            content.append(Spacer(1, 10))
            
            # Debug logging for recommendations
            recommendations = openai_analysis.get('recommendations', [])
            logger.info(f"Processing {len(recommendations)} recommendations")
            
            if recommendations:
                for rec in recommendations:
                    logger.info(f"Processing recommendation: {rec.get('title', 'No title')}")
                    content.append(Paragraph(rec['title'], styles['Heading2']))
                    content.append(Paragraph(rec['description'], styles['Normal']))
                    content.append(Paragraph(f"Action Type: {rec['action_type']}", styles['Normal']))
                    content.append(Paragraph("Implementation Steps:", styles['Normal']))
                    for step in rec['implementation_steps']:
                        content.append(Paragraph(f"• {step}", styles['Normal']))
                    content.append(Spacer(1, 10))
            else:
                content.append(Paragraph("No automated recommendations available.", styles['Normal']))
            
            # Build PDF
            doc.build(content)
            
            logger.info(f"Report generated successfully: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            logger.exception("Full traceback:")
            raise

    def send_report_email(self, recipient_email, recipient_name, website_url, pdf_path, key_findings):
        """Send the generated report via email."""
        try:
            print(f"\n📧 Attempting to send email to {recipient_email}")
            print(f"   From: {self.email_from}")
            print(f"   SMTP Server: {self.smtp_server}:{self.smtp_port}")
            
            # Verify email configuration
            if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password, self.email_from]):
                missing = []
                if not self.smtp_server: missing.append('SMTP_SERVER')
                if not self.smtp_port: missing.append('SMTP_PORT')
                if not self.smtp_username: missing.append('SMTP_USERNAME')
                if not self.smtp_password: missing.append('SMTP_PASSWORD')
                if not self.email_from: missing.append('EMAIL_FROM')
                raise ValueError(f"Missing email configuration: {', '.join(missing)}")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = recipient_email
            msg['Subject'] = f"SEO Audit Report - {website_url}"
            
            # Create email body
            email_body = f"""
            Dear {recipient_name},

            Please find attached your SEO audit report for {website_url}.

            Key Findings:
            {chr(10).join(f'- {finding}' for finding in key_findings)}

            Best regards,
            Your SEO Audit Team
            """
            
            print("   ✓ Created email message")
            
            # Attach text content
            msg.attach(MIMEText(email_body, 'plain'))
            print("   ✓ Attached email body")
            
            # Attach PDF
            print(f"   Attaching PDF from: {pdf_path}")
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
                
            with open(pdf_path, 'rb') as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
                msg.attach(pdf_attachment)
            print("   ✓ Attached PDF")
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            print("   ✓ Email sent successfully")
            
            return True
            
        except Exception as e:
            print(f"   ✗ Error sending email: {str(e)}")
            raise

    def generate_and_send_report(self, website_data, openai_analysis, recipient_email, recipient_name):
        """Generate and send the SEO report."""
        try:
            # Generate PDF report
            pdf_path = self.generate_report(website_data, openai_analysis)
            
            # Extract key findings from analysis
            key_findings = []
            if 'executive_summary' in openai_analysis:
                key_findings.append(openai_analysis['executive_summary'])
            
            # Add top recommendations
            for rec in openai_analysis.get('recommendations', [])[:3]:
                key_findings.append(f"{rec['title']}: {rec['description']}")
            
            # Send email
            self.send_report_email(recipient_email, recipient_name, website_data['url'], pdf_path, key_findings)
            
            return pdf_path
            
        except Exception as e:
            print(f"Error in generate_and_send_report: {str(e)}")
            raise 