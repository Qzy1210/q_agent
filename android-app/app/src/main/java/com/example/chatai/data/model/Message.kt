package com.example.chatai.data.model

import com.google.gson.annotations.SerializedName

/**
 * WebSocket消息模型
 */
data class Message(
    @SerializedName("id")
    val id: String,

    @SerializedName("type")
    val type: String,

    @SerializedName("from")
    val from: String,

    @SerializedName("to")
    val to: String? = null,

    @SerializedName("session_id")
    val sessionId: String,

    @SerializedName("timestamp")
    val timestamp: Long,

    @SerializedName("content")
    val content: MessageContent,

    /**
     * 客户端类型：1=用户发送的消息（右侧），2=Agent回复（左侧）
     * 用于判断消息展示方向
     */
    @SerializedName("client_type")
    val clientType: Int? = null
) {
    /**
     * 判断是否是自己发送的消息
     * 优先使用 client_type 判断：1=用户发送，2=Agent回复
     * 兜底使用 from 字段判断
     */
    fun isSentByMe(currentClientId: String): Boolean {
        // 优先根据 client_type 判断方向
        clientType?.let { return it == 1 }
        // 兜底：根据 from 判断
        return from == currentClientId
    }

    /**
     * 获取消息文本内容
     */
    fun getTextContent(): String? {
        return content.text
    }

    /**
     * 获取状态内容
     */
    fun getStatusContent(): String? {
        return content.message ?: content.status
    }

    /**
     * 获取显示内容 - 根据消息类型返回可读文本
     */
    fun getDisplayContent(): String {
        return when (type) {
            MessageType.TEXT -> content.text ?: ""
            MessageType.STATUS -> {
                val status = content.status ?: ""
                val msg = content.message ?: ""
                if (msg.isNotEmpty()) "$status: $msg" else status
            }
            MessageType.TOOL_CALL -> {
                val toolName = content.toolName ?: ""
                val params = content.parameters ?: ""
                "🔧 $toolName\n$params"
            }
            MessageType.TOOL_RESULT -> {
                val toolName = content.toolName ?: ""
                val result = content.result ?: ""
                "📋 $toolName\n$result"
            }
            MessageType.ERROR -> "❌ ${content.message ?: content.text ?: "未知错误"}"
            MessageType.HEARTBEAT -> "💓 心跳"
            MessageType.FILE -> "📁 ${content.name ?: "文件"}"
            else -> content.text ?: ""
        }
    }
}

/**
 * 消息内容模型
 */
data class MessageContent(
    @SerializedName("text")
    val text: String? = null,

    @SerializedName("status")
    val status: String? = null,

    @SerializedName("message")
    val message: String? = null,

    @SerializedName("timestamp")
    val timestamp: Long? = null,

    // 工具调用字段
    @SerializedName("tool_name")
    val toolName: String? = null,

    @SerializedName("parameters")
    val parameters: String? = null,

    // 工具结果字段
    @SerializedName("result")
    val result: String? = null,

    // 文件字段
    @SerializedName("name")
    val name: String? = null,

    @SerializedName("size")
    val size: Long? = null,

    @SerializedName("content")
    val fileContent: String? = null
)

/**
 * 消息类型常量
 */
object MessageType {
    const val TEXT = "text"
    const val FILE = "file"
    const val TOOL_CALL = "tool_call"
    const val TOOL_RESULT = "tool_result"
    const val HEARTBEAT = "heartbeat"
    const val STATUS = "status"
    const val ERROR = "error"
}
