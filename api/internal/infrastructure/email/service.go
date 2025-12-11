package email

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"html/template"
	"net/smtp"
	"os"
	"path/filepath"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// ============================================================================
// EMAIL SERVICE (1:1 with Python email_service.py)
// ============================================================================

// Config holds email configuration
type Config struct {
	Enabled   bool
	Host      string
	Port      int
	Username  string
	Password  string
	From      string
	FrontendURL string
}

// Service handles email sending and logging
type Service struct {
	config *Config
	db     *pgxpool.Pool
}

// NewService creates a new email service
func NewService(cfg *Config, db *pgxpool.Pool) *Service {
	return &Service{
		config: cfg,
		db:     db,
	}
}

// EmailLog represents an email log entry
type EmailLog struct {
	UserEmail      string            `json:"user_email"`
	RecipientEmail string            `json:"recipient_email"`
	EmailType      string            `json:"email_type"`
	Subject        string            `json:"subject"`
	Status         string            `json:"status"` // "sent", "failed", "skipped"
	ErrorMessage   string            `json:"error_message,omitempty"`
	AuditID        string            `json:"audit_id,omitempty"`
	AttachmentName string            `json:"attachment_name,omitempty"`
	SMTPServer     string            `json:"smtp_server"`
	SentFrom       string            `json:"sent_from"`
	SentAt         *time.Time        `json:"sent_at,omitempty"`
	Metadata       map[string]interface{} `json:"metadata,omitempty"`
}

// logEmailActivity logs email activity to database (1:1 with Python)
func (s *Service) logEmailActivity(ctx context.Context, log *EmailLog) {
	if s.db == nil {
		fmt.Printf("[EMAIL LOG] DB not available, skipping log: %s to %s - %s\n",
			log.EmailType, log.RecipientEmail, log.Status)
		return
	}

	metadataJSON, _ := json.Marshal(log.Metadata)

	query := `
		INSERT INTO email_logs
		(user_email, recipient_email, email_type, subject, status, error_message,
		 audit_id, attachment_name, smtp_server, sent_from, sent_at, metadata)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
	`

	var sentAt interface{}
	if log.SentAt != nil {
		sentAt = log.SentAt
	}

	_, err := s.db.Exec(ctx, query,
		log.UserEmail,
		log.RecipientEmail,
		log.EmailType,
		log.Subject,
		log.Status,
		log.ErrorMessage,
		log.AuditID,
		log.AttachmentName,
		log.SMTPServer,
		log.SentFrom,
		sentAt,
		string(metadataJSON),
	)

	if err != nil {
		fmt.Printf("[EMAIL LOG] Failed to log email activity: %v\n", err)
	} else {
		fmt.Printf("[EMAIL LOG] Logged email activity: %s to %s - %s\n",
			log.EmailType, log.RecipientEmail, log.Status)
	}
}

// SendAuditReportEmail sends audit report with PDF attachment (1:1 with Python)
func (s *Service) SendAuditReportEmail(ctx context.Context, recipientEmail, pdfPath, auditID string, seoScore float64, userEmail string) error {
	// Use recipient as user if not provided
	if userEmail == "" {
		userEmail = recipientEmail
	}

	subject := fmt.Sprintf("Your SEO Audit Report - Score: %.0f/100", seoScore)

	// Check if email is enabled
	if !s.config.Enabled {
		fmt.Printf("[EMAIL] Email disabled. Would have sent report to %s\n", recipientEmail)
		s.logEmailActivity(ctx, &EmailLog{
			UserEmail:      userEmail,
			RecipientEmail: recipientEmail,
			EmailType:      "audit_report",
			Subject:        subject,
			Status:         "skipped",
			ErrorMessage:   "Email disabled in settings",
			AuditID:        auditID,
			SMTPServer:     s.config.Host,
			SentFrom:       s.config.From,
		})
		return nil
	}

	// Generate HTML body
	body, err := s.generateAuditReportBody(seoScore, auditID)
	if err != nil {
		return fmt.Errorf("failed to generate email body: %w", err)
	}

	// Read PDF attachment
	var pdfData []byte
	var attachmentName string
	if pdfPath != "" {
		if _, err := os.Stat(pdfPath); err == nil {
			pdfData, err = os.ReadFile(pdfPath)
			if err != nil {
				fmt.Printf("[EMAIL] Warning: Could not read PDF file: %v\n", err)
			} else {
				attachmentName = fmt.Sprintf("seo_audit_%s.pdf", auditID)
			}
		}
	}

	// Send email
	err = s.sendEmail(recipientEmail, subject, body, attachmentName, pdfData)
	now := time.Now()

	if err != nil {
		// Log failed send
		s.logEmailActivity(ctx, &EmailLog{
			UserEmail:      userEmail,
			RecipientEmail: recipientEmail,
			EmailType:      "audit_report",
			Subject:        subject,
			Status:         "failed",
			ErrorMessage:   err.Error(),
			AuditID:        auditID,
			AttachmentName: attachmentName,
			SMTPServer:     s.config.Host,
			SentFrom:       s.config.From,
			Metadata:       map[string]interface{}{"seo_score": seoScore, "error_type": fmt.Sprintf("%T", err)}, // 1:1 with Python type(e).__name__
		})
		return fmt.Errorf("failed to send email: %w", err)
	}

	// Log successful send
	s.logEmailActivity(ctx, &EmailLog{
		UserEmail:      userEmail,
		RecipientEmail: recipientEmail,
		EmailType:      "audit_report",
		Subject:        subject,
		Status:         "sent",
		AuditID:        auditID,
		AttachmentName: attachmentName,
		SMTPServer:     s.config.Host,
		SentFrom:       s.config.From,
		SentAt:         &now,
		Metadata:       map[string]interface{}{"seo_score": seoScore},
	})

	return nil
}

// SendAuditNotification sends simple notification about audit completion (1:1 with Python)
func (s *Service) SendAuditNotification(ctx context.Context, recipientEmail, auditID string, seoScore float64, criticalIssues int, userEmail string) error {
	// Use recipient as user if not provided
	if userEmail == "" {
		userEmail = recipientEmail
	}

	subject := "Your SEO Audit is Complete"

	// Check if email is enabled
	if !s.config.Enabled {
		fmt.Printf("[EMAIL] Email disabled. Would have sent notification to %s\n", recipientEmail)
		s.logEmailActivity(ctx, &EmailLog{
			UserEmail:      userEmail,
			RecipientEmail: recipientEmail,
			EmailType:      "notification",
			Subject:        subject,
			Status:         "skipped",
			ErrorMessage:   "Email disabled in settings",
			AuditID:        auditID,
			SMTPServer:     s.config.Host,
			SentFrom:       s.config.From,
		})
		return nil
	}

	// Generate HTML body
	body := s.generateNotificationBody(seoScore, criticalIssues)

	// Send email (no attachment)
	err := s.sendEmail(recipientEmail, subject, body, "", nil)
	now := time.Now()

	if err != nil {
		// Log failed send
		s.logEmailActivity(ctx, &EmailLog{
			UserEmail:      userEmail,
			RecipientEmail: recipientEmail,
			EmailType:      "notification",
			Subject:        subject,
			Status:         "failed",
			ErrorMessage:   err.Error(),
			AuditID:        auditID,
			SMTPServer:     s.config.Host,
			SentFrom:       s.config.From,
			Metadata:       map[string]interface{}{"seo_score": seoScore, "critical_issues": criticalIssues},
		})
		return fmt.Errorf("failed to send notification: %w", err)
	}

	// Log successful send
	s.logEmailActivity(ctx, &EmailLog{
		UserEmail:      userEmail,
		RecipientEmail: recipientEmail,
		EmailType:      "notification",
		Subject:        subject,
		Status:         "sent",
		AuditID:        auditID,
		SMTPServer:     s.config.Host,
		SentFrom:       s.config.From,
		SentAt:         &now,
		Metadata:       map[string]interface{}{"seo_score": seoScore, "critical_issues": criticalIssues},
	})

	return nil
}

// sendEmail sends an email with optional attachment using STARTTLS
func (s *Service) sendEmail(to, subject, htmlBody, attachmentName string, attachmentData []byte) error {
	// Build the email
	var buf bytes.Buffer
	boundary := "solvia-email-boundary-2025"

	// Headers
	buf.WriteString(fmt.Sprintf("From: %s\r\n", s.config.From))
	buf.WriteString(fmt.Sprintf("To: %s\r\n", to))
	buf.WriteString(fmt.Sprintf("Subject: %s\r\n", subject))
	buf.WriteString("MIME-Version: 1.0\r\n")

	if len(attachmentData) > 0 {
		// Multipart email with attachment
		buf.WriteString(fmt.Sprintf("Content-Type: multipart/mixed; boundary=\"%s\"\r\n", boundary))
		buf.WriteString("\r\n")

		// HTML part
		buf.WriteString(fmt.Sprintf("--%s\r\n", boundary))
		buf.WriteString("Content-Type: text/html; charset=utf-8\r\n")
		buf.WriteString("Content-Transfer-Encoding: 7bit\r\n")
		buf.WriteString("\r\n")
		buf.WriteString(htmlBody)
		buf.WriteString("\r\n")

		// PDF attachment
		buf.WriteString(fmt.Sprintf("--%s\r\n", boundary))
		buf.WriteString("Content-Type: application/pdf\r\n")
		buf.WriteString("Content-Transfer-Encoding: base64\r\n")
		buf.WriteString(fmt.Sprintf("Content-Disposition: attachment; filename=\"%s\"\r\n", attachmentName))
		buf.WriteString("\r\n")
		buf.WriteString(base64.StdEncoding.EncodeToString(attachmentData))
		buf.WriteString("\r\n")

		buf.WriteString(fmt.Sprintf("--%s--\r\n", boundary))
	} else {
		// Simple HTML email
		buf.WriteString("Content-Type: text/html; charset=utf-8\r\n")
		buf.WriteString("\r\n")
		buf.WriteString(htmlBody)
	}

	// Connect to SMTP server
	addr := fmt.Sprintf("%s:%d", s.config.Host, s.config.Port)

	// Use PlainAuth
	auth := smtp.PlainAuth("", s.config.Username, s.config.Password, s.config.Host)

	// Send email
	err := smtp.SendMail(addr, auth, s.config.From, []string{to}, buf.Bytes())
	if err != nil {
		return fmt.Errorf("SMTP error: %w", err)
	}

	return nil
}

// generateAuditReportBody generates HTML body for audit report email (1:1 with Python)
func (s *Service) generateAuditReportBody(seoScore float64, auditID string) (string, error) {
	tmpl := `
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #EC6019; margin-bottom: 10px;">Your SEO Audit is Ready!</h1>
        </div>

        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="color: #1F2937; margin-top: 0;">SEO Score: {{.Score}}/100</h2>
            <p style="color: #6B7280;">
                We've completed a comprehensive analysis of your website's SEO performance.
                Your detailed report is attached to this email.
            </p>
        </div>

        <div style="margin-bottom: 20px;">
            <h3 style="color: #1F2937;">What's in the Report?</h3>
            <ul style="color: #6B7280;">
                <li>Complete SEO health score breakdown</li>
                <li>Key performance metrics and trends</li>
                <li>Critical issues affecting your visibility</li>
                <li>Actionable recommendations for improvement</li>
            </ul>
        </div>

        <div style="margin-bottom: 20px;">
            <p style="color: #6B7280;">
                <strong>Report ID:</strong> {{.AuditID}}<br>
                <strong>Generated:</strong> Today
            </p>
        </div>

        <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            <p style="color: #9CA3AF; font-size: 14px;">
                Powered by <strong style="color: #EC6019;">Solvia</strong> - Your AI SEO Assistant<br>
                &copy; 2025 Solvia. All rights reserved.
            </p>
        </div>
    </div>
</body>
</html>
`

	t, err := template.New("audit_report").Parse(tmpl)
	if err != nil {
		return "", err
	}

	data := struct {
		Score   string
		AuditID string
	}{
		Score:   fmt.Sprintf("%.0f", seoScore),
		AuditID: auditID,
	}

	var buf bytes.Buffer
	if err := t.Execute(&buf, data); err != nil {
		return "", err
	}

	return buf.String(), nil
}

// generateNotificationBody generates HTML body for notification email (1:1 with Python)
func (s *Service) generateNotificationBody(seoScore float64, criticalIssues int) string {
	issueText := fmt.Sprintf("%d critical issues found", criticalIssues)
	if criticalIssues == 0 {
		issueText = "No critical issues"
	}

	return fmt.Sprintf(`
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #EC6019;">Audit Complete!</h2>
        <p>Your SEO audit has been completed successfully.</p>
        <p><strong>SEO Score:</strong> %.0f/100<br>
        <strong>Status:</strong> %s</p>
        <p>View your full report in the Solvia dashboard.</p>
        <p style="margin-top: 20px;">
            <a href="%s/audit-history"
               style="background-color: #EC6019; color: white; padding: 10px 20px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View Report
            </a>
        </p>
    </div>
</body>
</html>
`, seoScore, issueText, s.config.FrontendURL)
}

// GetFilename extracts filename from path
func GetFilename(path string) string {
	return filepath.Base(path)
}
