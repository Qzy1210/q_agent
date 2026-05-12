package bootstrap

import (
	"websocket-platform/framework/config"
	"websocket-platform/framework/provider"
	"websocket-platform/framework/websocket"
	"websocket-platform/internal/logic"

	"go.uber.org/zap"
)

// 全局 WebSocket Provider 实例
var globalWebSocketProvider *WebSocketProvider

// WebSocketProvider WebSocket服务提供者
type WebSocketProvider struct {
	server          *websocket.Server
	sessionManager  *logic.SessionManager
}

// NewWebSocketProvider 创建WebSocket提供者
func NewWebSocketProvider() provider.Provider {
	return &WebSocketProvider{}
}

// Name 返回提供者名称
func (p *WebSocketProvider) Name() string {
	return "websocket"
}

// Init 初始化WebSocket（轻量级操作：创建实例）
func (p *WebSocketProvider) Init() error {
	// 创建会话管理器
	p.sessionManager = logic.NewSessionManager()

	// 初始化数据库表
	if err := p.sessionManager.InitTables(); err != nil {
		return err
	}

	// 创建WebSocket服务器
	wsConfig := config.WebSocketInstance()
	p.server = websocket.NewServer(&websocket.WebSocketConfig{
		ReadBufferSize:    wsConfig.ReadBufferSize,
		WriteBufferSize:   wsConfig.WriteBufferSize,
		PingPeriod:        wsConfig.PingPeriod,
		PongWait:          wsConfig.PongWait,
		MaxMessageSize:    wsConfig.MaxMessageSize,
		MaxConnections:    wsConfig.MaxConnections,
		ConnectionTimeout: wsConfig.ConnectionTimeout,
		MessageQueueSize:  wsConfig.MessageQueueSize,
		HeartbeatInterval: wsConfig.HeartbeatInterval,
	}, p.sessionManager)

	// 保存全局实例
	globalWebSocketProvider = p

	zap.L().Info("websocket provider initialized")
	return nil
}

// Boot 启动WebSocket服务（WebSocket不需要单独启动，由HTTP服务器管理）
func (p *WebSocketProvider) Boot() error {
	zap.L().Info("websocket provider booted")
	return nil
}

// Close 关闭WebSocket服务
func (p *WebSocketProvider) Close() error {
	if p.server != nil {
		return p.server.Close()
	}
	return nil
}

// GetServer 获取WebSocket服务器
func (p *WebSocketProvider) GetServer() *websocket.Server {
	return p.server
}

// GetSessionManager 获取会话管理器
func (p *WebSocketProvider) GetSessionManager() *logic.SessionManager {
	return p.sessionManager
}

// GetWebSocketProvider 获取全局 WebSocket Provider 实例
func GetWebSocketProvider() *WebSocketProvider {
	return globalWebSocketProvider
}

// GetWebSocketServer 获取全局 WebSocket Server 实例
func GetWebSocketServer() *websocket.Server {
	if globalWebSocketProvider == nil {
		return nil
	}
	return globalWebSocketProvider.server
}
