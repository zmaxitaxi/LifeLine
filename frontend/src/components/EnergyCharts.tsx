import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  CartesianGrid,
  AreaChart,
  Area,
  Legend,
} from "recharts";
import type { SimulationResponse } from "../../../contracts/api";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
export function EnergyCharts({ result }: { result: SimulationResponse }) {
  const battery = Array.from({ length: 25 }, (_, h) => ({
    hour: h,
    ...Object.fromEntries(
      ["baseline", "heuristic", "optimized"].map((k) => {
        const p = result[k as "baseline"];
        return [
          k,
          h === 0 ? p.hourly[0].soc_start_kwh : p.hourly[h - 1].soc_end_kwh,
        ];
      }),
    ),
  }));
  const forecast = result.optimized.hourly.map((h) => ({
    hour: h.hour,
    solar: h.pv_kwh,
    critical: h.critical_requested_kwh,
    flexible: h.flexible_served_kwh,
  }));
  return (
    <section className="section charts">
      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Battery through the day</h2>
          </CardTitle>
          <CardDescription>
            Stored energy (kWh) · 25 boundaries, including midnight
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className="chart"
            role="img"
            aria-label="Battery energy comparison with reserve target"
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={battery}
                margin={{ left: -20, right: 15, top: 12, bottom: 0 }}
              >
                <CartesianGrid vertical={false} stroke="#e4eae6" />
                <XAxis
                  dataKey="hour"
                  tickLine={false}
                  axisLine={false}
                  ticks={[0, 6, 12, 18, 24]}
                />
                <YAxis tickLine={false} axisLine={false} />
                <Tooltip
                  formatter={(v) => `${Number(v).toFixed(3)} kWh`}
                  labelFormatter={(h) => `${String(h).padStart(2, "0")}:00`}
                />
                <ReferenceLine
                  y={result.effective_config.reserve_kwh}
                  stroke="#bb862d"
                  strokeDasharray="4 4"
                  label={{
                    value: "Reserve",
                    position: "insideTopRight",
                    fill: "#936317",
                    fontSize: 11,
                  }}
                />
                <Line
                  type="linear"
                  dataKey="baseline"
                  name="Existing"
                  stroke="#687f92"
                  strokeWidth={2}
                  dot={false}
                  strokeDasharray="5 3"
                />
                <Line
                  type="linear"
                  dataKey="heuristic"
                  name="Sunshine-first"
                  stroke="#b58433"
                  dot={false}
                  strokeWidth={2}
                  strokeDasharray="2 4"
                />
                <Line
                  type="linear"
                  dataKey="optimized"
                  name="LifeLine"
                  stroke="#117457"
                  strokeWidth={3}
                  dot={false}
                />
                <Legend iconType="plainline" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Solar and equipment demand</h2>
          </CardTitle>
          <CardDescription>
            Energy in each hour (kWh) · critical demand is requested
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className="chart"
            role="img"
            aria-label="Solar generation and requested critical demand"
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={forecast}
                margin={{ left: -20, right: 15, top: 12, bottom: 0 }}
              >
                <CartesianGrid vertical={false} stroke="#e4eae6" />
                <XAxis
                  dataKey="hour"
                  tickLine={false}
                  axisLine={false}
                  ticks={[0, 6, 12, 18, 23]}
                />
                <YAxis axisLine={false} tickLine={false} />
                <Tooltip formatter={(v) => `${Number(v).toFixed(3)} kWh`} />
                <Area
                  type="linear"
                  dataKey="solar"
                  name="Solar"
                  stroke="#99761e"
                  fill="#f5eaca"
                  fillOpacity={0.65}
                />
                <Area
                  type="linear"
                  dataKey="critical"
                  name="Critical requested"
                  stroke="#667d94"
                  fill="#dfe7ec"
                  fillOpacity={0.4}
                />
                <Area
                  type="linear"
                  dataKey="flexible"
                  name="Flexible served"
                  stroke="#117457"
                  fill="#d1e9df"
                  fillOpacity={0.4}
                />
                <Legend />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
