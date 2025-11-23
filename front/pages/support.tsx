// pages/support.tsx
import { NextPage } from "next";
import { useEffect, useState } from "react";
import api from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import {
  SupportChat,
  SupportChatShort,
  SupportMessage,
  UserRole,
} from "../lib/types";

const FAQ_ITEMS = [
  {
    q: "Как считается самый выгодный маршрут?",
    a: "Мы учитываем общую стоимость всех сегментов маршрута, включая перелёты и наземный транспорт.",
  },
  {
    q: "Можно ли добавить несколько пассажиров?",
    a: "Да, при бронировании вы можете указать несколько пассажиров и их данные.",
  },
  {
    q: "Что делать, если на нужную дату нет рейсов?",
    a: "Попробуйте сдвинуть дату отправления или выбрать соседний город отправления/прибытия.",
  },
];

const SupportPage: NextPage = () => {
  const { user } = useAuth();
  const [myChat, setMyChat] = useState<SupportChat | null>(null);
  const [adminChats, setAdminChats] = useState<SupportChatShort[]>([]);
  const [selectedAdminChat, setSelectedAdminChat] = useState<SupportChat | null>(
    null
  );
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  const isAdmin = user?.role === UserRole.ADMIN;

  // загрузка чата пользователя
  useEffect(() => {
    if (!user || isAdmin) return;
    api
      .get<SupportChat>("/support/chats/me")
      .then((res) => setMyChat(res.data))
      .catch(() => {});
  }, [user, isAdmin]);

  // загрузка списка чатов для админа
  useEffect(() => {
    if (!user || !isAdmin) return;
    api
      .get<SupportChatShort[]>("/support/chats")
      .then((res) => setAdminChats(res.data))
      .catch(() => {});
  }, [user, isAdmin]);

  const loadAdminChat = async (chatId: number) => {
    const res = await api.get<SupportChat>(`/support/chats/${chatId}`);
    setSelectedAdminChat(res.data);
  };

  const currentChat: SupportChat | null = isAdmin ? selectedAdminChat : myChat;

  const handleSend = async () => {
    if (!message.trim() || !currentChat) return;
    setSending(true);
    try {
      const url = isAdmin
        ? `/support/chats/${currentChat.id}/messages`
        : `/support/chats/me/messages`;

      const res = await api.post<SupportMessage>(url, { content: message });
      const newMsg = res.data;

      if (isAdmin) {
        setSelectedAdminChat((prev) =>
          prev
            ? { ...prev, messages: [...prev.messages, newMsg] }
            : prev
        );
      } else {
        setMyChat((prev) =>
          prev
            ? { ...prev, messages: [...prev.messages, newMsg] }
            : prev
        );
      }
      setMessage("");
    } finally {
      setSending(false);
    }
  };

  const handleFaqClick = (text: string) => {
    setMessage((prev) => (prev ? prev + " " + text : text));
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 pt-10 pb-20">
      <div className="bg-white rounded-[32px] shadow-[0_20px_60px_rgba(15,23,42,0.12)] px-4 sm:px-8 py-6 sm:py-8 flex flex-col md:flex-row gap-6">
        {/* Левая часть: либо список чатов админа, либо FAQ */}
        <div className="w-full md:w-1/3 border-r border-gray-100 pr-0 md:pr-4">
          <h1 className="text-lg sm:text-xl font-semibold text-[#243850] mb-4">
            Поддержка
          </h1>

          {isAdmin ? (
            <div className="space-y-2 max-h-[480px] overflow-y-auto">
              {adminChats.map((c) => (
                <button
                  key={c.id}
                  onClick={() => loadAdminChat(c.id)}
                  className={`w-full text-left px-3 py-2 rounded-xl border text-sm mb-1 ${
                    selectedAdminChat?.id === c.id
                      ? "bg-[#243850] text-white border-[#243850]"
                      : "border-gray-200 hover:bg-gray-50"
                  }`}
                >
                  <div className="font-medium">{c.user_full_name}</div>
                  {c.last_message && (
                    <div className="text-xs opacity-80 truncate">
                      {c.last_message}
                    </div>
                  )}
                </button>
              ))}
              {adminChats.length === 0 && (
                <p className="text-sm text-gray-500">
                  Пока нет обращений в поддержку.
                </p>
              )}
            </div>
          ) : (
            <div>
              <p className="text-sm text-gray-500 mb-3">
                Частые вопросы — нажмите, чтобы подставить вопрос в чат:
              </p>
              <div className="space-y-2">
                {FAQ_ITEMS.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleFaqClick(item.q)}
                    className="w-full text-left px-3 py-2 rounded-xl border border-gray-200 hover:bg-gray-50 text-sm"
                  >
                    <div className="font-medium text-[#243850]">
                      {item.q}
                    </div>
                    <div className="text-xs text-gray-500">{item.a}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Правая часть: чат */}
        <div className="w-full md:w-2/3 flex flex-col">
          <div className="flex-1 rounded-2xl border border-gray-100 bg-gray-50 p-3 sm:p-4 mb-3 overflow-y-auto max-h-[420px]">
            {!currentChat ? (
              <p className="text-sm text-gray-500">
                {isAdmin
                  ? "Выберите чат пользователя слева, чтобы посмотреть диалог."
                  : "Напишите нам, если возникли вопросы по маршрутам или бронированию."}
              </p>
            ) : currentChat.messages.length === 0 ? (
              <p className="text-sm text-gray-500">
                Начните диалог — первое сообщение увидит администратор.
              </p>
            ) : (
              <div className="space-y-2">
                {currentChat.messages.map((msg) => {
                  const isMine = msg.sender_id === user?.id;
                  return (
                    <div
                      key={msg.id}
                      className={`flex ${
                        isMine ? "justify-end" : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${
                          isMine
                            ? "bg-[#243850] text-white"
                            : "bg-white text-[#243850] border border-gray-200"
                        }`}
                      >
                        <p>{msg.content}</p>
                        <p className="text-[10px] opacity-70 mt-1">
                          {new Date(msg.created_at).toLocaleString("ru-RU")}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ваш вопрос..."
              className="flex-1 px-3 py-2 rounded-full border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#243850]"
            />
            <button
              onClick={handleSend}
              disabled={!currentChat || sending || !message.trim()}
              className="px-4 py-2 rounded-full bg-[#243850] text-white text-sm disabled:opacity-60 disabled:cursor-not-allowed"
            >
              Отправить
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SupportPage;
