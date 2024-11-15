"use client";

import Head from 'next/head';
import Chat from './components/Chat';
import { Share2 } from 'lucide-react';

const Home: React.FC = () => {
  return (
    <div className="h-screen overflow-hidden">
      <Head>
        <title>GraphRAG</title>
        <meta name="description" content="Intelligent Graph-based RAG Assistant" />
      </Head>
      <main className="h-full relative">
        <div className="absolute top-4 left-8 flex items-center gap-2">
          <div className="logo-container">
            <Share2 className="logo-icon" size={28} />
          </div>
          <span className="text-2xl font-semibold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 via-blue-500 to-indigo-400">
            GraphRAG
          </span>
        </div>
        <Chat />
      </main>
    </div>
  );
};

export default Home;