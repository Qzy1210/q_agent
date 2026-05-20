package websocket

import (
	"encoding/json"

	"go.uber.org/zap"
	"websocket-platform/internal/logic"
)

// MessageRouter 消息路由器
type MessageRouter struct {
	handlers       map[MessageType]MessageHandler
	connManager    *ConnectionManager    // 连接管理器
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
	router.RegisterHandler(MessageTypeHistory, router.handleHistory)
	router.RegisterHandler(MessageTypeAgentResult, router.handleAgentResult)

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
		zap.L().Warn("⚠️ 未知的消息类型，无对应处理器",
			zap.String("type", string(message.Type)),
			zap.String("message_id", message.ID),
			zap.String("client_id", client.ID),
		)
		return
	}

	// 保存消息到数据库（心跳和历史消息不保存）
	if r.sessionManager != nil && message.Type != MessageTypeHeartbeat && message.Type != MessageTypeHistory {
		go r.saveMessage(client, message)
	}

	handler(client, message)
}

// saveMessage 保存消息到数据库
func (r *MessageRouter) saveMessage(client *Client, message *Message) {
	// 只序列化 content 部分，而不是整个消息
	contentBytes, err := json.Marshal(message.Content)
	if err != nil {
		zap.L().Error("failed to serialize message content for saving",
			zap.Error(err),
			zap.String("message_id", message.ID),
		)
		return
	}

	// 根据客户端类型确定消息来源类型
	// 1: App 发送的消息, 2: Agent 回复的消息
	clientType := 1 // 默认为 App
	if client.Type == ClientTypeAgent {
		clientType = 2
	}

	// 转换时间戳为毫秒（如果原来是秒级时间戳）
	timestamp := message.Timestamp
	if timestamp < 10000000000 { // 小于这个值说明是秒级时间戳，需要转换为毫秒
		timestamp = timestamp * 1000
	}

	if err := r.sessionManager.SaveMessage(
		message.ID,
		message.SessionID,
		string(message.Type),
		message.From,
		message.To,
		string(contentBytes),
		timestamp,
		clientType,
	); err != nil {
		zap.L().Error("failed to save message",
			zap.Error(err),
			zap.String("message_id", message.ID),
		)
	}
}

// handleTextMessage 处理文本消息
func (r *MessageRouter) handleTextMessage(client *Client, message *Message) {
	// 安全获取文本内容
	textContent := message.GetTextContent()
	textPreview := ""
	if textContent != nil {
		textPreview = truncateText(textContent.Text, 50)
	} else {
		textPreview = "[无法解析文本内容]"
	}

	zap.L().Info("💬 处理文本消息",
		zap.String("from", client.ID),
		zap.String("client_type", string(client.Type)),
		zap.String("session_id", client.SessionID),
		zap.String("text_preview", textPreview),
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
	zap.L().Info("📁 处理文件消息",
		zap.String("from", client.ID),
		zap.String("client_type", string(client.Type)),
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
	zap.L().Info("🔧 处理工具调用",
		zap.String("from", client.ID),
		zap.String("client_type", string(client.Type)),
		zap.String("session_id", client.SessionID),
	)

	// App 请求调用工具，转发给 Agent
	if client.Type == ClientTypeApp {
		r.forwardToAgent(client, message)
	}
}

// handleToolResult 处理工具结果
func (r *MessageRouter) handleToolResult(client *Client, message *Message) {
	zap.L().Info("✅ 处理工具结果",
		zap.String("from", client.ID),
		zap.String("client_type", string(client.Type)),
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

// handleHistory 处理历史消息请求
// 历史消息请求不需要转发给 Agent，而是直接从数据库查询并返回
func (r *MessageRouter) handleHistory(client *Client, message *Message) {
	zap.L().Info("📜 处理历史消息请求",
		zap.String("from", client.ID),
		zap.String("client_type", string(client.Type)),
		zap.String("session_id", client.SessionID),
	)

	// 历史消息请求由 Agent 客户端处理（查询数据库）
	// App 客户端发送 history 请求，转发给 Agent
	if client.Type == ClientTypeApp {
		r.forwardToAgent(client, message)
	}
}

// handleAgentResult 处理 Agent 执行结果消息
// Agent 返回的完整执行结果，包含工具调用轨迹，转发给 App 客户端
func (r *MessageRouter) handleAgentResult(client *Client, message *Message) {
	zap.L().Info("🎯 处理Agent结果消息",
		zap.String("from", client.ID),
		zap.String("client_type", string(client.Type)),
		zap.String("session_id", client.SessionID),
	)

	// Agent 结果消息转发给 App 客户端
	switch client.Type {
	case ClientTypeAgent:
		r.forwardToApp(client, message)
	case ClientTypeApp:
		// App 发送的 agent_result（不太可能，但安全处理）
		r.forwardToAgent(client, message)
	}
}

// forwardToAgent 转发消息给 Agent
func (r *MessageRouter) forwardToAgent(client *Client, message *Message) {
	// 设置消息来源类型：App发送的消息为1
	message.ClientType = 1

	// 获取同会话的 Agent 客户端列表
	agentClients := r.connManager.GetBySessionID(client.SessionID)
	if len(agentClients) == 0 {
		zap.L().Warn("⚠️ 会话中没有找到 Agent 客户端",
			zap.String("session_id", client.SessionID),
			zap.String("from_app", client.ID),
		)
		r.sendNoAgentError(client)
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
		zap.L().Warn("⚠️ 会话中没有可用的 Agent",
			zap.String("session_id", client.SessionID),
			zap.String("from_app", client.ID),
		)
		r.sendNoAgentError(client)
		return
	}

	// 序列化消息
	data, err := message.ToJSON()
	if err != nil {
		zap.L().Error("消息序列化失败",
			zap.Error(err),
			zap.String("message_id", message.ID),
		)
		return
	}

	// 发送消息给 Agent
	if err := targetAgent.WriteMessage(data); err != nil {
		zap.L().Error("发送消息给 Agent 失败",
			zap.Error(err),
			zap.String("agent_id", targetAgent.ID),
			zap.String("message_id", message.ID),
		)
		return
	}

	zap.L().Info("📤 消息已转发给 Agent",
		zap.String("from_app", client.ID),
		zap.String("to_agent", targetAgent.ID),
		zap.String("session_id", client.SessionID),
		zap.String("message_id", message.ID),
		zap.String("message_type", string(message.Type)),
	)
}

// forwardToApp 转发消息给 App
func (r *MessageRouter) forwardToApp(client *Client, message *Message) {
	// 设置消息来源类型：Agent回复的消息为2
	message.ClientType = 2

	// 获取同会话的 App 客户端列表
	appClients := r.connManager.GetBySessionID(client.SessionID)
	if len(appClients) == 0 {
		zap.L().Warn("⚠️ 会话中没有找到 App 客户端",
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
		zap.L().Warn("⚠️ 会话中没有可用的 App 客户端",
			zap.String("session_id", client.SessionID),
			zap.String("from_agent", client.ID),
		)
		return
	}

	// 序列化消息
	data, err := message.ToJSON()
	if err != nil {
		zap.L().Error("消息序列化失败",
			zap.Error(err),
			zap.String("message_id", message.ID),
		)
		return
	}

	// 发送消息给所有 App 客户端（支持多设备）
	successCount := 0
	for _, targetApp := range targetApps {
		if err := targetApp.WriteMessage(data); err != nil {
			zap.L().Error("发送消息给 App 失败",
				zap.Error(err),
				zap.String("app_id", targetApp.ID),
				zap.String("message_id", message.ID),
			)
			continue
		}
		successCount++
	}

	zap.L().Info("📤 消息已转发给 App",
		zap.String("from_agent", client.ID),
		zap.Int("target_app_count", len(targetApps)),
		zap.Int("success_count", successCount),
		zap.String("session_id", client.SessionID),
		zap.String("message_id", message.ID),
		zap.String("message_type", string(message.Type)),
	)
}

// truncateText 截断文本到指定长度
func truncateText(text string, maxLen int) string {
	if len(text) <= maxLen {
		return text
	}
	return text[:maxLen] + "..."
}

// sendNoAgentError 向 App 客户端发送"无可用 Agent"的错误消息
func (r *MessageRouter) sendNoAgentError(client *Client) {
	errMsg := NewMessage(MessageTypeError, "system", client.SessionID, map[string]interface{}{
		"code":    "no_agent_available",
		"message": "会话中没有可用的 Agent，请稍后再试",
	})
	if data, err := errMsg.ToJSON(); err == nil {
		client.WriteMessage(data)
	}
}
