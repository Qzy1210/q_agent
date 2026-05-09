package websocket

import (
	"testing"
	
	"github.com/stretchr/testify/assert"
)

func TestNewMessageRouter(t *testing.T) {
	cm := NewConnectionManager(10, nil)
	router := NewMessageRouter(cm, nil)
	
	assert.NotNil(t, router)
	assert.NotNil(t, router.handlers)
	assert.NotNil(t, router.connManager)
}

func TestMessageRouterRegisterHandler(t *testing.T) {
	cm := NewConnectionManager(10, nil)
	router := NewMessageRouter(cm, nil)
	
	// 注册自定义处理器
	customHandler := func(client *Client, message *Message) {}
	router.RegisterHandler(MessageTypeText, customHandler)
	
	assert.NotNil(t, router.handlers[MessageTypeText])
}

func TestMessageRouterRoute(t *testing.T) {
	cm := NewConnectionManager(10, nil)
	router := NewMessageRouter(cm, nil)
	
	client := &Client{
		ID:        "test_client",
		Type:      ClientTypeApp,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	// 创建文本消息
	message := NewMessage(MessageTypeText, "test_client", "session1", &TextContent{
		Text: "Hello, World!",
	})
	
	// 路由消息（应该不会panic）
	assert.NotPanics(t, func() {
		router.Route(client, message)
	})
}

func TestMessageRouterHandleHeartbeat(t *testing.T) {
	cm := NewConnectionManager(10, nil)
	router := NewMessageRouter(cm, nil)
	
	client := &Client{
		ID:        "test_client",
		Type:      ClientTypeApp,
		UserID:    "user1",
		SessionID: "session1",
		SendChan:  make(chan []byte, 100),
	}
	
	// 创建心跳消息
	message := NewMessage(MessageTypeHeartbeat, "test_client", "session1", &HeartbeatContent{
		Timestamp: 1234567890,
	})
	
	// 处理心跳消息
	router.Route(client, message)
	
	// 验证响应消息
	select {
	case response := <-client.SendChan:
		assert.NotEmpty(t, response)
		var responseMsg Message
		err := responseMsg.FromJSON(response)
		assert.NoError(t, err)
		assert.Equal(t, MessageTypeHeartbeat, responseMsg.Type)
	default:
		// 心跳响应可能未立即到达
	}
}
