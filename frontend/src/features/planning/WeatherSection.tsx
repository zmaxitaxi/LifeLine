import { CloudSun, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Disclosure } from "@/components/Disclosure";
import type { SolarForecast } from "../../../../contracts/forecast";
import type { SimulationResponse } from "../../../../contracts/api";
import { num } from "@/lib/clinic";

export function WeatherSection({
  forecast,
  simulation,
  date,
  loading,
  error,
  onRetry,
}: {
  forecast: SolarForecast | null;
  simulation: SimulationResponse | null;
  date: string | null;
  loading: boolean;
  error: string;
  onRetry: () => void;
}) {
  return (
    <section
      data-overview-section="weather"
      className="overview-section"
      aria-labelledby="weather-title"
    >
      <h2 id="weather-title">Weather</h2>
      {loading ? <p role="status">Checking the weather forecast…</p> : null}
      {error ? (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>Live weather is unavailable</AlertTitle>
          <AlertDescription>
            {error} No replacement forecast has been invented.
            <Button variant="outline" onClick={onRetry}>
              Retry weather
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}
      {forecast ? (
        <>
          <p>
            <CloudSun aria-hidden="true" className="inline-weather-icon" />
            {date ?? "Forecast"} · {forecast.timezone}
          </p>
          <p>
            <a href={forecast.attribution_url} target="_blank" rel="noreferrer">
              {forecast.source}
            </a>{" "}
            · {forecast.cache_status} · updated {forecast.retrieved_at}
          </p>
          {forecast.cache_status === "stale" ? (
            <p className="inline-warning">
              This cached forecast is stale. Review the update time before
              relying on this plan.
            </p>
          ) : null}
          <p>
            Sunshine can differ from the forecast. These are weather-model
            estimates, not measured clinic conditions.
          </p>
          {forecast.warnings.length ? (
            <ul>
              {forecast.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
          <Disclosure
            title="Hourly solar generation estimates"
            keepMounted={false}
          >
            {simulation ? (
              <>
                <p>
                  Simulated electricity from the solar panels for {date}. These
                  values come from the calculated plan.
                </p>
                <div className="hourly-solar-list">
                  <table>
                    <caption className="sr-only">
                      Hourly modeled solar electricity
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Hour</th>
                        <th scope="col">Estimated electricity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {simulation.optimized.hourly.map((h) => (
                        <tr key={h.hour}>
                          <th scope="row">
                            {String(h.hour).padStart(2, "0")}:00
                          </th>
                          <td>{num(h.pv_kwh)} kWh</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p>
                Calculate a current plan to see hourly solar electricity
                estimates. A weather forecast alone is not a calculated energy
                plan.
              </p>
            )}
          </Disclosure>
        </>
      ) : !loading && !error ? (
        <p>No forecast has been retrieved yet.</p>
      ) : null}
    </section>
  );
}
