package com.example.chatai.data.api

import com.example.chatai.data.model.*
import retrofit2.http.*

/**
 * REST API服务接口
 */
interface ApiService {

    /**
     * 获取用户会话列表
     * GET /api/sessions?user_id=xxx
     */
    @GET("api/sessions")
    suspend fun getSessions(
        @Query("user_id") userId: String
    ): SessionListResponse

    /**
     * 创建新会话
     * POST /api/sessions
     */
    @POST("api/sessions")
    suspend fun createSession(
        @Body request: CreateSessionRequest
    ): CreateSessionResponse

    /**
     * 获取会话详情
     * GET /api/sessions/:id
     */
    @GET("api/sessions/{id}")
    suspend fun getSession(
        @Path("id") sessionId: String
    ): Session

    /**
     * 获取会话消息历史
     * GET /api/sessions/:id/messages?limit=50&offset=0
     */
    @GET("api/sessions/{id}/messages")
    suspend fun getSessionMessages(
        @Path("id") sessionId: String,
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0
    ): MessageListResponse

    /**
     * 获取会话客户端列表
     * GET /api/sessions/:id/clients
     */
    @GET("api/sessions/{id}/clients")
    suspend fun getSessionClients(
        @Path("id") sessionId: String
    ): Map<String, Any>

    /**
     * 关闭会话
     * POST /api/sessions/:id/close
     */
    @POST("api/sessions/{id}/close")
    suspend fun closeSession(
        @Path("id") sessionId: String
    ): Map<String, Any>
}
