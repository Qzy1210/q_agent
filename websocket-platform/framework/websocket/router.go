package websocket

import (
	"go.uber.org/zap"
	"websocket-platform/internal/logic"
)

// MessageRouter 消息路由器
type MessageRouter struct {
	handlers       map[MessageType]MessageHandler
	connManager    *ConnectionManager // 连接管理器
	sessionManager *logic.SessionManager // 会话管理器
}

// MessageHandler 消息处理函数
type MessageHandler func(client *Client, message *Message)

// NewMessageRouter 创建消息路由器
func NewMessageRouter(connManager *ConnectionManager, sessionManager *logic.SessionManager) *MessageRouter {
	router := &MessageRouter{
		handlers:       make(map[MessageType]MessageHandler),
		connManager:    connManager,
		sessionManager: sessionManager,
	}
	
	// 注册默认处理器
	router.RegisterHandler(MessageTypeText, router.handleTextMessage)
	router.RegisterHandler(MessageTypeFile, router.handleFileMessage)
	router.RegisterHandler(MessageTypeToolCall, router.handleToolCall)
	router.RegisterHandler(MessageTypeToolResult, router.handleToolResult)
	router.RegisterHandler(MessageTypeHeartbeat, router.handleHeartbeat)
	
	return router
}

// RegisterHandler 注册消息处理器
func (r *MessageRouter) RegisterHandler(msgType MessageType, handler MessageHandler) {
	r.handlers[msgType] = handler
}

// Route 路由消息
func (r *MessageRouter) Route(client *Client, message *Message) {
	handler, exists := r.handlers[message.Type]
	if !exists {
		zap.L().Warn("no handler for message type",
			zap.String("type", string(message.Type)),
			zap.String("message_id", message.ID),
		)
		return
	}
	
	// 保存消息到数据库
	if r.sessionManager != nil && message.Type != MessageTypeHeartbeat {
		go r.saveMessage(message)
	}
	
	handler(client, message)
}

// saveMessage 保存消息到数据库
func (r *MessageRouter) saveMessage(message *Message) {
	content, err := message.ToJSON()
	if err != nil {
		zap.L().Error("failed to serialize message for saving",
			zap.Error(err),
			zap.String("message_id", message.ID),
		)
		return
	}
	
	if err := r.sessionManager.SaveMessage(
		message.ID,
		message.SessionID,
		string(message.Type),
		message.From,
		message.To,
		string(content),
		message.Timestamp,
	); err != nil {
		zap.L().Error("failed to save message",
			zap.Error(err),
			zap.String("message_id", message.ID),
		)
	}
}

// handleTextMessage 处理文本消息
func (r *MessageRouter) handleTextMessage(client *Client, message *Message) {
	zap.L().Info("handling text message",
		zap.String("from", client.ID),
		zap.String("session_id", client.SessionID),
		zap.String("text", message.Content.(*TextContent).Text),
	)
	
	// 根据客户端类型转发消息
	switch client.Type {
	case ClientTypeApp:
		// App 发送的消息转发给 Agent
		r.forwardToAgent(client, message)
	case ClientTypeAgent:
		// Agent 发送的消息转发给 App
		r.forwardToApp(client, message)
	}
}

// handleFileMessage 处理文件消息
func (r *MessageRouter) handleFileMessage(client *Client, message *Message) {
	zap.L().Info("handling file message",
		zap.String("from", client.ID),
		zap.String("session_id", client.SessionID),
	)
	
	// 文件消息转发逻辑与文本消息类似
	switch client.Type {
	case ClientTypeApp:
		r.forwardToAgent(client, message)
	case ClientTypeAgent:
		r.forwardToApp(client, message)
	}
}

// handleToolCall 处理工具调用
func (r *MessageRouter) handleToolCall(client *Client, message *Message) {
	zap.L().Info("handling tool call",
		zap.String("from", client.ID),
		zap.String("session_id", client.SessionID),
	)
	
	// App 请求调用工具，转发给 Agent
	if client.Type == ClientTypeApp {
		r.forwardToAgent(client, message)
	}
}

// handleToolResult 处理工具结果
func (r *MessageRouter) handleToolResult(client *Client, message *Message) {
	zap.L().Info("handling tool result",
		zap.String("from", client.ID),
		zap.String("session_id", client.SessionID),
	)
	
	// Agent 返回工具结果，转发给 App
	if client.Type == ClientTypeAgent {
		r.forwardToApp(client, message)
	}
}

// handleHeartbeat 处理心跳消息
func (r *MessageRouter) handleHeartbeat(client *Client, message *Message) {
	// 心跳消息不需要转发，直接响应
	pongMsg := NewMessage(MessageTypeHeartbeat, "system", client.SessionID, &HeartbeatContent{
		Timestamp: message.Timestamp,
	})
	
	if data, err := pongMsg.ToJSON(); err == nil {
		client.WriteMessage(data)
	}
}

// forwardToAgent 转发消息给 Agent
func (r *MessageRouter) forwardToAgent(client *Client, message *Message) {
	// 获取同会话的 Agent 客户端列表
	agentClients := r.connManager.GetBySessionID(client.SessionID)
	if len(agentClients) == 0 {
		zap.L().Warn("no agent client found for session",
			zap.String("session_id", client.SessionID),
			zap.String("from_app", client.ID),
		)
		return
	}
	
	// 找到同会话的 Agent 客户端
	var targetAgent *Client
	for _, c := range agentClients {
		if c.Type == ClientTypeAgent && c.ID != client.ID {
			targetAgent = c
			break
		}
	}
	
	if targetAgent == nil {
		zap.L().Warn("no agent client found in session",
			zap.String("session_id", client.SessionID),
			zap.String("from_app", client.ID),
		)
		return
	}
	
	// 序列化消息
	data, err := message.ToJSON()
	if err != nil {
		zap.L().Error("failed to serialize message",
			zap.Error(err),
			zap.String("message_id", message.ID),
		)
		return
	}
	
	// 发送消息给 Agent
	if err := targetAgent.WriteMessage(data); err != nil {
		zap.L().Error("failed to send message to agent",
			zap.Error(err),
			zap.String("agent_id", targetAgent.ID),
			zap.String("message_id", message.ID),
		)
		return
	}
	
	zap.L().Info("message forwarded to agent",
		zap.String("from_app", client.ID),
		zap.String("to_agent", targetAgent.ID),
		zap.String("session_id", client.SessionID),
		zap.String("message_id", message.ID),
		zap.String("message_type", string(message.Type)),
	)
}

// forwardToApp 转发消息给 App
func (r *MessageRouter) forwardToApp(client *Client, message *Message) {
	// 获取同会话的 App 客户端列表
	appClients := r.connManager.GetBySessionID(client.SessionID)
	if len(appClients) == 0 {
		zap.L().Warn("no app client found for session",
			zap.String("session_id", client.SessionID),
			zap.String("from_agent", client.ID),
		)
		return
	}
	
	// 找到同会话的所有 App 客户端（可能多个设备）
	var targetApps []*Client
	for _, c := range appClients {
		if c.Type == ClientTypeApp && c.ID != client.ID {
			targetApps = append(targetApps, c)
		}
	}
	
	if len(targetApps) == 0 {
		zap.L().Warn("no app client found in session",
			zap.String("session_id", client.SessionID),
			zap.String("from_agent", client.ID),
		)
		return
	}
	
	// 序列化消息
	data, err := message.ToJSON()
	if err != nil {
		zap.L().Error("failed to serialize message",
			zap.Error(err),
			zap.String("message_id", message.ID),
		)
		return
	}
	
	// 发送消息给所有 App 客户端（支持多设备）
	successCount := 0
	for _, targetApp := range targetApps {
		if err := targetApp.WriteMessage(data); err != nil {
			zap.L().Error("failed to send message to app",
				zap.Error(err),
				zap.String("app_id", targetApp.ID),
				zap.String("message_id", message.ID),
			)
			continue
		}
		successCount++
	}
	
	zap.L().Info("message forwarded to app",
		zap.String("from_agent", client.ID),
		zap.Int("target_app_count", len(targetApps)),
		zap.Int("success_count", successCount),
		zap.String("session_id", client.SessionID),
		zap.String("message_id", message.ID),
		zap.String("message_type", string(message.Type)),
	)
}
