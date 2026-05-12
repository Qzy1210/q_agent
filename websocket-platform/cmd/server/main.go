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
	configProvider := bootstrap.NewConfigProvider("conf/dev.yml")
	// 2. 日志
	loggerProvider := bootstrap.NewLoggerProvider()
	// 3. 数据库
	mysqlProvider := bootstrap.NewMysqlProvider()
	// 4. WebSocket
	wsProvider := bootstrap.NewWebSocketProvider()

	app.RegisterProvider(configProvider)
	app.RegisterProvider(loggerProvider)
	app.RegisterProvider(mysqlProvider)
	app.RegisterProvider(wsProvider)

	// ===== 第一阶段：初始化配置和日志 =====
	// 配置初始化（日志初始化需要读取配置）
	if err := configProvider.Init(); err != nil {
		panic("failed to initialize config: " + err.Error())
	}

	// 日志初始化（其他组件依赖日志）
	if err := loggerProvider.Init(); err != nil {
		panic("failed to initialize logger: " + err.Error())
	}

	zap.L().Info("config and logger initialized")

	// ===== 第二阶段：启动数据库（WebSocket Init 需要数据库连接） =====
	if err := mysqlProvider.Boot(); err != nil {
		zap.L().Fatal("failed to boot mysql", zap.Error(err))
	}
	zap.L().Info("mysql provider booted")

	// ===== 第三阶段：初始化剩余 Provider =====
	if err := wsProvider.Init(); err != nil {
		zap.L().Fatal("failed to initialize websocket", zap.Error(err))
	}

	// 启动剩余 Provider
	if err := wsProvider.Boot(); err != nil {
		zap.L().Fatal("failed to boot websocket", zap.Error(err))
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
