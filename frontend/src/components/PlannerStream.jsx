import React, { useState, useRef, useEffect } from "react";
import ChatBubble from "./ChatBubble";

export default function PlannerStream() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    const last = messages[messages.length - 1];
    if (last?.sender === "user") {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [messages]);

  useEffect(() => {
    if (!loading && messages.length > 0) {
      const last = messages[messages.length - 1];
      if (last.sender === "bot") {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      }
    }
  }, [loading, messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setMessages((prev) => [...prev, { sender: "user", text: question }]);
    setQuestion("");
    setLoading(true);

    const url = `http://localhost:8000/plan_stream?question=${encodeURIComponent(question)}`;

    // Add empty bot message for streaming
    setMessages((prev) => [...prev, { sender: "bot", text: "" }]);

    const processStream = async () => {
      try {
        const response = await fetch(url);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          // SSE format is "data: ...\n\n". We need to extract the content.
          const lines = chunk.split("\n").filter(line => line.startsWith("data: "));
          for (const line of lines) {
            const jsonStr = line.substring(6); // Remove "data: "
            if (jsonStr) {
              try {
                const data = JSON.parse(jsonStr);
                const token = data.token;
                if (token) {
                  setMessages((prev) => {
                    const last = prev[prev.length - 1];
                    const updated = { ...last, text: last.text + token };
                    return [...prev.slice(0, -1), updated];
                  });
                }
              } catch {
                console.error("Failed to parse JSON:", jsonStr);
              }
            }
          }
        }
      } catch (error) {
        console.error("Stream error:", error);
      } finally {
        setLoading(false);
      }
    };

    processStream();
  };

  return (
    <div className="flex flex-col w-full h-screen bg-gray-900 text-white">
      <div className="text-6xl font-bold my-6 text-center">🎓 Degree Planner</div>

      <div className="flex-1 w-full max-w-2xl mx-auto py-6 overflow-y-auto">
        <div className="w-full bg-gray-800 p-6 rounded-xl shadow-inner min-h-screen">
          <div className="w-full flex flex-col px-9 space-y-2">
            {messages.map((msg, idx) => (
              <ChatBubble key={idx} message={msg.text} isUser={msg.sender === "user"} />
            ))}
            {loading && (
              <div className="flex justify-start px-4 py-2">
                <div className="italic text-gray-400">Thinking...</div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        className="w-full max-w-2xl mx-auto px-4 py-4 flex gap-2 bg-gray-900"
      >
        <textarea
          className="flex-1 bg-gray-800 text-white p-4 rounded-lg border border-gray-700 resize-none h-24"
          placeholder="Ask a planning question..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
        />
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg"
          disabled={loading}
        >
          {loading ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
