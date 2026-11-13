import { useEffect, useRef, useState } from "react";
import { CloudSun, LoaderCircle } from "lucide-react";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Disclosure } from "./Disclosure";
import { ScheduleOverview } from "./ScheduleOverview";
import { DetailedAnalysis } from "./DetailedAnalysis";
import { api, num } from "@/lib/clinic";
import type { SimulationRequest } from "../../../contracts/api";
import type {
  ForecastPlanResponse,
  GuidedForecastResponse,
  SolarForecast,
} from "../../../contracts/forecast";

interface LocationOption {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
}
const QUESTION =
  "Can our clinic safely operate tomorrow given the weather forecast?";

export function ForecastProvenance({ forecast }: { forecast: SolarForecast }) {
  return (
    <div
      className="space-y-2 text-sm text-muted-foreground"
      data-testid="forecast-provenance"
    >
      <p>
        <a
          href={forecast.attribution_url}
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          Weather data by Open-Meteo.com
        </a>{" "}
        · Weather-model forecast, not observations.
      </p>
      <p>
        Requested location: {forecast.requested_location.latitude},{" "}
        {forecast.requested_location.longitude}. Model grid:{" "}
        {forecast.model_grid_location.latitude},{" "}
        {forecast.model_grid_location.longitude}.
      </p>
      <p>
        Dates: {forecast.days.map((d) => d.date).join(" / ")} · Timezone:{" "}
        {forecast.timezone}
      </p>
      <p>
        Retrieved:{" "}
        <time dateTime={forecast.retrieved_at}>{forecast.retrieved_at}</time> ·{" "}
        {forecast.cache_status === "stale"
          ? "STALE cached forecast"
          : forecast.cache_status === "cached"
            ? "Cached forecast"
            : "Live retrieval"}
      </p>
      <p>
        <a
          className="underline"
          href={forecast.source_url}
          target="_blank"
          rel="noreferrer"
        >
          Provider request
        </a>{" "}
        ·{" "}
        <a
          className="underline"
          href={forecast.licence_url}
          target="_blank"
          rel="noreferrer"
        >
          CC BY 4.0
        </a>
        . Radiation converted to estimated PV energy by LifeLine.
      </p>
    </div>
  );
}

export function ForecastResults({ result }: { result: ForecastPlanResponse }) {
  const cases = [
    { sunshine_factor: 1, plan: result.plan },
    ...result.uncertainty_cases,
  ];
  return (
    <div className="space-y-5" data-testid="forecast-plan-result">
      <p className="text-sm text-muted-foreground">
        Forecast for {result.planning_date} · {result.forecast.timezone} ·{" "}
        {result.forecast.requested_location.latitude},{" "}
        {result.forecast.requested_location.longitude}. Retrieved{" "}
        {result.forecast.retrieved_at} ({result.forecast.cache_status}).{" "}
        <a
          className="underline"
          href={result.forecast.attribution_url}
          target="_blank"
          rel="noreferrer"
        >
          Weather data by Open-Meteo.com
        </a>
        .
      </p>
      {result.forecast.cache_status === "stale" ? (
        <Alert className="border-amber-400 bg-amber-50 text-amber-950">
          <AlertTitle>Using a stale forecast</AlertTitle>
          <AlertDescription>{result.forecast.warnings[0]}</AlertDescription>
        </Alert>
      ) : null}
      <Alert
        variant={
          result.plan.status === "CRITICAL_SHORTAGE" ? "destructive" : "default"
        }
        className={
          result.plan.status === "RESERVE_AT_RISK"
            ? "border-amber-400 bg-amber-50 text-amber-950"
            : undefined
        }
      >
        <AlertTitle>
          <h3>Computed plan for {result.planning_date}</h3>
        </AlertTitle>
        <AlertDescription>
          <p>{result.assessment}</p>
          <p>
            {result.initial_battery_basis} Assumed charge:{" "}
            {num(result.midnight_battery_kwh)} kWh.
          </p>
        </AlertDescription>
      </Alert>
      <ol className="list-decimal space-y-2 pl-5 text-sm">
        {result.actions.slice(0, 3).map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ol>
      <ScheduleOverview result={result.plan} id="forecast-schedule" />
      <div>
        <h3 className="mb-2">What if sunshine is lower?</h3>
        <p className="mb-3 text-sm text-muted-foreground">
          Same equipment, starting battery, and physical limits. Only forecast
          sunlight changes. These are sensitivity cases, not probabilities.
        </p>
        <Table aria-label="Forecast uncertainty comparison">
          <TableHeader>
            <TableRow>
              <TableHead>Solar case</TableHead>
              <TableHead>Solar (kWh)</TableHead>
              <TableHead>Essential coverage</TableHead>
              <TableHead>Minimum battery (kWh)</TableHead>
              <TableHead>Work deferred (kWh)</TableHead>
              <TableHead>Essential unmet (kWh)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {cases.map(({ sunshine_factor: factor, plan }) => (
              <TableRow key={factor}>
                <TableHead scope="row">
                  {factor === 1
                    ? "Forecast"
                    : `${Math.round((1 - factor) * 100)}% lower sunshine`}
                </TableHead>
                <TableCell>
                  {num(plan.optimized.metrics.total_solar_kwh)}
                </TableCell>
                <TableCell>
                  {plan.optimized.metrics.critical_coverage_pct === null
                    ? "N/A"
                    : `${num(plan.optimized.metrics.critical_coverage_pct, 1)}%`}
                </TableCell>
                <TableCell>{num(plan.optimized.metrics.min_soc_kwh)}</TableCell>
                <TableCell>
                  {num(plan.optimized.metrics.flexible_deferred_kwh)}
                </TableCell>
                <TableCell>
                  {num(plan.optimized.metrics.critical_unserved_kwh)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Disclosure title="Forecast detailed analysis" keepMounted={false}>
        <DetailedAnalysis result={result.plan} idPrefix="forecast-" />
      </Disclosure>
      <Disclosure title="Forecast assumptions, limitations and provenance">
        <ForecastProvenance forecast={result.forecast} />
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm">
          {result.limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      </Disclosure>
    </div>
  );
}

/** Independent module so the concurrent UI work can reuse it without redesign. */
export function LiveForecastPlanner({
  clinic,
  onPlan,
  questionPrompt,
}: {
  clinic: SimulationRequest;
  onPlan?: (result: ForecastPlanResponse, answer?: string) => void;
  questionPrompt?: { text: string; id: number } | null;
}) {
  const [locations, setLocations] = useState<LocationOption[]>([]);
  const [selected, setSelected] = useState("kisumu");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [midnight, setMidnight] = useState(
    clinic.initial_battery_kwh?.toString() ?? "",
  );
  const [confirmed, setConfirmed] = useState(false);
  const [day, setDay] = useState<"today" | "tomorrow">("tomorrow");
  const [question, setQuestion] = useState(QUESTION);
  const [forecast, setForecast] = useState<SolarForecast | null>(null);
  const [result, setResult] = useState<ForecastPlanResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const abort = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const signature = JSON.stringify(clinic);
  useEffect(() => {
    if (questionPrompt) {
      setQuestion(questionPrompt.text);
      setDay("tomorrow");
    }
  }, [questionPrompt]);
  useEffect(() => {
    const controller = new AbortController();
    api<{ locations: LocationOption[] }>(
      "forecast/locations",
      undefined,
      controller.signal,
    )
      .then((r) => {
        setLocations(r.locations);
        const first = r.locations[0];
        if (first) {
          setLatitude(String(first.latitude));
          setLongitude(String(first.longitude));
        }
      })
      .catch((e) => {
        if (e.name !== "AbortError")
          setError(
            "Could not load location examples. You can enter coordinates manually.",
          );
      });
    return () => {
      controller.abort();
      abort.current?.abort();
    };
  }, []);
  useEffect(() => {
    ++sequence.current;
    abort.current?.abort();
    setBusy(false);
    setResult(null);
    setMessage("");
  }, [signature, latitude, longitude, midnight, day, question]);
  useEffect(() => {
    setForecast(null);
  }, [latitude, longitude]);
  useEffect(() => {
    setConfirmed(false);
  }, [signature, midnight, day]);

  async function run(plan: boolean) {
    const lat = Number(latitude),
      lon = Number(longitude),
      charge = Number(midnight);
    if (
      !latitude.trim() ||
      !longitude.trim() ||
      !Number.isFinite(lat) ||
      !Number.isFinite(lon) ||
      Math.abs(lat) > 90 ||
      Math.abs(lon) > 180
    ) {
      setError(
        "Enter a latitude from −90 to 90 and a longitude from −180 to 180.",
      );
      return;
    }
    if (
      plan &&
      (!confirmed || !midnight.trim() || !Number.isFinite(charge) || charge < 0)
    ) {
      setError(
        "Enter and confirm the assumed battery energy at local midnight. This is not automatically today’s current charge.",
      );
      return;
    }
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    const current = ++sequence.current;
    setBusy(true);
    setError("");
    setMessage("");
    setResult(null);
    try {
      if (!plan) {
        const f = await api<SolarForecast>(
          `forecast?latitude=${lat}&longitude=${lon}`,
          undefined,
          controller.signal,
        );
        if (current === sequence.current) setForecast(f);
      } else {
        // Today uses the same validated planning endpoint; tomorrow's primary
        // question demonstrates the structured tool-driven guided fallback.
        const body = {
          clinic,
          latitude: lat,
          longitude: lon,
          day,
          midnight_battery_kwh: charge,
          reduced_sunshine_factors: [0.75, 0.5],
        };
        let output: ForecastPlanResponse | null;
        let answer: string | undefined;
        if (day === "tomorrow") {
          const response = await api<GuidedForecastResponse>(
            "planner/ask",
            { ...body, question },
            controller.signal,
          );
          if (current !== sequence.current) return;
          setMessage(response.message);
          answer = response.message;
          output = response.result;
        } else
          output = await api<ForecastPlanResponse>(
            "forecast/plan",
            body,
            controller.signal,
          );
        if (current === sequence.current && output) {
          setForecast(output.forecast);
          setResult(output);
          onPlan?.(output, answer);
        }
      }
    } catch (e) {
      if (
        e instanceof Error &&
        e.name !== "AbortError" &&
        current === sequence.current
      ) {
        setForecast(null);
        setError(
          e.message +
            " Historical NASA and synthetic examples remain available in the main planner.",
        );
      }
    } finally {
      if (current === sequence.current) setBusy(false);
    }
  }
  return (
    <Card
      id="live-forecast"
      className="my-5"
      aria-label="Live weather planning"
    >
      <CardHeader>
        <CardTitle>
          <h2 className="flex items-center gap-2">
            <CloudSun />
            Plan with live weather
          </h2>
        </CardTitle>
        <CardDescription>
          Open-Meteo today/tomorrow forecasts replace example sunshine, using
          this clinic’s equipment and physical limits. Guided planning is
          deterministic; no hosted language model is connected.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <FieldGroup className="grid gap-4 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="forecast-location">Clinic location</FieldLabel>
            <NativeSelect
              id="forecast-location"
              value={selected}
              onChange={(e) => {
                setSelected(e.target.value);
                const location = locations.find((l) => l.id === e.target.value);
                if (location) {
                  setLatitude(String(location.latitude));
                  setLongitude(String(location.longitude));
                }
              }}
            >
              {locations.map((l) => (
                <NativeSelectOption key={l.id} value={l.id}>
                  {l.name}
                </NativeSelectOption>
              ))}
              <NativeSelectOption value="custom">
                Enter coordinates
              </NativeSelectOption>
            </NativeSelect>
          </Field>
          <Field>
            <FieldLabel htmlFor="forecast-day">Planning day</FieldLabel>
            <NativeSelect
              id="forecast-day"
              value={day}
              onChange={(e) => setDay(e.target.value as "today" | "tomorrow")}
            >
              <NativeSelectOption value="today">
                Today · whole calendar day
              </NativeSelectOption>
              <NativeSelectOption value="tomorrow">Tomorrow</NativeSelectOption>
            </NativeSelect>
          </Field>
          <Field>
            <FieldLabel htmlFor="forecast-latitude">Clinic latitude</FieldLabel>
            <Input
              id="forecast-latitude"
              inputMode="decimal"
              value={latitude}
              onChange={(e) => {
                setLatitude(e.target.value);
                setSelected("custom");
              }}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="forecast-longitude">
              Clinic longitude
            </FieldLabel>
            <Input
              id="forecast-longitude"
              inputMode="decimal"
              value={longitude}
              onChange={(e) => {
                setLongitude(e.target.value);
                setSelected("custom");
              }}
            />
          </Field>
        </FieldGroup>
        <Button
          type="button"
          variant="outline"
          disabled={busy}
          onClick={() => void run(false)}
        >
          Fetch today and tomorrow’s forecast
        </Button>
        {forecast ? <ForecastProvenance forecast={forecast} /> : null}
        {forecast?.warnings.map((w, i) => (
          <p key={i} className="text-sm text-muted-foreground">
            {w}
          </p>
        ))}
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="midnight-charge">
              Assumed battery energy at local midnight (kWh)
            </FieldLabel>
            <Input
              id="midnight-charge"
              inputMode="decimal"
              value={midnight}
              onChange={(e) => setMidnight(e.target.value)}
            />
            <p className="text-sm text-muted-foreground">
              For tomorrow, enter a reviewed assumption for tomorrow at 00:00.
              This is not a prediction from today’s current charge.
            </p>
          </Field>
        </FieldGroup>
        <label className="flex flex-row items-center gap-3 text-sm">
          <Checkbox
            checked={confirmed}
            onCheckedChange={setConfirmed}
            aria-label="Confirm midnight battery assumption"
          />
          <span>I reviewed the midnight battery assumption.</span>
        </label>
        {day === "tomorrow" ? (
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="forecast-question">
                Ask about tomorrow’s weather
              </FieldLabel>
              <textarea
                id="forecast-question"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={2}
                maxLength={2000}
                className="w-full rounded-md border border-input bg-card p-3 text-sm"
              />
            </Field>
          </FieldGroup>
        ) : null}
        <Button
          type="button"
          disabled={busy || !confirmed}
          onClick={() => void run(true)}
        >
          {busy ? <LoaderCircle className="animate-spin" /> : null}Calculate
          forecast-backed plan
        </Button>
        {busy ? (
          <p role="status">Retrieving forecast and running the energy model…</p>
        ) : null}
        {error ? (
          <Alert variant="destructive">
            <AlertTitle>Forecast plan unavailable</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        {message ? (
          <p role="status" className="text-sm">
            {message}
          </p>
        ) : null}
        {result ? <ForecastResults result={result} /> : null}
      </CardContent>
    </Card>
  );
}
