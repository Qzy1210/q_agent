package framework

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
	"websocket-platform/framework/bootstrap"
	"websocket-platform/framework/config"
	frameworkHTTP "websocket-platform/framework/http"
	"websocket-platform/framework/provider"
)

// App 应用容器
type App struct {
	providers []provider.Provider
	engine    *gin.Engine
}

// NewApp 创建应用容器
func NewApp() *App {
	return &App{
		providers: make([]provider.Provider, 0),
	}
}

// RegisterProvider 注册服务提供者
func (a *App) RegisterProvider(p provider.Provider) {
	a.providers = append(a.providers, p)
}

// Init 初始化所有 Provider
func (a *App) Init() error {
	for _, p := range a.providers {
		// 使用 fmt.Printf 而非 zap.L()，因为日志可能尚未初始化
		if err := p.Init(); err != nil {
			return err
		}
	}
	return nil
}

// Boot 启动所有 Provider
func (a *App) Boot() error {
	for _, p := range a.providers {
		// 使用 fmt.Printf 而非 zap.L()，因为日志可能尚未初始化
		if err := p.Boot(); err != nil {
			return err
		}
	}
	return nil
}

// Close 关闭所有 Provider（反向顺序）
func (a *App) Close() error {
	zap.L().Info("closing providers...")

	// 反向顺序关闭
	for i := len(a.providers) - 1; i >= 0; i-- {
		p := a.providers[i]
		zap.L().Info("closing provider", zap.String("name", p.Name()))
		if err := p.Close(); err != nil {
			return err
		}
	}

	return nil
}

// Run 运行应用
func (a *App) Run() error {
	// 启动所有 Provider（Init 已在外部完成）
	if err := a.Boot(); err != nil {
		return err
	}

	// 启动 HTTP 服务器（非阻塞）
	go func() {
		if err := frameworkHTTP.Start(); err != nil && err != http.ErrServerClosed {
			zap.L().Fatal("failed to start http server", zap.Error(err))
		}
	}()

	zap.L().Info("application started")

	// 等待中断信号
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	zap.L().Info("shutting down application...")

	// 优雅关闭
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := frameworkHTTP.Shutdown(ctx); err != nil {
		zap.L().Error("failed to shutdown http server", zap.Error(err))
	}

	// 关闭所有 Provider
	if err := a.Close(); err != nil {
		return err
	}

	zap.L().Info("application stopped")
	return nil
}

// SetupApp 设置应用（快速启动）
func SetupApp(configPath string) *App {
	app := NewApp()

	// 注册 Provider（按顺序）
	app.RegisterProvider(bootstrap.NewConfigProvider(configPath))
	app.RegisterProvider(bootstrap.NewLoggerProvider())
	app.RegisterProvider(bootstrap.NewMysqlProvider())
	app.RegisterProvider(bootstrap.NewWebSocketProvider())

	// 初始化 HTTP
	appConfig := config.AppInstance()
	app.engine = frameworkHTTP.InitHTTP(appConfig.Port, appConfig.Mode)

	return app
}