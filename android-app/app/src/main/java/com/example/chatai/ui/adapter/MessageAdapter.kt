package com.example.chatai.ui.adapter

import android.graphics.drawable.GradientDrawable
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import androidx.cardview.widget.CardView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.chatai.R
import com.example.chatai.data.model.Message
import com.example.chatai.data.model.MessageType
import java.text.SimpleDateFormat
import java.util.Locale

/**
 * 消息列表适配器
 * 参考 web 效果，根据消息类型和方向展示不同样式
 */
class MessageAdapter(
    private val currentClientId: String
) : ListAdapter<Message, MessageAdapter.ViewHolder>(DiffCallback()) {

    private val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_message, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val message = getItem(position)
        holder.bind(message)
    }

    inner class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        // 发送的消息（右侧）
        private val layoutSent: LinearLayout = itemView.findViewById(R.id.layoutSent)
        private val tvTypeSent: TextView = itemView.findViewById(R.id.tvTypeSent)
        private val tvMessageSent: TextView = itemView.findViewById(R.id.tvMessageSent)
        private val tvTimeSent: TextView = itemView.findViewById(R.id.tvTimeSent)

        // 接收的消息（左侧）
        private val layoutReceived: LinearLayout = itemView.findViewById(R.id.layoutReceived)
        private val tvTypeReceived: TextView = itemView.findViewById(R.id.tvTypeReceived)
        private val tvMessageReceived: TextView = itemView.findViewById(R.id.tvMessageReceived)
        private val tvTimeReceived: TextView = itemView.findViewById(R.id.tvTimeReceived)

        // 系统消息（居中）
        private val layoutSystem: LinearLayout = itemView.findViewById(R.id.layoutSystem)
        private val tvMessageSystem: TextView = itemView.findViewById(R.id.tvMessageSystem)

        fun bind(message: Message) {
            val isSentByMe = message.isSentByMe(currentClientId)
            val time = timeFormat.format(message.timestamp)
            val displayContent = message.getDisplayContent()

            // 根据消息类型判断是否为系统消息
            val isSystemMessage = message.type == MessageType.STATUS || message.type == MessageType.HEARTBEAT

            when {
                isSystemMessage -> {
                    // 系统消息（居中）
                    layoutSent.visibility = View.GONE
                    layoutReceived.visibility = View.GONE
                    layoutSystem.visibility = View.VISIBLE
                    tvMessageSystem.text = displayContent
                }
                isSentByMe -> {
                    // 发送的消息（右侧）
                    layoutSent.visibility = View.VISIBLE
                    layoutReceived.visibility = View.GONE
                    layoutSystem.visibility = View.GONE
                    tvMessageSent.text = displayContent
                    tvTimeSent.text = time
                    setupTypeBadge(tvTypeSent, message.type)
                }
                else -> {
                    // 接收的消息（左侧）
                    layoutSent.visibility = View.GONE
                    layoutReceived.visibility = View.VISIBLE
                    layoutSystem.visibility = View.GONE
                    tvMessageReceived.text = displayContent
                    tvTimeReceived.text = time
                    setupTypeBadge(tvTypeReceived, message.type)
                }
            }
        }

        /**
         * 设置消息类型标签样式
         */
        private fun setupTypeBadge(textView: TextView, type: String) {
            // 普通文本消息不显示类型标签
            if (type == MessageType.TEXT) {
                textView.visibility = View.GONE
                return
            }

            textView.visibility = View.VISIBLE
            textView.text = type

            // 根据类型设置颜色
            val (bgColor, textColor) = when (type) {
                MessageType.FILE -> Pair(R.color.type_file_bg, R.color.type_file_text)
                MessageType.TOOL_CALL -> Pair(R.color.type_tool_call_bg, R.color.type_tool_call_text)
                MessageType.TOOL_RESULT -> Pair(R.color.type_tool_result_bg, R.color.type_tool_result_text)
                MessageType.STATUS -> Pair(R.color.type_status_bg, R.color.type_status_text)
                MessageType.ERROR -> Pair(R.color.type_error_bg, R.color.type_error_text)
                MessageType.HEARTBEAT -> Pair(R.color.type_heartbeat_bg, R.color.type_heartbeat_text)
                else -> Pair(R.color.type_text_bg, R.color.type_text_text)
            }

            // 设置背景
            val context = textView.context
            val drawable = GradientDrawable().apply {
                cornerRadius = 4f
                setColor(ContextCompat.getColor(context, bgColor))
            }
            textView.background = drawable
            textView.setTextColor(ContextCompat.getColor(context, textColor))
        }
    }

    class DiffCallback : DiffUtil.ItemCallback<Message>() {
        override fun areItemsTheSame(oldItem: Message, newItem: Message): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: Message, newItem: Message): Boolean {
            return oldItem == newItem
        }
    }
}
