import { useCallback } from "react"
import { CommandDrawer } from "@/components/aeroloop/CommandDrawer"
import { EngineCutaway } from "@/components/aeroloop/EngineCutaway"
import { FindingsSection } from "@/components/aeroloop/FindingsSection"
import { HeroFlightRecorder } from "@/components/aeroloop/HeroFlightRecorder"
import { IndexRail } from "@/components/aeroloop/IndexRail"
import { InspectionRecord } from "@/components/aeroloop/InspectionRecord"
import { MissionMetrics } from "@/components/aeroloop/MissionMetrics"
import { PreviousRunsTable } from "@/components/aeroloop/PreviousRunsTable"
import { TelemetryPanel } from "@/components/aeroloop/TelemetryPanel"
import { useCommandRunner } from "@/hooks/useCommandRunner"
import { useMotionPreferences } from "@/hooks/useMotionPreferences"
import { useSectionNavigation } from "@/hooks/useSectionNavigation"
import type { AeroLoopData, SectionId } from "@/types/aeroloop"

const navigableSections: SectionId[] = ["active-run", "engine", "telemetry", "findings", "previous-runs"]

interface AeroLoopShellProps {
  data: AeroLoopData
}

export function AeroLoopShell({ data }: AeroLoopShellProps) {
  const { isMotionPaused, prefersReducedMotion, toggleMotion } = useMotionPreferences()
  const { activeSection, scrollToSection, swipeHandlers } = useSectionNavigation(navigableSections, isMotionPaused)
  const command = useCommandRunner({ initialEntries: data.initialEntries })

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
        <InspectionRecord onOpenPlate={() => scrollToSection("engine")} stages={data.stages} />
        <EngineCutaway onReviewTelemetry={reviewTelemetry} />
        <TelemetryPanel traceData={data.traceData} traces={data.traces} />
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
        onAttachContext={command.attachContext}
        onCommandChange={command.setCommandText}
        onSelectRun={(runId) => command.attachContext(`${runId} selected`)}
        onSubmit={command.submit}
        previousRuns={data.previousRuns}
      />
    </div>
  )
}
