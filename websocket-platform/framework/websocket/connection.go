package websocket

import (
	"context"
	"sync"
	"time"
	
	"github.com/gorilla/websocket"
	"go.uber.org/zap"
	"websocket-platform/internal/logic"
)

// ClientType 客户端类型
type ClientType string

const (
	ClientTypeApp   ClientType = "app"   // App 客户端
	ClientTypeAgent ClientType = "agent" // Agent 客户端
)

// Client WebSocket 客户端连接
type Client struct {
	ID           string            // 客户端唯一标识
	Type         ClientType        // 客户端类型
	UserID       string            // 用户ID
	SessionID    string            // 会话ID
	Conn         *websocket.Conn   // WebSocket 连接
	SendChan     chan []byte       // 发送消息通道
	LastActivity time.Time         // 最后活动时间
	mu           sync.RWMutex      // 读写锁
	ctx          context.Context   // 上下文
	cancel       context.CancelFunc // 取消函数
	closed       bool              // 是否已关闭（防止重复关闭）
	closeMu      sync.Mutex        // 关闭锁（确保关闭操作原子性）
}

// NewClient 创建新的 WebSocket 客户端
func NewClient(id string, clientType ClientType, userID, sessionID string, conn *websocket.Conn) *Client {
	ctx, cancel := context.WithCancel(context.Background())
	return &Client{
		ID:           id,
		Type:         clientType,
		UserID:       userID,
		SessionID:    sessionID,
		Conn:         conn,
		SendChan:     make(chan []byte, 100),
		LastActivity: time.Now(),
		ctx:          ctx,
		cancel:       cancel,
		closed:       false,
	}
}

// WriteMessage 发送消息
func (c *Client) WriteMessage(message []byte) error {
	select {
	case c.SendChan <- message:
		return nil
	default:
		return ErrSendChannelFull
	}
}

// Close 关闭客户端连接
// 使用 closeMu 确保只关闭一次，防止 panic: close of closed channel
func (c *Client) Close() {
	c.closeMu.Lock()
	defer c.closeMu.Unlock()

	// 检查是否已关闭
	if c.closed {
		return
	}
	c.closed = true

	// 取消上下文
	c.cancel()

	// 关闭发送通道
	close(c.SendChan)

	// 关闭 WebSocket 连接
	c.Conn.Close()
}

// IsClosed 检查客户端是否已关闭
func (c *Client) IsClosed() bool {
	select {
	case <-c.ctx.Done():
		return true
	default:
		return false
	}
}

// UpdateActivity 更新活动时间
func (c *Client) UpdateActivity() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.LastActivity = time.Now()
}

// ConnectionManager 连接管理器
type ConnectionManager struct {
	clients        map[string]*Client // 客户端连接映射
	userMap        map[string][]string // 用户ID -> 客户端ID列表
	sessionMap     map[string][]string // 会话ID -> 客户端ID列表
	mu             sync.RWMutex       // 读写锁
	maxConns       int                // 最大连接数
	sessionManager *logic.SessionManager // 会话管理器
}

// NewConnectionManager 创建连接管理器
func NewConnectionManager(maxConns int, sessionManager *logic.SessionManager) *ConnectionManager {
	return &ConnectionManager{
		clients:        make(map[string]*Client),
		userMap:        make(map[string][]string),
		sessionMap:     make(map[string][]string),
		maxConns:       maxConns,
		sessionManager: sessionManager,
	}
}

// Register 注册客户端连接
func (cm *ConnectionManager) Register(client *Client) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	// 检查连接数限制
	if len(cm.clients) >= cm.maxConns {
		zap.L().Warn("⚠️ 连接数已达上限",
			zap.Int("max_connections", cm.maxConns),
			zap.Int("current_connections", len(cm.clients)),
		)
		return ErrMaxConnectionsReached
	}

	// 注册客户端
	cm.clients[client.ID] = client

	// 更新用户映射
	cm.userMap[client.UserID] = append(cm.userMap[client.UserID], client.ID)

	// 更新会话映射
	cm.sessionMap[client.SessionID] = append(cm.sessionMap[client.SessionID], client.ID)

	// 持久化到数据库
	if cm.sessionManager != nil {
		if err := cm.sessionManager.RegisterClient(
			client.SessionID,
			client.ID,
			string(client.Type),
			client.UserID,
		); err != nil {
			zap.L().Error("客户端注册持久化失败",
				zap.Error(err),
				zap.String("client_id", client.ID),
			)
		}
	}

	zap.L().Info("✓ 客户端注册成功",
		zap.String("client_id", client.ID),
		zap.String("client_type", string(client.Type)),
		zap.String("user_id", client.UserID),
		zap.String("session_id", client.SessionID),
		zap.Int("total_connections", len(cm.clients)),
	)

	return nil
}

// Unregister 注销客户端连接
func (cm *ConnectionManager) Unregister(clientID string) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	client, exists := cm.clients[clientID]
	if !exists {
		return
	}

	// 从客户端映射中删除
	delete(cm.clients, clientID)

	// 从用户映射中删除
	if clientIDs, ok := cm.userMap[client.UserID]; ok {
		cm.userMap[client.UserID] = removeFromSlice(clientIDs, clientID)
		if len(cm.userMap[client.UserID]) == 0 {
			delete(cm.userMap, client.UserID)
		}
	}

	// 从会话映射中删除
	if clientIDs, ok := cm.sessionMap[client.SessionID]; ok {
		cm.sessionMap[client.SessionID] = removeFromSlice(clientIDs, clientID)
		if len(cm.sessionMap[client.SessionID]) == 0 {
			delete(cm.sessionMap, client.SessionID)
		}
	}

	// 持久化到数据库
	if cm.sessionManager != nil {
		if err := cm.sessionManager.UnregisterClient(clientID); err != nil {
			zap.L().Error("客户端注销持久化失败",
				zap.Error(err),
				zap.String("client_id", clientID),
			)
		}
	}

	zap.L().Info("✓ 客户端注销成功",
		zap.String("client_id", client.ID),
		zap.String("client_type", string(client.Type)),
		zap.String("user_id", client.UserID),
		zap.String("session_id", client.SessionID),
		zap.Int("remaining_connections", len(cm.clients)),
	)
}

// Get 获取客户端
func (cm *ConnectionManager) Get(clientID string) (*Client, bool) {
	cm.mu.RLock()
	defer cm.mu.RUnlock()
	
	client, exists := cm.clients[clientID]
	return client, exists
}

// GetByUserID 根据用户ID获取客户端列表
func (cm *ConnectionManager) GetByUserID(userID string) []*Client {
	cm.mu.RLock()
	defer cm.mu.RUnlock()
	
	clientIDs, exists := cm.userMap[userID]
	if !exists {
		return nil
	}
	
	clients := make([]*Client, 0, len(clientIDs))
	for _, id := range clientIDs {
		if client, ok := cm.clients[id]; ok {
			clients = append(clients, client)
		}
	}
	
	return clients
}

// GetBySessionID 根据会话ID获取客户端列表
func (cm *ConnectionManager) GetBySessionID(sessionID string) []*Client {
	cm.mu.RLock()
	defer cm.mu.RUnlock()
	
	clientIDs, exists := cm.sessionMap[sessionID]
	if !exists {
		return nil
	}
	
	clients := make([]*Client, 0, len(clientIDs))
	for _, id := range clientIDs {
		if client, ok := cm.clients[id]; ok {
			clients = append(clients, client)
		}
	}
	
	return clients
}

// Count 获取当前连接数
func (cm *ConnectionManager) Count() int {
	cm.mu.RLock()
	defer cm.mu.RUnlock()
	return len(cm.clients)
}

// removeFromSlice 从切片中移除元素
func removeFromSlice(slice []string, element string) []string {
	for i, v := range slice {
		if v == element {
			return append(slice[:i], slice[i+1:]...)
		}
	}
	return slice
}
