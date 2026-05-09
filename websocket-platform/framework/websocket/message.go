package websocket

import (
	"encoding/json"
	"time"
)

// MessageType 消息类型
type MessageType string

const (
	MessageTypeText       MessageType = "text"        // 文本消息
	MessageTypeFile       MessageType = "file"        // 文件消息
	MessageTypeToolCall   MessageType = "tool_call"   // 工具调用
	MessageTypeToolResult MessageType = "tool_result" // 工具结果
	MessageTypeHeartbeat  MessageType = "heartbeat"   // 心跳消息
	MessageTypeStatus     MessageType = "status"      // 状态消息
	MessageTypeError      MessageType = "error"       // 错误消息
)

// Message WebSocket 消息
type Message struct {
	ID        string      `json:"id"`         // 消息唯一标识
	Type      MessageType `json:"type"`       // 消息类型
	From      string      `json:"from"`       // 发送者ID
	To        string      `json:"to"`         // 接收者ID（可选）
	SessionID string      `json:"session_id"` // 会话ID
	Timestamp int64       `json:"timestamp"`  // 时间戳
	Content   interface{} `json:"content"`    // 消息内容
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
	return json.Unmarshal(data, m)
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
