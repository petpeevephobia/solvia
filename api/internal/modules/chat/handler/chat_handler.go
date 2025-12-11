package handler

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/service"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/response"
)

// ChatHandler handles chat HTTP requests
type ChatHandler struct {
	chatService *service.ChatService
}

// NewChatHandler creates a new chat handler
func NewChatHandler(chatService *service.ChatService) *ChatHandler {
	return &ChatHandler{chatService: chatService}
}

// Chat processes a chat message
func (h *ChatHandler) Chat(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	var req domain.ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Message is required")
		return
	}

	resp, err := h.chatService.Chat(c.Request.Context(), userEmail, &req)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, resp)
}

// GetConversation retrieves a conversation with messages
func (h *ChatHandler) GetConversation(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid conversation ID")
		return
	}

	conv, err := h.chatService.GetConversation(c.Request.Context(), id, userEmail)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, conv)
}

// GetConversations retrieves all conversations for a user
func (h *ChatHandler) GetConversations(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	limitStr := c.DefaultQuery("limit", "20")
	limit, _ := strconv.Atoi(limitStr)

	conversations, err := h.chatService.GetConversations(c.Request.Context(), userEmail, limit)
	if err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"conversations": conversations,
	})
}

// DeleteConversation deletes a conversation
func (h *ChatHandler) DeleteConversation(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid conversation ID")
		return
	}

	if err := h.chatService.DeleteConversation(c.Request.Context(), id, userEmail); err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"message": "Conversation deleted successfully",
	})
}

// UpdateConversationTitleRequest represents the request to update title
type UpdateConversationTitleRequest struct {
	Title string `json:"title" binding:"required"`
}

// UpdateConversationTitle updates the title of a conversation
func (h *ChatHandler) UpdateConversationTitle(c *gin.Context) {
	userEmail := c.GetString("user_email")
	if userEmail == "" {
		response.Error(c, http.StatusUnauthorized, "UNAUTHORIZED", "User not authenticated")
		return
	}

	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Invalid conversation ID")
		return
	}

	var req UpdateConversationTitleRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, "BAD_REQUEST", "Title is required")
		return
	}

	if err := h.chatService.UpdateConversationTitle(c.Request.Context(), id, userEmail, req.Title); err != nil {
		handleError(c, err)
		return
	}

	response.Success(c, http.StatusOK, gin.H{
		"message": "Title updated successfully",
	})
}

// handleError converts AppError to HTTP response
func handleError(c *gin.Context, err error) {
	if appErr := apperrors.GetAppError(err); appErr != nil {
		response.Error(c, appErr.StatusCode, appErr.Code, appErr.Message)
		return
	}
	response.Error(c, http.StatusInternalServerError, "INTERNAL_ERROR", "An unexpected error occurred")
}
