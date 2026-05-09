package logic

import (
	"testing"
	
	"github.com/stretchr/testify/assert"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"websocket-platform/internal/model"
)

func setupTestDB(t *testing.T) *gorm.DB {
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	assert.NoError(t, err)
	
	// 自动迁移表
	err = db.AutoMigrate(
		&model.Session{},
		&model.SessionClient{},
		&model.Message{},
	)
	assert.NoError(t, err)
	
	return db
}

func TestNewSessionManager(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	assert.NotNil(t, sm)
	assert.NotNil(t, sm.db)
}

func TestCreateSession(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	err := sm.CreateSession("session1", "user1")
	assert.NoError(t, err)
	
	// 验证会话已创建
	var session model.Session
	err = sm.db.Where("id = ?", "session1").First(&session).Error
	assert.NoError(t, err)
	assert.Equal(t, "session1", session.ID)
	assert.Equal(t, "user1", session.UserID)
	assert.Equal(t, model.SessionStatusActive, session.Status)
}

func TestGetSession(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	// 创建会话
	sm.CreateSession("session1", "user1")
	
	// 获取会话
	session, err := sm.GetSession("session1")
	assert.NoError(t, err)
	assert.NotNil(t, session)
	assert.Equal(t, "session1", session.ID)
	assert.Equal(t, "user1", session.UserID)
}

func TestGetSessionNotFound(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	session, err := sm.GetSession("nonexistent")
	assert.NoError(t, err)
	assert.Nil(t, session)
}

func TestUpdateSessionStatus(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	// 创建会话
	sm.CreateSession("session1", "user1")
	
	// 更新状态
	err := sm.UpdateSessionStatus("session1", model.SessionStatusClosed)
	assert.NoError(t, err)
	
	// 验证状态已更新
	session, _ := sm.GetSession("session1")
	assert.Equal(t, model.SessionStatusClosed, session.Status)
}

func TestRegisterClient(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	err := sm.RegisterClient("session1", "client1", "app", "user1")
	assert.NoError(t, err)
	
	// 验证客户端已注册
	var sessionClient model.SessionClient
	err = sm.db.Where("client_id = ?", "client1").First(&sessionClient).Error
	assert.NoError(t, err)
	assert.Equal(t, "client1", sessionClient.ClientID)
	assert.Equal(t, "session1", sessionClient.SessionID)
	assert.Equal(t, "app", sessionClient.ClientType)
	assert.Equal(t, model.ClientStatusOnline, sessionClient.Status)
}

func TestUnregisterClient(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	// 注册客户端
	sm.RegisterClient("session1", "client1", "app", "user1")
	
	// 注销客户端
	err := sm.UnregisterClient("client1")
	assert.NoError(t, err)
	
	// 验证客户端状态已更新
	var sessionClient model.SessionClient
	err = sm.db.Where("client_id = ?", "client1").First(&sessionClient).Error
	assert.NoError(t, err)
	assert.Equal(t, model.ClientStatusOffline, sessionClient.Status)
	assert.NotNil(t, sessionClient.DisconnectedAt)
}

func TestGetSessionClients(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	// 注册多个客户端
	sm.RegisterClient("session1", "client1", "app", "user1")
	sm.RegisterClient("session1", "client2", "agent", "user1")
	
	// 获取会话客户端
	clients, err := sm.GetSessionClients("session1")
	assert.NoError(t, err)
	assert.Len(t, clients, 2)
}

func TestSaveMessage(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	err := sm.SaveMessage("msg1", "session1", "text", "client1", "client2", `{"text":"Hello"}`, 1234567890)
	assert.NoError(t, err)
	
	// 验证消息已保存
	var message model.Message
	err = sm.db.Where("id = ?", "msg1").First(&message).Error
	assert.NoError(t, err)
	assert.Equal(t, "msg1", message.ID)
	assert.Equal(t, "session1", message.SessionID)
	assert.Equal(t, "text", message.Type)
	assert.Equal(t, "client1", message.From)
}

func TestGetSessionMessages(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	// 保存多条消息
	sm.SaveMessage("msg1", "session1", "text", "client1", "client2", `{"text":"Hello1"}`, 1234567890)
	sm.SaveMessage("msg2", "session1", "text", "client1", "client2", `{"text":"Hello2"}`, 1234567891)
	sm.SaveMessage("msg3", "session1", "text", "client1", "client2", `{"text":"Hello3"}`, 1234567892)
	
	// 获取消息历史
	messages, err := sm.GetSessionMessages("session1", 10, 0)
	assert.NoError(t, err)
	assert.Len(t, messages, 3)
}

func TestGetUserSessions(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	// 创建多个会话
	sm.CreateSession("session1", "user1")
	sm.CreateSession("session2", "user1")
	sm.CreateSession("session3", "user2")
	
	// 获取用户会话
	sessions, err := sm.GetUserSessions("user1")
	assert.NoError(t, err)
	assert.Len(t, sessions, 2)
}

func TestDeleteSession(t *testing.T) {
	db := setupTestDB(t)
	sm := &SessionManager{db: db}
	
	// 创建会话并注册客户端
	sm.CreateSession("session1", "user1")
	sm.RegisterClient("session1", "client1", "app", "user1")
	sm.RegisterClient("session1", "client2", "agent", "user1")
	
	// 删除会话
	err := sm.DeleteSession("session1")
	assert.NoError(t, err)
	
	// 验证会话状态已更新
	session, _ := sm.GetSession("session1")
	assert.Equal(t, model.SessionStatusClosed, session.Status)
	
	// 验证客户端已离线
	clients, _ := sm.GetSessionClients("session1")
	assert.Len(t, clients, 0)
}
