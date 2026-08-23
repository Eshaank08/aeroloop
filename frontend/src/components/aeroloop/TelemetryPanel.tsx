import { LineChart, Line, ReferenceLine, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import type { TelemetryPoint, TelemetryTrace } from "@/types/aeroloop"

interface TelemetryPanelProps {
  traceData: TelemetryPoint[]
  traces: TelemetryTrace[]
}

const chartConfig: ChartConfig = {
  vibration: { label: "Vibration", color: "#FFCD82" },
  temperature: { label: "Temperature", color: "#FFF8ED" },
  pressure: { label: "Pressure", color: "#ADDBFF" },
  thrust: { label: "Thrust", color: "#6CB8D9" },
  fuel: { label: "Fuel flow", color: "#C88D43" },
}

const normalizedPoint = (point: TelemetryPoint) => ({
  time: point.time,
  vibration: point.vibration / 8,
  temperature: (point.temperature - 700) / 100,
  pressure: (point.pressure - 190) / 80,
  thrust: (point.thrust - 70) / 30,
  fuel: (point.fuel - 1.4) / 0.6,
})

export function TelemetryPanel({ traceData, traces }: TelemetryPanelProps) {
  const chartData = traceData.map(normalizedPoint)

  return (
    <section className="telemetry-surface relative border-b border-aero-brown px-8 py-12" id="telemetry">
      <div className="flex items-end justify-between border-b border-aero-paper/25 pb-4">
        <div>
          <p className="aero-mono text-[10px] uppercase tracking-[.2em] text-aero-sun">04 / Recorded flight data</p>
          <h2 className="aero-display mt-2 text-[44px] font-semibold leading-none">Telemetry, one time cursor</h2>
        </div>
        <div className="text-right aero-mono text-[9px] uppercase leading-5 text-aero-paper/60">
          12.00 S WINDOW
          <br />
          <span className="text-aero-sun">THRESHOLD BREACH / 14:32:08</span>
        </div>
      </div>
      <div className="telemetry-layout mt-7 grid grid-cols-[135px_1fr] gap-5">
        <div className="telemetry-health border-r border-aero-paper/20 pr-5">
          <p className="aero-mono text-[9px] uppercase text-aero-paper/55">Engine health</p>
          <p className="aero-display mt-2 text-[72px] leading-none text-aero-sun">86</p>
          <p className="aero-mono mt-1 text-[14px] text-aero-paper/55">/100</p>
          <div className="mt-10 space-y-4 border-t border-aero-paper/20 pt-4">
            <div><p className="aero-mono text-[8px] uppercase text-aero-paper/55">Current stage</p><p className="mt-1 text-[12px] font-semibold text-aero-sun">Combustor sweep</p></div>
            <div><p className="aero-mono text-[8px] uppercase text-aero-paper/55">Readiness</p><p className="mt-1 text-[12px] font-semibold text-aero-sun">HOLD</p></div>
            <div><p className="aero-mono text-[8px] uppercase text-aero-paper/55">Findings</p><p className="mt-1 text-[12px] font-semibold">02 recorded</p></div>
          </div>
        </div>
        <div className="telemetry-grid relative min-h-[420px] border border-aero-paper/20 p-4">
          <div className="pointer-events-none absolute inset-x-4 bottom-4 top-4">
            <div className="absolute left-0 right-0 top-[15%] border-t border-dashed border-aero-danger/70" />
            <div className="absolute left-0 right-0 top-[43%] border-t border-dashed border-aero-danger/70" />
            <div className="absolute left-0 right-0 top-[73%] border-t border-dashed border-aero-danger/70" />
            <div className="absolute bottom-0 left-[80%] top-0 border-l border-dashed border-aero-sun" />
          </div>
          <ChartContainer className="relative z-10 h-[380px] w-full" config={chartConfig}>
            <LineChart data={chartData} margin={{ top: 12, right: 0, left: 0, bottom: 18 }}>
              <XAxis dataKey="time" hide /><YAxis domain={[0, 1.05]} hide />
              <ReferenceLine x="14:32:08" stroke="#FFCD82" strokeDasharray="4 6" />
              {traces.map((trace) => <Line activeDot={{ r: 3, fill: trace.color, stroke: "#14293A", strokeWidth: 1 }} dataKey={trace.id} dot={false} key={trace.id} stroke={trace.color} strokeWidth={2.5} type="monotone" />)}
              <ChartTooltip content={<ChartTooltipContent className="border-aero-sun/40 bg-aero-navy text-aero-paper" labelClassName="text-aero-sun" />} />
            </LineChart>
          </ChartContainer>
          <div className="pointer-events-none absolute inset-x-5 top-4 z-20 flex flex-col justify-between text-[10px] text-aero-paper">
            {traces.map((trace) => <span className="aero-mono h-[62px] uppercase" key={trace.id} style={{ color: trace.color }}>{trace.label} / {trace.unit} / {trace.threshold}</span>)}
          </div>
          <span className="absolute right-5 top-4 z-20 aero-mono text-[10px] text-aero-sun">14:32:08</span>
          <div className="absolute bottom-3 left-4 right-4 z-20 flex justify-between aero-mono text-[9px] text-aero-paper/70"><span>14:31:58</span><span>14:32:04</span><span>14:32:16</span></div>
        </div>
      </div>
      <div className="mt-5 border-t border-aero-paper/20 pt-4">
        <div className="flex items-center justify-between aero-mono text-[9px] uppercase tracking-[.13em] text-aero-paper/55"><span>EVENT RAIL / AGENT ACTIONS LINKED TO SAMPLES</span><span>LAST VALID SAMPLE / 14:32:16 UTC</span></div>
        <div className="relative mt-5 h-7 border-t border-aero-paper/30"><span className="absolute left-[13%] top-[-5px] h-2.5 w-2.5 bg-aero-sun" /><span className="absolute left-[52%] top-[-5px] h-2.5 w-2.5 bg-aero-amber" /><span className="absolute right-[20%] top-[-5px] h-2.5 w-2.5 bg-aero-sun" /></div>
        <div className="event-labels flex justify-between aero-mono text-[9px] text-aero-paper/70"><span>14:31:42 / FAN CHECK</span><span className="text-aero-sun">14:32:08 / HOLD</span><span>14:32:16 / EVIDENCE SAVED</span></div>
      </div>
    </section>
  )
}
