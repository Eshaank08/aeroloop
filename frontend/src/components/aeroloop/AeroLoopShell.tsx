import { ProjectStory } from "@/components/aeroloop/ProjectStory"
import { HeroFlightRecorder } from "@/components/aeroloop/HeroFlightRecorder"
import { IndexRail } from "@/components/aeroloop/IndexRail"
import { useMotionPreferences } from "@/hooks/useMotionPreferences"
import { useSectionNavigation } from "@/hooks/useSectionNavigation"
import type { SectionId } from "@/types/aeroloop"

const navigableSections: SectionId[] = ["active-run", "problem", "workflow", "proof", "demo"]

export function AeroLoopShell() {
  const { isMotionPaused, prefersReducedMotion, toggleMotion } = useMotionPreferences()
  const { activeSection, scrollToSection, swipeHandlers } = useSectionNavigation(navigableSections, isMotionPaused)

  return (
    <div className={`aero-app ${isMotionPaused ? "motion-paused" : ""}`}>
      <IndexRail
        activeSection={activeSection}
        isMotionPaused={isMotionPaused}
        onNavigate={scrollToSection}
        onToggleMotion={toggleMotion}
      />
      <main className="record-main swipe-surface ml-16" {...swipeHandlers}>
        <HeroFlightRecorder
          isMotionPaused={isMotionPaused}
          onNavigate={scrollToSection}
          prefersReducedMotion={prefersReducedMotion}
        />
        <ProjectStory />
        <footer className="flex items-center justify-between bg-aero-navy px-8 py-5 aero-mono text-[9px] uppercase tracking-[.14em] text-aero-paper/55">
          <span>AeroLoop / Devin for autonomous inspection</span>
          <a className="text-aero-sun hover:text-aero-paper" href="/mission_view.html">Launch simulator ↗</a>
        </footer>
      </main>
    </div>
  )
}
