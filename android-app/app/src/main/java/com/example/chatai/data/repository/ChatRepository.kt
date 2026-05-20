package com.example.chatai.data.repository

import android.content.Context
import android.util.Log
import com.example.chatai.data.api.ApiClient
import com.example.chatai.data.api.ApiService
import com.example.chatai.data.api.WebSocketManager
import com.example.chatai.data.model.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * 聊天数据仓库
 * 统一管理WebSocket和API数据
 */
class ChatRepository(
    private val scope: CoroutineScope,
    private val context: Context? = null
) {

    companion object {
        private const val TAG = "ChatRepository"
        private const val PREFS_NAME = "chat_prefs"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_CLIENT_ID = "client_id"
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_SESSION_ID = "session_id"
    }

    private val apiService: ApiService = ApiClient.getApiService()
    private val webSocketManager = WebSocketManager()

    // 当前用户ID - 从持久化存储获取或创建新ID
    private var currentUserId: String = getPersistedUserId()

    // 当前客户端ID - 从持久化存储获取或创建新ID
    private var currentClientId: String = getPersistedClientId()

    // 当前会话ID - 从持久化存储获取
    private var currentSessionId: String? = getPersistedSessionId()

    // 服务器地址
    private var serverUrl: String = getPersistedServerUrl()

    // 消息列表
    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages

    // 会话列表
    private val _sessions = MutableStateFlow<List<Session>>(emptyList())
    val sessions: StateFlow<List<Session>> = _sessions

    // 加载状态
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    // 错误信息
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    init {
        // 初始化WebSocket
        webSocketManager.init(scope, serverUrl)

        // 监听WebSocket消息
        scope.launch {
            webSocketManager.messageFlow.collect { message ->
                message?.let {
                    addMessage(it)
                }
            }
        }
    }

    /**
     * 获取连接状态
     */
    fun getConnectionState(): StateFlow<ConnectionState> {
        return webSocketManager.connectionState
    }

    /**
     * 设置服务器地址
     */
    fun setServerUrl(url: String) {
        this.serverUrl = url
        webSocketManager.setServerUrl(url)
        // 持久化保存
        context?.let {
            val prefs = it.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putString(KEY_SERVER_URL, url).apply()
        }
        Log.d(TAG, "Server URL set to: $url")
    }

    /**
     * 获取当前服务器地址
     */
    fun getServerUrl(): String = serverUrl

    /**
     * 设置用户ID
     */
    fun setUserId(userId: String) {
        this.currentUserId = userId
        // 持久化保存
        context?.let {
            val prefs = it.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putString(KEY_USER_ID, userId).apply()
        }
        Log.d(TAG, "User ID set to: $userId")
    }

    /**
     * 设置客户端ID
     */
    fun setClientId(clientId: String) {
        this.currentClientId = clientId
        // 持久化保存
        context?.let {
            val prefs = it.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putString(KEY_CLIENT_ID, clientId).apply()
        }
        Log.d(TAG, "Client ID set to: $clientId")
    }

    /**
     * 设置会话ID
     */
    fun setSessionId(sessionId: String) {
        this.currentSessionId = sessionId
        // 持久化保存
        context?.let {
            val prefs = it.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().putString(KEY_SESSION_ID, sessionId).apply()
        }
        Log.d(TAG, "Session ID set to: $sessionId")
    }

    /**
     * 获取当前会话ID
     */
    fun getSessionId(): String? = currentSessionId

    /**
     * 连接WebSocket
     */
    fun connect(sessionId: String) {
        Log.d(TAG, "Connecting to session: $sessionId, clientId: $currentClientId, userId: $currentUserId")
        currentSessionId = sessionId
        webSocketManager.connect(currentClientId, currentUserId, sessionId)
    }

    /**
     * 使用当前配置连接WebSocket
     */
    fun connect() {
        currentSessionId?.let { sessionId ->
            connect(sessionId)
        } ?: run {
            Log.e(TAG, "No session ID set, cannot connect")
        }
    }

    /**
     * 断开WebSocket
     */
    fun disconnect() {
        webSocketManager.disconnect()
    }

    /**
     * 发送消息
     */
    fun sendMessage(text: String): Boolean {
        if (text.isBlank()) return false

        val success = webSocketManager.sendMessage(text)
        if (success) {
            // 添加到本地消息列表（乐观更新）
            val message = Message(
                id = "msg_${System.currentTimeMillis()}_${UUID.randomUUID().toString().take(4)}",
                type = MessageType.TEXT,
                from = currentClientId,
                sessionId = currentSessionId ?: "",
                timestamp = System.currentTimeMillis(),
                content = MessageContent(text = text),
                clientType = 1 // 用户发送
            )
            addMessage(message)
        }
        return success
    }

    /**
     * 添加消息到列表
     */
    private fun addMessage(message: Message) {
        val currentList = _messages.value.toMutableList()
        // 检查是否已存在（避免重复）
        if (currentList.none { it.id == message.id }) {
            currentList.add(message)
            _messages.value = currentList
        }
    }

    /**
     * 获取会话列表
     */
    suspend fun loadSessions() {
        _isLoading.value = true
        _error.value = null

        try {
            val response = apiService.getSessions(currentUserId)
            _sessions.value = response.sessions
        } catch (e: Exception) {
            _error.value = "获取会话列表失败: ${e.message}"
        } finally {
            _isLoading.value = false
        }
    }

    /**
     * 创建新会话
     */
    suspend fun createSession(): String? {
        Log.d(TAG, "createSession: calling API with userId=$currentUserId")
        _isLoading.value = true
        _error.value = null

        try {
            val response = apiService.createSession(
                CreateSessionRequest(currentUserId)
            )
            Log.d(TAG, "createSession: API response sessionId=${response.sessionId}")
            // 刷新会话列表
            loadSessions()
            return response.sessionId
        } catch (e: Exception) {
            Log.e(TAG, "createSession error: ${e.message}", e)
            _error.value = "创建会话失败: ${e.message}"
            return null
        } finally {
            _isLoading.value = false
        }
    }

    /**
     * 加载会话消息历史
     * 使用合并策略，不会覆盖已有消息（避免WebSocket历史消息丢失）
     */
    suspend fun loadMessages(sessionId: String, limit: Int = 50, offset: Int = 0) {
        _isLoading.value = true
        _error.value = null

        try {
            val response = apiService.getSessionMessages(sessionId, limit, offset)
            // 转换MessageData为Message
            val newMessages = response.messages.map { data ->
                // 解析 content 字段（JSON 字符串）为 MessageContent
                val content = parseMessageContent(data.content)
                Message(
                    id = data.id,
                    type = data.type,
                    from = data.from,
                    to = data.to,
                    sessionId = data.sessionId,
                    timestamp = data.timestamp,
                    content = content,
                    clientType = data.clientType
                )
            }
            // 合并消息而不是覆盖，去重处理
            mergeMessages(newMessages)
        } catch (e: Exception) {
            _error.value = "获取消息历史失败: ${e.message}"
        } finally {
            _isLoading.value = false
        }
    }

    /**
     * 合并新消息到现有列表（去重处理）
     */
    private fun mergeMessages(newMessages: List<Message>) {
        val currentList = _messages.value.toMutableList()
        for (msg in newMessages) {
            // 检查是否已存在（避免重复）
            if (currentList.none { it.id == msg.id }) {
                currentList.add(msg)
            }
        }
        // 按时间排序
        currentList.sortBy { it.timestamp }
        _messages.value = currentList
    }

    /**
     * 解析消息内容 JSON 字符串
     */
    private fun parseMessageContent(contentJson: String): MessageContent {
        return try {
            // 尝试解析为 MessageContent 对象
            val json = org.json.JSONObject(contentJson)
            MessageContent(
                text = json.optString("text").takeIf { it.isNotEmpty() },
                status = json.optString("status").takeIf { it.isNotEmpty() },
                message = json.optString("message").takeIf { it.isNotEmpty() },
                timestamp = json.optLong("timestamp", 0),
                toolName = json.optString("tool_name").takeIf { it.isNotEmpty() },
                parameters = json.optString("parameters").takeIf { it.isNotEmpty() },
                result = json.optString("result").takeIf { it.isNotEmpty() },
                name = json.optString("name").takeIf { it.isNotEmpty() },
                size = json.optLong("size", 0),
                fileContent = json.optString("content").takeIf { it.isNotEmpty() }
            )
        } catch (e: Exception) {
            // 解析失败，返回原始内容作为文本
            MessageContent(text = contentJson)
        }
    }

    /**
     * 清空消息
     */
    fun clearMessages() {
        _messages.value = emptyList()
    }

    /**
     * 获取当前用户ID
     */
    fun getCurrentUserId(): String = currentUserId

    /**
     * 获取当前客户端ID
     */
    fun getCurrentClientId(): String = currentClientId

    /**
     * 是否已连接
     */
    fun isConnected(): Boolean = webSocketManager.isConnected()

    /**
     * 获取持久化的用户ID
     * 如果不存在则创建新的并保存
     */
    private fun getPersistedUserId(): String {
        context?.let {
            val prefs = it.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            var userId = prefs.getString(KEY_USER_ID, null)
            if (userId == null) {
                userId = "user_${UUID.randomUUID().toString().replace("-", "").take(16)}"
                prefs.edit().putString(KEY_USER_ID, userId).apply()
                Log.d(TAG, "Created new user ID: $userId")
            } else {
                Log.d(TAG, "Loaded persisted user ID: $userId")
            }
            return userId
        } ?: run {
            // 没有context时使用固定ID（仅用于测试）
            return "user_default_${UUID.randomUUID().toString().take(8)}"
        }
    }

    /**
     * 获取持久化的客户端ID
     * 如果不存在则创建新的并保存
     */
    private fun getPersistedClientId(): String {
        context?.let {
            val prefs = it.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            var clientId = prefs.getString(KEY_CLIENT_ID, null)
            if (clientId == null) {
                clientId = "client_${UUID.randomUUID().toString().replace("-", "").take(9)}"
                prefs.edit().putString(KEY_CLIENT_ID, clientId).apply()
                Log.d(TAG, "Created new client ID: $clientId")
            } else {
                Log.d(TAG, "Loaded persisted client ID: $clientId")
            }
            return clientId
        } ?: run {
            return "client_${UUID.randomUUID().toString().take(9)}"
        }
    }

    /**
     * 获取持久化的服务器地址
     */
    private fun getPersistedServerUrl(): String {
        context?.let {
            val prefs = it.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return prefs.getString(KEY_SERVER_URL, WebSocketManager.DEFAULT_URL) ?: WebSocketManager.DEFAULT_URL
        } ?: return WebSocketManager.DEFAULT_URL
    }

    /**
     * 获取持久化的会话ID
     */
    private fun getPersistedSessionId(): String? {
        context?.let {
            val prefs = it.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return prefs.getString(KEY_SESSION_ID, null)
        }
        return null
    }
}
