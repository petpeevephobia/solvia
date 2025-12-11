package pdf

// ============================================================================
// TEXT STYLES (1:1 with Python pdf_generator.py lines 301-371)
// ============================================================================

// TextStyle defines text formatting properties
type TextStyle struct {
	FontFamily string
	FontStyle  string // "", "B", "I", "BI"
	FontSize   float64
	Color      Color
	Alignment  string // "L", "C", "R", "J"
	LineHeight float64
}

// Predefined styles matching Python exactly
var (
	// Title: "Your SEO Audit Report" - 32pt Bold, Dark, Centered
	StyleTitle = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "B",
		FontSize:   32,
		Color:      SolviaDark,
		Alignment:  "C",
		LineHeight: 1.2,
	}

	// Heading1: "Summary", "Health Score" - 21pt Bold, Dark
	StyleHeading1 = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "B",
		FontSize:   21,
		Color:      SolviaDark,
		Alignment:  "L",
		LineHeight: 1.2,
	}

	// Heading2: "Your Next Steps" - 12pt Bold, Dark
	StyleHeading2 = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "B",
		FontSize:   12,
		Color:      SolviaDark,
		Alignment:  "L",
		LineHeight: 1.2,
	}

	// Body: Summary paragraphs, descriptions - 11pt Regular, Gray, Justified
	StyleBody = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "",
		FontSize:   11,
		Color:      SolviaGray,
		Alignment:  "J",
		LineHeight: 1.27, // 14pt leading / 11pt size
	}

	// Quote: Motivational quotes - 11pt Regular, Gray (1:1 with Python - uses SOLVIA_GRAY in quote box)
	StyleQuote = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "",
		FontSize:   11,
		Color:      SolviaGray, // Python uses #6B7280 via <font color="..."> in RoundedQuoteBox
		Alignment:  "L",
		LineHeight: 1.182, // 13pt leading / 11pt size = 1.182 (1:1 with Python line 368)
	}

	// Footer: "Generated on..." - 9pt Regular, Gray
	StyleFooter = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "",
		FontSize:   9,
		Color:      SolviaGray,
		Alignment:  "L",
		LineHeight: 1.2,
	}

	// Score Number: "48" in circle - 36pt Bold, Dark
	StyleScoreNumber = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "B",
		FontSize:   36,
		Color:      SolviaDark,
		Alignment:  "C",
		LineHeight: 1.0,
	}

	// Score Suffix: "/100" - 14pt Regular, Dark
	StyleScoreSuffix = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "",
		FontSize:   14,
		Color:      SolviaDark,
		Alignment:  "C",
		LineHeight: 1.0,
	}

	// Stage Name: "Hidden", "Emerging", etc - 11pt Bold
	StyleStageName = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "B",
		FontSize:   11,
		Color:      SolviaBlack, // Changes to White when current
		Alignment:  "C",
		LineHeight: 1.0,
	}

	// Stage Threshold: "50 impressions" - 9pt Italic
	StyleStageThreshold = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "I",
		FontSize:   9,
		Color:      SolviaBlack, // Changes to White when current
		Alignment:  "C",
		LineHeight: 1.0,
	}

	// Table Header: Bold, White on Gray
	StyleTableHeader = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "B",
		FontSize:   11,
		Color:      SolviaWhite,
		Alignment:  "L",
		LineHeight: 1.2,
	}

	// Table Body: Regular
	StyleTableBody = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "",
		FontSize:   11,
		Color:      SolviaDark,
		Alignment:  "L",
		LineHeight: 1.2,
	}

	// Info Text: Website URL, Report ID - 11pt, various colors
	StyleInfo = TextStyle{
		FontFamily: "Helvetica",
		FontStyle:  "",
		FontSize:   11,
		Color:      SolviaGray,
		Alignment:  "C",
		LineHeight: 1.4,
	}
)

// ============================================================================
// PAGE DIMENSIONS (1:1 with Python - Letter size)
// ============================================================================

const (
	// Letter page size in points (72 points = 1 inch)
	PageWidth  = 612.0 // 8.5 inches
	PageHeight = 792.0 // 11 inches

	// Margins
	MarginLeft   = 50.0
	MarginRight  = 50.0
	MarginTop    = 50.0
	MarginBottom = 50.0

	// Content area
	ContentWidth = PageWidth - MarginLeft - MarginRight // 512pt

	// Progress bar dimensions
	ProgressBarWidth  = 512.0 // Full content width
	ProgressBarHeight = 41.0  // Compact with 9pt padding
	ProgressBarRadius = 20.5  // Half of height for pill shape

	// Quote box dimensions
	QuoteIconSize    = 24.0  // Reduced from 32 for better proportion
	QuoteGap         = 8.0
	QuotePadding     = 12.0
	QuoteRadius      = 8.0
	QuoteBubbleWidth = 480.0 // ContentWidth - IconSize - Gap (512 - 24 - 8)

	// Score circle dimensions
	ScoreCircleSize   = 109.0
	ScoreCircleStroke = 8.0

	// Table column widths (in points, 1 inch = 72pt)
	TableColMetric  = 108.0 // 1.5 inch
	TableColValue   = 108.0 // 1.5 inch
	TableColChange  = 108.0 // 1.5 inch
	TableColNotes   = 187.2 // 2.6 inch
)

// Spacing constants (in points) - 1:1 with Python
const (
	SpacerSmall  = 4.0
	SpacerMedium = 8.0
	Spacer10     = 10.0 // After title, after Page 2 quote
	SpacerLarge  = 12.0 // Before Next Steps, after stage description
	SpacerXLarge = 20.0 // After Page 1 quote, spaceBefore Heading1
	SpacerXXL    = 30.0 // After info text block

	// Style-specific spacing (from Python paragraph styles)
	SpaceAfterTitle    = 20.0 // SolviaTitle spaceAfter
	SpaceBeforeHeading = 20.0 // SolviaHeading1 spaceBefore
	SpaceAfterHeading  = 12.0 // SolviaHeading1 spaceAfter
	SpaceAfterHeading2 = 8.0  // SolviaHeading2 spaceAfter
	SpaceAfterBody     = 8.0  // SolviaBody spaceAfter
	SpaceBetweenBullets = 2.0 // Between bullet list items
)
