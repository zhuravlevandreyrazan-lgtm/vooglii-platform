"use client";

import { useRef, useState } from "react";
import { sendAdvisorQuery } from "@/features/advisor/services/advisor-query";
import { formatApiErrorMessage } from "@/shared/api";
import type {
  AdvisorConversationStatus,
  AdvisorQueryContext,
  AdvisorQueryMessage
} from "@/features/advisor/types";

const MAX_MESSAGE_LENGTH = 1000;

function createMessageId(prefix: "user" | "assistant") {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function createUserMessage(text: string): AdvisorQueryMessage {
  return {
    id: createMessageId("user"),
    role: "user",
    text,
    createdAt: new Date().toISOString(),
    status: "ready"
  };
}

function createAssistantMessage(
  text: string,
  status: AdvisorConversationStatus,
  response?: AdvisorQueryMessage["response"]
): AdvisorQueryMessage {
  return {
    id: createMessageId("assistant"),
    role: "assistant",
    text,
    createdAt: new Date().toISOString(),
    status,
    response
  };
}

export function useAdvisorConversation(context?: AdvisorQueryContext) {
  const [messages, setMessages] = useState<AdvisorQueryMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastUserMessageRef = useRef<string | null>(null);

  const clearConversation = () => {
    abortControllerRef.current?.abort();
    setMessages([]);
    setInput("");
    setError(null);
    setSending(false);
    lastUserMessageRef.current = null;
  };

  const executeQuery = async (rawMessage: string, appendUserMessage: boolean) => {
    const message = rawMessage.trim();
    if (!message || sending) {
      return;
    }
    if (message.length > MAX_MESSAGE_LENGTH) {
      setError(`Message is too long. Maximum length is ${MAX_MESSAGE_LENGTH} characters.`);
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current?.abort();
    abortControllerRef.current = controller;

    setSending(true);
    setError(null);
    lastUserMessageRef.current = message;

    if (appendUserMessage) {
      setMessages((current) => [...current, createUserMessage(message)]);
    }

    try {
      const response = await sendAdvisorQuery(message, context, controller.signal);
      if (controller.signal.aborted) {
        return;
      }
      setMessages((current) => [
        ...current,
        createAssistantMessage(response.answer, response.status === "error" ? "error" : "ready", response)
      ]);
      setInput("");
      if (response.status === "error") {
        setError("Advisor returned a structured error response.");
      }
    } catch (sendError) {
      if (controller.signal.aborted) {
        return;
      }
      const formatted = formatApiErrorMessage(sendError);
      setError(formatted);
      setMessages((current) => [
        ...current,
        createAssistantMessage(
          "Advisor query failed before a valid response was returned.",
          "error"
        )
      ]);
    } finally {
      if (!controller.signal.aborted) {
        setSending(false);
      }
    }
  };

  const sendMessage = async (messageOverride?: string) => {
    await executeQuery(messageOverride ?? input, true);
  };

  const retryLast = async () => {
    if (!lastUserMessageRef.current || sending) {
      return;
    }
    setError(null);
    await executeQuery(lastUserMessageRef.current, false);
  };

  return {
    messages,
    input,
    setInput,
    sending,
    error,
    sendMessage,
    retryLast,
    clearConversation
  };
}
