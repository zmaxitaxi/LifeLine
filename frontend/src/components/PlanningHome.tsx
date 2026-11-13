import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  BatteryCharging,
  CalendarDays,
  Cloud,
  LoaderCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Disclosure } from "@/components/Disclosure";
import type { PlanningQuestion } from "../../../contracts/api";

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}
const actions = [
  {
    label: "Plan tomorrow’s electricity",
    message: "Will we have enough electricity tomorrow?",
    icon: CalendarDays,
  },
  {
    label: "Prepare for cloudy weather",
    message:
      "What if the weather is worse than expected? Test with 25% of the current sunshine.",
    icon: Cloud,
  },
  {
    label: "Check battery reliability",
    message: "Check battery reliability",
    icon: BatteryCharging,
  },
];

export function PlanningHome({
  busy,
  messages,
  pending,
  hasPlan,
  onAsk,
  onCancel,
}: {
  busy: boolean;
  messages: ChatMessage[];
  pending: PlanningQuestion | null;
  hasPlan: boolean;
  onAsk: (message: string, followup?: boolean) => void;
  onCancel: () => void;
}) {
  const [message, setMessage] = useState("");
  const input = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (pending) input.current?.focus();
  }, [pending]);
  function submit() {
    if (!message.trim() || busy) return;
    onAsk(message.trim(), true);
    setMessage("");
  }
  return (
    <section className="planning-home" aria-labelledby="welcome-title">
      {!hasPlan ? (
        <div className="welcome-heading">
          <h2 id="welcome-title">What does your clinic need?</h2>
          <p>
            Plan when to run equipment and see whether the battery can support
            essential needs.
          </p>
        </div>
      ) : null}
      <div
        className={`planning-actions ${hasPlan ? "compact-actions" : ""}`}
        aria-label="Start a plan"
      >
        {actions.map(({ label, message: prompt, icon: Icon }, index) => (
          <Button
            key={label}
            type="button"
            variant={index === 0 ? "secondary" : "outline"}
            className="planning-action"
            disabled={busy}
            onClick={() => onAsk(prompt)}
          >
            <Icon data-icon="inline-start" />
            <span>{label}</span>
            <ArrowRight data-icon="inline-end" />
          </Button>
        ))}
      </div>
      <form
        className="assistant-composer"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <h2 id="assistant-title">Ask LifeLine</h2>
        {messages.length > 2 ? (
          <Disclosure title="Earlier conversation">
            {messages.slice(0, -2).map((m, i) => (
              <p className="chat-message" key={i}>
                <strong>{m.role === "user" ? "You" : "LifeLine"}:</strong>{" "}
                {m.text}
              </p>
            ))}
          </Disclosure>
        ) : null}
        {messages.length ? (
          <div
            className="conversation"
            role="log"
            aria-label="Conversation with LifeLine"
            aria-live="polite"
          >
            {messages.slice(-2).map((m, i) => (
              <p className="chat-message" key={`${messages.length}-${i}`}>
                <strong>{m.role === "user" ? "You" : "LifeLine"}:</strong>{" "}
                {m.text}
              </p>
            ))}
          </div>
        ) : null}
        <FieldGroup className="composer-fields">
          <Field>
            <FieldLabel
              htmlFor="clinic-question"
              className={pending ? "question-label sr-only" : "sr-only"}
            >
              {pending?.prompt ?? "Describe your clinic’s situation"}
            </FieldLabel>
            <textarea
              id="clinic-question"
              ref={input}
              value={message}
              maxLength={2000}
              rows={2}
              placeholder={
                pending
                  ? "Type your answer here…"
                  : "For example: Will we have enough electricity tomorrow?"
              }
              aria-describedby="assistant-availability"
              disabled={busy}
              onChange={(e) => setMessage(e.target.value)}
            />
          </Field>
          <Button type="submit" size="lg" disabled={busy || !message.trim()}>
            {busy ? (
              <LoaderCircle className="loading-spin" data-icon="inline-start" />
            ) : null}
            {busy
              ? "Checking your plan…"
              : pending
                ? "Continue"
                : "Make a plan"}
            <ArrowRight data-icon="inline-end" />
          </Button>
        </FieldGroup>
        <div className="composer-footer">
          <p id="assistant-availability">
            Local example planning available · Open the live-weather panel for
            local AI tools and forecast-backed answers
          </p>
          {pending ? (
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel question
            </Button>
          ) : null}
        </div>
      </form>
    </section>
  );
}
