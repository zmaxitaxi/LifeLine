import { useEffect, useId, useState } from "react";
import { AlertTriangle, Pause, Play, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import type { PlanResult, SimulationResponse } from "../../../../contracts/api";
import type { EvidenceOption } from "./presentation";
import { num, shortName } from "@/lib/clinic";
import { Disclosure } from "@/components/Disclosure";

// Expose modeled boundaries only. CSS eases the fill without inventing readouts.
export function batteryAt(plan: PlanResult, hour: number) {
  const boundary = Math.max(0, Math.min(24, Math.floor(hour)));
  return boundary === 24
    ? plan.hourly[23].soc_end_kwh
    : plan.hourly[boundary].soc_start_kwh;
}
const timeLabel = (hour: number) => `${String(hour).padStart(2, "0")}:00`;
type Scenario = {
  label: string;
  simulation: SimulationResponse;
  plan: PlanResult;
};

export function OutcomeIndicators({
  current,
  proposed,
}: {
  current: Scenario;
  proposed?: Scenario;
}) {
  const scenarios = proposed ? [current, proposed] : [current];
  const originalWork = current.plan.metrics.flexible_requested_kwh;
  return (
    <div className="recovery-indicators" aria-label="Modeled outcomes">
      {[
        {
          title: "Essential equipment power",
          value: (s: Scenario) => {
            const m = s.plan.metrics;
            return m.critical_coverage_pct === null
              ? "No essential needs configured"
              : m.critical_unserved_kwh > 1e-6
                ? `${num(m.critical_unserved_kwh)} kWh short · ${m.critical_coverage_pct.toFixed(1)}% covered`
                : "All modeled needs covered";
          },
        },
        {
          title: "Battery reserve",
          value: (s: Scenario) => {
            const m = s.plan.metrics;
            const reserve = s.simulation.effective_config.reserve_kwh;
            return `${m.min_soc_kwh < reserve - 1e-6 ? "Below target" : "Target met"} · lowest ${num(m.min_soc_kwh)} kWh / ${num(reserve)} kWh target`;
          },
        },
        {
          title: "Requested work completion",
          value: (s: Scenario) =>
            originalWork <= 1e-6
              ? "No flexible work requested"
              : `${num(s.plan.metrics.flexible_served_kwh)} of ${num(originalWork)} kWh of original flexible work`,
        },
      ].map(({ title, value }) => (
        <div key={title}>
          <h4>{title}</h4>
          {scenarios.map((s) => (
            <p key={s.label}>
              <strong>{proposed ? `${s.label}: ` : ""}</strong>
              {value(s)}
            </p>
          ))}
        </div>
      ))}
    </div>
  );
}

function Battery({
  scenario,
  hour,
  current,
}: {
  scenario: Scenario;
  hour: number;
  current: boolean;
}) {
  const id = useId().replace(/:/g, "");
  const { plan, simulation, label } = scenario;
  const { battery_capacity_kwh: capacity, reserve_kwh: reserve } =
    simulation.effective_config;
  const energy = batteryAt(plan, hour);
  const percentage = (energy / capacity) * 100;
  const fill = Math.max(0, Math.min(1, energy / capacity));
  const row = plan.hourly[Math.min(23, hour)];
  const low = energy < reserve - 1e-6;
  const flow =
    hour === 24
      ? "End of simulated day"
      : row.charge_input_kwh > 1e-6
        ? "Solar charges the battery this hour"
        : row.discharge_output_kwh > 1e-6
          ? "Battery supplies equipment this hour"
          : "Stored energy stays steady this hour";
  return (
    <div
      className={`battery-state ${low ? "battery-low" : ""}`}
      data-testid={current ? "existing-battery" : "optimized-battery"}
      data-energy-kwh={energy}
      data-capacity-kwh={capacity}
      data-percentage={percentage}
      data-reserve-kwh={reserve}
    >
      <h4>{label}</h4>
      <div className="battery-graphic">
        <svg
          viewBox="0 0 180 250"
          role="img"
          aria-label={`${label}: ${percentage.toFixed(1)}% charge, ${num(energy)} kWh stored at ${timeLabel(hour)}`}
        >
          <defs>
            <clipPath id={id}>
              <rect x="29" y="26" width="122" height="206" rx="13" />
            </clipPath>
          </defs>
          <rect
            className="battery-terminal"
            x="69"
            y="7"
            width="42"
            height="15"
            rx="4"
          />
          <rect
            className="battery-outline"
            x="23"
            y="20"
            width="134"
            height="218"
            rx="19"
          />
          <rect
            className="battery-empty"
            x="29"
            y="26"
            width="122"
            height="206"
            rx="13"
          />
          <g clipPath={`url(#${id})`}>
            <rect
              className="battery-fill"
              x="29"
              y={232 - 206 * fill}
              width="122"
              height={206 * fill}
            />
          </g>
          <line
            className="battery-reserve"
            x1="29"
            x2="151"
            y1={232 - (206 * reserve) / capacity}
            y2={232 - (206 * reserve) / capacity}
          />
        </svg>
        <div className="battery-value">
          <strong>
            {percentage.toFixed(1)}
            <span>%</span>
          </strong>
          <span>{num(energy)} kWh stored</span>
          <span>{num(capacity)} kWh capacity</span>
        </div>
      </div>
      <p className="battery-flow">{flow}</p>
      <div className="battery-state-meta"><p className="battery-minimum">Daily minimum: {num(plan.metrics.min_soc_kwh)} kWh</p>
      <p className={low ? "battery-warning" : "battery-reserve-caption"}>
        {low ? (
          <>
            <AlertTriangle aria-hidden="true" />
            Below reserve:{" "}
          </>
        ) : (
          "Reserve target: "
        )}
        {num(reserve)} kWh
      </p></div>
      {hour < 24 && row.critical_unserved_kwh > 1e-6 ? (
        <p className="battery-warning">
          <AlertTriangle aria-hidden="true" />
          Essential equipment is short of {num(row.critical_unserved_kwh)} kWh
          in this hour.
        </p>
      ) : null}
    </div>
  );
}

export function BatteryEvidence({
  result,
  date,
  intervention,
  showIndicators = true,
}: {
  result: SimulationResponse;
  date: string;
  intervention?: EvidenceOption;
  showIndicators?: boolean;
}) {
  const [hour, setHour] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [mode, setMode] = useState<"current" | "recovery" | "compare">(
    !intervention || intervention.kind === "existing" ? "current" : "compare",
  );
  const [reducedMotion, setReducedMotion] = useState(false);
  const sliderId = useId();
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(preference.matches);
    update();
    preference.addEventListener("change", update);
    return () => preference.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    setHour(0);
    setPlaying(false);
    setMode(!intervention || intervention.kind === "existing" ? "current" : "compare");
  }, [result, intervention]);
  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(
      () => setHour((value) => Math.min(24, value + 1)),
      1000,
    );
    return () => clearInterval(timer);
  }, [playing]);
  useEffect(() => {
    if (hour >= 24) setPlaying(false);
  }, [hour]);
  const current: Scenario = {
    label: "Current plan",
    simulation: result,
    plan: result.baseline,
  };
  const recovered = intervention?.simulation ?? result;
  const proposed: Scenario = {
    label: "Selected plan",
    simulation: recovered,
    plan: intervention?.plan ?? recovered.optimized,
  };
  const visible =
    mode === "compare"
      ? [current, proposed]
      : [mode === "current" ? current : proposed];
  return (
    <section
      className="battery-playback"
      aria-labelledby={`${sliderId}-title`}
      data-testid="battery-playback"
      data-reduced-motion={reducedMotion}
    >
      <div className="battery-playback-heading">
        <div>
          <h3 id={`${sliderId}-title`}>Battery evidence</h3>
          <p>
            {date} · {result.timezone} · forecast-based simulation
          </p>
        </div>
        <time className="battery-clock" aria-label="Selected simulation time">
          {timeLabel(hour)}
        </time>
      </div>
      {showIndicators ? (
        <OutcomeIndicators
          current={mode === "recovery" ? proposed : current}
          proposed={mode === "compare" ? proposed : undefined}
        />
      ) : null}
      {intervention && intervention.kind !== "existing" ? <div
        className="battery-modes"
        role="group"
        aria-label="Battery visualization mode"
      >
        {(
          [
            ["current", "Current plan"],
            ["recovery", "Selected plan"],
            ["compare", "Compare"],
          ] as const
        ).map(([value, label]) => (
          <Button
            key={value}
            variant={mode === value ? "default" : "outline"}
            aria-pressed={mode === value}
            onClick={() => setMode(value)}
          >
            {label}
          </Button>
        ))}
      </div> : null}
      <div
        className={`battery-pair ${mode === "compare" ? "with-comparison" : ""}`}
      >
        {visible.map((s) => (
          <Battery
            key={s.label}
            scenario={s}
            hour={hour}
            current={s === current}
          />
        ))}
      </div>
      <div className="battery-timeline"><div className="battery-controls">
        <Button
          variant="outline"
          aria-label={
            playing ? "Pause battery playback" : "Play battery playback"
          }
          onClick={() => {
            if (hour >= 24) setHour(0);
            setPlaying((value) => !value);
          }}
        >
          {playing ? (
            <Pause data-icon="inline-start" />
          ) : (
            <Play data-icon="inline-start" />
          )}
          {playing ? "Pause" : "Play"}
        </Button>
        <Button
          variant="ghost"
          aria-label="Restart battery playback"
          onClick={() => {
            setHour(0);
            setPlaying(false);
          }}
        >
          <RotateCcw data-icon="inline-start" />
          Restart
        </Button>
        <span>1 step = 1 modeled hour</span>
      </div>
      <label id={`${sliderId}-label`} className="sr-only">
        Simulation time
      </label>
      <Slider
        aria-labelledby={`${sliderId}-label`}
        thumbLabel="Simulation time"
        min={0}
        max={24}
        step={1}
        value={[hour]}
        onValueChange={(value) => {
          setPlaying(false);
          setHour(Array.isArray(value) ? value[0] : value);
        }}
      />
      <div className="battery-time-labels" aria-hidden="true">
        {[0, 6, 12, 18, 24].map((t) => (
          <span key={t}>{timeLabel(t)}</span>
        ))}
      </div>
      </div>
      <p className="battery-method-note">
        Hourly values only; fill movement is visual. Not a live battery reading.
        {recovered.effective_config.battery_capacity_kwh !==
        result.effective_config.battery_capacity_kwh
          ? " Capacities differ: compare stored kWh as well as percentages."
          : ""}
      </p>
      <Disclosure
        title="Equipment and exact energy details"
        className="battery-details"
        keepMounted={false}
      >
        <p>
          No sub-hour simulation. Capacity is the size of the battery; stored
          kWh is the energy available. Each scenario’s percentage uses its own
          capacity. The dashed line marks its absolute reserve target.
        </p>
        {visible.map((s) => (
          <div key={s.label} className="battery-exact-details">
            <h4>
              {s.label} · {timeLabel(hour)}
            </h4>
            <p>
              {batteryAt(s.plan, hour).toFixed(6)} kWh stored /{" "}
              {s.simulation.effective_config.battery_capacity_kwh} kWh capacity.
              Reserve: {s.simulation.effective_config.reserve_kwh} kWh. Minimum:{" "}
              {s.plan.metrics.min_soc_kwh.toFixed(6)} kWh. Essential unmet:{" "}
              {s.plan.metrics.critical_unserved_kwh.toFixed(6)} kWh. Flexible
              work deferred against this scenario’s request:{" "}
              {s.plan.metrics.flexible_deferred_kwh.toFixed(6)} kWh.
            </p>
            {hour === 24 ? (
              <p>End of day; no equipment slot selected.</p>
            ) : (
              <>
                <p>
                  Activity in {timeLabel(hour)}–{timeLabel(hour + 1)}. Served
                  energy is not proof of medical-cycle completion.
                </p>
                <ul>
                  {s.simulation.equipment.map((e) => {
                    const requested =
                      e.category === "critical"
                        ? e.required_hours.includes(hour)
                          ? e.power_kw
                          : 0
                        : (s.plan.flexible_tasks
                            .find((t) => t.task_id === e.id)
                            ?.allocations.find((a) => a.hour === hour)
                            ?.served_kwh ?? 0);
                    return requested > 1e-6 ? (
                      <li key={e.id}>
                        {shortName(e.name)}: {requested.toFixed(3)} kWh{" "}
                        {e.category === "critical"
                          ? "required (essential)"
                          : "scheduled and served"}
                      </li>
                    ) : null;
                  })}
                </ul>
                <p>
                  Essential energy served this hour:{" "}
                  {s.plan.hourly[hour].critical_served_kwh.toFixed(6)} of{" "}
                  {s.plan.hourly[hour].critical_requested_kwh.toFixed(6)} kWh
                  requested.
                </p>
              </>
            )}
          </div>
        ))}
      </Disclosure>
    </section>
  );
}
