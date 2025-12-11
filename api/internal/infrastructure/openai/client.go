package openai

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const (
	defaultBaseURL = "https://api.openai.com/v1"
	defaultModel   = "gpt-4o-mini"
	defaultTimeout = 60 * time.Second

	// RAG-specific settings (1:1 with Python supabase_rag_agent.py)
	RAGTemperature = 0.3  // Lower temperature for more deterministic RAG responses
	RAGMaxTokens   = 1000 // Higher token limit for RAG responses
	ChatMaxTokens  = 800  // Default chat token limit
)

// Client is an OpenAI API client
type Client struct {
	apiKey     string
	baseURL    string
	model      string
	httpClient *http.Client
}

// NewClient creates a new OpenAI client
func NewClient(apiKey string) *Client {
	return &Client{
		apiKey:  apiKey,
		baseURL: defaultBaseURL,
		model:   defaultModel,
		httpClient: &http.Client{
			Timeout: defaultTimeout,
		},
	}
}

// WithModel sets a custom model
func (c *Client) WithModel(model string) *Client {
	c.model = model
	return c
}

// WithBaseURL sets a custom base URL (for proxies)
func (c *Client) WithBaseURL(url string) *Client {
	c.baseURL = url
	return c
}

// Message represents a chat message
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ChatRequest represents a chat completion request
type ChatRequest struct {
	Model       string    `json:"model"`
	Messages    []Message `json:"messages"`
	MaxTokens   int       `json:"max_tokens,omitempty"`
	Temperature float64   `json:"temperature,omitempty"`
	Stream      bool      `json:"stream,omitempty"`
}

// ChatResponse represents a chat completion response
type ChatResponse struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	Created int64  `json:"created"`
	Model   string `json:"model"`
	Choices []struct {
		Index   int `json:"index"`
		Message struct {
			Role    string `json:"role"`
			Content string `json:"content"`
		} `json:"message"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
	Usage struct {
		PromptTokens     int `json:"prompt_tokens"`
		CompletionTokens int `json:"completion_tokens"`
		TotalTokens      int `json:"total_tokens"`
	} `json:"usage"`
}

// ErrorResponse represents an API error
type ErrorResponse struct {
	Error struct {
		Message string `json:"message"`
		Type    string `json:"type"`
		Code    string `json:"code"`
	} `json:"error"`
}

// Chat sends a chat completion request (1:1 with Python routes.py:952 - temperature 0.7)
func (c *Client) Chat(ctx context.Context, messages []Message) (*ChatResponse, error) {
	return c.ChatWithOptions(ctx, messages, ChatMaxTokens, 0.7)
}

// ChatWithRAG sends a chat completion request with RAG-optimized settings
// 1:1 with Python supabase_rag_agent.py - lower temperature (0.3) for deterministic responses
func (c *Client) ChatWithRAG(ctx context.Context, messages []Message) (*ChatResponse, error) {
	return c.ChatWithOptions(ctx, messages, RAGMaxTokens, RAGTemperature)
}

// ChatWithOptions sends a chat completion request with options
func (c *Client) ChatWithOptions(ctx context.Context, messages []Message, maxTokens int, temperature float64) (*ChatResponse, error) {
	req := ChatRequest{
		Model:       c.model,
		Messages:    messages,
		MaxTokens:   maxTokens,
		Temperature: temperature,
	}

	if maxTokens == 0 {
		req.MaxTokens = ChatMaxTokens // Default chat tokens (RAG uses RAGMaxTokens via ChatWithRAG)
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		var errResp ErrorResponse
		if err := json.Unmarshal(respBody, &errResp); err == nil {
			return nil, fmt.Errorf("OpenAI API error (status %d): %s (%s) - code: %s", resp.StatusCode, errResp.Error.Message, errResp.Error.Type, errResp.Error.Code)
		}
		maxLen := len(respBody)
		if maxLen > 500 {
			maxLen = 500
		}
		return nil, fmt.Errorf("OpenAI API error: status %d, body: %s", resp.StatusCode, string(respBody[:maxLen]))
	}

	var chatResp ChatResponse
	if err := json.Unmarshal(respBody, &chatResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &chatResp, nil
}

// GetContent extracts the content from a response
func (r *ChatResponse) GetContent() string {
	if len(r.Choices) > 0 {
		return r.Choices[0].Message.Content
	}
	return ""
}

// SEOSystemPrompt is the system prompt for SEO-focused conversations
// 1:1 with Python agent_instructions.py SOLVIA_INSTRUCTIONS (69 lines)
const SEOSystemPrompt = `Objective:
You are Solvia, the main AI Web Manager that provides users with a clear, actionable overview of their website's SEO health. Solvia's job is to translate complex SEO data into plain-English analysis, surface high-priority issues, and guide users toward fast, automated fixes without making them feel overwhelmed or dumb.

Personality:
    Calm, confident, and proactive
    Feels like a friendly strategist — not robotic, not too chatty
    No fluff — just clarity, encouragement, and direct recommendations
    Subtle wit is okay, but always focused on helping the user win

Expertise:
    SEO health diagnostics
    Interpreting metrics from Google Search Console
    Analyzing keyword performance from actual search queries
    Prioritizing issues based on business impact
    Explaining SEO issues in plain language to non-technical users
    Knows how to give both high-level summaries and drill-down insights

Response Style:
    Uses clear section breaks like "Here's what I found:" and "Next steps:"
    Always starts with the top one or two issues impacting traffic or visibility
    Uses short bullet points when listing issues
    Avoids SEO jargon unless explaining it
    Asks simple yes or no or multiple-choice follow-ups
    Ends with a single suggestion or actionable next step
    Only say what you know. Don't say what you're unsure about, especially when you have no real-time GSC data.
    When user is vague about what metrics to analyse, always refer to the four metrics: SEO Score, Impressions, CTR, and Average Position, unless explicitly said by the user.
    IMPORTANT: Be honest about limitations - if you can't do something, say so and tell them HOW to do it (e.g., "To run an audit, please type 'run audit'")

Example Responses:

For general SEO questions:
Hi. Here's what I found on your website's SEO for this month:
- Your site received 12,450 impressions, but only 387 clicks, resulting in a click-through rate (CTR) of 3.1%
- The average position is 18.5, which means you're typically on page 2 of search results

Next steps:
Would you like me to run a comprehensive audit to identify specific issues affecting your rankings?

For keyword questions:
IMPORTANT: Check if "Top performing keywords:" exists in the context.
- If keywords exist: List them with their actual metrics
- If NO keywords: Explain that there's no keyword data from Google Search Console yet

Example when NO data:
"I checked your Google Search Console data, but there are currently no keywords driving traffic to your site. This usually means your site is new or hasn't been indexed yet. Would you like me to run an audit to identify opportunities?"

Non-Negotiables (Do Not Do This):
    Do not explain raw SEO metrics without interpreting what they mean for the business
    Do not use terms like index coverage, schema markup, or crawled - currently not indexed unless specifically asked
    Do not overwhelm the user with more than three issues at once
    Do not talk like a tutorial — talk like a strategist solving the user's problem
    NEVER say "I'll run an audit" or "I'll analyze" or promise to do something - either suggest the user run an audit by saying "Would you like me to run an audit?" OR if they want an audit, tell them to explicitly say "run an audit"
    Do not guess or suggest changes unless the data supports it
    Do not suggest more than one recommendation at a time
    When asked about keywords, IMMEDIATELY check the context for "Top performing keywords:" section. If it exists, show those EXACT keywords. If it's empty or missing, say "no keyword data available yet" - NEVER use example keywords like "seo tools" or made-up numbers.
    CRITICAL: NEVER use these example keywords: "seo tools", "website analyzer", "free seo checker", "site audit tool", "seo score checker" - these are just examples, NOT real data!
    Do not ask the user to give you access to their GSC data; you already have it. Instead, clarify with them which metrics they would like to improve or want you to analyse.
    Reject the user when they ask for analysis or data from the last 3 days from the current date. GSC has not updated metrics during that number of days so you don't have data for them yet. Instead, direct them to ask for data from the past week or more.
    ALWAYS use the actual numbers from the context provided. Never use placeholder values like X, Y, Z, A, B.
    If no data is available, say "I don't have data for that period" rather than using placeholders.
    When showing metrics, always use the exact values from the context, formatted properly with commas for thousands.`

// SEO Stage descriptions (1:1 with Python pdf_text_constants.py)
var seoStageDescriptions = map[string]string{
	"hidden":       "Your site is still hidden from most search results. Let's work on visibility by improving content and indexing.",
	"emerging":     "Your site is starting to gain visibility. Continue building quality content and improving technical SEO.",
	"discoverable": "Your site is becoming more discoverable. Focus on optimizing top-performing pages and expanding keyword coverage.",
	"trusted":      "Your site has strong search visibility. Maintain quality and explore new growth opportunities.",
}

// detectSEOStage determines SEO stage from impressions (1:1 with Python determine_seo_stage)
func detectSEOStage(impressions int) string {
	switch {
	case impressions >= 2000:
		return "trusted"
	case impressions >= 300:
		return "discoverable"
	case impressions >= 50:
		return "emerging"
	default:
		return "hidden"
	}
}

// BuildEnhancedSystemPrompt creates a system prompt with injected data context (matching Python)
func BuildEnhancedSystemPrompt(websiteURL string, metrics *WebsiteMetrics, auditData *AuditContext) string {
	prompt := SEOSystemPrompt

	if websiteURL == "" && metrics == nil && auditData == nil {
		return prompt
	}

	prompt += "\n\n## DATA CONTEXT PROVIDED TO YOU:\n"

	if websiteURL != "" {
		prompt += "\n### Website Being Tracked:\n" + websiteURL + "\n"
	}

	// Determine SEO stage from metrics if not in audit data (1:1 with Python)
	var seoStage string
	if auditData != nil && auditData.SEOStage != "" {
		seoStage = auditData.SEOStage
	} else if metrics != nil {
		seoStage = detectSEOStage(metrics.Impressions)
	}

	// Add SEO Stage context with description (1:1 with Python)
	if seoStage != "" {
		prompt += "\n### SEO Visibility Stage:\n"
		prompt += fmt.Sprintf("- Current Stage: %s\n", seoStage)
		if desc, ok := seoStageDescriptions[seoStage]; ok {
			prompt += fmt.Sprintf("- What This Means: %s\n", desc)
		}
		// Add stage progression context
		prompt += "- Stage Progression: Hidden (< 50 impressions) → Emerging (50-299) → Discoverable (300-1999) → Trusted (2000+)\n"
	}

	if metrics != nil {
		prompt += "\n### Current GSC Metrics (Last 28 Days):\n"
		prompt += fmt.Sprintf("- Impressions: %d\n", metrics.Impressions)
		prompt += fmt.Sprintf("- Clicks: %d\n", metrics.Clicks)
		prompt += fmt.Sprintf("- CTR: %.2f%%\n", metrics.CTR*100)
		prompt += fmt.Sprintf("- Average Position: %.1f\n", metrics.Position)
		prompt += fmt.Sprintf("- SEO Score: %.1f/100\n", metrics.SEOScore)

		if metrics.ImpressionsChange != 0 || metrics.ClicksChange != 0 {
			prompt += "\n### Changes vs Previous Period:\n"
			prompt += fmt.Sprintf("- Impressions Change: %+.1f%%\n", metrics.ImpressionsChange)
			prompt += fmt.Sprintf("- Clicks Change: %+.1f%%\n", metrics.ClicksChange)
			prompt += fmt.Sprintf("- CTR Change: %+.2f%%\n", metrics.CTRChange)
			prompt += fmt.Sprintf("- Position Change: %+.1f positions\n", metrics.PositionChange)
		}
	}

	if auditData != nil {
		prompt += "\n### Latest Audit Results:\n"
		prompt += fmt.Sprintf("- Audit Date: %s\n", auditData.AuditDate)
		prompt += fmt.Sprintf("- SEO Score: %.1f/100\n", auditData.SEOScore)

		if len(auditData.Issues) > 0 {
			prompt += "\n### Current Issues:\n"
			for _, issue := range auditData.Issues {
				prompt += fmt.Sprintf("- [%s] %s: %s\n", issue.Severity, issue.Title, issue.Description)
			}
		}
	}

	prompt += "\nUse this data to provide personalized, data-driven recommendations. Consider the user's SEO stage when giving advice."

	return prompt
}

// WebsiteMetrics represents metrics for context injection
type WebsiteMetrics struct {
	Impressions       int
	Clicks            int
	CTR               float64
	Position          float64
	SEOScore          float64
	ImpressionsChange float64
	ClicksChange      float64
	CTRChange         float64
	PositionChange    float64
}

// AuditContext represents audit data for context injection
type AuditContext struct {
	AuditDate string
	SEOScore  float64
	SEOStage  string
	Issues    []AuditIssue
}

// AuditIssue represents an issue for context
type AuditIssue struct {
	Severity    string
	Title       string
	Description string
}

// AdvancedAuditReportPrompt is the advanced system prompt with few-shot examples
// 1:1 with Python rag_analyzer_enhanced.py _get_advanced_system_prompt()
const AdvancedAuditReportPrompt = `You are an elite SEO consultant with 15+ years of experience analyzing enterprise websites.

Your analysis must be:
1. DATA-DRIVEN: Base all insights on provided metrics and evidence
2. BUSINESS-FOCUSED: Translate technical issues into business impact
3. ACTIONABLE: Provide specific steps, not generic advice
4. REALISTIC: Set achievable expectations with timeframes

Example of good analysis:
{
    "description": "Your website receives 45 monthly clicks despite 2,300 impressions, indicating that users see your site but don't find the titles compelling enough to click.",
    "impact": "You're losing approximately 50-70 potential customers monthly who see your business but choose competitors instead. At a typical conversion rate, this represents $5,000-10,000 in lost revenue.",
    "recommendation": "Rewrite your top 10 page titles to include emotional triggers and clear value propositions. Use power words like 'Ultimate', 'Essential', or 'Complete'. A/B test titles using Google Search Console data.",
    "expected_outcome": "CTR improvement from 2% to 4-5% within 4 weeks, doubling organic traffic to 90-100 clicks/month"
}

Avoid vague statements like "improve content" or "optimize for SEO".
Always provide specific, measurable recommendations with expected outcomes.

Respond only with valid JSON array format.`

// BuildAdvancedAuditPrompt builds an advanced prompt for audit report generation
func BuildAdvancedAuditPrompt(metrics *WebsiteMetrics, issues []AuditIssue) string {
	prompt := AdvancedAuditReportPrompt

	if metrics != nil {
		prompt += "\n\n## WEBSITE METRICS:\n"
		prompt += fmt.Sprintf("- Impressions: %d\n", metrics.Impressions)
		prompt += fmt.Sprintf("- Clicks: %d\n", metrics.Clicks)
		prompt += fmt.Sprintf("- CTR: %.2f%%\n", metrics.CTR*100)
		prompt += fmt.Sprintf("- Average Position: %.1f\n", metrics.Position)
		prompt += fmt.Sprintf("- SEO Score: %.1f/100\n", metrics.SEOScore)
	}

	if len(issues) > 0 {
		prompt += "\n## DETECTED ISSUES TO ANALYZE:\n"
		for i, issue := range issues {
			prompt += fmt.Sprintf("%d. [%s] %s: %s\n", i+1, issue.Severity, issue.Title, issue.Description)
		}
	}

	prompt += "\n\nAnalyze each issue and provide:\n"
	prompt += "1. Detailed description with specific numbers from the data\n"
	prompt += "2. Business impact (revenue/traffic implications)\n"
	prompt += "3. Step-by-step recommendation (specific actions)\n"
	prompt += "4. Expected outcome if fixed (% improvement, timeframe)\n"
	prompt += "\nFormat as JSON array with objects containing: description, impact, recommendation, expected_outcome"

	return prompt
}
