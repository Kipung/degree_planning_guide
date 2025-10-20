import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ChatBubble({ message, isUser }) {
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} px-1`}>
      <div
        className={`
          max-w-[75%] px-4 py-3 text-sm rounded-2xl shadow-lg
          ${isUser
            ? "bg-blue-600 text-white rounded-br-none"
            : "bg-gray-700 text-white rounded-bl-none"}
        `}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ inline, children, ...props }) {
              return inline ? (
                <code
                  className="bg-gray-800 px-1 py-0.5 rounded text-green-400"
                  {...props}
                >
                  {children}
                </code>
              ) : (
                <pre className="bg-gray-800 p-3 rounded overflow-x-auto text-green-400 text-sm my-2">
                  <code {...props}>{children}</code>
                </pre>
              );
            },
            pre({ children }) {
              return <>{children}</>; // prevent double-wrapping
            },
            ul({ children }) {
              return (
                <ul className="list-disc list-inside ml-4 my-2">{children}</ul>
              );
            },
            ol({ children }) {
              return (
                <ol className="list-decimal list-inside ml-4 my-2">{children}</ol>
              );
            },
            blockquote({ children }) {
              return (
                <blockquote className="border-l-4 border-gray-500 pl-4 italic text-gray-300 my-2">
                  {children}
                </blockquote>
              );
            },
          }}
        >
          {message}
        </ReactMarkdown>
      </div>
    </div>
  );
}