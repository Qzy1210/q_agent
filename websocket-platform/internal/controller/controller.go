package controller

import (
	"net/http"
	
	"github.com/gin-gonic/gin"
)

// HealthCheck 健康检查
func HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "ok",
		"message": "WebSocket Platform is running",
	})
}
