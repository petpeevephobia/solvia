package pdf

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/jung-kurt/gofpdf"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/domain"
	auditPDF "github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/pdf"
)

// ============================================================================
// PDF REPORT GENERATOR (1:1 with Python pdf_generator.py)
// ============================================================================

// Generator handles PDF report generation with exact Python parity
type Generator struct {
	outputDir string
	iconPath  string
}

// NewGenerator creates a new PDF generator
func NewGenerator(outputDir string) *Generator {
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		panic(fmt.Sprintf("failed to create PDF output directory: %v", err))
	}

	// Icon path - try multiple locations for compatibility
	// Priority: 1) api/static/images (development), 2) relative to working dir
	possiblePaths := []string{
		// Development path from api/ directory
		"static/images/orange-emblem.png",
		// Alternative relative paths
		"../static/images/orange-emblem.png",
		"../../static/images/orange-emblem.png",
		filepath.Join(outputDir, "..", "..", "static", "images", "orange-emblem.png"),
	}

	var iconPath string
	for _, p := range possiblePaths {
		if _, err := os.Stat(p); err == nil {
			iconPath = p
			fmt.Printf("[PDF] Found icon at: %s\n", p)
			break
		}
	}

	if iconPath == "" {
		fmt.Printf("[PDF] Warning: orange-emblem.png not found in any expected location\n")
		iconPath = "static/images/orange-emblem.png" // fallback
	}

	return &Generator{
		outputDir: outputDir,
		iconPath:  iconPath,
	}
}

// SetIconPath sets a custom icon path
func (g *Generator) SetIconPath(path string) {
	g.iconPath = path
}

// ReportData contains all data needed for PDF generation
type ReportData struct {
	WebsiteURL string
	AuditID    string
	SEOScore   float64
	StartDate  string
	EndDate    string

	// From data processor
	PDFData *auditPDF.PDFData
}

// GenerateReport generates a PDF report and returns the file path
func (g *Generator) GenerateReport(data *ReportData) (string, error) {
	pdf := g.createDocument()

	// Page 1
	g.buildPage1(pdf, data)

	// Page 2
	pdf.AddPage()
	g.buildPage2(pdf, data)

	// Generate filename (1:1 with Python: seo_audit_{audit_id}.pdf)
	filename := fmt.Sprintf("seo_audit_%s.pdf", data.AuditID)
	outputPath := filepath.Join(g.outputDir, filename)

	// Save PDF
	if err := pdf.OutputFileAndClose(outputPath); err != nil {
		return "", fmt.Errorf("failed to save PDF: %w", err)
	}

	return outputPath, nil
}

// GenerateReportBytes generates PDF and returns as bytes
func (g *Generator) GenerateReportBytes(data *ReportData) ([]byte, error) {
	pdf := g.createDocument()

	// Page 1
	g.buildPage1(pdf, data)

	// Page 2
	pdf.AddPage()
	g.buildPage2(pdf, data)

	// Generate bytes
	var buf bytes.Buffer
	if err := pdf.Output(&buf); err != nil {
		return nil, fmt.Errorf("failed to generate PDF: %w", err)
	}

	return buf.Bytes(), nil
}

// ============================================================================
// ADAPTER METHOD (for backward compatibility with audit service)
// ============================================================================

// GenerateAuditReport generates a PDF report from audit domain data (adapter)
// This bridges the audit service to the new PDF generator (1:1 with Python)
func (g *Generator) GenerateAuditReport(auditData *domain.AuditData) (string, error) {
	if auditData == nil || auditData.Audit == nil {
		return "", fmt.Errorf("audit data is nil")
	}

	// Convert domain data to PDF metrics
	pdfMetrics := &auditPDF.PDFMetrics{
		TotalImpressions: auditData.Metrics.Impressions,
		TotalClicks:      auditData.Metrics.Clicks,
		AverageCTR:       auditData.Metrics.CTR,
		AveragePosition:  auditData.Metrics.Position,
		IndexedPages:     0, // Not available from GSC
	}

	// Convert time series data
	var timeSeriesData []auditPDF.DailyMetric
	for _, ts := range auditData.TimeSeriesData {
		timeSeriesData = append(timeSeriesData, auditPDF.DailyMetric{
			Date:        ts.Date,
			Clicks:      ts.Clicks,
			Impressions: ts.Impressions,
			CTR:         ts.CTR,
			Position:    ts.Position,
		})
	}

	// Process PDF data using data processor
	pdfData := auditPDF.ProcessPDFData(
		auditData.Audit.WebsiteURL,
		pdfMetrics,
		timeSeriesData,
	)

	// Calculate date range from time series
	startDate := ""
	endDate := ""
	if len(timeSeriesData) > 0 {
		startDate = timeSeriesData[0].Date
		endDate = timeSeriesData[len(timeSeriesData)-1].Date
	} else {
		// Fallback to 30-day range
		now := time.Now()
		endDate = now.AddDate(0, 0, -1).Format("2006-01-02")
		startDate = now.AddDate(0, 0, -30).Format("2006-01-02")
	}

	// Build ReportData
	reportData := &ReportData{
		WebsiteURL: auditData.Audit.WebsiteURL,
		AuditID:    fmt.Sprintf("%d", auditData.Audit.ID),
		SEOScore:   auditData.Audit.SEOScore,
		StartDate:  startDate,
		EndDate:    endDate,
		PDFData:    pdfData,
	}

	// Generate PDF
	return g.GenerateReport(reportData)
}

// createDocument creates a new PDF document with correct settings
func (g *Generator) createDocument() *gofpdf.Fpdf {
	// Letter size: 8.5" x 11" = 612 x 792 points
	// gofpdf uses mm by default, Letter in mm is 215.9 x 279.4
	pdf := gofpdf.NewCustom(&gofpdf.InitType{
		UnitStr: "pt",
		Size:    gofpdf.SizeType{Wd: PageWidth, Ht: PageHeight},
	})

	pdf.SetMargins(MarginLeft, MarginTop, MarginRight)
	pdf.SetAutoPageBreak(false, MarginBottom)

	return pdf
}

// ============================================================================
// PAGE 1 BUILDER
// ============================================================================

func (g *Generator) buildPage1(pdf *gofpdf.Fpdf, data *ReportData) {
	pdf.AddPage()
	y := MarginTop

	// 1. Title
	y = g.drawTitle(pdf, y)

	// 2. Info Block (Website, Report ID, Date Range)
	y = g.drawInfoBlock(pdf, y, data)

	// 3. Summary Heading + 3 Paragraphs
	y = g.drawSummary(pdf, y, data)

	// 4. Progress Bar
	y = g.drawProgressBar(pdf, y, data.PDFData.SEOStage)

	// 5. Stage Description
	y = g.drawStageDescription(pdf, y, data.PDFData.SEOStageInfo.Description)

	// 6. Motivational Quote Box
	g.drawQuoteBox(pdf, y, data.PDFData.QuotePage1)

	// Footer
	g.drawFooter(pdf, 1)
}

// ============================================================================
// PAGE 2 BUILDER
// ============================================================================

func (g *Generator) buildPage2(pdf *gofpdf.Fpdf, data *ReportData) {
	y := MarginTop

	// 1. Health Score Heading + Circle
	y = g.drawHealthScore(pdf, y, data.SEOScore)

	// 2. Metrics Table
	y = g.drawMetricsTable(pdf, y, data)

	// 3. Next Steps
	y = g.drawNextSteps(pdf, y, data.PDFData.NextSteps)

	// 4. Progress Bar (again)
	y = g.drawProgressBar(pdf, y, data.PDFData.SEOStage)

	// 5. Motivational Quote Box (Page 2)
	g.drawQuoteBox(pdf, y, data.PDFData.QuotePage2)

	// Footer
	g.drawFooter(pdf, 2)
}

// ============================================================================
// DRAWING METHODS
// ============================================================================

// drawTitle draws "Your SEO Audit Report" centered
func (g *Generator) drawTitle(pdf *gofpdf.Fpdf, y float64) float64 {
	pdf.SetFont(StyleTitle.FontFamily, StyleTitle.FontStyle, StyleTitle.FontSize)
	r, gr, b := StyleTitle.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)

	title := "Your SEO Audit Report"
	titleWidth := pdf.GetStringWidth(title)
	x := (PageWidth - titleWidth) / 2

	pdf.SetXY(x, y)
	pdf.Cell(titleWidth, StyleTitle.FontSize*StyleTitle.LineHeight, title)

	return y + StyleTitle.FontSize*StyleTitle.LineHeight + 10 // SpaceAfter=20 in Python, but title has built-in space
}

// drawInfoBlock draws website URL, report ID, and date range (1:1 with Python)
// Python uses mixed colors: "Website:" in gray, URL in orange bold
func (g *Generator) drawInfoBlock(pdf *gofpdf.Fpdf, y float64, data *ReportData) float64 {
	lineHeight := 14.0

	// Line 1: "Website:" gray + URL orange bold (1:1 with Python)
	labelWebsite := "Website: "
	pdf.SetFont("Helvetica", "", 11)
	r, gr, b := SolviaGray.ToRGB()
	pdf.SetTextColor(r, gr, b)
	labelWidth := pdf.GetStringWidth(labelWebsite)

	pdf.SetFont("Helvetica", "B", 11)
	r2, gr2, b2 := SolviaOrange.ToRGB()
	urlWidth := pdf.GetStringWidth(data.WebsiteURL)

	totalW1 := labelWidth + urlWidth
	startX1 := (PageWidth - totalW1) / 2

	// Draw "Website:" in gray
	pdf.SetFont("Helvetica", "", 11)
	pdf.SetTextColor(r, gr, b)
	pdf.SetXY(startX1, y)
	pdf.Cell(labelWidth, lineHeight, labelWebsite)

	// Draw URL in orange bold
	pdf.SetFont("Helvetica", "B", 11)
	pdf.SetTextColor(r2, gr2, b2)
	pdf.SetXY(startX1+labelWidth, y)
	pdf.Cell(urlWidth, lineHeight, data.WebsiteURL)
	y += lineHeight

	// Line 2: "Report ID:" gray + ID gray (all gray)
	pdf.SetFont("Helvetica", "", 11)
	pdf.SetTextColor(r, gr, b)
	line2 := fmt.Sprintf("Report ID: %s", data.AuditID)
	w2 := pdf.GetStringWidth(line2)
	pdf.SetXY((PageWidth-w2)/2, y)
	pdf.Cell(w2, lineHeight, line2)
	y += lineHeight

	// Line 3: "Data from:" gray + date range gray
	line3 := fmt.Sprintf("Data from: %s to %s", data.StartDate, data.EndDate)
	w3 := pdf.GetStringWidth(line3)
	pdf.SetXY((PageWidth-w3)/2, y)
	pdf.Cell(w3, lineHeight, line3)
	y += lineHeight

	return y + SpacerXXL // 30pt spacer
}

// drawSummary draws "Summary" heading and 3 paragraphs with bold text support
func (g *Generator) drawSummary(pdf *gofpdf.Fpdf, y float64, data *ReportData) float64 {
	// Heading with spaceBefore: 20pt (from Python SolviaHeading1)
	y += SpaceBeforeHeading
	pdf.SetFont(StyleHeading1.FontFamily, StyleHeading1.FontStyle, StyleHeading1.FontSize)
	r, gr, b := StyleHeading1.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)

	pdf.SetXY(MarginLeft, y)
	pdf.Cell(ContentWidth, StyleHeading1.FontSize*1.2, "Summary")
	y += StyleHeading1.FontSize*1.2 + SpaceAfterHeading // spaceAfter: 12pt

	// Body text style
	pdf.SetFont(StyleBody.FontFamily, StyleBody.FontStyle, StyleBody.FontSize)
	r, gr, b = StyleBody.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)

	// Paragraph 1: Impressions (with bold text - pass original markdown)
	y = g.drawParagraph(pdf, y, data.PDFData.Summary.ImpressionsPara)
	y += SpaceAfterBody // 8pt

	// Paragraph 2: Clicks & CTR
	y = g.drawParagraph(pdf, y, data.PDFData.Summary.ClicksCTRPara)
	y += SpaceAfterBody // 8pt

	// Paragraph 3: Position
	y = g.drawParagraph(pdf, y, data.PDFData.Summary.PositionPara)
	y += SpaceAfterBody // 8pt

	return y
}

// sanitizeTextForPDF replaces Unicode characters with ASCII equivalents
// gofpdf doesn't handle Unicode well with default fonts (causes index out of range panic)
// 1:1 with Python: FPDF also has issues with Unicode, Python uses latin-1 encoding
func sanitizeTextForPDF(text string) string {
	replacements := map[string]string{
		"\u2014": "-",   // Em-dash
		"\u2013": "-",   // En-dash
		"\u201C": "\"",  // Left double quote
		"\u201D": "\"",  // Right double quote
		"\u2018": "'",   // Left single quote
		"\u2019": "'",   // Right single quote
		"\u2026": "...", // Ellipsis
		"\u2022": "*",   // Bullet
		"\u00A0": " ",   // Non-breaking space
		"\u2122": "(TM)", // Trademark
		"\u00AE": "(R)",  // Registered
		"\u00A9": "(C)",  // Copyright
		"\u00B0": "deg",  // Degree
		"\u00B1": "+/-",  // Plus-minus
		"\u00D7": "x",    // Multiplication
		"\u00F7": "/",    // Division
		"\u2192": "->",   // Right arrow
		"\u2190": "<-",   // Left arrow
		"\u2191": "^",    // Up arrow
		"\u2193": "v",    // Down arrow
	}

	result := text
	for unicodeChar, asciiChar := range replacements {
		result = strings.ReplaceAll(result, unicodeChar, asciiChar)
	}
	return result
}

// BoldSegment represents a text segment that may be bold or regular
type BoldSegment struct {
	Text   string
	IsBold bool
}

// parseBoldText parses markdown **bold** into segments (1:1 with Python re.sub)
func (g *Generator) parseBoldText(text string) []BoldSegment {
	var segments []BoldSegment
	re := regexp.MustCompile(`\*\*(.*?)\*\*`)

	lastEnd := 0
	matches := re.FindAllStringSubmatchIndex(text, -1)

	for _, match := range matches {
		// Text before this bold segment
		if match[0] > lastEnd {
			segments = append(segments, BoldSegment{
				Text:   text[lastEnd:match[0]],
				IsBold: false,
			})
		}
		// The bold text (group 1)
		segments = append(segments, BoldSegment{
			Text:   text[match[2]:match[3]],
			IsBold: true,
		})
		lastEnd = match[1]
	}

	// Remaining text after last match
	if lastEnd < len(text) {
		segments = append(segments, BoldSegment{
			Text:   text[lastEnd:],
			IsBold: false,
		})
	}

	return segments
}

// drawParagraphWithBold draws a paragraph with bold text support (1:1 with Python)
func (g *Generator) drawParagraphWithBold(pdf *gofpdf.Fpdf, y float64, text string) float64 {
	// Sanitize text to handle Unicode characters that gofpdf can't handle
	text = sanitizeTextForPDF(text)

	segments := g.parseBoldText(text)
	lineHeight := StyleBody.FontSize * StyleBody.LineHeight

	// Calculate total text width and split into lines
	// First, build plain text for word wrapping
	plainText := strings.ReplaceAll(text, "**", "")
	pdf.SetFont(StyleBody.FontFamily, "", StyleBody.FontSize)
	lines := pdf.SplitText(plainText, ContentWidth)

	// Draw each line with proper bold/regular segments
	for _, line := range lines {
		x := MarginLeft
		remainingLine := line

		// Find and draw segments for this line
		for len(remainingLine) > 0 {
			// Find if there's a bold segment starting in this remaining text
			foundBold := false
			for _, seg := range segments {
				if seg.IsBold && strings.Contains(remainingLine, seg.Text) {
					idx := strings.Index(remainingLine, seg.Text)
					if idx > 0 {
						// Draw regular text before bold
						beforeText := remainingLine[:idx]
						pdf.SetFont(StyleBody.FontFamily, "", StyleBody.FontSize)
						pdf.SetXY(x, y)
						pdf.Cell(pdf.GetStringWidth(beforeText), lineHeight, beforeText)
						x += pdf.GetStringWidth(beforeText)
						remainingLine = remainingLine[idx:]
					}

					// Draw bold text
					pdf.SetFont(StyleBody.FontFamily, "B", StyleBody.FontSize)
					pdf.SetXY(x, y)
					pdf.Cell(pdf.GetStringWidth(seg.Text), lineHeight, seg.Text)
					x += pdf.GetStringWidth(seg.Text)
					remainingLine = strings.Replace(remainingLine, seg.Text, "", 1)
					foundBold = true
					break
				}
			}

			if !foundBold {
				// Draw remaining as regular text
				pdf.SetFont(StyleBody.FontFamily, "", StyleBody.FontSize)
				pdf.SetXY(x, y)
				pdf.Cell(pdf.GetStringWidth(remainingLine), lineHeight, remainingLine)
				break
			}
		}
		y += lineHeight
	}

	// Reset to regular font
	pdf.SetFont(StyleBody.FontFamily, "", StyleBody.FontSize)
	return y
}

// drawParagraph draws a multi-line paragraph with word wrap and bold support
func (g *Generator) drawParagraph(pdf *gofpdf.Fpdf, y float64, text string) float64 {
	// Sanitize text to handle Unicode characters that gofpdf can't handle
	text = sanitizeTextForPDF(text)

	// Check if text has bold markers
	if strings.Contains(text, "**") {
		return g.drawParagraphWithBold(pdf, y, text)
	}

	// Simple text without bold
	pdf.SetXY(MarginLeft, y)
	lines := pdf.SplitText(text, ContentWidth)

	lineHeight := StyleBody.FontSize * StyleBody.LineHeight
	for _, line := range lines {
		pdf.SetX(MarginLeft)
		pdf.Cell(ContentWidth, lineHeight, line)
		y += lineHeight
	}

	return y
}

// drawProgressBar draws the 4-stage progress bar (1:1 with Python)
// Adds margin top and bottom for proper spacing
func (g *Generator) drawProgressBar(pdf *gofpdf.Fpdf, y float64, currentStage string) float64 {
	// Add margin top before progress bar (1:1 with Python spacing)
	y += SpacerMedium

	x := MarginLeft
	boxWidth := ProgressBarWidth / 4
	height := ProgressBarHeight
	radius := ProgressBarRadius

	stages := []struct {
		key       string
		name      string
		threshold string
	}{
		{"hidden", "Hidden", "1 impression"},
		{"emerging", "Emerging", "50 impressions"},
		{"discoverable", "Discoverable", "300 impressions"},
		{"trusted", "Trusted", "2000+ impressions"},
	}

	// Find current stage index
	currentIdx := 0
	for i, s := range stages {
		if s.key == currentStage {
			currentIdx = i
			break
		}
	}

	// Draw fills
	for i, stage := range stages {
		boxX := x + float64(i)*boxWidth
		isCurrent := stage.key == currentStage

		// Set fill color
		if isCurrent {
			r, gr, b := SolviaOrange.ToRGB()
			pdf.SetFillColor(r, gr, b)
		} else {
			pdf.SetFillColor(255, 255, 255)
		}

		// Draw box (with rounded corners for first/last)
		if i == 0 {
			// First box: rounded left, square right
			g.drawRoundedRectLeft(pdf, boxX, y, boxWidth, height, radius)
		} else if i == 3 {
			// Last box: square left, rounded right
			g.drawRoundedRectRight(pdf, boxX, y, boxWidth, height, radius)
		} else {
			// Middle boxes: square
			pdf.Rect(boxX, y, boxWidth, height, "F")
		}
	}

	// Draw outer border
	pdf.SetLineWidth(1)
	r, gr, b := SolviaBlack.ToRGB()
	pdf.SetDrawColor(r, gr, b)
	g.drawRoundedRectBorder(pdf, x, y, ProgressBarWidth, height, radius)

	// Draw separators
	for i := 1; i < 4; i++ {
		sepX := x + float64(i)*boxWidth

		// Color based on adjacency to current stage
		if i == currentIdx || i == currentIdx+1 {
			r, gr, b := SolviaOrange.ToRGB()
			pdf.SetDrawColor(r, gr, b)
		} else {
			r, gr, b := SolviaBlack.ToRGB()
			pdf.SetDrawColor(r, gr, b)
		}

		pdf.Line(sepX, y, sepX, y+height)
	}

	// Draw text (1:1 with Python positions)
	// Python: name_y = y + 22 from bottom = 36-22 = 14 from top
	// Python: threshold_y = y + 8 from bottom = 36-8 = 28 from top
	for i, stage := range stages {
		boxX := x + float64(i)*boxWidth
		centerX := boxX + boxWidth/2
		isCurrent := stage.key == currentStage

		// Set text color
		if isCurrent {
			pdf.SetTextColor(255, 255, 255)
		} else {
			pdf.SetTextColor(0, 0, 0)
		}

		// Stage name (bold, 11pt) - 9pt from top
		// With 41pt height: y + (41 - 32) = y + 9
		pdf.SetFont("Helvetica", "B", 11)
		nameWidth := pdf.GetStringWidth(stage.name)
		pdf.SetXY(centerX-nameWidth/2, y+(height-32))
		pdf.Cell(nameWidth, 11, stage.name)

		// Threshold (italic, 9pt) - 9pt from bottom
		// With 41pt height: y + (41 - 18) = y + 23, text ends at y + 32, leaving 9pt bottom
		// Gap between name (ends at y+20) and threshold (starts at y+23) = 3pt
		pdf.SetFont("Helvetica", "I", 9)
		threshWidth := pdf.GetStringWidth(stage.threshold)
		pdf.SetXY(centerX-threshWidth/2, y+(height-18))
		pdf.Cell(threshWidth, 9, stage.threshold)
	}

	// Add margin bottom after progress bar (more spacing before stage description)
	// Return y + height + spacing (spacing from bar bottom, not text)
	return y + height + SpacerLarge // 12pt spacing below progress bar
}

// drawStageDescription draws the stage description paragraph
func (g *Generator) drawStageDescription(pdf *gofpdf.Fpdf, y float64, description string) float64 {
	pdf.SetFont(StyleBody.FontFamily, StyleBody.FontStyle, StyleBody.FontSize)
	r, gr, b := StyleBody.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)

	y = g.drawParagraph(pdf, y, description)
	return y + SpacerLarge
}

// drawQuoteBox draws the motivational quote with icon (1:1 with Python RoundedQuoteBox)
// PIXEL-PERFECT: Icon at bottom-left of box, bubble to the right, text centered in bubble
func (g *Generator) drawQuoteBox(pdf *gofpdf.Fpdf, y float64, quote string) float64 {
	// Add margin top before quote box (1:1 with Python: ~44pt gap from previous element)
	y += 32 // Additional spacing to create ~44pt total gap

	// Sanitize text to handle Unicode characters that gofpdf can't handle
	quote = sanitizeTextForPDF(quote)

	x := MarginLeft

	// Calculate text height first (needed for positioning)
	pdf.SetFont(StyleQuote.FontFamily, StyleQuote.FontStyle, StyleQuote.FontSize)
	bubbleWidth := QuoteBubbleWidth
	textWidth := bubbleWidth - QuotePadding*2
	lines := pdf.SplitText(quote, textWidth)
	textHeight := float64(len(lines)) * StyleQuote.FontSize * StyleQuote.LineHeight

	// Calculate bubble height (1:1 with Python: max of icon_size or text + padding)
	bubbleHeight := textHeight + QuotePadding*2
	if bubbleHeight < QuoteIconSize {
		bubbleHeight = QuoteIconSize
	}

	// Draw bubble background first (so icon can overlap if needed)
	bubbleX := x + QuoteIconSize + QuoteGap
	r, gr, b := SolviaLightGrayBG.ToRGB()
	pdf.SetFillColor(r, gr, b)
	pdf.RoundedRect(bubbleX, y, bubbleWidth, bubbleHeight, QuoteRadius, "1234", "F")

	// Draw icon at TOP-LEFT (aligned with top of quote bubble)
	iconY := y // Icon starts at same Y as bubble top
	if _, err := os.Stat(g.iconPath); err == nil {
		pdf.Image(g.iconPath, x, iconY, QuoteIconSize, QuoteIconSize, false, "", 0, "")
	} else {
		fmt.Printf("[PDF] Warning: Icon not found at %s\n", g.iconPath)
	}

	// Draw text centered vertically in bubble (1:1 with Python)
	r, gr, b = StyleQuote.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)

	// Python: text_y = (self.height - text_height) / 2
	// In gofpdf, we add y (top of box) and account for text going downward
	textY := y + (bubbleHeight-textHeight)/2
	for _, line := range lines {
		pdf.SetXY(bubbleX+QuotePadding, textY)
		pdf.Cell(textWidth, StyleQuote.FontSize*StyleQuote.LineHeight, line)
		textY += StyleQuote.FontSize * StyleQuote.LineHeight
	}

	return y + bubbleHeight + SpacerXLarge
}

// drawHealthScore draws "Health Score" heading and score circle
// Python ReportLab coordinate system: Y=0 at BOTTOM, baseline positioning
// gofpdf coordinate system: Y=0 at TOP, top-left positioning
// Python: score_y = size/2 + 2 = 56.5 (baseline 2pt above center from bottom)
// Python: suffix_y = size/2 - 18 = 36.5 (baseline 18pt below center from bottom)
func (g *Generator) drawHealthScore(pdf *gofpdf.Fpdf, y float64, score float64) float64 {
	// Heading with spaceBefore: 20pt (from Python SolviaHeading1)
	y += SpaceBeforeHeading
	pdf.SetFont(StyleHeading1.FontFamily, StyleHeading1.FontStyle, StyleHeading1.FontSize)
	r, gr, b := StyleHeading1.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)

	pdf.SetXY(MarginLeft, y)
	pdf.Cell(ContentWidth, StyleHeading1.FontSize*1.2, "Health Score")
	y += StyleHeading1.FontSize*1.2 + SpaceAfterHeading // spaceAfter: 12pt

	// Score circle - centered
	circleX := PageWidth / 2
	circleY := y + ScoreCircleSize/2

	// Draw circle outline (stroke only)
	scoreColor := GetScoreColor(score)
	r, gr, b = scoreColor.ToRGB()
	pdf.SetDrawColor(r, gr, b)
	pdf.SetLineWidth(ScoreCircleStroke)
	// Python uses radius = size/2 - 10 = 44.5, which accounts for stroke
	pdf.Circle(circleX, circleY, ScoreCircleSize/2-10, "D")

	// COORDINATE CONVERSION (Python ReportLab -> gofpdf):
	// Python: Y=0 at bottom, drawString uses baseline
	// gofpdf: Y=0 at top, Cell uses top-left corner
	//
	// Centering approach: Position both texts so they appear centered as a unit
	// Score (36pt) + small gap + Suffix (14pt) should be visually centered
	// Total text height ≈ 36 + 4 (gap) + 14 = 54pt
	// Center offset = 54/2 = 27pt from center

	// Draw score number "58"
	pdf.SetFont(StyleScoreNumber.FontFamily, StyleScoreNumber.FontStyle, StyleScoreNumber.FontSize)
	r, gr, b = StyleScoreNumber.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)

	scoreStr := fmt.Sprintf("%.0f", score)
	scoreWidth := pdf.GetStringWidth(scoreStr)
	// Position score to center both texts as unit: center - 27pt (half of total height)
	scoreTextY := circleY - 24
	pdf.SetXY(circleX-scoreWidth/2, scoreTextY)
	pdf.Cell(scoreWidth, StyleScoreNumber.FontSize, scoreStr)

	// Draw "/100"
	pdf.SetFont(StyleScoreSuffix.FontFamily, StyleScoreSuffix.FontStyle, StyleScoreSuffix.FontSize)
	r, gr, b = StyleScoreSuffix.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)
	suffixWidth := pdf.GetStringWidth("/100")
	// Position suffix right below score with minimal gap (4pt)
	suffixTextY := scoreTextY + 36 + 2 // score height + small gap
	pdf.SetXY(circleX-suffixWidth/2, suffixTextY)
	pdf.Cell(suffixWidth, StyleScoreSuffix.FontSize, "/100")

	// Python: Spacer(1, 4) after score circle
	return y + ScoreCircleSize + SpacerSmall
}

// drawMetricsTable draws the 5-row metrics table (1:1 with Python)
func (g *Generator) drawMetricsTable(pdf *gofpdf.Fpdf, y float64, data *ReportData) float64 {
	x := MarginLeft
	rowHeight := 28.0   // Increased for better cell spacing
	cellPadding := 8.0  // Horizontal padding
	fontSize := 10.0    // Table font size

	colWidths := []float64{TableColMetric, TableColValue, TableColChange, TableColNotes}
	headers := []string{"Metric", "Current Value", "30-Day Change", "Notes"}

	// Draw header row
	r, gr, b := SolviaGray.ToRGB()
	pdf.SetFillColor(r, gr, b)
	pdf.Rect(x, y, ContentWidth, rowHeight, "F")

	pdf.SetFont(StyleTableHeader.FontFamily, StyleTableHeader.FontStyle, StyleTableHeader.FontSize)
	pdf.SetTextColor(255, 255, 255)

	// Vertical center: (rowHeight - fontSize) / 2
	textYOffset := (rowHeight - fontSize) / 2

	cellX := x
	for i, header := range headers {
		pdf.SetXY(cellX+cellPadding, y+textYOffset)
		pdf.Cell(colWidths[i]-cellPadding*2, fontSize, header)
		cellX += colWidths[i]
	}
	y += rowHeight

	// Data rows
	metrics := data.PDFData.Metrics
	changes := data.PDFData.Changes
	notes := data.PDFData.Notes

	// 1:1 with Python: Each row has specific format type for change column
	rows := []struct {
		metric     string
		value      string
		change     interface{}
		note       string
		isPos      bool   // true if positive change is good (inverse for position)
		changeType string // format type: "percentage", "ctr", "position", "absolute"
	}{
		{"Total Impressions", fmt.Sprintf("%d", metrics.TotalImpressions), changes.ImpressionsChange, notes.ImpressionsNote, false, "percentage"},
		{"Total Clicks", fmt.Sprintf("%d", metrics.TotalClicks), changes.ClicksChange, notes.ClicksNote, false, "percentage"},
		{"Click-Through Rate", auditPDF.FormatCTRDisplay(metrics.AverageCTR), changes.CTRChange, notes.CTRNote, false, "ctr"}, // 1:1 with Python: uses "pp"
		{"Average Position", fmt.Sprintf("%.1f", metrics.AveragePosition), changes.PositionChange, notes.PositionNote, true, "position"},
		{"Indexed Pages", fmt.Sprintf("%d", metrics.IndexedPages), changes.IndexedPagesChange, notes.IndexedPagesNote, false, "absolute"},
	}

	pdf.SetFont(StyleTableBody.FontFamily, StyleTableBody.FontStyle, StyleTableBody.FontSize)

	for i, row := range rows {
		// Alternating row background
		if i%2 == 1 {
			r, gr, b := SolviaLightGray.ToRGB()
			pdf.SetFillColor(r, gr, b)
			pdf.Rect(x, y, ContentWidth, rowHeight, "F")
		}

		// Metric name
		r, gr, b := SolviaDark.ToRGB()
		pdf.SetTextColor(r, gr, b)
		pdf.SetXY(x+cellPadding, y+textYOffset)
		pdf.Cell(colWidths[0]-cellPadding*2, fontSize, row.metric)

		// Current value
		pdf.SetXY(x+colWidths[0]+cellPadding, y+textYOffset)
		pdf.Cell(colWidths[1]-cellPadding*2, fontSize, row.value)

		// Change value with color (1:1 with Python - each metric has specific format)
		changeStr := auditPDF.FormatChangeDisplay(row.change, row.changeType)
		changeColor := g.getChangeColor(row.change, row.isPos)
		r, gr, b = changeColor.ToRGB()
		pdf.SetTextColor(r, gr, b)
		pdf.SetXY(x+colWidths[0]+colWidths[1]+cellPadding, y+textYOffset)
		pdf.Cell(colWidths[2]-cellPadding*2, fontSize, changeStr)

		// Note
		r, gr, b = SolviaGray.ToRGB()
		pdf.SetTextColor(r, gr, b)
		pdf.SetXY(x+colWidths[0]+colWidths[1]+colWidths[2]+cellPadding, y+textYOffset)
		pdf.Cell(colWidths[3]-cellPadding*2, fontSize, row.note)

		y += rowHeight
	}

	// Draw grid lines
	pdf.SetLineWidth(0.5)
	r, gr, b = SolviaLightGray.ToRGB()
	pdf.SetDrawColor(r, gr, b)

	// Vertical lines
	lineX := x
	for _, w := range colWidths {
		lineX += w
		pdf.Line(lineX, y-rowHeight*5, lineX, y)
	}

	// Add footnote: *pp = percentage points (1:1 with Python)
	// Small spacing after table, footnote on same line as table bottom
	pdf.SetFont("Helvetica", "I", 9)
	r, gr, b = SolviaGray.ToRGB()
	pdf.SetTextColor(r, gr, b)
	pdf.SetXY(MarginLeft, y+2) // 2pt below table
	pdf.Cell(ContentWidth, 10, "*pp = percentage points")

	// Python: Spacer(1, 4) after table
	return y + 12 + SpacerSmall // footnote height (10) + 2pt gap + 4pt spacer
}

// drawNextSteps draws "Your Next Steps" section
func (g *Generator) drawNextSteps(pdf *gofpdf.Fpdf, y float64, steps []string) float64 {
	y += SpacerLarge

	// Heading
	pdf.SetFont(StyleHeading2.FontFamily, StyleHeading2.FontStyle, StyleHeading2.FontSize)
	r, gr, b := StyleHeading2.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)

	pdf.SetXY(MarginLeft, y)
	pdf.Cell(ContentWidth, StyleHeading2.FontSize*1.2, "Your Next Steps")
	y += StyleHeading2.FontSize*1.2 + 8

	// Bullet points
	pdf.SetFont(StyleBody.FontFamily, StyleBody.FontStyle, StyleBody.FontSize)
	r, gr, b = StyleBody.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)

	maxSteps := 5
	if len(steps) < maxSteps {
		maxSteps = len(steps)
	}

	bulletRadius := 2.5 // Small circle radius
	bulletIndent := 12.0 // Space for bullet + gap

	for i := 0; i < maxSteps; i++ {
		// Draw filled circle bullet (1:1 with Python: • character)
		bulletY := y + StyleBody.FontSize/2 // Center bullet vertically with text
		pdf.SetFillColor(r, gr, b)
		pdf.Circle(MarginLeft+bulletRadius, bulletY, bulletRadius, "F")

		// Draw text after bullet
		stepText := sanitizeTextForPDF(steps[i])
		pdf.SetXY(MarginLeft+bulletIndent, y)
		pdf.Cell(ContentWidth-bulletIndent, StyleBody.FontSize*StyleBody.LineHeight, stepText)
		y += StyleBody.FontSize*StyleBody.LineHeight + 2
	}

	return y + SpacerMedium
}

// drawFooter draws the page footer
func (g *Generator) drawFooter(pdf *gofpdf.Fpdf, pageNum int) {
	pdf.SetFont(StyleFooter.FontFamily, StyleFooter.FontStyle, StyleFooter.FontSize)
	r, gr, b := StyleFooter.Color.ToRGB()
	pdf.SetTextColor(r, gr, b)

	// Left: "Generated on {date} with Solvia"
	dateStr := time.Now().Format("January 2, 2006")
	leftText := fmt.Sprintf("Generated on %s with Solvia", dateStr)
	pdf.SetXY(MarginLeft, PageHeight-30)
	pdf.Cell(0, StyleFooter.FontSize, leftText)

	// Right: Page number
	pageStr := fmt.Sprintf("%d", pageNum)
	pageWidth := pdf.GetStringWidth(pageStr)
	pdf.SetXY(PageWidth-MarginRight-pageWidth, PageHeight-30)
	pdf.Cell(pageWidth, StyleFooter.FontSize, pageStr)
}

// ============================================================================
// HELPER METHODS
// ============================================================================

// getChangeColor determines color for change value
func (g *Generator) getChangeColor(change interface{}, inverse bool) Color {
	if change == nil || change == "N/A" {
		return SolviaGray
	}

	changeNum, ok := change.(float64)
	if !ok {
		return SolviaGray
	}

	if inverse {
		changeNum = -changeNum
	}

	if changeNum > 0 {
		return SolviaGreen
	} else if changeNum < 0 {
		return SolviaRed
	}
	return SolviaGray
}

// drawRoundedRectLeft draws rectangle with rounded left corners
func (g *Generator) drawRoundedRectLeft(pdf *gofpdf.Fpdf, x, y, w, h, r float64) {
	pdf.RoundedRect(x, y, w+r, h, r, "13", "F")
	pdf.Rect(x+w, y, r, h, "F") // Square off right side
}

// drawRoundedRectRight draws rectangle with rounded right corners
func (g *Generator) drawRoundedRectRight(pdf *gofpdf.Fpdf, x, y, w, h, r float64) {
	pdf.Rect(x-r, y, r, h, "F") // Square off left side
	pdf.RoundedRect(x-r, y, w+r, h, r, "24", "F")
}

// drawRoundedRectBorder draws rounded rectangle border only
func (g *Generator) drawRoundedRectBorder(pdf *gofpdf.Fpdf, x, y, w, h, r float64) {
	pdf.RoundedRect(x, y, w, h, r, "1234", "D")
}
