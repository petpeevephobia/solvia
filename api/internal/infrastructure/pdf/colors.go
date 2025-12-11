package pdf

// ============================================================================
// SOLVIA BRAND COLORS (1:1 with Python pdf_generator.py lines 21-30)
// ============================================================================

// Color represents RGB color values
type Color struct {
	R, G, B int
}

// Brand colors matching Python exactly
var (
	// Primary brand color - used for current stage, highlights, links
	SolviaOrange = Color{236, 96, 25} // #EC6019

	// Text colors
	SolviaDark = Color{31, 41, 55}   // #1F2937 - Headers, titles
	SolviaGray = Color{107, 114, 128} // #6B7280 - Body text, secondary

	// Background colors
	SolviaLightGray   = Color{243, 244, 246} // #F3F4F6 - Table rows, borders
	SolviaLightGrayBG = Color{238, 238, 238} // #EEEEEE - Quote box background

	// Status colors
	SolviaGreen  = Color{22, 163, 74}  // #16A34A - Positive, score 80+
	SolviaRed    = Color{239, 68, 68}  // #EF4444 - Negative, score <40
	SolviaYellow = Color{245, 158, 11} // #F59E0B - Warning, score 60-79

	// Basic colors
	SolviaBlack = Color{0, 0, 0}       // #000000 - Borders
	SolviaWhite = Color{255, 255, 255} // #FFFFFF - Backgrounds
)

// GetScoreColor returns the appropriate color for a given SEO score (1:1 with Python)
func GetScoreColor(score float64) Color {
	switch {
	case score >= 80:
		return SolviaGreen
	case score >= 60:
		return SolviaYellow
	case score >= 40:
		return SolviaOrange
	default:
		return SolviaRed
	}
}

// GetChangeColor returns color for change values (positive=green, negative=red)
func GetChangeColor(change float64, inverse bool) Color {
	// For position, negative change is improvement (inverse=true)
	if inverse {
		change = -change
	}

	switch {
	case change > 0:
		return SolviaGreen
	case change < 0:
		return SolviaRed
	default:
		return SolviaGray
	}
}

// ToRGB returns color as RGB values (0-255)
func (c Color) ToRGB() (int, int, int) {
	return c.R, c.G, c.B
}

// ToHex returns color as hex string
func (c Color) ToHex() string {
	return "#" + intToHex(c.R) + intToHex(c.G) + intToHex(c.B)
}

func intToHex(i int) string {
	hex := "0123456789ABCDEF"
	return string(hex[i/16]) + string(hex[i%16])
}
