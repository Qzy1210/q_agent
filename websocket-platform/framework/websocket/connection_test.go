package websocket

import (
	"testing"
	"time"
	
	"github.com/stretchr/testify/assert"
)

func TestNewClient(t *testing.T) {
	// 创建测试客户端
	client := &Client{
		ID:        "test_client",
		Type:      ClientTypeApp,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	assert.NotNil(t, client)
	assert.Equal(t, "test_client", client.ID)
	assert.Equal(t, ClientTypeApp, client.Type)
	assert.Equal(t, "user1", client.UserID)
	assert.Equal(t, "session1", client.SessionID)
}

func TestClientWriteMessage(t *testing.T) {
	client := &Client{
		ID:        "test_client",
		Type:      ClientTypeApp,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	// 测试发送消息
	message := []byte("test message")
	err := client.WriteMessage(message)
	assert.NoError(t, err)
	
	// 验证消息已发送到通道
	select {
	case msg := <-client.SendChan:
		assert.Equal(t, message, msg)
	default:
		t.Error("message not sent to channel")
	}
}

func TestClientUpdateActivity(t *testing.T) {
	client := &Client{
		ID:           "test_client",
		Type:         ClientTypeApp,
		UserID:       "user1",
		SessionID:    "session1",
		SendChan:     make(chan []byte, 100),
		LastActivity: time.Now().Add(-time.Hour),
	}
	
	// 更新活动时间
	oldActivity := client.LastActivity
	client.UpdateActivity()
	
	assert.True(t, client.LastActivity.After(oldActivity))
}

func TestConnectionManager(t *testing.T) {
	// 创建连接管理器
	cm := NewConnectionManager(10, nil)
	
	assert.NotNil(t, cm)
	assert.Equal(t, 0, cm.Count())
}

func TestConnectionManagerRegister(t *testing.T) {
	cm := NewConnectionManager(10, nil)
	
	client := &Client{
		ID:        "test_client",
		Type:      ClientTypeApp,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	// 注册客户端
	err := cm.Register(client)
	assert.NoError(t, err)
	assert.Equal(t, 1, cm.Count())
	
	// 验证客户端已注册
	registeredClient, exists := cm.Get("test_client")
	assert.True(t, exists)
	assert.Equal(t, client, registeredClient)
}

func TestConnectionManagerUnregister(t *testing.T) {
	cm := NewConnectionManager(10, nil)
	
	client := &Client{
		ID:        "test_client",
		Type:      ClientTypeApp,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	// 注册客户端
	cm.Register(client)
	assert.Equal(t, 1, cm.Count())
	
	// 注销客户端
	cm.Unregister("test_client")
	assert.Equal(t, 0, cm.Count())
	
	// 验证客户端已注销
	_, exists := cm.Get("test_client")
	assert.False(t, exists)
}

func TestConnectionManagerGetByUserID(t *testing.T) {
	cm := NewConnectionManager(10, nil)
	
	client1 := &Client{
		ID:        "client1",
		Type:      ClientTypeApp,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	client2 := &Client{
		ID:        "client2",
		Type:      ClientTypeApp,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	// 注册客户端
	cm.Register(client1)
	cm.Register(client2)
	
	// 根据用户ID获取客户端
	clients := cm.GetByUserID("user1")
	assert.Len(t, clients, 2)
}

func TestConnectionManagerGetBySessionID(t *testing.T) {
	cm := NewConnectionManager(10, nil)
	
	client1 := &Client{
		ID:        "client1",
		Type:      ClientTypeApp,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	client2 := &Client{
		ID:        "client2",
		Type:      ClientTypeAgent,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	// 注册客户端
	cm.Register(client1)
	cm.Register(client2)
	
	// 根据会话ID获取客户端
	clients := cm.GetBySessionID("session1")
	assert.Len(t, clients, 2)
}

func TestConnectionManagerMaxConnections(t *testing.T) {
	cm := NewConnectionManager(2, nil)
	
	client1 := &Client{
		ID:        "client1",
		Type:      ClientTypeApp,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	client2 := &Client{
		ID:        "client2",
		Type:      ClientTypeApp,
		UserID:    "user2",
		SessionID: "session2",
		SendChan:  make(chan []byte, 100),
	}
	
	client3 := &Client{
		ID:        "client3",
		Type:      ClientTypeApp,
		UserID:    "user3",
		SessionID: "session3",
		SendChan:  make(chan []byte, 100),
	}
	
	// 注册前两个客户端
	err := cm.Register(client1)
	assert.NoError(t, err)
	
	err = cm.Register(client2)
	assert.NoError(t, err)
	
	// 第三个客户端应该失败（达到最大连接数）
	err = cm.Register(client3)
	assert.Error(t, err)
	assert.Equal(t, ErrMaxConnectionsReached, err)
}
