package com.example.chatai.data.api

import com.example.chatai.data.model.*
import com.google.gson.Gson
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import okhttp3.*
import java.util.UUID
import java.util.concurrent.TimeUnit

/**
 * WebSocket管理器
 * 负责WebSocket连接、消息收发、心跳保活、自动重连
 */
class WebSocketManager {

    private val gson = Gson()
    private var webSocket: WebSocket? = null
    private var okHttpClient: OkHttpClient? = null
    private var heartbeatJob: Job? = null
    private var reconnectJob: Job? = null
    private var scope: CoroutineScope? = null

    // 连接参数
    private var clientId: String = ""
    private var userId: String = ""
    private var sessionId: String = ""
    private var serverUrl: String = DEFAULT_URL

    // 重连配置
    private var reconnectAttempts = 0
    private val maxReconnectAttempts = 5
    private val reconnectDelay = 3000L // 3秒

    // 状态流
    private val _connectionState = MutableStateFlow<ConnectionState>(
        ConnectionState.disconnected()
    )
    val connectionState: StateFlow<ConnectionState> = _connectionState

    // 消息流
    private val _messageFlow = MutableStateFlow<Message?>(null)
    val messageFlow: StateFlow<Message?> = _messageFlow

    companion object {
        // Android模拟器访问本机地址
        const val DEFAULT_URL = "ws://10.0.2.2:8080"
    }

    /**
     * 初始化WebSocket
     */
    fun init(scope: CoroutineScope, serverUrl: String = DEFAULT_URL) {
        this.scope = scope
        this.serverUrl = serverUrl
        this.okHttpClient = OkHttpClient.Builder()
            .pingInterval(30, TimeUnit.SECONDS)
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .writeTimeout(10, TimeUnit.SECONDS)
            .build()
    }

    /**
     * 连接WebSocket
     */
    fun connect(clientId: String, userId: String, sessionId: String) {
        this.clientId = clientId
        this.userId = userId
        this.sessionId = sessionId

        if (okHttpClient == null) {
            scope?.let { init(it) }
        }

        _connectionState.value = ConnectionState.connecting()

        val url = buildUrl()
        val request = Request.Builder()
            .url(url)
            .build()

        webSocket = okHttpClient?.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                _connectionState.value = ConnectionState.connected()
                reconnectAttempts = 0
                startHeartbeat()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val message = gson.fromJson(text, Message::class.java)
                    handleMessage(message)
                } catch (e: Exception) {
                    // 解析失败，忽略
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                _connectionState.value = ConnectionState.disconnected(reason)
                stopHeartbeat()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                _connectionState.value = ConnectionState.disconnected(reason)
                stopHeartbeat()
                attemptReconnect()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                _connectionState.value = ConnectionState.error(t)
                stopHeartbeat()
                attemptReconnect()
            }
        })
    }

    /**
     * 构建WebSocket URL
     */
    private fun buildUrl(): String {
        return "$serverUrl/ws/app?client_id=$clientId&user_id=$userId&session_id=$sessionId"
    }

    /**
     * 处理接收到的消息
     */
    private fun handleMessage(message: Message) {
        when (message.type) {
            MessageType.STATUS -> {
                // 状态消息，已由连接状态处理
            }
            MessageType.HEARTBEAT -> {
                // 心跳响应，忽略
            }
            else -> {
                // 其他消息，通知UI
                _messageFlow.value = message
            }
        }
    }

    /**
     * 发送消息
     */
    fun sendMessage(text: String): Boolean {
        if (!_connectionState.value.isConnected()) {
            return false
        }

        val message = Message(
            id = generateMessageId(),
            type = MessageType.TEXT,
            from = clientId,
            sessionId = sessionId,
            timestamp = System.currentTimeMillis(),
            content = MessageContent(text = text)
        )

        return sendMessage(message)
    }

    /**
     * 发送消息对象
     */
    fun sendMessage(message: Message): Boolean {
        if (!_connectionState.value.isConnected()) {
            return false
        }

        try {
            val json = gson.toJson(message)
            webSocket?.send(json)
            return true
        } catch (e: Exception) {
            return false
        }
    }

    /**
     * 发送心跳
     */
    private fun sendHeartbeat() {
        if (!_connectionState.value.isConnected()) {
            return
        }

        val message = Message(
            id = generateMessageId(),
            type = MessageType.HEARTBEAT,
            from = clientId,
            sessionId = sessionId,
            timestamp = System.currentTimeMillis(),
            content = MessageContent(timestamp = System.currentTimeMillis())
        )

        try {
            val json = gson.toJson(message)
            webSocket?.send(json)
        } catch (e: Exception) {
            // 忽略心跳发送失败
        }
    }

    /**
     * 启动心跳
     */
    private fun startHeartbeat() {
        stopHeartbeat()
        heartbeatJob = scope?.launch {
            while (isActive) {
                delay(30000) // 30秒
                sendHeartbeat()
            }
        }
    }

    /**
     * 停止心跳
     */
    private fun stopHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = null
    }

    /**
     * 尝试重连
     */
    private fun attemptReconnect() {
        if (reconnectAttempts >= maxReconnectAttempts) {
            return
        }

        reconnectAttempts++
        _connectionState.value = ConnectionState.reconnecting()

        reconnectJob?.cancel()
        reconnectJob = scope?.launch {
            delay(reconnectDelay)
            connect(clientId, userId, sessionId)
        }
    }

    /**
     * 断开连接
     */
    fun disconnect() {
        stopHeartbeat()
        reconnectJob?.cancel()
        webSocket?.close(1000, "User disconnect")
        webSocket = null
        _connectionState.value = ConnectionState.disconnected("User disconnect")
    }

    /**
     * 生成消息ID
     */
    private fun generateMessageId(): String {
        return UUID.randomUUID().toString()
    }

    /**
     * 是否已连接
     */
    fun isConnected(): Boolean {
        return _connectionState.value.isConnected()
    }

    /**
     * 获取当前客户端ID
     */
    fun getClientId(): String = clientId
}
