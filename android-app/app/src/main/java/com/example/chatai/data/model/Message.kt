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
    val content: MessageContent
) {
    /**
     * 判断是否是自己发送的消息
     */
    fun isSentByMe(currentClientId: String): Boolean {
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
    val timestamp: Long? = null
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
