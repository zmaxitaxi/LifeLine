import { CloudOff } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import type {
  PlanningStatus,
  SimulationResponse,
} from "../../../contracts/api";
import type { Draft } from "../lib/clinic";
import { Disclosure } from "@/components/Disclosure";

export function WeatherContext({
  draft,
  status,
  statusError,
  result,
  onChange,
}: {
  draft: Draft;
  status: PlanningStatus | null;
  statusError: boolean;
  result: SimulationResponse | null;
  onChange: (d: Draft) => void;
}) {
  const sunshine =
    (draft.clouds.slice(6, 18).reduce((sum, c) => sum + c, 0) / 12) *
    draft.weather;
  const conditions =
    sunshine > 70
      ? "strong sunshine"
      : sunshine > 30
        ? "reduced sunshine"
        : "little sunshine";
  return (
    <Alert
      className="weather-context"
      role="region"
      aria-label="Weather availability and source"
    >
      <CloudOff aria-hidden="true" />
      <AlertTitle>Live forecast unavailable</AlertTitle>
      <AlertDescription>
        <p>
          {statusError ? "Forecast availability could not be checked. " : ""}Use
          an example day to explore a plan.
        </p>
        <label className="weather-choice">
          Weather for this plan
          <NativeSelect
            className="w-full"
            aria-label="Weather for this plan"
            value={draft.dataset}
            onChange={(e) =>
              onChange({
                ...draft,
                dataset: e.target.value as Draft["dataset"],
                weather: 100,
                clouds: Array(24).fill(1),
              })
            }
          >
            <NativeSelectOption value="synthetic">
              Demonstration sunshine
            </NativeSelectOption>
            <NativeSelectOption value="kisumu-2025-01-14">
              Historical weather · NASA · 14 Jan 2025
            </NativeSelectOption>
          </NativeSelect>
        </label>
        <p className="weather-provenance">
          {draft.dataset === "synthetic"
            ? `Example: ${conditions}. Source: LifeLine synthetic daylight model.`
            : "Historical sunshine · 14 Jan 2025. Source: NASA POWER."}
        </p>
        <Disclosure className="weather-metadata" title="Forecast details">
          <p>
            No live forecast provider is connected. Requested day:{" "}
            {status?.forecast.requested_date ?? "tomorrow"}. Live forecast date:
            unavailable. Last forecast update: unavailable.
          </p>
          <p>
            {Math.round(sunshine)}% of the selected daylight profile.{" "}
            {result
              ? "Energy sufficiency is modeled below; it is not a measurement. "
              : ""}
            Historical weather is satellite-derived irradiance, not clinic
            measurements. Solar production is approximated; tilt and shading are
            omitted.
          </p>
        </Disclosure>
      </AlertDescription>
    </Alert>
  );
}
