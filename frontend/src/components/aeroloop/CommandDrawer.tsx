import { ArrowUpRight, Paperclip } from "lucide-react"
import { useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { CommandDrone } from "@/components/aeroloop/CommandDrone"
import type { CommandEntry, PreviousRun, SimulatorPlanner } from "@/types/aeroloop"

interface CommandDrawerProps {
  commandText: string
  contextLabel: string
  entries: CommandEntry[]
  isMotionPaused: boolean
  isRunning: boolean
  planner: SimulatorPlanner
  previousRuns: PreviousRun[]
  onAttachContext: (label?: string) => void
  onCommandChange: (value: string) => void
  onPlannerChange: (planner: SimulatorPlanner) => void
  onSelectRun: (runId: string) => void
  onSubmit: () => void
}

export function CommandDrawer({
  commandText,
  contextLabel,
  entries,
  isMotionPaused,
  isRunning,
  planner,
  previousRuns,
  onAttachContext,
  onCommandChange,
  onPlannerChange,
  onSelectRun,
  onSubmit,
}: CommandDrawerProps) {
  const logRef = useRef<HTMLElement>(null)
  const isReady = commandText.trim().length > 0 && !isRunning

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [entries])

  return (
    <aside aria-label="AeroLoop command drawer" className="command-drawer fixed inset-y-0 right-0 z-50 flex w-[360px] flex-col" id="command-drawer">
      <header className="shrink-0 border-b border-aero-brown px-5 py-5">
        <div className="flex items-center justify-between">
          <p className="aero-mono text-[9px] uppercase tracking-[.2em] text-aero-paper/55">Command record</p>
          <span className="flex items-center gap-2 aero-mono text-[9px] uppercase text-aero-sun">
            <i aria-hidden="true" className="h-2 w-2 bg-aero-sun" />
            {planner === "devin" ? "Devin" : "Local pilot"} {isRunning ? "running" : "ready"}
          </span>
        </div>
        <div className="mt-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="aero-display text-[33px] font-semibold leading-none">Live mission</h2>
            <p className="mt-2 text-[12px] text-aero-paper/60">Working simulator backend</p>
          </div>
          <span className="aero-mono border border-aero-sun px-2 py-1 text-[9px] uppercase text-aero-sun">{isRunning ? "RUNNING" : "READY"}</span>
        </div>
      </header>
      <section className="shrink-0 border-b border-aero-brown px-5 py-4">
        <div className="flex items-center justify-between">
          <p className="aero-mono text-[9px] uppercase tracking-[.18em] text-aero-paper/55">Recorded sample runs</p>
          <span className="aero-mono text-[9px] text-aero-paper/40">INDEXED / 03</span>
        </div>
        <div className="mt-2">
          {previousRuns.slice(0, 3).map((run, index) => (
            <Button
              className={`flex min-h-[34px] w-full items-center justify-between rounded-none border-0 border-b border-aero-paper/15 bg-transparent px-0 text-left text-[12px] text-aero-paper/70 hover:bg-aero-paper/10 hover:text-aero-paper ${run.current ? "text-aero-paper" : ""}`}
              key={run.id}
              onClick={() => onSelectRun(run.id)}
              type="button"
              variant="ghost"
            >
              <span><b className={`aero-mono mr-3 text-[10px] ${run.current ? "text-aero-sun" : "text-aero-paper/40"}`}>{String(index + 1).padStart(2, "0")}</b>{run.id.split(" · ")[0]} / {run.current ? "active" : index === 1 ? "turbine" : "intake"}</span>
              <span className="aero-mono text-[9px] text-aero-sun">{run.readiness}</span>
            </Button>
          ))}
        </div>
      </section>
      <section aria-labelledby="command-log-title" className="command-log min-h-0 flex-1 overflow-y-auto px-5 py-4" ref={logRef}>
        <p className="aero-mono text-[9px] uppercase tracking-[.18em] text-aero-paper/55" id="command-log-title">Recorded + live entries</p>
        <div className="mt-3 space-y-0" id="command-entries">
          {entries.map((entry) => (
            <article className={`command-entry border-b border-aero-paper/15 py-4 pl-3 ${entry.alert ? "command-alert" : ""}`} key={entry.id}>
              <p className="aero-mono text-[9px] text-aero-paper/45">{entry.timestamp} / {entry.author}</p>
              <p className="mt-2 text-[12px] leading-5">{entry.message}</p>
              <p className="aero-mono mt-2 text-[9px] uppercase text-aero-sun">{entry.status}</p>
            </article>
          ))}
        </div>
      </section>
      <footer className="shrink-0 border-t border-aero-brown bg-aero-brown px-5 py-4">
        <div className="flex items-center justify-between">
          <Label className="aero-mono text-[9px] uppercase tracking-[.18em] text-aero-paper/75" htmlFor="command-input">Command AeroLoop</Label>
          <span aria-live="polite" className={`aero-mono text-[9px] uppercase ${contextLabel === "No context" ? "text-aero-paper/45" : "text-aero-sun"}`}>{contextLabel}</span>
        </div>
        <label className="aero-mono mt-3 flex items-center justify-between text-[9px] uppercase tracking-[.12em] text-aero-paper/55">
          Decision maker
          <select
            className="border border-aero-paper/30 bg-aero-navy px-2 py-1 text-aero-paper outline-none focus:border-aero-sun"
            disabled={isRunning}
            onChange={(event) => onPlannerChange(event.target.value as SimulatorPlanner)}
            value={planner}
          >
            <option value="devin">Devin live</option>
            <option value="baseline">Local test pilot</option>
          </select>
        </label>
        <div className={`command-flightbox relative mt-3 overflow-hidden border border-aero-paper/30 bg-aero-navy ${isRunning ? "is-rendering" : ""}`} id="command-flightbox">
          <Textarea
            aria-describedby="command-help"
            className="relative z-10 block min-h-[74px] w-full resize-none rounded-none border-0 bg-transparent p-3 text-[12px] leading-5 text-aero-paper outline-none placeholder:text-aero-paper/35 focus-visible:border-aero-sun focus-visible:ring-0 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isRunning}
            id="command-input"
            onChange={(event) => onCommandChange(event.target.value)}
            placeholder="Ask for a stage or next action."
            rows={2}
            value={commandText}
          />
          <CommandDrone isMotionPaused={isMotionPaused} isVisible={!isRunning} />
        </div>
        <div aria-hidden="true" className={`command-progress mt-3 h-[2px] w-0 bg-aero-sun ${isRunning ? "is-running" : ""}`} id="command-progress" />
        <p className="mt-2 text-[9px] leading-4 text-aero-paper/45" id="command-help">Starts a real backend mission. A running mission completes or safely stops under backend control.</p>
        <div className="mt-3 flex items-center justify-between gap-3">
          <Button
            aria-pressed={contextLabel !== "No context"}
            className={`aero-mono min-h-[40px] rounded-none border-0 bg-transparent px-0 text-[9px] uppercase tracking-[.1em] text-aero-paper/65 hover:bg-transparent hover:text-aero-sun ${contextLabel !== "No context" ? "context-attached" : ""}`}
            onClick={() => onAttachContext()}
            type="button"
            variant="ghost"
          >
            <Paperclip aria-hidden="true" className="mr-2 h-3.5 w-3.5" />
            Attach context
          </Button>
          <Button
            className={`command-submit min-h-[40px] rounded-none border-0 border-l-4 border-aero-blue bg-aero-navy px-4 text-[11px] font-bold text-aero-paper/45 hover:bg-aero-navy ${isReady ? "is-ready" : ""} ${isRunning ? "is-running" : ""}`}
            disabled={!isReady}
            id="command-submit"
            onClick={onSubmit}
            type="button"
          >
            {isRunning ? "Mission running" : "Send command"}
            <ArrowUpRight aria-hidden="true" className="ml-2 h-3.5 w-3.5" />
          </Button>
        </div>
      </footer>
    </aside>
  )
}
