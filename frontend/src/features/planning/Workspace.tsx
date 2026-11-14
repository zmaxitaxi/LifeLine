import { useEffect, useRef, useState, type ReactNode } from "react";
import { Activity, MessageCircle, ClipboardList } from "lucide-react";
import type { OverviewSection } from "./presentation";

export function useWorkspaceNavigation() {
  const read = () => {
    const [page, section] = location.hash.slice(1).split("/");
    return {
      page: page.startsWith("overview") ? "overview" : "assistant",
      section: section as OverviewSection | undefined,
    } as const;
  };
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const change = () => setRoute(read());
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);
  function explore(section: OverviewSection = "solutions") {
    location.hash = `overview/${section}`;
  }
  return { ...route, explore };
}

export function Workspace({
  page,
  section,
  modelStatus,
  context,
  assistant,
  overview,
  setup = false,
}: {
  page: "assistant" | "overview";
  section?: OverviewSection;
  modelStatus: ReactNode;
  context: ReactNode;
  assistant: ReactNode;
  overview: ReactNode;
  setup?: boolean;
}) {
  const overviewRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (page === "overview" && section) {
      // A section is still part of Clinic Overview, not another primary route.
      overviewRef.current
        ?.querySelector(`[data-overview-section="${section}"]`)
        ?.scrollIntoView({ block: "start" });
    }
  }, [page, section]);
  return (
    <div className="chat-app two-page-app" data-page={page}>
      <a
        className="skip-link"
        href={page === "assistant" ? setup ? "#setup-name" : "#chat-input" : "#overview-title"}
      >
        Skip to {page === "assistant" ? setup ? "clinic setup" : "message" : "clinic overview"}
      </a>
      <header className="chat-header">
        <div>
          <a
            href="#assistant"
            className="chat-brand"
            aria-label="LifeLine home"
          >
            <Activity aria-hidden="true" />
            <span>LifeLine</span>
          </a>
          <div className="model-status" role="status">
            {modelStatus}
          </div>
        </div>
      </header>
      <div className="workspace-navigation">
        <nav aria-label="Primary navigation">
          <a
            href="#assistant"
            aria-current={page === "assistant" ? "page" : undefined}
          >
            <MessageCircle aria-hidden="true" />
            AI Assistant
          </a>
          <a
            href="#overview"
            aria-current={page === "overview" ? "page" : undefined}
          >
            <ClipboardList aria-hidden="true" />
            Clinic Overview
          </a>
        </nav>
      </div>
      <main className="chat-workspace" id="main-chat">
        {context}
        <section
          hidden={page !== "assistant"}
          className="assistant-page"
          aria-label="AI Assistant"
        >
          {assistant}
        </section>
        <section
          hidden={page !== "overview"}
          className="overview-page"
          aria-labelledby="overview-title"
          ref={overviewRef}
        >
          <div className="overview-heading">
            <h1 id="overview-title" tabIndex={-1}>
              Clinic Overview
            </h1>
            <p>
              Activities, equipment, and the latest calculated plan in one
              place.
            </p>
          </div>
          {overview}
        </section>
      </main>
    </div>
  );
}
