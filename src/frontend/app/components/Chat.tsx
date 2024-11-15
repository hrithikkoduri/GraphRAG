"use client";

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import '../globals.css';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

type Message = {
    role: 'user' | 'assistant';
    content: string;
};

const Chat = () => {
    const [query, setQuery] = useState<string>('');
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const chatWindowRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = (behavior: 'auto' | 'smooth' = 'smooth') => {
        if (chatWindowRef.current) {
            const scrollHeight = chatWindowRef.current.scrollHeight;
            chatWindowRef.current.scrollTo({
                top: scrollHeight,
                behavior: behavior
            });
        }
    };

    useEffect(() => {
        scrollToBottom('auto');
    }, [messages]);

    const LoadingIndicator = () => (
        <div className="message assistant loading-message">
            <div className="loading-container">
                <span className="text-indigo-600 font-medium">AI is thinking</span>
                <div className="loading-dots">
                    <div className="dot"></div>
                    <div className="dot"></div>
                    <div className="dot"></div>
                </div>
            </div>
        </div>
    );

    const handleSend = async () => {
        if (!query.trim()) return;

        const userMessage: Message = { role: 'user', content: query };
        setMessages((prev) => [...prev, userMessage]);
        setIsLoading(true);
        scrollToBottom();

        try {
            const response = await axios.post<{ response: string }>('http://localhost:8000/generate-response', {
                query: query,
            });
            const botMessage: Message = { role: 'assistant', content: response.data.response };
            setMessages((prev) => [...prev, botMessage]);
            scrollToBottom();
        } catch (error) {
            console.error('Error sending message:', error);
        } finally {
            setIsLoading(false);
        }

        setQuery('');
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
            setQuery('');
        }
    };

    const renderMessage = (content: string, role: 'user' | 'assistant') => {
        if (role === 'user') {
            return <div className="message-text">{content}</div>;
        }
        
        return (
            <ReactMarkdown
                className="message-text markdown"
                components={{
                    p: ({children}) => <p className="mb-2">{children}</p>,
                    strong: ({children}) => <span className="text-indigo-600 font-semibold">{children}</span>,
                    ul: ({children}) => <ul className="space-y-2">{children}</ul>,
                    li: ({children}) => (
                        <li className="message-item">
                            <span className="message-item-label">{children}</span>
                        </li>
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        );
    };

    return (
        <div className="chat-container">
            <div ref={chatWindowRef} className="chat-window">
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.role}`}>
                        {renderMessage(msg.content, msg.role)}
                    </div>
                ))}
                {isLoading && <LoadingIndicator />}
            </div>
            <div className="input-container">
                <div className="relative w-full">
                    <input
                        type="text"
                        className={`input ${isLoading ? 'loading' : ''}`}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={isLoading ? 'AI is thinking...' : 'Ask a question...'}
                        disabled={isLoading}
                    />
                    <button 
                        className="send-button"
                        onClick={handleSend}
                        disabled={!query.trim()}
                    >
                        <Send size={18} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Chat;