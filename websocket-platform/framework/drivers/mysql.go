package drivers

import (
	"fmt"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"sync"
	"time"
)

var (
	dbInstance *gorm.DB
	dbOnce     sync.Once
)

// InitMySQL 初始化MySQL连接
func InitMySQL(host string, port int, database, username, password, charset string,
	maxOpenConns, maxIdleConns, connMaxLifetime int) error {
	var initErr error
	dbOnce.Do(func() {
		dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=%s&parseTime=True&loc=Local",
			username, password, host, port, database, charset)

		db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
		if err != nil {
			initErr = fmt.Errorf("failed to connect database: %w", err)
			return
		}

		sqlDB, err := db.DB()
		if err != nil {
			initErr = fmt.Errorf("failed to get sql.DB: %w", err)
			return
		}

		// 设置连接池参数
		sqlDB.SetMaxOpenConns(maxOpenConns)
		sqlDB.SetMaxIdleConns(maxIdleConns)
		sqlDB.SetConnMaxLifetime(time.Duration(connMaxLifetime) * time.Second)

		dbInstance = db
	})

	return initErr
}

// DB 获取数据库实例
func DB() *gorm.DB {
	if dbInstance == nil {
		panic("database not initialized")
	}
	return dbInstance
}

// Close 关闭数据库连接
func Close() error {
	if dbInstance != nil {
		sqlDB, err := dbInstance.DB()
		if err != nil {
			return err
		}
		return sqlDB.Close()
	}
	return nil
}
