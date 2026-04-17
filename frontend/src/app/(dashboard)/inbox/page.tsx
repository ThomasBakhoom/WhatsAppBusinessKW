"use client";

import { useState, useRef, useEffect } from "react";
import {
  useConversations, useConversation, useSendMessage, useUpdateConversation,
} from "@/hooks/use-conversations";
import type { ConversationItem, MessageItem } from "@/hooks/use-conversations";
import { formatRelativeTime } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { Search, Send, MessageSquare, Check, CheckCheck, Clock, X as XIcon, ChevronDown } from "lucide-react";

export default function InboxPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: convData, isLoading } = useConversations({ status: statusFilter || undefined, limit: 50 });
  const conversations = convData?.data ?? [];

  useEffect(() => {
    if (!selectedId && conversations.length > 0) setSelectedId(conversations[0].id);
  }, [conversations, selectedId]);

  return (
    <div className="flex -m-4 lg:-m-6" style={{ height: "calc(100vh - 4rem)" }}>
      {/* Left: Conversation List */}
      <div className="w-[340px] flex-shrink-0 flex flex-col bg-white" style={{ borderRight: "1px solid #E2E8F0" }}>
        {/* Header */}
        <div className="p-4" style={{ borderBottom: "1px solid #F1F5F9" }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold" style={{ color: "#0F172A" }}>Inbox</h2>
            <span className="text-xs font-medium rounded-full px-2 py-0.5" style={{ background: "#F1F5F9", color: "#64748B" }}>
              {conversations.length}
            </span>
          </div>

          {/* Search */}
          <div className="relative mb-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: "#94A3B8" }} />
            <input type="text" placeholder="Search conversations..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-9 rounded-xl pl-9 pr-3 text-sm" style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", color: "#0F172A" }}
            />
          </div>

          {/* Filter pills */}
          <div className="flex gap-1.5">
            {["", "open", "pending", "closed"].map((s) => (
              <button key={s} onClick={() => setStatusFilter(s)}
                className="rounded-lg px-2.5 py-1 text-xs font-medium transition-all"
                style={{
                  background: statusFilter === s ? "#0F172A" : "#F8FAFC",
                  color: statusFilter === s ? "#ffffff" : "#64748B",
                }}>
                {s || "All"}
              </button>
            ))}
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-5 w-5 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "#10B981", borderTopColor: "transparent" }} />
            </div>
          ) : conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-6">
              <div className="h-12 w-12 rounded-2xl flex items-center justify-center mb-3" style={{ background: "#F1F5F9" }}>
                <MessageSquare className="h-6 w-6" style={{ color: "#94A3B8" }} />
              </div>
              <p className="text-sm font-medium" style={{ color: "#64748B" }}>No conversations</p>
              <p className="text-xs mt-1" style={{ color: "#94A3B8" }}>Messages will appear here</p>
            </div>
          ) : (
            conversations.map((conv) => (
              <ConversationRow key={conv.id} conversation={conv} isSelected={conv.id === selectedId} onClick={() => setSelectedId(conv.id)} />
            ))
          )}
        </div>
      </div>

      {/* Right: Message Thread */}
      <div className="flex-1 flex flex-col" style={{ background: "#F8FAFC" }}>
        {selectedId ? (
          <MessageThread conversationId={selectedId} />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center">
            <div className="h-16 w-16 rounded-2xl flex items-center justify-center mb-4" style={{ background: "#F1F5F9" }}>
              <MessageSquare className="h-8 w-8" style={{ color: "#CBD5E1" }} />
            </div>
            <p className="font-medium" style={{ color: "#64748B" }}>Select a conversation</p>
            <p className="text-sm mt-1" style={{ color: "#94A3B8" }}>Choose from the list to start messaging</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ConversationRow({ conversation, isSelected, onClick }: { conversation: ConversationItem; isSelected: boolean; onClick: () => void }) {
  const contactName = conversation.contact?.full_name ?? "Unknown";
  const initials = contactName.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const statusColors: Record<string, string> = { open: "#10B981", pending: "#F59E0B", snoozed: "#6366F1", closed: "#94A3B8" };

  return (
    <button onClick={onClick} className="w-full text-left px-4 py-3 transition-all"
      style={{
        background: isSelected ? "#F0FDF4" : "transparent",
        borderLeft: isSelected ? "3px solid #10B981" : "3px solid transparent",
        borderBottom: "1px solid #F8FAFC",
      }}
      onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = "#F8FAFC"; }}
      onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="relative flex-shrink-0">
          <div className="h-10 w-10 rounded-full flex items-center justify-center text-xs font-bold text-white"
            style={{ background: "linear-gradient(135deg, #10B981, #059669)" }}>
            {initials}
          </div>
          <div className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white"
            style={{ background: statusColors[conversation.status] || "#94A3B8" }} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold truncate" style={{ color: "#0F172A" }}>{contactName}</span>
            <span className="text-[10px] flex-shrink-0 ml-2" style={{ color: "#94A3B8" }}>
              {conversation.last_message_at ? formatRelativeTime(conversation.last_message_at) : ""}
            </span>
          </div>
          <div className="flex items-center justify-between mt-0.5">
            <p className="text-xs truncate" style={{ color: "#64748B" }}>
              {conversation.last_message_preview || "No messages yet"}
            </p>
            {conversation.unread_count > 0 && (
              <span className="flex-shrink-0 ml-2 h-5 min-w-5 px-1.5 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
                style={{ background: "#10B981" }}>
                {conversation.unread_count}
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

function MessageThread({ conversationId }: { conversationId: string }) {
  const { data: detail, isLoading } = useConversation(conversationId);
  const sendMessage = useSendMessage();
  const updateConv = useUpdateConversation();
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [detail?.messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const text = input;
    setInput("");
    await sendMessage.mutateAsync({ conversation_id: conversationId, content: text });
  };

  if (isLoading || !detail) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="h-6 w-6 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "#10B981", borderTopColor: "transparent" }} />
      </div>
    );
  }

  const contactName = detail.contact?.full_name ?? "Unknown";
  const initials = contactName.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <>
      {/* Chat Header */}
      <div className="flex items-center justify-between px-5 py-3 bg-white" style={{ borderBottom: "1px solid #E2E8F0" }}>
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-full flex items-center justify-center text-xs font-bold text-white"
            style={{ background: "linear-gradient(135deg, #10B981, #059669)" }}>
            {initials}
          </div>
          <div>
            <h3 className="text-sm font-semibold" style={{ color: "#0F172A" }}>{contactName}</h3>
            <p className="text-xs" style={{ color: "#94A3B8" }}>{detail.contact?.phone} &middot; {detail.channel}</p>
          </div>
        </div>
        <select value={detail.status}
          onChange={(e) => updateConv.mutate({ id: conversationId, data: { status: e.target.value } })}
          className="rounded-lg px-3 py-1.5 text-xs font-medium" style={{ background: "#F1F5F9", border: "1px solid #E2E8F0", color: "#334155" }}>
          <option value="open">Open</option>
          <option value="pending">Pending</option>
          <option value="snoozed">Snoozed</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {detail.messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="h-12 w-12 rounded-2xl flex items-center justify-center mb-3" style={{ background: "#F1F5F9" }}>
              <Send className="h-6 w-6" style={{ color: "#CBD5E1" }} />
            </div>
            <p className="text-sm" style={{ color: "#94A3B8" }}>Send the first message</p>
          </div>
        ) : (
          detail.messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-5 py-3 bg-white" style={{ borderTop: "1px solid #E2E8F0" }}>
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="Type a message..." rows={1}
              className="w-full resize-none rounded-xl px-4 py-2.5 text-sm focus:outline-none"
              style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", color: "#0F172A", minHeight: "42px" }}
            />
          </div>
          <button onClick={handleSend} disabled={!input.trim() || sendMessage.isPending}
            className="h-[42px] w-[42px] rounded-xl flex items-center justify-center text-white disabled:opacity-40 transition-all hover:scale-105 active:scale-95"
            style={{ background: "linear-gradient(135deg, #10B981, #059669)", boxShadow: "0 2px 8px rgba(16,185,129,0.3)" }}>
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </>
  );
}

function MessageBubble({ message }: { message: MessageItem }) {
  const isOutbound = message.direction === "outbound";

  return (
    <div className={cn("flex", isOutbound ? "justify-end" : "justify-start")}>
      <div className="max-w-[70%] rounded-2xl px-4 py-2.5"
        style={{
          background: isOutbound ? "linear-gradient(135deg, #10B981, #059669)" : "#ffffff",
          color: isOutbound ? "#ffffff" : "#0F172A",
          borderBottomRightRadius: isOutbound ? "6px" : "16px",
          borderBottomLeftRadius: isOutbound ? "16px" : "6px",
          boxShadow: isOutbound ? "0 2px 8px rgba(16,185,129,0.2)" : "0 1px 3px rgba(0,0,0,0.06)",
          border: isOutbound ? "none" : "1px solid #F1F5F9",
        }}>
        {message.message_type !== "text" && !message.content && (
          <p className="text-xs italic" style={{ opacity: 0.7 }}>[{message.message_type}]</p>
        )}
        {message.content && (
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
        )}
        <div className={cn("flex items-center gap-1.5 mt-1", isOutbound ? "justify-end" : "justify-start")}>
          <span className="text-[10px]" style={{ opacity: 0.6 }}>{formatRelativeTime(message.created_at)}</span>
          {isOutbound && <DeliveryIcon status={message.delivery_status} />}
        </div>
      </div>
    </div>
  );
}

function DeliveryIcon({ status }: { status: string }) {
  const style = { width: 14, height: 14, opacity: status === "read" ? 1 : 0.5 };
  const color = status === "read" ? "#93C5FD" : "currentColor";

  switch (status) {
    case "pending": return <Clock style={style} />;
    case "sent": return <Check style={{ ...style, color }} />;
    case "delivered": return <CheckCheck style={{ ...style, color }} />;
    case "read": return <CheckCheck style={{ ...style, color }} />;
    case "failed": return <XIcon style={{ ...style, color: "#EF4444" }} />;
    default: return null;
  }
}
