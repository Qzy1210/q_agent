package router

import (
	"github.com/gin-gonic/gin"
	"websocket-platform/framework/bootstrap"
	"websocket-platform/internal/controller"
)

// RegisterRoutes 注册路由
func RegisterRoutes(engine *gin.Engine) {
	// API 路由组
	api := engine.Group("/api")
	{
		// 健康检查
		api.GET("/health", controller.HealthCheck)
	}
	
	// WebSocket 路由
	ws := engine.Group("/ws")
	{
		// WebSocket 连接端点
		// /ws/:client_type?client_id=xxx&user_id=xxx&session_id=xxx
		ws.GET("/:client_type", func(c *gin.Context) {
			// 获取 WebSocket Provider
			wsProvider := bootstrap.NewWebSocketProvider()
			wsServer := wsProvider.(*bootstrap.WebSocketProvider).GetServer()
			
			// 处理 WebSocket 连接
			wsServer.HandleWebSocket(c)
		})
	}
}
