package websocket

import (
	"encoding/json"
	"time"
)

// MessageType 消息类型
type MessageType string

const (
	MessageTypeText         MessageType = "text"         // 文本消息
	MessageTypeFile         MessageType = "file"         // 文件消息
	MessageTypeToolCall     MessageType = "tool_call"    // 工具调用
	MessageTypeToolResult   MessageType = "tool_result"  // 工具结果
	MessageTypeHeartbeat    MessageType = "heartbeat"    // 心跳消息
	MessageTypeStatus       MessageType = "status"       // 状态消息
	MessageTypeError        MessageType = "error"        // 错误消息
	MessageTypeHistory      MessageType = "history"      // 历史消息请求/响应
	MessageTypeAgentResult  MessageType = "agent_result" // Agent 执行结果（包含工具调用轨迹）
)

// Message WebSocket 消息
type Message struct {
	ID         string      `json:"id"`          // 消息唯一标识
	Type       MessageType `json:"type"`        // 消息类型
	From       string      `json:"from"`        // 发送者ID
	To         string      `json:"to"`          // 接收者ID（可选）
	SessionID  string      `json:"session_id"`  // 会话ID
	Timestamp  int64       `json:"timestamp"`   // 时间戳
	Content    interface{} `json:"content"`     // 消息内容
	ClientType int         `json:"client_type,omitempty"` // 客户端类型(1:App,2:Agent)
}

// NewMessage 创建新消息
func NewMessage(msgType MessageType, from, sessionID string, content interface{}) *Message {
	return &Message{
		ID:        generateMessageID(),
		Type:      msgType,
		From:      from,
		SessionID: sessionID,
		Timestamp: time.Now().Unix(),
		Content:   content,
	}
}

// ToJSON 序列化为JSON
func (m *Message) ToJSON() ([]byte, error) {
	return json.Marshal(m)
}

// FromJSON 从JSON反序列化
func (m *Message) FromJSON(data []byte) error {
	// 使用临时结构体来解析，避免直接解析 Content
	type tempMessage struct {
		ID        string          `json:"id"`
		Type      MessageType     `json:"type"`
		From      string          `json:"from"`
		To        string          `json:"to"`
		SessionID string          `json:"session_id"`
		Timestamp int64           `json:"timestamp"`
		Content   json.RawMessage `json:"content"`
	}

	var temp tempMessage
	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}

	m.ID = temp.ID
	m.Type = temp.Type
	m.From = temp.From
	m.To = temp.To
	m.SessionID = temp.SessionID
	m.Timestamp = temp.Timestamp

	// 根据消息类型解析 Content
	m.Content = parseContent(temp.Type, temp.Content)

	return nil
}

// parseContent 根据消息类型解析内容
func parseContent(msgType MessageType, rawContent json.RawMessage) interface{} {
	if len(rawContent) == 0 {
		return nil
	}

	switch msgType {
	case MessageTypeText:
		var content TextContent
		if err := json.Unmarshal(rawContent, &content); err == nil {
			return &content
		}
	case MessageTypeFile:
		var content FileContent
		if err := json.Unmarshal(rawContent, &content); err == nil {
			return &content
		}
	case MessageTypeToolCall:
		var content ToolCallContent
		if err := json.Unmarshal(rawContent, &content); err == nil {
			return &content
		}
	case MessageTypeToolResult:
		var content ToolResultContent
		if err := json.Unmarshal(rawContent, &content); err == nil {
			return &content
		}
	case MessageTypeStatus:
		var content StatusContent
		if err := json.Unmarshal(rawContent, &content); err == nil {
			return &content
		}
	case MessageTypeHeartbeat:
		var content HeartbeatContent
		if err := json.Unmarshal(rawContent, &content); err == nil {
			return &content
		}
	case MessageTypeHistory:
		var content HistoryContent
		if err := json.Unmarshal(rawContent, &content); err == nil {
			return &content
		}
	}

	// 如果解析失败，返回原始 map
	var generic map[string]interface{}
	if err := json.Unmarshal(rawContent, &generic); err == nil {
		return generic
	}

	return nil
}

// GetTextContent 安全获取文本内容
func (m *Message) GetTextContent() *TextContent {
	switch c := m.Content.(type) {
	case *TextContent:
		return c
	case map[string]interface{}:
		if text, ok := c["text"].(string); ok {
			return &TextContent{Text: text}
		}
	}
	return nil
}

// GetStatusContent 安全获取状态内容
func (m *Message) GetStatusContent() *StatusContent {
	switch c := m.Content.(type) {
	case *StatusContent:
		return c
	case map[string]interface{}:
		status, _ := c["status"].(string)
		message, _ := c["message"].(string)
		return &StatusContent{Status: status, Message: message}
	}
	return nil
}

// TextContent 文本消息内容
type TextContent struct {
	Text string `json:"text"` // 文本内容
}

// FileContent 文件消息内容
type FileContent struct {
	Name     string `json:"name"`     // 文件名
	Type     string `json:"type"`     // 文件类型
	Size     int64  `json:"size"`     // 文件大小
	Content  string `json:"content"`  // 文件内容（Base64）
}

// ToolCallContent 工具调用内容
type ToolCallContent struct {
	ToolName   string                 `json:"tool_name"`   // 工具名称
	Parameters map[string]interface{} `json:"parameters"`  // 工具参数
}

// ToolResultContent 工具结果内容
type ToolResultContent struct {
	ToolName string      `json:"tool_name"` // 工具名称
	Result   interface{} `json:"result"`    // 工具结果
	Error    string      `json:"error"`     // 错误信息
}

// StatusContent 状态消息内容
type StatusContent struct {
	Status  string `json:"status"`  // 状态
	Message string `json:"message"` // 状态描述
}

// HeartbeatContent 心跳消息内容
type HeartbeatContent struct {
	Timestamp int64 `json:"timestamp"` // 时间戳
}

// HistoryContent 历史消息内容
type HistoryContent struct {
	SessionID string                   `json:"session_id"` // 会话ID
	Messages  []map[string]interface{} `json:"messages"`   // 消息列表
	Total     int                      `json:"total"`      // 消息总数
}

// generateMessageID 生成消息ID
func generateMessageID() string {
	return time.Now().Format("20060102150405") + randomString(8)
}

// randomString 生成随机字符串
func randomString(n int) string {
	const letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, n)
	for i := range b {
		b[i] = letters[i%len(letters)]
	}
	return string(b)
}
