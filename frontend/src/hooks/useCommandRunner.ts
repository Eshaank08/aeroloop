import { useCallback, useState } from "react"
import { utcTime } from "@/lib/formatters"
import type { CommandEntry, SimulatorMessage, SimulatorPlanner, SimulatorState } from "@/types/aeroloop"

interface UseCommandRunnerOptions {
  initialEntries: CommandEntry[]
  onStart: (command: string, planner: SimulatorPlanner) => void
}

export function useCommandRunner({ initialEntries, onStart }: UseCommandRunnerOptions) {
  const [commandText, setCommandText] = useState("")
  const [isRunning, setIsRunning] = useState(false)
  const [planner, setPlanner] = useState<SimulatorPlanner>("devin")
  const [simulatorState, setSimulatorState] = useState<SimulatorState>("idle")
  const [simulatorMessage, setSimulatorMessage] = useState("Waiting for the simulator.")
  const [contextLabel, setContextLabel] = useState("No context")
  const [entries, setEntries] = useState<CommandEntry[]>(() => initialEntries)

  const start = useCallback(() => {
    const command = commandText.trim()
    if (!command || isRunning) return false

    setIsRunning(true)
    setEntries((current) => [
      ...current,
      {
        id: `command-${Date.now()}`,
        author: "OPERATOR",
        timestamp: utcTime(new Date()),
        message: command,
        status: "STAGE 04 · RUNNING",
      },
    ])
    setCommandText("")
    setSimulatorState("starting")
    setSimulatorMessage("Sending the work order to the simulator backend.")
    onStart(command, planner)
    return true
  }, [commandText, isRunning, onStart, planner])

  const submit = useCallback(() => start(), [start])

  const receiveSimulatorMessage = useCallback((event: SimulatorMessage) => {
    const message = event.message || "Simulator state updated."
    if (event.type === "ready") {
      setSimulatorState("ready")
      setSimulatorMessage(message)
      if (event.devinAvailable === false) setPlanner("baseline")
      return
    }
    if (event.type === "starting" || event.type === "accepted" || event.type === "progress") {
      setIsRunning(true)
      setSimulatorState(event.type === "starting" ? "starting" : "running")
      setSimulatorMessage(message)
      setEntries((current) => {
        const next: CommandEntry = {
          id: `system-${Date.now()}`,
          author: event.planner === "devin" ? "DEVIN" : "SYSTEM",
          timestamp: utcTime(new Date()),
          message,
          status: `${(event.stage || event.type).replaceAll("_", " ").toUpperCase()} · LIVE`,
        }
        const last = current.at(-1)
        return last?.status.endsWith("· LIVE") ? [...current.slice(0, -1), next] : [...current, next]
      })
      return
    }

    setIsRunning(false)
    setSimulatorState(event.type === "complete" ? "complete" : "failed")
    setSimulatorMessage(message)
    setEntries((current) => [
      ...current,
      {
        id: `${event.type}-${Date.now()}`,
        author: "SYSTEM",
        timestamp: utcTime(new Date()),
        message,
        status: event.type === "complete"
          ? `${event.disposition || "COMPLETE"} · ${event.inspectedCount ?? 0}/${event.waypointCount ?? 0} VIEWS`
          : "MISSION FAILED · SAFE STOP",
        alert: event.type === "failed" || event.disposition !== "PASS",
      },
    ])
  }, [])

  const attachContext = useCallback((label = "Stage 04 attached") => {
    setContextLabel((current) => (current === label ? "No context" : label))
  }, [])

  const prefill = useCallback((value: string) => {
    setIsRunning(false)
    setCommandText(value)
  }, [])

  return {
    commandText,
    setCommandText,
    isRunning,
    planner,
    setPlanner,
    simulatorMessage,
    simulatorState,
    contextLabel,
    entries,
    submit,
    receiveSimulatorMessage,
    attachContext,
    prefill,
  }
}
