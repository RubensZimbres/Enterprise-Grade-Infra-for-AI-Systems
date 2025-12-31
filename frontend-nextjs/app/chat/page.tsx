import React from 'react';
import ChatInterface from './ChatInterface';

export default function ChatPage() {
  // Authentication is handled by the parent layout/AuthProvider
  // Payment status is verified by the ChatInterface when calling the API
  return <ChatInterface />;
}