package main

import (
	"go.uber.org/zap"
	"websocket-platform/framework"
	"websocket-platform/framework/bootstrap"
	"websocket-platform/framework/config"
	"websocket-platform/framework/http"
	"websocket-platform/internal/router"
)

func main() {
	// 创建应用
	app := framework.NewApp()
	
	// 注册 Provider（按顺序）
	// 1. 配置
	app.RegisterProvider(bootstrap.NewConfigProvider("conf/dev.yml"))
	// 2. 日志
	app.RegisterProvider(bootstrap.NewLoggerProvider())
	// 3. 数据库
	app.RegisterProvider(bootstrap.NewMysqlProvider())
	// 4. WebSocket
	app.RegisterProvider(bootstrap.NewWebSocketProvider())
	
	// 初始化 Provider
	if err := app.Init(); err != nil {
		zap.L().Fatal("failed to initialize app", zap.Error(err))
	}
	
	// 初始化 HTTP
	appConfig := config.AppInstance()
	engine := http.InitHTTP(appConfig.Port, appConfig.Mode)
	
	// 注册路由
	router.RegisterRoutes(engine)
	
	// 启动应用
	if err := app.Run(); err != nil {
		zap.L().Fatal("failed to run app", zap.Error(err))
	}
}
