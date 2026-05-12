package com.example.chatai.ui.adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
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
        private val layoutSent: LinearLayout = itemView.findViewById(R.id.layoutSent)
        private val layoutReceived: LinearLayout = itemView.findViewById(R.id.layoutReceived)
        private val tvMessageSent: TextView = itemView.findViewById(R.id.tvMessageSent)
        private val tvMessageReceived: TextView = itemView.findViewById(R.id.tvMessageReceived)
        private val tvTimeSent: TextView = itemView.findViewById(R.id.tvTimeSent)
        private val tvTimeReceived: TextView = itemView.findViewById(R.id.tvTimeReceived)

        fun bind(message: Message) {
            val isSentByMe = message.isSentByMe(currentClientId)
            val time = timeFormat.format(message.timestamp)

            if (isSentByMe) {
                // 发送的消息（右侧）
                layoutSent.visibility = View.VISIBLE
                layoutReceived.visibility = View.GONE
                tvMessageSent.text = message.getTextContent() ?: ""
                tvTimeSent.text = time
            } else {
                // 接收的消息（左侧）
                layoutSent.visibility = View.GONE
                layoutReceived.visibility = View.VISIBLE
                tvMessageReceived.text = message.getTextContent() ?: ""
                tvTimeReceived.text = time
            }
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
