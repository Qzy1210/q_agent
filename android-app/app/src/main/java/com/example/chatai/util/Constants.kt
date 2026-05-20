package com.example.chatai.util

/**
 * 常量定义
 */
object Constants {

    // WebSocket服务器地址 (远端服务器)
//    const val WS_BASE_URL = "ws://49.233.105.26:8088"
//    const val HTTP_BASE_URL = "http://49.233.105.26:8088/"

    // 如果使用模拟器访问本机
    // const val WS_BASE_URL = "ws://10.0.2.2:8080"
    // const val HTTP_BASE_URL = "http://10.0.2.2:8080/"

    // 如果使用真机，请使用电脑的局域网IP
     const val WS_BASE_URL = "ws://192.168.1.6:8088"
     const val HTTP_BASE_URL = "http://192.168.1.6:8088/"

    // WebSocket配置
    const val HEARTBEAT_INTERVAL = 30000L  // 心跳间隔（毫秒）
    const val RECONNECT_DELAY = 3000L      // 重连延迟（毫秒）
    const val MAX_RECONNECT_ATTEMPTS = 5   // 最大重连次数

    // API配置
    const val DEFAULT_PAGE_SIZE = 50       // 默认分页大小

    // Intent Extra Keys
    const val EXTRA_SESSION_ID = "session_id"
    const val EXTRA_USER_ID = "user_id"
    const val EXTRA_CLIENT_ID = "client_id"

    // SharedPreferences Keys
    const val PREF_USER_ID = "pref_user_id"
    const val PREF_CLIENT_ID = "pref_client_id"
    const val PREF_LAST_SESSION = "pref_last_session"
}
