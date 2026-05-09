package websocket

import (
	"context"
	"fmt"
	"net/http"
	"sync"
	"time"
	
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"go.uber.org/zap"
	"websocket-platform/internal/logic"
)

// WebSocketConfig WebSocket配置
type WebSocketConfig struct {
	ReadBufferSize    int
	WriteBufferSize   int
	PingPeriod        string
	PongWait          string
	MaxMessageSize    int
	MaxConnections    int
	ConnectionTimeout string
	MessageQueueSize  int
	HeartbeatInterval string
}

// Server WebSocket服务器
type Server struct {
	config          *WebSocketConfig
	upgrader        websocket.Upgrader
	connManager     *ConnectionManager
	router          *MessageRouter
	sessionManager  *logic.SessionManager
	mu              sync.RWMutex
	ctx             context.Context
	cancel          context.CancelFunc
}

// NewServer 创建 WebSocket 服务器
func NewServer(config *WebSocketConfig, sessionManager *logic.SessionManager) *Server {
	ctx, cancel := context.WithCancel(context.Background())
	
	// 先创建连接管理器，传入会话管理器
	connManager := NewConnectionManager(config.MaxConnections, sessionManager)
	
	// 创建消息路由器，传入连接管理器和会话管理器
	router := NewMessageRouter(connManager, sessionManager)
	
	return &Server{
		config:         config,
		sessionManager: sessionManager,
		upgrader: websocket.Upgrader{
			ReadBufferSize:  config.ReadBufferSize,
			WriteBufferSize: config.WriteBufferSize,
			CheckOrigin: func(r *http.Request) bool {
				return true // 允许所有来源
			},
		},
		connManager: connManager,
		router:      router,
		ctx:         ctx,
		cancel:      cancel,
	}
}

// HandleWebSocket 处理 WebSocket 连接
func (s *Server) HandleWebSocket(c *gin.Context) {
	// 解析参数
	clientType := c.Param("client_type")
	clientID := c.Query("client_id")
	userID := c.Query("user_id")
	sessionID := c.Query("session_id")
	
	// 验证参数
	if clientID == "" || userID == "" || sessionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing required parameters"})
		return
	}
	
	// 验证客户端类型
	var ct ClientType
	switch clientType {
	case "app":
		ct = ClientTypeApp
	case "agent":
		ct = ClientTypeAgent
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid client type"})
		return
	}
	
	// 升级为 WebSocket 连接
	conn, err := s.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		zap.L().Error("failed to upgrade connection", zap.Error(err))
		return
	}
	
	// 创建客户端
	client := NewClient(clientID, ct, userID, sessionID, conn)
	
	// 注册客户端
	if err := s.connManager.Register(client); err != nil {
		zap.L().Error("failed to register client", zap.Error(err))
		client.Close()
		return
	}
	
	// 启动读写协程
	go s.readPump(client)
	go s.writePump(client)
	
	// 发送欢迎消息
	welcomeMsg := NewMessage(MessageTypeStatus, "system", sessionID, &StatusContent{
		Status:  "connected",
		Message: fmt.Sprintf("Welcome! Client ID: %s", clientID),
	})
	if data, err := welcomeMsg.ToJSON(); err == nil {
		client.WriteMessage(data)
	}
}

// readPump 读取客户端消息
func (s *Server) readPump(client *Client) {
	defer func() {
		s.connManager.Unregister(client.ID)
		client.Close()
	}()
	
	// 设置读取限制
	client.Conn.SetReadLimit(int64(s.config.MaxMessageSize))
	
	// 设置读取超时
	pongWait, _ := time.ParseDuration(s.config.PongWait)
	client.Conn.SetReadDeadline(time.Now().Add(pongWait))
	
	// 设置 Pong 处理器
	client.Conn.SetPongHandler(func(string) error {
		client.Conn.SetReadDeadline(time.Now().Add(pongWait))
		client.UpdateActivity()
		return nil
	})
	
	for {
		_, message, err := client.Conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				zap.L().Error("unexpected close error", zap.Error(err))
			}
			break
		}
		
		// 更新活动时间
		client.UpdateActivity()
		
		// 处理消息
		s.handleMessage(client, message)
	}
}

// writePump 向客户端发送消息
func (s *Server) writePump(client *Client) {
	ticker := time.NewTicker(54 * time.Second)
	defer func() {
		ticker.Stop()
		client.Close()
	}()
	
	for {
		select {
		case <-s.ctx.Done():
			return
		case <-client.ctx.Done():
			return
		case message, ok := <-client.SendChan:
			if !ok {
				// 通道已关闭
				client.Conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}
			
			// 发送消息
			client.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := client.Conn.WriteMessage(websocket.TextMessage, message); err != nil {
				zap.L().Error("failed to write message", zap.Error(err))
				return
			}
			
		case <-ticker.C:
			// 发送心跳
			client.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := client.Conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// handleMessage 处理接收到的消息
func (s *Server) handleMessage(client *Client, data []byte) {
	// 解析消息
	var msg Message
	if err := msg.FromJSON(data); err != nil {
		zap.L().Error("failed to parse message", zap.Error(err))
		return
	}
	
	// 设置消息来源
	msg.From = client.ID
	msg.SessionID = client.SessionID
	
	// 记录日志
	zap.L().Info("message received",
		zap.String("message_id", msg.ID),
		zap.String("type", string(msg.Type)),
		zap.String("from", msg.From),
		zap.String("session_id", msg.SessionID),
	)
	
	// 路由消息
	s.router.Route(client, &msg)
}

// Close 关闭服务器
func (s *Server) Close() error {
	s.cancel()
	return nil
}

// GetConnectionManager 获取连接管理器
func (s *Server) GetConnectionManager() *ConnectionManager {
	return s.connManager
}

// GetMessageRouter 获取消息路由器
func (s *Server) GetMessageRouter() *MessageRouter {
	return s.router
}

// GetSessionManager 获取会话管理器
func (s *Server) GetSessionManager() *logic.SessionManager {
	return s.sessionManager
}
