package config

import (
	"fmt"
	"github.com/spf13/viper"
	"sync"
)

var (
	configInstance *Config
	configOnce     sync.Once
)

// Config 配置管理器
type Config struct {
	viper *viper.Viper
}

// AppConfig 应用配置
type AppConfig struct {
	Name string `mapstructure:"name"`
	Env  string `mapstructure:"env"`
	Port int    `mapstructure:"port"`
	Mode string `mapstructure:"mode"`
}

// MysqlConfig MySQL配置
type MysqlConfig struct {
	Host            string `mapstructure:"host"`
	Port            int    `mapstructure:"port"`
	Database        string `mapstructure:"database"`
	Username        string `mapstructure:"username"`
	Password        string `mapstructure:"password"`
	Charset         string `mapstructure:"charset"`
	MaxOpenConns    int    `mapstructure:"max_open_conns"`
	MaxIdleConns    int    `mapstructure:"max_idle_conns"`
	ConnMaxLifetime int    `mapstructure:"conn_max_lifetime"`
}

// LoggerConfig 日志配置
type LoggerConfig struct {
	Level           string   `mapstructure:"level"`
	Encoding        string   `mapstructure:"encoding"`
	OutputPaths     []string `mapstructure:"output_paths"`
	ErrorOutputPaths []string `mapstructure:"error_output_paths"`
}

// WebSocketConfig WebSocket配置
type WebSocketConfig struct {
	ReadBufferSize    int    `mapstructure:"read_buffer_size"`
	WriteBufferSize   int    `mapstructure:"write_buffer_size"`
	PingPeriod        string `mapstructure:"ping_period"`
	PongWait          string `mapstructure:"pong_wait"`
	MaxMessageSize    int    `mapstructure:"max_message_size"`
	MaxConnections    int    `mapstructure:"max_connections"`
	ConnectionTimeout string `mapstructure:"connection_timeout"`
	MessageQueueSize  int    `mapstructure:"message_queue_size"`
	HeartbeatInterval string `mapstructure:"heartbeat_interval"`
}

// InitConfig 初始化配置
func InitConfig(configPath string) error {
	var initErr error
	configOnce.Do(func() {
		v := viper.New()
		v.SetConfigFile(configPath)
		v.SetConfigType("yaml")
		
		// 读取配置文件
		if err := v.ReadInConfig(); err != nil {
			initErr = fmt.Errorf("failed to read config file: %w", err)
			return
		}
		
		// 加载 includes
		var includes []string
		if err := v.UnmarshalKey("includes", &includes); err == nil {
			for _, include := range includes {
				v.SetConfigFile(include)
				if err := v.MergeInConfig(); err != nil {
					initErr = fmt.Errorf("failed to merge config %s: %w", include, err)
					return
				}
			}
		}
		
		configInstance = &Config{viper: v}
	})
	
	return initErr
}

// Instance 获取配置实例
func Instance() *Config {
	if configInstance == nil {
		panic("config not initialized")
	}
	return configInstance
}

// AppInstance 获取应用配置
func AppInstance() *AppConfig {
	var app AppConfig
	if err := Instance().viper.UnmarshalKey("app", &app); err != nil {
		panic(fmt.Errorf("failed to unmarshal app config: %w", err))
	}
	return &app
}

// MysqlInstance 获取MySQL配置
func MysqlInstance() *MysqlConfig {
	var mysql MysqlConfig
	if err := Instance().viper.UnmarshalKey("mysql", &mysql); err != nil {
		panic(fmt.Errorf("failed to unmarshal mysql config: %w", err))
	}
	return &mysql
}

// LoggerInstance 获取日志配置
func LoggerInstance() *LoggerConfig {
	var logger LoggerConfig
	if err := Instance().viper.UnmarshalKey("logger", &logger); err != nil {
		panic(fmt.Errorf("failed to unmarshal logger config: %w", err))
	}
	return &logger
}

// WebSocketInstance 获取WebSocket配置
func WebSocketInstance() *WebSocketConfig {
	var ws WebSocketConfig
	if err := Instance().viper.UnmarshalKey("websocket", &ws); err != nil {
		panic(fmt.Errorf("failed to unmarshal websocket config: %w", err))
	}
	return &ws
}

// Get 获取配置值
func (c *Config) Get(key string) interface{} {
	return c.viper.Get(key)
}

// GetString 获取字符串配置
func (c *Config) GetString(key string) string {
	return c.viper.GetString(key)
}

// GetInt 获取整数配置
func (c *Config) GetInt(key string) int {
	return c.viper.GetInt(key)
}
