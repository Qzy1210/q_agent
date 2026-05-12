package com.example.chatai.data.model

/**
 * WebSocket连接状态
 */
enum class WebSocketState {
    CONNECTING,     // 连接中
    CONNECTED,      // 已连接
    DISCONNECTED,   // 已断开
    ERROR,          // 连接错误
    RECONNECTING    // 重连中
}

/**
 * 连接状态信息
 */
data class ConnectionState(
    val state: WebSocketState,
    val message: String = "",
    val error: Throwable? = null
) {
    companion object {
        fun connecting(): ConnectionState = ConnectionState(
            state = WebSocketState.CONNECTING,
            message = "连接中..."
        )

        fun connected(): ConnectionState = ConnectionState(
            state = WebSocketState.CONNECTED,
            message = "已连接"
        )

        fun disconnected(reason: String = ""): ConnectionState = ConnectionState(
            state = WebSocketState.DISCONNECTED,
            message = reason.ifEmpty { "已断开" }
        )

        fun error(error: Throwable): ConnectionState = ConnectionState(
            state = WebSocketState.ERROR,
            message = error.message ?: "连接错误",
            error = error
        )

        fun reconnecting(): ConnectionState = ConnectionState(
            state = WebSocketState.RECONNECTING,
            message = "重连中..."
        )
    }

    fun isConnected(): Boolean = state == WebSocketState.CONNECTED
    fun isConnecting(): Boolean = state == WebSocketState.CONNECTING || state == WebSocketState.RECONNECTING
}
