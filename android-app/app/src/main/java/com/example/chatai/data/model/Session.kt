package com.example.chatai.data.model

import com.google.gson.annotations.SerializedName
import java.util.Date

/**
 * 会话模型
 */
data class Session(
    @SerializedName("id")
    val id: String,

    @SerializedName("user_id")
    val userId: String,

    @SerializedName("status")
    val status: String,

    @SerializedName("created_at")
    val createdAt: Date? = null,

    @SerializedName("updated_at")
    val updatedAt: Date? = null
) {
    companion object {
        const val STATUS_ACTIVE = "active"
        const val STATUS_INACTIVE = "inactive"
        const val STATUS_CLOSED = "closed"
    }

    fun isActive(): Boolean = status == STATUS_ACTIVE
}

/**
 * 会话列表响应
 */
data class SessionListResponse(
    @SerializedName("user_id")
    val userId: String,

    @SerializedName("sessions")
    val sessions: List<Session>,

    @SerializedName("count")
    val count: Int
)

/**
 * 创建会话请求
 */
data class CreateSessionRequest(
    @SerializedName("user_id")
    val userId: String
)

/**
 * 创建会话响应
 */
data class CreateSessionResponse(
    @SerializedName("session_id")
    val sessionId: String,

    @SerializedName("user_id")
    val userId: String,

    @SerializedName("status")
    val status: String
)

/**
 * 消息列表响应
 */
data class MessageListResponse(
    @SerializedName("session_id")
    val sessionId: String,

    @SerializedName("messages")
    val messages: List<MessageData>,

    @SerializedName("count")
    val count: Int,

    @SerializedName("limit")
    val limit: Int,

    @SerializedName("offset")
    val offset: Int
)

/**
 * 数据库存储的消息模型
 */
data class MessageData(
    @SerializedName("id")
    val id: String,

    @SerializedName("session_id")
    val sessionId: String,

    @SerializedName("type")
    val type: String,

    @SerializedName("from")
    val from: String,

    @SerializedName("to")
    val to: String? = null,

    @SerializedName("content")
    val content: String,

    @SerializedName("timestamp")
    val timestamp: Long,

    @SerializedName("created_at")
    val createdAt: Date? = null
)
