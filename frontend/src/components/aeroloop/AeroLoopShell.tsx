import { lazy, Suspense, useCallback, useEffect, useRef } from "react"
import { CommandDrawer } from "@/components/aeroloop/CommandDrawer"
import { EngineCutaway } from "@/components/aeroloop/EngineCutaway"
import { FindingsSection } from "@/components/aeroloop/FindingsSection"
import { HeroFlightRecorder } from "@/components/aeroloop/HeroFlightRecorder"
import { IndexRail } from "@/components/aeroloop/IndexRail"
import { InspectionRecord } from "@/components/aeroloop/InspectionRecord"
import { LiveSimulator } from "@/components/aeroloop/LiveSimulator"
import { MissionMetrics } from "@/components/aeroloop/MissionMetrics"
import { PreviousRunsTable } from "@/components/aeroloop/PreviousRunsTable"
import { useCommandRunner } from "@/hooks/useCommandRunner"
import { useMotionPreferences } from "@/hooks/useMotionPreferences"
import { useSectionNavigation } from "@/hooks/useSectionNavigation"
import type { AeroLoopData, SectionId, SimulatorMessage, SimulatorPlanner } from "@/types/aeroloop"

const navigableSections: SectionId[] = ["active-run", "live-simulator", "engine", "telemetry", "findings", "previous-runs"]
const TelemetryPanel = lazy(() => import("@/components/aeroloop/TelemetryPanel").then((module) => ({ default: module.TelemetryPanel })))

interface AeroLoopShellProps {
  data: AeroLoopData
}

export function AeroLoopShell({ data }: AeroLoopShellProps) {
  const { isMotionPaused, prefersReducedMotion, toggleMotion } = useMotionPreferences()
  const { activeSection, scrollToSection, swipeHandlers } = useSectionNavigation(navigableSections, isMotionPaused)
  const simulatorRef = useRef<HTMLIFrameElement>(null)
  const pendingMission = useRef<{ command: string; planner: SimulatorPlanner } | null>(null)

  const postMission = useCallback((command: string, planner: SimulatorPlanner) => {
    simulatorRef.current?.contentWindow?.postMessage({
      source: "aeroloop-dashboard",
      type: "run-mission",
      command,
      planner,
    }, window.location.origin)
  }, [])

  const startMission = useCallback((command: string, planner: SimulatorPlanner) => {
    pendingMission.current = { command, planner }
    postMission(command, planner)
    scrollToSection("live-simulator")
  }, [postMission, scrollToSection])

  const command = useCommandRunner({ initialEntries: data.initialEntries, onStart: startMission })
  const receiveSimulatorMessage = command.receiveSimulatorMessage

  useEffect(() => {
    const receiveMessage = (event: MessageEvent<SimulatorMessage>) => {
      if (
        event.origin !== window.location.origin
        || event.source !== simulatorRef.current?.contentWindow
        || event.data?.source !== "aeroloop-simulator"
      ) return

      receiveSimulatorMessage(event.data)
      if (event.data.type === "ready" && pendingMission.current) {
        postMission(pendingMission.current.command, pendingMission.current.planner)
      }
      if (event.data.type === "accepted") pendingMission.current = null
    }
    window.addEventListener("message", receiveMessage)
    return () => window.removeEventListener("message", receiveMessage)
  }, [postMission, receiveSimulatorMessage])

  const reviewTelemetry = useCallback(() => {
    command.attachContext("EV-208-02 attached")
    scrollToSection("telemetry")
  }, [command, scrollToSection])

  const prefillCommand = useCallback((value: string) => {
    command.prefill(value)
    window.requestAnimationFrame(() => document.getElementById("command-input")?.focus())
  }, [command])

  return (
    <div className={`aero-app ${isMotionPaused ? "motion-paused" : ""}`}>
      <IndexRail
        activeSection={activeSection}
        isMotionPaused={isMotionPaused}
        onNavigate={scrollToSection}
        onToggleMotion={toggleMotion}
      />
      <main className="record-main swipe-surface ml-16 mr-[360px]" {...swipeHandlers}>
        <HeroFlightRecorder
          isMotionPaused={isMotionPaused}
          onNavigate={scrollToSection}
          prefersReducedMotion={prefersReducedMotion}
        />
        <MissionMetrics metrics={data.metrics} />
        <LiveSimulator
          message={command.simulatorMessage}
          ref={simulatorRef}
          state={command.simulatorState}
        />
        <InspectionRecord onOpenPlate={() => scrollToSection("engine")} stages={data.stages} />
        <EngineCutaway onReviewTelemetry={reviewTelemetry} />
        <Suspense fallback={<section className="telemetry-surface min-h-[520px] px-8 py-12" id="telemetry">Loading recorded telemetry…</section>}>
          <TelemetryPanel traceData={data.traceData} traces={data.traces} />
        </Suspense>
        <FindingsSection
          findings={data.findings}
          onAttachContext={command.attachContext}
          onPrefill={prefillCommand}
          onReviewTelemetry={reviewTelemetry}
        />
        <PreviousRunsTable previousRuns={data.previousRuns} />
        <footer className="flex items-center justify-between bg-aero-navy px-8 py-5 aero-mono text-[9px] uppercase tracking-[.14em] text-aero-paper/55">
          <span>AeroLoop / flight record</span>
          <span>Simulation interface</span>
        </footer>
      </main>
      <CommandDrawer
        commandText={command.commandText}
        contextLabel={command.contextLabel}
        entries={command.entries}
        isMotionPaused={isMotionPaused}
        isRunning={command.isRunning}
        planner={command.planner}
        simulatorMessage={command.simulatorMessage}
        simulatorState={command.simulatorState}
        onAttachContext={command.attachContext}
        onCommandChange={command.setCommandText}
        onPlannerChange={command.setPlanner}
        onSubmit={command.submit}
      />
    </div>
  )
}
