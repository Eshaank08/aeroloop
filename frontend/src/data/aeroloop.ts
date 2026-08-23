import type { AeroLoopData, CommandEntry, Finding, MetricItem, PreviousRun, Stage, TelemetryPoint, TelemetryTrace } from "@/types/aeroloop"

export const stages: Stage[] = [
  { id: 1, title: "Intake scan", status: "complete", result: "PASS", detail: "Inlet edge registered.", telemetry: "Pressure · temperature", action: "Route registered" },
  { id: 2, title: "Fan survey", status: "complete", result: "PASS", detail: "Thrust response balanced.", telemetry: "Thrust · fuel flow", action: "Samples saved" },
  { id: 3, title: "Compressor map", status: "complete", result: "PASS", detail: "Axial pressure stable.", telemetry: "Pressure · vibration", action: "Threshold checked" },
  { id: 4, title: "Combustor sweep", status: "current", result: "HOLD", description: "Vibration window under load", detail: "Radial vibration is above threshold. Devin paused the run and preserved the evidence window.", telemetry: "Vibration · pressure · thrust", action: "Evidence captured" },
  { id: 5, title: "Turbine load", status: "queued", result: "QUEUED", detail: "Waiting for operator review.", telemetry: "Temperature · thrust", action: "Waiting" },
  { id: 6, title: "Exhaust profile", status: "queued", result: "QUEUED", detail: "Waiting for release.", telemetry: "Temperature · pressure", action: "Waiting" },
  { id: 7, title: "Evidence closeout", status: "queued", result: "QUEUED", detail: "Final trace not started.", telemetry: "All five traces", action: "Not started" },
]

export const metrics: MetricItem[] = [
  { label: "Mission", value: "AL-208", detail: "Turbofan 02" },
  { label: "Health", value: "86", detail: "/100", emphasis: true },
  { label: "Stage", value: "04 / 07", detail: "Combustor" },
  { label: "Findings", value: "02", detail: "Recorded", emphasis: true },
  { label: "Readiness", value: "HOLD", detail: "Review needed", emphasis: true },
]

export const traces: TelemetryTrace[] = [
  { id: "vibration", label: "VIBRATION", unit: "mm/s", color: "#FFCD82", threshold: "LIMIT 5.0" },
  { id: "temperature", label: "TEMPERATURE", unit: "°C", color: "#FFF8ED", threshold: "LIMIT 780" },
  { id: "pressure", label: "PRESSURE", unit: "kPa", color: "#ADDBFF", threshold: "LIMIT 250" },
  { id: "thrust", label: "THRUST", unit: "kN", color: "#6CB8D9", threshold: "TARGET 92" },
  { id: "fuel", label: "FUEL FLOW", unit: "kg/s", color: "#C88D43", threshold: "NOMINAL 1.8" },
]

export const traceData: TelemetryPoint[] = [
  { time: "14:31:58", vibration: 3.3, temperature: 744, pressure: 214, thrust: 79, fuel: 1.65 },
  { time: "14:32:00", vibration: 4.2, temperature: 748, pressure: 218, thrust: 81, fuel: 1.68 },
  { time: "14:32:02", vibration: 3.7, temperature: 751, pressure: 222, thrust: 83, fuel: 1.7 },
  { time: "14:32:04", vibration: 5.9, temperature: 756, pressure: 229, thrust: 86, fuel: 1.74 },
  { time: "14:32:06", vibration: 4.4, temperature: 761, pressure: 237, thrust: 88, fuel: 1.78 },
  { time: "14:32:08", vibration: 6.8, temperature: 768, pressure: 247, thrust: 90, fuel: 1.82 },
  { time: "14:32:10", vibration: 5.2, temperature: 771, pressure: 245, thrust: 89, fuel: 1.81 },
  { time: "14:32:12", vibration: 4.6, temperature: 774, pressure: 242, thrust: 91, fuel: 1.8 },
  { time: "14:32:16", vibration: 3.9, temperature: 776, pressure: 240, thrust: 92, fuel: 1.79 },
]

export const findings: Finding[] = [
  { id: "EV-208-02", kind: "vibration", title: "High radial vibration", status: "HOLD", component: "Compressor stage 3", observed: "6.8 / 5.0 mm/s", threshold: "limit 5.0", captured: "14:32:08 UTC" },
  { id: "EV-208-01", kind: "temperature", title: "Elevated combustor temperature", status: "HOLD", component: "Annular combustor", observed: "744°C observed", threshold: "780°C threshold", captured: "14:31:58 UTC" },
]

export const previousRuns: PreviousRun[] = [
  { id: "AL-208 · A-17", engine: "Turbofan 02", health: "86 / 100", readiness: "HOLD", elapsed: "14:32", findings: "02", captured: "14:32:08", current: true },
  { id: "AL-207 · A-17", engine: "Turbofan 02", health: "92 / 100", readiness: "READY", elapsed: "11:18", findings: "00", captured: "12:06:41" },
  { id: "AL-206 · B-04", engine: "Turbojet 01", health: "88 / 100", readiness: "READY", elapsed: "09:54", findings: "01", captured: "09:48:27" },
  { id: "AL-205 · B-04", engine: "Turbojet 01", health: "79 / 100", readiness: "HOLD", elapsed: "07:16", findings: "03", captured: "17:21:02" },
]

export const initialEntries: CommandEntry[] = [
  { id: "entry-1", author: "OPERATOR", timestamp: "14:31:42", message: "Run compressor stage 3.", status: "STAGE 03 · ACCEPTED" },
  { id: "entry-2", author: "DEVIN", timestamp: "14:32:08", message: "Vibration crossed threshold. Holding run.", status: "EVIDENCE 14:32:08 · HOLD", alert: true },
  { id: "entry-3", author: "SYSTEM", timestamp: "14:32:16", message: "Trace window attached.", status: "CONTEXT · SAVED" },
]

export const aeroLoopData: AeroLoopData = {
  stages,
  metrics,
  traces,
  traceData,
  findings,
  previousRuns,
  initialEntries,
}
