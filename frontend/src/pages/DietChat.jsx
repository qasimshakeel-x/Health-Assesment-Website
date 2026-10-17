import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { sendChatMessage } from '../services/api';
import EmojiText from '../components/EmojiText';
import { FaPaperPlane, FaTriangleExclamation, FaCircleInfo, FaArrowsRotate, FaClipboardList, FaCalendarDays, FaMagnifyingGlass, FaDumbbell, FaChartColumn, FaScaleBalanced, FaDroplet, FaDrumstickBite, FaBowlFood } from 'react-icons/fa6';

// Har chat-open pe naya session id — storage session-based rehti hai, purane messages display nahi hote.
const newSessionId = () =>
  typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

function MessageBubble({ message, isUser, bubbleRef }) {
  // Simple markdown-like bold
  const renderContent = (text) => {
    return text.split('\n').map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g);
      return (
        <p key={i} className={i > 0 ? 'mt-1' : ''}>
          {parts.map((part, j) =>
            part.startsWith('**') && part.endsWith('**') ? (
              <strong key={j} className="text-white">
                <EmojiText text={part.slice(2, -2)} />
              </strong>
            ) : (
              <EmojiText key={j} text={part} />
            )
          )}
        </p>
      );
    });
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        ref={bubbleRef}
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-primary-500/20 border border-primary-500/30 text-white'
            : 'glass-light text-gray-200'
        }`}
      >
        <div className="text-sm leading-relaxed">{renderContent(message)}</div>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="glass-light rounded-2xl px-4 py-3">
        <div className="flex gap-1.5">
          <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}

export default function DietChat() {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [riskContext, setRiskContext] = useState(null);
  const [sessionId, setSessionId] = useState(() => newSessionId());
  const messagesContainerRef = useRef(null);
  const lastAssistantRef = useRef(null);

  // Reply end mein add hoti hai, lekin user ke liye uske start se parhna aasan ho:
  // isliye naye assistant reply ke bubble ko container ke top par le kar aate hain.
  useEffect(() => {
    const container = messagesContainerRef.current;
    const lastMsg = messages[messages.length - 1];
    if (!container || !lastMsg || lastMsg.role !== 'assistant') return;
    const bubble = lastAssistantRef.current;
    if (!bubble) return;
    const delta = bubble.getBoundingClientRect().top - container.getBoundingClientRect().top;
    container.scrollTo({ top: container.scrollTop + delta, behavior: 'smooth' });
  }, [messages]);

  const startNewChat = () => {
    setMessages([]);
    setInput('');
    setRiskContext(null);
    setSessionId(newSessionId());
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);
    try {
      const res = await sendChatMessage(user.id, userMsg, sessionId);
      if (res.data.session_id) setSessionId(res.data.session_id);
      setMessages((prev) => [...prev, { role: 'assistant', content: res.data.response }]);
      if (res.data.risk_context) setRiskContext(res.data.risk_context);
    } catch (err) {
        const msg = err.response?.data?.detail || err.message || 'Unknown error';
        let helpText = '';
        if (err.response?.status === 404) {
          helpText = ' Please complete a health assessment first to use the Diet Advisor.';
        }
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: `Sorry, I encountered an error: ${msg}.${helpText}` },
        ]);
    } finally {
      setLoading(false);
    }
  };

  const quickQuestions = [
    { icon: FaClipboardList, label: 'Show my risk profile' },
    { icon: FaCalendarDays, label: 'Generate my diet plan' },
    { icon: FaMagnifyingGlass, label: 'Calories in chicken breast' },
    { icon: FaDumbbell, label: 'Exercise for chest' },
    { icon: FaChartColumn, label: 'Calculate my macros' },
    { icon: FaScaleBalanced, label: 'Compare chicken vs rice' },
    { icon: FaDroplet, label: 'How much water should I drink' },
    { icon: FaDrumstickBite, label: 'High protein foods' },
  ];

  // Page exactly 100vh: main ka py-6 (3rem) minus karke, taake chat page viewport
  // mein fit ho aur sirf andar ka messages area scroll kare (poora page na scroll ho).
  return (
    <div className="pt-20 pb-4 px-4 max-w-3xl mx-auto flex flex-col h-[calc(100vh-3rem)]">
      <div className="animate-slide-up flex-1 flex flex-col min-h-0">
        {messages.length > 0 && (
          <div className="flex justify-end mb-3">
            <button
              type="button"
              onClick={startNewChat}
              aria-label="Start a new chat session"
              className="glass-light px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-surface-100 transition-all flex items-center gap-1.5 shrink-0"
            >
              <FaArrowsRotate size={13} /> New Chat
            </button>
          </div>
        )}

        {/* Risk Context Badge */}
        {riskContext && (
          <div className="glass-light p-3 flex items-center gap-3 mb-4">
            <FaTriangleExclamation className="text-yellow-400 shrink-0" size={16} />
            <span className="text-xs text-gray-300">{riskContext}</span>
          </div>
        )}

        {/* Chat Messages */}
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto mb-4 space-y-1 min-h-0" role="log" aria-live="polite" aria-label="Chat messages">
          {messages.length === 0 && (
            <div className="text-center py-8">
              <div className="w-16 h-16 rounded-2xl bg-primary-500/10 flex items-center justify-center mx-auto mb-4">
                <span className="text-primary-300"><FaBowlFood size={30} aria-hidden="true" /></span>
              </div>
              <h3 className="text-white font-semibold mb-2">Your AI Diet Advisor</h3>
              <p className="text-sm text-gray-400 mb-6 max-w-sm mx-auto">
                I can help you with meal plans, real nutrition data, exercises, calorie calculations, and more!
              </p>
              <div className="flex flex-wrap justify-center gap-2 max-w-md mx-auto">
                {quickQuestions.map(({ icon: Icon, label }) => (
                  <button
                    key={label}
                    onClick={() => { setInput(label); }}
                    className="glass-light px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-surface-100 transition-all inline-flex items-center gap-1.5"
                  >
                    <Icon className="shrink-0" size={13} aria-hidden="true" />
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              message={msg.content}
              isUser={msg.role === 'user'}
              bubbleRef={msg.role === 'assistant' && i === messages.length - 1 ? lastAssistantRef : null}
            />
          ))}
          {loading && <TypingIndicator />}
        </div>

        {/* Disclaimer */}
        <div className="glass-light p-3 flex items-start gap-2 mb-3">
          <FaCircleInfo className="text-gray-500 shrink-0 mt-0.5" size={14} />
          <p className="text-xs text-gray-500">
            AI-generated dietary guidance, not medical advice. Always consult a registered dietitian.
          </p>
        </div>

        {/* Input */}
        <form onSubmit={handleSend} className="flex gap-3">
          <label htmlFor="chat-input" className="sr-only">Message</label>
          <input
            id="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about diet, calories, exercises, BMI, or your health risks..."
            className="input-field flex-1"
            aria-label="Message to diet advisor"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            aria-label="Send message"
            className="btn-primary px-4 disabled:opacity-30"
          >
            <FaPaperPlane size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
