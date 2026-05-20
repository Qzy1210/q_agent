package model

import (
	"time"
)

// Session 会话模型
type Session struct {
	ID        string    `gorm:"primaryKey;type:varchar(64);comment:会话ID" json:"id"`
	UserID    string    `gorm:"type:varchar(64);not null;index;comment:用户ID" json:"user_id"`
	Status    string    `gorm:"type:varchar(20);default:'active';comment:会话状态" json:"status"`
	CreatedAt time.Time `gorm:"autoCreateTime;comment:创建时间" json:"created_at"`
	UpdatedAt time.Time `gorm:"autoUpdateTime;comment:更新时间" json:"updated_at"`
}

// TableName 指定表名
func (Session) TableName() string {
	return "sessions"
}

// SessionClient 会话客户端关联模型
type SessionClient struct {
	ID         string    `gorm:"primaryKey;type:varchar(64);comment:记录ID" json:"id"`
	SessionID  string    `gorm:"type:varchar(64);not null;index;comment:会话ID" json:"session_id"`
	ClientID   string    `gorm:"type:varchar(64);not null;index;comment:客户端ID" json:"client_id"`
	ClientType string    `gorm:"type:varchar(20);not null;comment:客户端类型(app/agent)" json:"client_type"`
	UserID     string    `gorm:"type:varchar(64);not null;index;comment:用户ID" json:"user_id"`
	Status     string    `gorm:"type:varchar(20);default:'online';comment:连接状态" json:"status"`
	ConnectedAt time.Time `gorm:"autoCreateTime;comment:连接时间" json:"connected_at"`
	DisconnectedAt *time.Time `gorm:"comment:断开时间" json:"disconnected_at"`
}

// TableName 指定表名
func (SessionClient) TableName() string {
	return "session_clients"
}

// Message 消息记录模型
type Message struct {
	ID         string    `gorm:"primaryKey;type:varchar(64);comment:消息ID" json:"id"`
	SessionID  string    `gorm:"type:varchar(64);not null;index;comment:会话ID" json:"session_id"`
	Type       string    `gorm:"type:varchar(20);not null;comment:消息类型" json:"type"`
	From       string    `gorm:"type:varchar(64);not null;index;comment:发送者ID" json:"from"`
	To         string    `gorm:"type:varchar(64);comment:接收者ID" json:"to"`
	Content    string    `gorm:"type:text;comment:消息内容(JSON)" json:"content"`
	Timestamp  int64     `gorm:"not null;index;comment:时间戳(毫秒)" json:"timestamp"`
	ClientType int       `gorm:"type:tinyint;default:0;comment:客户端类型(1:App,2:Agent)" json:"client_type"`
	CreatedAt  time.Time `gorm:"autoCreateTime;comment:创建时间" json:"created_at"`
}

// TableName 指定表名
func (Message) TableName() string {
	return "messages"
}

// SessionStatus 会话状态常量
const (
	SessionStatusActive    = "active"    // 活跃
	SessionStatusInactive  = "inactive"  // 不活跃
	SessionStatusClosed    = "closed"    // 已关闭
)

// ClientStatus 客户端状态常量
const (
	ClientStatusOnline  = "online"  // 在线
	ClientStatusOffline = "offline" // 离线
)

// MessageClientType 消息客户端类型常量
const (
	MessageClientTypeApp   = 1 // App 发送的消息
	MessageClientTypeAgent = 2 // Agent 回复的消息
)

// MessageType 消息类型常量
const (
	MessageTypeText       = "text"
	MessageTypeFile       = "file"
	MessageTypeToolCall   = "tool_call"
	MessageTypeToolResult = "tool_result"
	MessageTypeHeartbeat  = "heartbeat"
	MessageTypeStatus     = "status"
	MessageTypeError      = "error"
)
