"use client";

import Link from "next/link";
import { useAdvisorConversation } from "@/features/advisor/hooks/use-advisor-conversation";
import { RuntimeBadge } from "@/shared/api";
import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/components/status-badge";
import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AdvisorQueryContext, AdvisorQueryMessage } from "@/features/advisor/types";

const QUICK_PROMPTS = [
  "Что делать сегодня?",
  "Почему прибыль изменилась?",
  "Какие SKU в риске?",
  "Где реклама сжигает деньги?",
  "Что пополнить в первую очередь?",
  "Какие товары масштабировать?"
];

function formatConfidence(value: number) {
  return `${Math.round(value * 100)}%`;
}

function MessageBubble({ message }: { message: AdvisorQueryMessage }) {
  if (message.role === "user") {
    return (
      <div className="ml-auto max-w-3xl rounded-[24px] bg-[var(--ink)] px-5 py-4 text-sm leading-7 text-white">
        {message.text}
      </div>
    );
  }

  return (
    <div className="max-w-4xl rounded-[24px] border border-[var(--line)] bg-[var(--panel)] px-5 py-5">
      <div className="space-y-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
            Advisor answer
          </p>
          <p className="mt-3 text-sm leading-7 text-[var(--ink)]">{message.text}</p>
        </div>

        {message.response ? (
          <>
            <div className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                Summary
              </p>
              <p className="mt-3 text-sm leading-6 text-[var(--ink)]">{message.response.summary}</p>
            </div>

            {message.response.recommendations.length > 0 ? (
              <div className="space-y-3">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  Recommendations
                </p>
                {message.response.recommendations.map((item) => (
                  <div key={item.id} className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <SeverityBadge severity={item.priority} />
                      <StatusBadge tone="neutral">{item.confidence} confidence</StatusBadge>
                    </div>
                    <p className="mt-3 text-sm font-semibold">{item.title}</p>
                    <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.reason}</p>
                    <Link className="mt-3 inline-flex text-sm font-semibold text-[var(--accent-strong)]" href={item.href}>
                      Open workspace
                    </Link>
                  </div>
                ))}
              </div>
            ) : null}

            {message.response.evidence.length > 0 ? (
              <div className="space-y-3">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  Evidence
                </p>
                {message.response.evidence.map((item) => (
                  <div key={item.id} className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-4">
                    <p className="text-sm font-semibold">{item.label}</p>
                    <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.detail}</p>
                    {item.metrics.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.metrics.map((metric) => (
                          <StatusBadge key={metric} tone="neutral">
                            {metric}
                          </StatusBadge>
                        ))}
                      </div>
                    ) : null}
                    <Link className="mt-3 inline-flex text-sm font-semibold text-[var(--accent-strong)]" href={item.href}>
                      Open source
                    </Link>
                  </div>
                ))}
              </div>
            ) : null}

            {message.response.links.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2">
                {message.response.links.map((item) => (
                  <Link
                    key={item.id}
                    className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-4 transition hover:border-[var(--accent)]"
                    href={item.href}
                  >
                    <p className="text-sm font-semibold">{item.label}</p>
                    <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.description}</p>
                  </Link>
                ))}
              </div>
            ) : null}

            {message.response.related.length > 0 ? (
              <div className="space-y-3">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  Related
                </p>
                <div className="grid gap-3 md:grid-cols-2">
                  {message.response.related.map((item) => (
                    <div key={item.id} className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge tone="accent">{item.type}</StatusBadge>
                        <p className="text-sm font-semibold">{item.label}</p>
                      </div>
                      {item.note ? (
                        <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.note}</p>
                      ) : null}
                      {item.href ? (
                        <Link className="mt-3 inline-flex text-sm font-semibold text-[var(--accent-strong)]" href={item.href}>
                          Open
                        </Link>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge tone={message.response.status === "degraded" ? "watch" : "healthy"}>
                {message.response.status}
              </StatusBadge>
              <StatusBadge tone="neutral">
                Confidence {formatConfidence(message.response.confidence)}
              </StatusBadge>
              <RuntimeBadge diagnostics={message.response.diagnostics} />
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

export function AdvisorConversationCard({
  context,
  prompt,
  loading = false,
  error = null
}: {
  context?: AdvisorQueryContext;
  prompt?: string;
  loading?: boolean;
  error?: string | null;
}) {
  const { messages, input, setInput, sending, sendMessage, retryLast, clearConversation } =
    useAdvisorConversation(context);

  const disabled = loading || sending;
  const helperText =
    error ??
    prompt ??
    "Ask the advisor about finance, advertising, SKU risk, stock coverage, or what to do next.";

  const onSubmit = async () => {
    await sendMessage();
  };

  return (
    <WidgetCard
      error={null}
      loading={loading}
      subtitle="Copilot conversation"
      title="Advisor Conversation"
    >
      <div className="space-y-6">
        <div className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
          <p className="text-sm leading-6 text-[var(--ink-soft)]">{helperText}</p>
          {context?.sku ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="accent">{`SKU ${context.sku}`}</StatusBadge>
              {context.workspace ? <StatusBadge tone="neutral">{context.workspace}</StatusBadge> : null}
              {context.organizationId ? <StatusBadge tone="neutral">{context.organizationId}</StatusBadge> : null}
              {context.cabinetId ? <StatusBadge tone="neutral">{context.cabinetId}</StatusBadge> : null}
            </div>
          ) : context?.workspace ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="neutral">{context.workspace}</StatusBadge>
              {context.organizationId ? <StatusBadge tone="neutral">{context.organizationId}</StatusBadge> : null}
              {context.cabinetId ? <StatusBadge tone="neutral">{context.cabinetId}</StatusBadge> : null}
            </div>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          {QUICK_PROMPTS.map((item) => (
            <button
              key={item}
              className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={disabled}
              onClick={() => {
                void sendMessage(item);
              }}
              type="button"
            >
              {item}
            </button>
          ))}
        </div>

        <div className="space-y-4">
          {messages.length > 0 ? (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          ) : (
            <div className="rounded-[24px] border border-dashed border-[var(--line)] bg-[var(--panel)] px-5 py-8 text-sm leading-7 text-[var(--ink-soft)]">
              Ask a management question to receive an advisor answer, recommendations, evidence, links, related items, and runtime diagnostics.
            </div>
          )}

          {sending ? (
            <div className="max-w-4xl rounded-[24px] border border-[var(--line)] bg-[var(--panel)] px-5 py-5 text-sm leading-7 text-[var(--ink-soft)]">
              Advisor is preparing a response...
            </div>
          ) : null}
        </div>

        <div className="rounded-[24px] border border-[var(--line)] bg-white p-4">
          <label
            className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]"
            htmlFor="advisor-input"
          >
            Ask the advisor
          </label>
          <textarea
            aria-label="Advisor conversation input"
            className="mt-3 min-h-32 w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm leading-7 outline-none transition focus:border-[var(--accent)]"
            disabled={disabled}
            id="advisor-input"
            maxLength={1000}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void onSubmit();
              }
            }}
            placeholder="Ask what to do today, why profit changed, which SKU is in risk, or where ad spend is leaking."
            value={input}
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--ink-soft)]">
              {`${input.trim().length}/1000`}
            </p>
            <div className="flex flex-wrap gap-3">
              <Button disabled={disabled || messages.length === 0} onClick={clearConversation} type="button" variant="ghost">
                Clear
              </Button>
              <Button disabled={disabled || messages.length === 0} onClick={() => void retryLast()} type="button" variant="ghost">
                Retry
              </Button>
              <Button disabled={disabled || input.trim().length === 0} onClick={() => void onSubmit()} type="button" variant="secondary">
                {sending ? "Sending..." : "Send"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </WidgetCard>
  );
}
