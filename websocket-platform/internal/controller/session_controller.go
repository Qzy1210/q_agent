package controller

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
	"websocket-platform/internal/logic"
	"websocket-platform/internal/model"
)

// SessionController 会话控制器
type SessionController struct {
	sessionManager *logic.SessionManager
}

// NewSessionController 创建会话控制器
func NewSessionController() *SessionController {
	return &SessionController{
		sessionManager: logic.NewSessionManager(),
	}
}

// CreateSessionRequest 创建会话请求
type CreateSessionRequest struct {
	UserID string `json:"user_id" binding:"required"`
}

// CreateSessionResponse 创建会话响应
type CreateSessionResponse struct {
	SessionID string `json:"session_id"`
	UserID    string `json:"user_id"`
	Status    string `json:"status"`
}

// CreateSession 创建新会话
// POST /api/sessions
func (sc *SessionController) CreateSession(c *gin.Context) {
	var req CreateSessionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request: " + err.Error()})
		return
	}

	// 生成会话ID
	sessionID := uuid.New().String()

	// 创建会话
	if err := sc.sessionManager.CreateSession(sessionID, req.UserID); err != nil {
		zap.L().Error("failed to create session",
			zap.Error(err),
			zap.String("user_id", req.UserID),
		)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create session"})
		return
	}

	zap.L().Info("session created via API",
		zap.String("session_id", sessionID),
		zap.String("user_id", req.UserID),
	)

	c.JSON(http.StatusCreated, CreateSessionResponse{
		SessionID: sessionID,
		UserID:    req.UserID,
		Status:    model.SessionStatusActive,
	})
}

// GetSession 获取会话详情
// GET /api/sessions/:id
func (sc *SessionController) GetSession(c *gin.Context) {
	sessionID := c.Param("id")

	session, err := sc.sessionManager.GetSession(sessionID)
	if err != nil {
		zap.L().Error("failed to get session",
			zap.Error(err),
			zap.String("session_id", sessionID),
		)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get session"})
		return
	}

	if session == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "session not found"})
		return
	}

	c.JSON(http.StatusOK, session)
}

// GetUserSessions 获取用户会话列表
// GET /api/sessions?user_id=xxx
func (sc *SessionController) GetUserSessions(c *gin.Context) {
	userID := c.Query("user_id")
	if userID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "user_id is required"})
		return
	}

	sessions, err := sc.sessionManager.GetUserSessions(userID)
	if err != nil {
		zap.L().Error("failed to get user sessions",
			zap.Error(err),
			zap.String("user_id", userID),
		)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get sessions"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"user_id":  userID,
		"sessions": sessions,
		"count":    len(sessions),
	})
}

// GetSessionMessages 获取会话消息历史
// GET /api/sessions/:id/messages?limit=50&offset=0
func (sc *SessionController) GetSessionMessages(c *gin.Context) {
	sessionID := c.Param("id")

	// 解析分页参数
	limit := 50
	offset := 0
	if l := c.Query("limit"); l != "" {
		if parsed, err := parseIntParam(l); err == nil && parsed > 0 {
			limit = parsed
		}
	}
	if o := c.Query("offset"); o != "" {
		if parsed, err := parseIntParam(o); err == nil && parsed >= 0 {
			offset = parsed
		}
	}

	// 获取消息
	messages, err := sc.sessionManager.GetSessionMessages(sessionID, limit, offset)
	if err != nil {
		zap.L().Error("failed to get session messages",
			zap.Error(err),
			zap.String("session_id", sessionID),
		)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get messages"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"session_id": sessionID,
		"messages":   messages,
		"count":      len(messages),
		"limit":      limit,
		"offset":     offset,
	})
}

// GetSessionClients 获取会话客户端列表
// GET /api/sessions/:id/clients
func (sc *SessionController) GetSessionClients(c *gin.Context) {
	sessionID := c.Param("id")

	clients, err := sc.sessionManager.GetSessionClients(sessionID)
	if err != nil {
		zap.L().Error("failed to get session clients",
			zap.Error(err),
			zap.String("session_id", sessionID),
		)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get clients"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"session_id": sessionID,
		"clients":    clients,
		"count":      len(clients),
	})
}

// CloseSession 关闭会话
// POST /api/sessions/:id/close
func (sc *SessionController) CloseSession(c *gin.Context) {
	sessionID := c.Param("id")

	// 检查会话是否存在
	session, err := sc.sessionManager.GetSession(sessionID)
	if err != nil {
		zap.L().Error("failed to get session",
			zap.Error(err),
			zap.String("session_id", sessionID),
		)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to get session"})
		return
	}

	if session == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "session not found"})
		return
	}

	// 关闭会话
	if err := sc.sessionManager.DeleteSession(sessionID); err != nil {
		zap.L().Error("failed to close session",
			zap.Error(err),
			zap.String("session_id", sessionID),
		)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to close session"})
		return
	}

	zap.L().Info("session closed via API",
		zap.String("session_id", sessionID),
	)

	c.JSON(http.StatusOK, gin.H{
		"session_id": sessionID,
		"status":     model.SessionStatusClosed,
		"message":    "session closed successfully",
	})
}

// parseIntParam 解析整数参数
func parseIntParam(s string) (int, error) {
	return strconv.Atoi(s)
}
