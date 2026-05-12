package router

import (
	"github.com/gin-gonic/gin"
	"websocket-platform/framework/bootstrap"
	"websocket-platform/internal/controller"
)

// RegisterRoutes 注册路由
func RegisterRoutes(engine *gin.Engine) {
	// 创建控制器
	sessionController := controller.NewSessionController()

	// API 路由组
	api := engine.Group("/api")
	{
		// 健康检查
		api.GET("/health", controller.HealthCheck)

		// 会话管理 API
		sessions := api.Group("/sessions")
		{
			// 获取用户会话列表
			// GET /api/sessions?user_id=xxx
			sessions.GET("", sessionController.GetUserSessions)

			// 创建新会话
			// POST /api/sessions
			sessions.POST("", sessionController.CreateSession)

			// 获取会话详情
			// GET /api/sessions/:id
			sessions.GET("/:id", sessionController.GetSession)

			// 获取会话消息历史
			// GET /api/sessions/:id/messages?limit=50&offset=0
			sessions.GET("/:id/messages", sessionController.GetSessionMessages)

			// 获取会话客户端列表
			// GET /api/sessions/:id/clients
			sessions.GET("/:id/clients", sessionController.GetSessionClients)

			// 关闭会话
			// POST /api/sessions/:id/close
			sessions.POST("/:id/close", sessionController.CloseSession)
		}
	}

	// WebSocket 路由
	ws := engine.Group("/ws")
	{
		// WebSocket 连接端点
		// /ws/:client_type?client_id=xxx&user_id=xxx&session_id=xxx
		ws.GET("/:client_type", func(c *gin.Context) {
			// 获取已初始化的全局 WebSocket Server
			wsServer := bootstrap.GetWebSocketServer()
			if wsServer == nil {
				c.JSON(500, gin.H{"error": "websocket server not initialized"})
				return
			}

			// 处理 WebSocket 连接
			wsServer.HandleWebSocket(c)
		})
	}
}
