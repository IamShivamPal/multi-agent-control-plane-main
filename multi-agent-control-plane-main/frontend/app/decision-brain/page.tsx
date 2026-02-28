"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ActionButton } from "@/components/ActionButton";
import { FormSelect } from "@/components/FormSelect";
import { StatCard } from "@/components/StatCard";
import { StatusBadge } from "@/components/StatusBadge";
import {
  getActionScope,
  getDecisionSummary,
  getHealth,
  getRecentActivity,
  makeDecision,
  makeDecisionWithControlPlane,
  type ActionScopeResponse,
  type DecisionResponse,
  type HealthResponse,
} from "@/lib/api";

const environmentOptions = [
  { value: "DEV", label: "DEV" },
  { value: "STAGE", label: "STAGE" },
  { value: "PROD", label: "PROD" }
];

const eventTypeOptions = [
  { value: "HIGH_CPU", label: "High CPU" },
  { value: "HIGH_MEMORY", label: "High Memory" },
  { value: "LATENCY", label: "Latency" }
];

const defaultActionScope: ActionScopeResponse = {
  DEV: ["noop", "scale_up", "scale_down", "restart"],
  STAGE: ["noop", "scale_up", "scale_down"],
  PROD: ["noop", "restart"]
};

function isEnvironment(value: string): value is "DEV" | "STAGE" | "PROD" {
  return value === "DEV" || value === "STAGE" || value === "PROD";
}

function isEventType(value: string): value is "HIGH_CPU" | "HIGH_MEMORY" | "LATENCY" {
  return value === "HIGH_CPU" || value === "HIGH_MEMORY" || value === "LATENCY";
}

export default function DecisionBrainPage() {
  const [environment, setEnvironment] = useState<"DEV" | "STAGE" | "PROD">("DEV");
  const [eventType, setEventType] = useState<"HIGH_CPU" | "HIGH_MEMORY" | "LATENCY">("HIGH_CPU");
  const [cpuPercent, setCpuPercent] = useState("");
  const [memoryPercent, setMemoryPercent] = useState("");

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [actionScope, setActionScope] = useState<ActionScopeResponse>(defaultActionScope);
  const [recentActivity, setRecentActivity] = useState<DecisionResponse[]>([]);
  const [totalRequests, setTotalRequests] = useState(0);
  const [lastAction, setLastAction] = useState("-");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);

  const successRateLabel = useMemo(() => {
    if (!health) {
      return "100%";
    }
    return `${Math.round(health.success_rate * 100)}%`;
  }, [health]);

  useEffect(() => {
    let isMounted = true;

    async function loadSummaryMetrics() {
      try {
        const data = await getDecisionSummary();
        if (isMounted) {
          setTotalRequests(data.total_decisions ?? 0);
          setLastAction(data.last_action ?? "-");
        }
      } catch {
        // Silent fail for summary metrics; health/scope will still load
      }
    }

    async function loadInitialData() {
      try {
        const [healthData, actionScopeData, recentData] = await Promise.all([
          getHealth(),
          getActionScope(),
          getRecentActivity(),
        ]);

        if (!isMounted) {
          return;
        }

        setHealth(healthData);
        setActionScope(actionScopeData);
        setRecentActivity(recentData.items);
        await loadSummaryMetrics();
      } catch {
        if (!isMounted) {
          return;
        }
        setErrorMessage("Decision Brain API is unreachable. Showing default values.");
      }
    }

    loadInitialData();

    const interval = window.setInterval(() => {
      void loadInitialData();
    }, 4000);

    return () => {
      isMounted = false;
      window.clearInterval(interval);
    };
  }, []);

  async function handleGetDecision() {
    setIsSubmitting(true);
    setErrorMessage(null);

    const payload = {
      environment,
      event_type: eventType,
      cpu: Number(cpuPercent || 0),
      memory: Number(memoryPercent || 0)
    };

    try {
      let decision: DecisionResponse;
      try {
        const response = await makeDecisionWithControlPlane(payload);
        decision = response.decision;
      } catch {
        decision = await makeDecision(payload);
      }
      setRecentActivity((previous) => [decision, ...previous].slice(0, 10));
      
      // Refresh summary metrics from backend after decision
      setIsLoadingSummary(true);
      try {
        const summaryData = await getDecisionSummary();
        setTotalRequests(summaryData.total_decisions ?? 0);
        setLastAction(summaryData.last_action ?? decision.selected_action);
      } catch {
        // Fallback: use local decision data if summary fetch fails
        setLastAction(decision.selected_action);
        setTotalRequests((previous) => previous + 1);
      } finally {
        setIsLoadingSummary(false);
      }
    } catch {
      setErrorMessage("Unable to fetch decision. Check backend service.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleClearActivity() {
    setRecentActivity([]);
  }

  function handleEnvironmentChange(value: string) {
    if (isEnvironment(value)) {
      setEnvironment(value);
    }
  }

  function handleEventTypeChange(value: string) {
    if (isEventType(value)) {
      setEventType(value);
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-violet-700 via-purple-700 to-indigo-700 px-4 py-8 md:px-8 md:py-10">
      <div className="mx-auto w-full max-w-7xl rounded-3xl bg-white/95 p-6 shadow-2xl backdrop-blur md:p-8">
        <div className="space-y-8">
          <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl" aria-hidden="true">🧠</span>
              <h1 className="text-2xl font-bold text-slate-900 md:text-3xl">RL Decision Brain</h1>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label={health?.status === "healthy" ? "HEALTHY" : "UNAVAILABLE"} icon="✅" variant="green" />
              <StatusBadge label={health?.demo_frozen ? "DEMO-FROZEN" : "LIVE"} icon="🧪" variant="blue" />
              <StatusBadge label={health?.stateless ?? true ? "STATELESS" : "STATEFUL"} icon="⚡" variant="purple" />
            </div>
          </header>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Key metrics">
            <StatCard icon="📥" title="Total Requests" value={String(totalRequests)} subtext="Since page load" />
            <StatCard icon="🧭" title="Last Action" value={lastAction} subtext="Most recent decision" />
            <StatCard icon="🎯" title="Success Rate" value={successRateLabel} subtext="API response rate" />
          </section>

          <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
            <h2 className="text-lg font-semibold text-slate-900">Test Decision Maker</h2>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <FormSelect id="environment" label="Environment" value={environment} options={environmentOptions} onChange={handleEnvironmentChange} />
              <FormSelect id="eventType" label="Event Type" value={eventType} options={eventTypeOptions} onChange={handleEventTypeChange} />

              <div className="space-y-2">
                <label htmlFor="cpuPercent" className="text-sm font-medium text-slate-700">CPU % <span className="text-xs text-slate-500">(30=noop, 80+=scale_up, &lt;30=scale_down)</span></label>
                <input
                  id="cpuPercent"
                  type="number"
                  value={cpuPercent}
                  onChange={(event) => setCpuPercent(event.target.value)}
                  placeholder="e.g. 85 for scale_up, 50 for noop, 10 for scale_down"
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="memoryPercent" className="text-sm font-medium text-slate-700">Memory % <span className="text-xs text-slate-500">(≤85=normal, &gt;85=scale_up)</span></label>
                <input
                  id="memoryPercent"
                  type="number"
                  value={memoryPercent}
                  onChange={(event) => setMemoryPercent(event.target.value)}
                  placeholder="e.g. 90 for scale_up, 50 for normal"
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={handleGetDecision}
              disabled={isSubmitting}
              className="mt-6 w-full rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 px-4 py-3 text-base font-semibold text-white shadow-md transition hover:from-violet-700 hover:to-purple-700 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2"
              aria-label="Get decision"
            >
              {isSubmitting ? "⏳ Getting Decision..." : "🚀 Get Decision"}
            </button>
            {errorMessage ? <p className="mt-3 text-sm text-rose-600">{errorMessage}</p> : null}
          </section>

          <section className="grid gap-4 xl:grid-cols-2">
            <article className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
              <h2 className="text-lg font-semibold text-slate-900">Action Scope</h2>
              <div className="mt-5 space-y-5">
                <div>
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">DEV</h3>
                  <div className="flex flex-wrap gap-2">{actionScope.DEV.map((action) => <ActionButton key={`DEV-${action}`} label={action} />)}</div>
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">STAGE</h3>
                  <div className="flex flex-wrap gap-2">{actionScope.STAGE.map((action) => <ActionButton key={`STAGE-${action}`} label={action} />)}</div>
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">PROD</h3>
                  <div className="flex flex-wrap gap-2">{actionScope.PROD.map((action) => <ActionButton key={`PROD-${action}`} label={action} />)}</div>
                </div>
              </div>
            </article>

            <article className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">Recent Activity</h2>
                {recentActivity.length > 0 && (
                  <button
                    type="button"
                    onClick={handleClearActivity}
                    className="rounded-lg bg-rose-50 px-3 py-1 text-sm font-medium text-rose-600 transition hover:bg-rose-100 active:scale-95"
                    aria-label="Clear recent activity"
                  >
                    🗑️ Clear
                  </button>
                )}
              </div>
              {recentActivity.length === 0 ? (
                <div className="mt-5 flex min-h-48 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8">
                  <p className="text-sm text-slate-400">No activity yet.</p>
                </div>
              ) : (
                <ul className="mt-5 max-h-64 space-y-3 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3">
                  {recentActivity.map((item) => (
                    <li key={item.decision_id} className="rounded-lg border border-slate-100 bg-white p-3">
                      <p className="text-sm font-semibold text-slate-800">{item.environment} • {item.selected_action}</p>
                      <p className="mt-1 text-xs text-slate-500">{item.reason}</p>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          </section>

          <footer className="flex justify-center pt-2">
            <Link href="/" className="rounded-full px-4 py-2 text-sm font-medium text-violet-700 transition hover:bg-violet-50 hover:text-violet-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500">
              📦 Open Control Plane
            </Link>
          </footer>
        </div>
      </div>
    </main>
  );
}
