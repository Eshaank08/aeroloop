import { useCallback, useState } from "react"
import { utcTime } from "@/lib/formatters"
import type { CommandEntry } from "@/types/aeroloop"

interface UseCommandRunnerOptions {
  initialEntries: CommandEntry[]
}

export function useCommandRunner({ initialEntries }: UseCommandRunnerOptions) {
  const [commandText, setCommandText] = useState("")
  const [isRunning, setIsRunning] = useState(false)
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
    return true
  }, [commandText, isRunning])

  const stop = useCallback(() => {
    if (!isRunning) return false

    setIsRunning(false)
    setEntries((current) => [
      ...current,
      {
        id: `stop-${Date.now()}`,
        author: "OPERATOR",
        timestamp: utcTime(new Date()),
        message: "Run stopped. Evidence retained.",
        status: "OPERATOR STOP · SAVED",
        alert: true,
      },
    ])
    return true
  }, [isRunning])

  const submit = useCallback(() => (isRunning ? stop() : start()), [isRunning, start, stop])

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
    contextLabel,
    entries,
    submit,
    attachContext,
    prefill,
  }
}
