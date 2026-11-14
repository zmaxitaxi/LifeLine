import { useEffect, useRef, useState } from "react";
import {
  Sun,
  Moon,
  CloudSun,
  CloudMoon,
  Cloud,
  CloudFog,
  CloudDrizzle,
  CloudRain,
  CloudSnow,
  CloudLightning,
  CircleHelp,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/Disclosure";
import { api } from "@/lib/clinic";
import type { ForecastLocation } from "../../../../contracts/forecast";
import type {
  WeatherCondition,
  WeatherOutlook,
} from "../../../../contracts/weather";
import type { ComputedPlan } from "../../../../contracts/planning";
import type { RecoveryOption } from "../../../../contracts/recovery";
import { WeatherEnergy } from "./WeatherEnergy";
const icons: Record<WeatherCondition, LucideIcon> = {
  clear: Sun,
  mainly_clear: Sun,
  partly_cloudy: CloudSun,
  overcast: Cloud,
  fog: CloudFog,
  drizzle: CloudDrizzle,
  freezing_drizzle: CloudDrizzle,
  rain: CloudRain,
  freezing_rain: CloudRain,
  snow: CloudSnow,
  rain_showers: CloudRain,
  snow_showers: CloudSnow,
  thunderstorm: CloudLightning,
  unavailable: CircleHelp,
};
const temperature = (value: number | null) =>
  value == null ? "—" : `${Math.round(value)}°`;
export function WeatherSection({ location, date, computed, selected }: { location: ForecastLocation; date: string; computed: ComputedPlan | null; selected?: RecoveryOption }) {
  const energyDetails = useRef<HTMLDivElement>(null);
  const [selectedDate, setSelectedDate] = useState(date);
  const [outlook, setOutlook] = useState<WeatherOutlook | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const abort = new AbortController();
    setLoading(true);
    setError("");
    setOutlook(null);
    void api<WeatherOutlook>(
      `weather/outlook?latitude=${location.latitude}&longitude=${location.longitude}`,
      undefined,
      abort.signal,
    )
      .then((data) => {
        if (!abort.signal.aborted) setOutlook(data);
      })
      .catch((reason) => {
        if (!abort.signal.aborted)
          setError(
            reason instanceof Error
              ? reason.message
              : "Weather connection unavailable",
          );
      })
      .finally(() => {
        if (!abort.signal.aborted) setLoading(false);
      });
    return () => abort.abort();
  }, [location.latitude, location.longitude, retry]);
  const CurrentIcon = outlook
    ? outlook.current.is_day === false &&
      ["clear", "mainly_clear"].includes(outlook.current.condition)
      ? Moon
      : outlook.current.is_day === false && outlook.current.condition === "partly_cloudy" ? CloudMoon : icons[outlook.current.condition]
    : Cloud;
  return (
    <section
      data-overview-section="weather"
      className="overview-section overview-square"
      aria-labelledby="weather-title"
      tabIndex={0}
    >
      <h2 id="weather-title">Weather</h2>
      <div className="overview-square-body">
        {loading ? (
          <p role="status" className="panel-lead">
            Checking weather…
          </p>
        ) : outlook ? (
          <>
            <div className="current-weather" aria-label="Current weather">
              <CurrentIcon aria-hidden="true" />
              <div>
                <strong>
                  {temperature(outlook.current.temperature_c)}
                  <small>C</small>
                </strong>
                <span>{outlook.current.description}</span>
              </div>
            </div>
            {outlook.cache_status === "stale" ? (
              <p className="panel-attention">
                Older forecast · update when connected
              </p>
            ) : null}
            <div className="weekly-weather" aria-label="Seven-day forecast">
              {outlook.days.map((day) => {
                const Icon = icons[day.condition];
                const label = new Intl.DateTimeFormat("en", {
                  weekday: "short",
                  timeZone: "UTC",
                }).format(new Date(`${day.date}T12:00:00Z`));
                return (
                  <button type="button"
                    key={day.date}
                    aria-pressed={selectedDate === day.date}
                    onClick={() => { setSelectedDate(day.date); requestAnimationFrame(() => energyDetails.current?.scrollIntoView({ block: "nearest" })); }}
                    className="weather-day"
                    title={`${day.date}: ${day.description}`}
                    aria-label={`${label}, ${day.description}, high ${temperature(day.temperature_max_c)}, low ${temperature(day.temperature_min_c)}`}
                  >
                    <strong>{label}</strong>
                    <Icon aria-hidden="true" />
                    <span>{temperature(day.temperature_max_c)}</span>
                    <small>{temperature(day.temperature_min_c)}</small>
                  </button>
                );
              })}
            </div>
            <div ref={energyDetails}><WeatherEnergy key={`${selectedDate}-${computed?.generation}`} day={selectedDate} planningDate={date} computed={computed} selected={selected} /></div>
            <Disclosure title="Weather details" keepMounted={false}>
              <p>
                <a
                  href={outlook.attribution_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {outlook.source}
                </a>{" "}
                · {outlook.cache_status} · updated{" "}
                {new Intl.DateTimeFormat("en", {
                  dateStyle: "medium",
                  timeStyle: "short",
                  timeZone: outlook.timezone,
                }).format(new Date(outlook.retrieved_at))}{" "}
                ({outlook.timezone}).
              </p>
              <p>
                Current conditions and the week ahead are weather-model
                estimates, not station measurements. The electricity plan uses
                its own hourly solar forecast.
              </p>
              <ul>
                {outlook.days.map((day) => (
                  <li key={day.date}>
                    {day.date}: {day.description}. High{" "}
                    {temperature(day.temperature_max_c)}C, low{" "}
                    {temperature(day.temperature_min_c)}C; rain chance{" "}
                    {day.precipitation_probability_pct == null
                      ? "unavailable"
                      : `${day.precipitation_probability_pct}%`}
                    .
                  </li>
                ))}
              </ul>
              {outlook.warnings.length ? (
                <ul>
                  {outlook.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              ) : null}
            </Disclosure>
          </>
        ) : (
          <div role="status">
            <p className="panel-lead">Weather is unavailable.</p>
            <Button
              variant="outline"
              onClick={() => setRetry((value) => value + 1)}
            >
              Retry weather
            </Button>
            <Disclosure title="Connection details" keepMounted={false}>
              <p>{error}</p>
            </Disclosure>
          </div>
        )}
      </div>
    </section>
  );
}
