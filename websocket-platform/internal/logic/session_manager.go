package logic

import (
	"fmt"
	"time"
	
	"go.uber.org/zap"
	"gorm.io/gorm"
	"websocket-platform/framework/drivers"
	"websocket-platform/internal/model"
)

// SessionManager 会话管理器
type SessionManager struct {
	db *gorm.DB
}

// NewSessionManager 创建会话管理器
func NewSessionManager() *SessionManager {
	return &SessionManager{
		db: drivers.DB(),
	}
}

// InitTables 初始化数据表
func (sm *SessionManager) InitTables() error {
	err := sm.db.AutoMigrate(
		&model.Session{},
		&model.SessionClient{},
		&model.Message{},
	)
	if err != nil {
		return fmt.Errorf("failed to migrate tables: %w", err)
	}
	zap.L().Info("session tables migrated successfully")
	return nil
}

// CreateSession 创建会话
func (sm *SessionManager) CreateSession(sessionID, userID string) error {
	session := &model.Session{
		ID:     sessionID,
		UserID: userID,
		Status: model.SessionStatusActive,
	}
	
	if err := sm.db.Create(session).Error; err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}
	
	zap.L().Info("session created",
		zap.String("session_id", sessionID),
		zap.String("user_id", userID),
	)
	return nil
}

// GetSession 获取会话
func (sm *SessionManager) GetSession(sessionID string) (*model.Session, error) {
	var session model.Session
	if err := sm.db.Where("id = ?", sessionID).First(&session).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get session: %w", err)
	}
	return &session, nil
}

// UpdateSessionStatus 更新会话状态
func (sm *SessionManager) UpdateSessionStatus(sessionID, status string) error {
	if err := sm.db.Model(&model.Session{}).
		Where("id = ?", sessionID).
		Update("status", status).Error; err != nil {
		return fmt.Errorf("failed to update session status: %w", err)
	}
	return nil
}

// RegisterClient 注册客户端到会话
func (sm *SessionManager) RegisterClient(sessionID, clientID, clientType, userID string) error {
	// 先检查会话是否存在，不存在则创建
	session, err := sm.GetSession(sessionID)
	if err != nil {
		return err
	}
	if session == nil {
		if err := sm.CreateSession(sessionID, userID); err != nil {
			return err
		}
	}

	// 注册客户端：使用 upsert 操作处理断线重连场景
	// 如果记录已存在，更新状态为在线；不存在则创建新记录
	sessionClient := &model.SessionClient{
		ID:         fmt.Sprintf("%s_%s", sessionID, clientID),
		SessionID:  sessionID,
		ClientID:   clientID,
		ClientType: clientType,
		UserID:     userID,
		Status:     model.ClientStatusOnline,
		// DisconnectedAt 置为 nil 表示重新上线
		DisconnectedAt: nil,
	}

	// 使用 GORM 的 FirstOrCreate 实现幂等注册
	// 先查询是否存在，存在则更新状态，不存在则创建
	var existingClient model.SessionClient
	result := sm.db.Where("id = ?", sessionClient.ID).First(&existingClient)
	if result.Error == gorm.ErrRecordNotFound {
		// 记录不存在，创建新记录
		if err := sm.db.Create(sessionClient).Error; err != nil {
			return fmt.Errorf("failed to register client: %w", err)
		}
	} else if result.Error != nil {
		return fmt.Errorf("failed to query client: %w", result.Error)
	} else {
		// 记录已存在（断线重连），更新状态为在线
		now := time.Now()
		if err := sm.db.Model(&existingClient).Updates(map[string]interface{}{
			"status":          model.ClientStatusOnline,
			"connected_at":    now,
			"disconnected_at": nil,
		}).Error; err != nil {
			return fmt.Errorf("failed to update client status: %w", err)
		}
	}

	zap.L().Info("client registered to session",
		zap.String("session_id", sessionID),
		zap.String("client_id", clientID),
		zap.String("client_type", clientType),
	)
	return nil
}

// UnregisterClient 注销客户端
func (sm *SessionManager) UnregisterClient(clientID string) error {
	now := time.Now()
	if err := sm.db.Model(&model.SessionClient{}).
		Where("client_id = ?", clientID).
		Updates(map[string]interface{}{
			"status":          model.ClientStatusOffline,
			"disconnected_at": &now,
		}).Error; err != nil {
		return fmt.Errorf("failed to unregister client: %w", err)
	}
	
	zap.L().Info("client unregistered", zap.String("client_id", clientID))
	return nil
}

// GetSessionClients 获取会话的所有客户端
func (sm *SessionManager) GetSessionClients(sessionID string) ([]*model.SessionClient, error) {
	var clients []*model.SessionClient
	if err := sm.db.Where("session_id = ? AND status = ?", sessionID, model.ClientStatusOnline).
		Find(&clients).Error; err != nil {
		return nil, fmt.Errorf("failed to get session clients: %w", err)
	}
	return clients, nil
}

// SaveMessage 保存消息
func (sm *SessionManager) SaveMessage(messageID, sessionID, msgType, from, to, content string, timestamp int64, clientType int) error {
	message := &model.Message{
		ID:         messageID,
		SessionID:  sessionID,
		Type:       msgType,
		From:       from,
		To:         to,
		Content:    content,
		Timestamp:  timestamp,
		ClientType: clientType,
	}

	if err := sm.db.Create(message).Error; err != nil {
		return fmt.Errorf("failed to save message: %w", err)
	}

	zap.L().Debug("message saved",
		zap.String("message_id", messageID),
		zap.String("session_id", sessionID),
		zap.Int("client_type", clientType),
	)
	return nil
}

// GetSessionMessages 获取会话消息历史
func (sm *SessionManager) GetSessionMessages(sessionID string, limit, offset int) ([]*model.Message, error) {
	var messages []*model.Message
	if err := sm.db.Where("session_id = ?", sessionID).
		Order("timestamp DESC").
		Limit(limit).
		Offset(offset).
		Find(&messages).Error; err != nil {
		return nil, fmt.Errorf("failed to get session messages: %w", err)
	}
	return messages, nil
}

// GetUserSessions 获取用户的所有会话
func (sm *SessionManager) GetUserSessions(userID string) ([]*model.Session, error) {
	var sessions []*model.Session
	if err := sm.db.Where("user_id = ?", userID).
		Order("updated_at DESC").
		Find(&sessions).Error; err != nil {
		return nil, fmt.Errorf("failed to get user sessions: %w", err)
	}
	return sessions, nil
}

// DeleteSession 删除会话（软删除）
func (sm *SessionManager) DeleteSession(sessionID string) error {
	// 更新会话状态为已关闭
	if err := sm.UpdateSessionStatus(sessionID, model.SessionStatusClosed); err != nil {
		return err
	}
	
	// 注销所有客户端
	now := time.Now()
	if err := sm.db.Model(&model.SessionClient{}).
		Where("session_id = ?", sessionID).
		Updates(map[string]interface{}{
			"status":          model.ClientStatusOffline,
			"disconnected_at": &now,
		}).Error; err != nil {
		return fmt.Errorf("failed to offline session clients: %w", err)
	}
	
	zap.L().Info("session deleted", zap.String("session_id", sessionID))
	return nil
}
