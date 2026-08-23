export type RunStatus = "PASS" | "HOLD" | "QUEUED" | "READY"
export type StageStatus = "complete" | "current" | "queued"
export type CommandEntryAuthor = "OPERATOR" | "DEVIN" | "SYSTEM"
export type FindingKind = "vibration" | "temperature"
export type SimulatorPlanner = "devin" | "baseline"
export type SimulatorState = "idle" | "ready" | "starting" | "running" | "complete" | "failed"
export type SectionId =
  | "active-run"
  | "live-simulator"
  | "inspection-record"
  | "engine"
  | "telemetry"
  | "findings"
  | "previous-runs"

export interface Stage {
  id: number
  title: string
  status: StageStatus
  result: RunStatus
  description?: string
  detail: string
  telemetry: string
  action: string
}

export interface MetricItem {
  label: string
  value: string
  detail?: string
  emphasis?: boolean
}

export interface TelemetryPoint {
  time: string
  vibration: number
  temperature: number
  pressure: number
  thrust: number
  fuel: number
}

export interface TelemetryTrace {
  id: keyof Omit<TelemetryPoint, "time">
  label: string
  unit: string
  color: string
  threshold: string
}

export interface Finding {
  id: string
  kind: FindingKind
  title: string
  status: RunStatus
  component: string
  observed: string
  threshold: string
  captured: string
}

export interface PreviousRun {
  id: string
  engine: string
  health: string
  readiness: RunStatus
  elapsed: string
  findings: string
  captured: string
  current?: boolean
}

export interface CommandEntry {
  id: string
  author: CommandEntryAuthor
  timestamp: string
  message: string
  status: string
  alert?: boolean
}

export interface SimulatorMessage {
  source: "aeroloop-simulator"
  type: "ready" | "starting" | "accepted" | "progress" | "complete" | "failed"
  message?: string
  stage?: string
  disposition?: string
  inspectedCount?: number
  waypointCount?: number
  planner?: string
  devinAvailable?: boolean
}

export interface AeroLoopData {
  stages: Stage[]
  metrics: MetricItem[]
  traces: TelemetryTrace[]
  traceData: TelemetryPoint[]
  findings: Finding[]
  previousRuns: PreviousRun[]
  initialEntries: CommandEntry[]
}

export interface AeroLoopAppProps {
  data?: AeroLoopData
}
