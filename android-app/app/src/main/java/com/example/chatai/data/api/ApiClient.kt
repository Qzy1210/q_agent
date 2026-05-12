package com.example.chatai.data.api

import com.example.chatai.data.model.SessionListResponse
import com.example.chatai.data.model.CreateSessionRequest
import com.example.chatai.data.model.CreateSessionResponse
import com.example.chatai.data.model.MessageListResponse
import com.example.chatai.data.model.Session
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * Retrofit API客户端
 */
object ApiClient {

    // 默认服务器地址（可根据实际情况修改）
    private const val BASE_URL = "http://10.0.2.2:8080/"  // Android模拟器访问本机

    private var retrofit: Retrofit? = null
    private var apiService: ApiService? = null

    /**
     * 获取Retrofit实例
     */
    private fun getRetrofit(): Retrofit {
        return retrofit ?: synchronized(this) {
            retrofit ?: Retrofit.Builder()
                .baseUrl(BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .also { retrofit = it }
        }
    }

    /**
     * 获取API服务实例
     */
    fun getApiService(): ApiService {
        return apiService ?: synchronized(this) {
            apiService ?: getRetrofit().create(ApiService::class.java).also { apiService = it }
        }
    }

    /**
     * 更新服务器地址
     */
    fun updateBaseUrl(url: String) {
        retrofit = Retrofit.Builder()
            .baseUrl(url)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        apiService = retrofit!!.create(ApiService::class.java)
    }
}
