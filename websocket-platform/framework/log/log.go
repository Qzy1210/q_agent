package log

import (
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"sync"
)

var (
	loggerInstance *zap.Logger
	loggerOnce     sync.Once
)

// InitLogger 初始化日志
func InitLogger(level, encoding string, outputPaths, errorOutputPaths []string) error {
	var initErr error
	loggerOnce.Do(func() {
		// 解析日志级别
		var zapLevel zapcore.Level
		if err := zapLevel.UnmarshalText([]byte(level)); err != nil {
			initErr = err
			return
		}

		// 创建配置
		cfg := zap.Config{
			Level:            zap.NewAtomicLevelAt(zapLevel),
			Development:      true,
			Encoding:         encoding,
			EncoderConfig:    zap.NewDevelopmentEncoderConfig(),
			OutputPaths:      outputPaths,
			ErrorOutputPaths: errorOutputPaths,
		}

		// 创建 logger
		logger, err := cfg.Build()
		if err != nil {
			initErr = err
			return
		}

		loggerInstance = logger
		// 替换 zap 全局 logger，使 zap.L() 能获取到我们初始化的 logger
		zap.ReplaceGlobals(logger)
	})

	return initErr
}

// Logger 获取日志实例
func Logger() *zap.Logger {
	if loggerInstance == nil {
		panic("logger not initialized")
	}
	return loggerInstance
}

func Info(msg string, fields ...zap.Field) {
	Logger().Info(msg, fields...)
}

func Error(msg string, fields ...zap.Field) {
	Logger().Error(msg, fields...)
}

func Debug(msg string, fields ...zap.Field) {
	Logger().Debug(msg, fields...)
}

// Sync 刷新日志缓冲
func Sync() error {
	if loggerInstance != nil {
		return loggerInstance.Sync()
	}
	return nil
}
