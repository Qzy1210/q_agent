package http

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

var (
	serverInstance *http.Server
	engineInstance *gin.Engine
)

// InitHTTP 初始化 HTTP 服务器
func InitHTTP(port int, mode string) *gin.Engine {
	// 设置运行模式
	gin.SetMode(mode)

	// 创建 Gin 引擎
	engineInstance = gin.New()

	// 添加中间件
	engineInstance.Use(gin.Recovery())
	engineInstance.Use(LoggerMiddleware())

	// 创建 HTTP 服务器
	serverInstance = &http.Server{
		Addr:         fmt.Sprintf("0.0.0.0:%d", port),
		Handler:      engineInstance,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	return engineInstance
}

// Engine 获取 Gin 引擎
func Engine() *gin.Engine {
	if engineInstance == nil {
		panic("http engine not initialized")
	}
	return engineInstance
}

// Start 启动 HTTP 服务器
func Start() error {
	if serverInstance == nil {
		return fmt.Errorf("http server not initialized")
	}

	zap.L().Info("starting http server", zap.String("addr", serverInstance.Addr))
	return serverInstance.ListenAndServe()
}

// Shutdown 优雅关闭 HTTP 服务器
func Shutdown(ctx context.Context) error {
	if serverInstance != nil {
		return serverInstance.Shutdown(ctx)
	}
	return nil
}

// LoggerMiddleware 日志中间件
func LoggerMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		c.Next()

		latency := time.Since(start)
		status := c.Writer.Status()
		method := c.Request.Method

		zap.L().Info("http request",
			zap.String("method", method),
			zap.String("path", path),
			zap.String("query", query),
			zap.Int("status", status),
			zap.Duration("latency", latency),
		)
	}
}
