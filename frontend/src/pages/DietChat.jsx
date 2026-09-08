import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { sendChatMessage, getChatHistory } from '../services/api';
import { FiSend, FiAlertTriangle, FiInfo } from 'react-icons/fi';

function MessageBubble({ message, isUser }) {
  // Simple markdown-like bold
  const renderContent = (text) => {
    return text.split('\n').map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g);
      return (
        <p key={i} className={i > 0 ? 'mt-1' : ''}>
          {parts.map((part, j) =>
            part.startsWith('**') && part.endsWith('**') ? (
              <strong key={j} className="text-white">{part.slice(2, -2)}</strong>
            ) : (
              <span key={j}>{part}</span>
            )
          )}
        </p>
      );
    });
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
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
  const messagesEndRef = useRef(null);

  useEffect(() => {
    async function fetchHistory() {
      if (!user) return;
      try {
        const res = await getChatHistory(user.id);
        if (res.data.messages?.length) {
          setMessages(res.data.messages);
          setRiskContext(res.data.risk_context);
        }
      } catch {
        // No history yet — that's fine
      }
    }
    fetchHistory();
  }, [user]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);      try {
        const res = await sendChatMessage(user.id, userMsg);
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
          { role: 'assistant', content: `⚠️ Sorry, I encountered an error: ${msg}.${helpText}` },
        ]);
    } finally {
      setLoading(false);
    }
  };

  const quickQuestions = [
    '📋 Show my risk profile',
    '🗓️ Generate my diet plan',
    '🔍 Calories in chicken breast',
    '🏋️ Exercise for chest',
    '📊 Calculate my macros',
    '⚖️ Compare chicken vs rice',
    '💧 How much water should I drink',
    '💪 High protein foods',
  ];

  return (
    <div className="pt-20 pb-4 px-4 max-w-3xl mx-auto flex flex-col min-h-screen">
      <div className="animate-slide-up flex-1 flex flex-col">
        <h1 className="font-display text-2xl font-bold text-white mb-1">Diet Advisor</h1>
        <p className="text-gray-400 text-sm mb-4">AI-powered nutrition guidance based on your health profile</p>

        {/* Risk Context Badge */}
        {riskContext && (
          <div className="glass-light p-3 flex items-center gap-3 mb-4">
            <FiAlertTriangle className="text-yellow-400 shrink-0" size={16} />
            <span className="text-xs text-gray-300">{riskContext}</span>
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto mb-4 space-y-1">
          {messages.length === 0 && (
            <div className="text-center py-8">
              <div className="w-16 h-16 rounded-2xl bg-primary-500/10 flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">🥗</span>
              </div>
              <h3 className="text-white font-semibold mb-2">Your AI Diet Advisor</h3>
              <p className="text-sm text-gray-400 mb-6 max-w-sm mx-auto">
                I can help you with meal plans, real nutrition data, exercises, calorie calculations, and more!
              </p>
              <div className="flex flex-wrap justify-center gap-2 max-w-md mx-auto">
                {quickQuestions.map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); }}
                    className="glass-light px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-surface-100 transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg.content} isUser={msg.role === 'user'} />
          ))}
          {loading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Disclaimer */}
        <div className="glass-light p-3 flex items-start gap-2 mb-3">
          <FiInfo className="text-gray-500 shrink-0 mt-0.5" size={14} />
          <p className="text-xs text-gray-500">
            AI-generated dietary guidance, not medical advice. Always consult a registered dietitian.
          </p>
        </div>

        {/* Input */}
        <form onSubmit={handleSend} className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about diet, calories, exercises, BMI, or your health risks..."
            className="input-field flex-1"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="btn-primary px-4 disabled:opacity-30"
          >
            <FiSend size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
