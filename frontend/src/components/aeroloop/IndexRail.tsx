import { Pause, Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { SectionId } from "@/types/aeroloop"

interface IndexRailProps {
  activeSection: SectionId
  isMotionPaused: boolean
  onNavigate: (sectionId: SectionId) => void
  onToggleMotion: () => void
}

const navigation = [
  { id: "active-run" as const, index: "01", label: "Run" },
  { id: "live-simulator" as const, index: "02", label: "Live" },
  { id: "engine" as const, index: "03", label: "Engine" },
  { id: "telemetry" as const, index: "04", label: "Data" },
  { id: "findings" as const, index: "05", label: "Findings" },
  { id: "previous-runs" as const, index: "06", label: "Archive" },
]

export function IndexRail({
  activeSection,
  isMotionPaused,
  onNavigate,
  onToggleMotion,
}: IndexRailProps) {
  const motionLabel = isMotionPaused ? "Resume motion" : "Pause motion"
  const MotionIcon = isMotionPaused ? Play : Pause

  return (
    <aside
      aria-label="Flight record index"
      className="index-rail fixed inset-y-0 left-0 z-50 flex w-16 flex-col items-center border-r border-aero-brown"
    >
      <div className="flex h-16 w-full items-center justify-center border-b border-aero-brown">
        <span className="aero-display text-[25px] font-semibold tracking-[-.06em] text-aero-sun">
          AL
        </span>
      </div>
      <nav aria-label="Record sections" className="flex w-full flex-1 flex-col gap-1 py-3">
        {navigation.map((item) => (
          <a
            key={item.id}
            aria-current={activeSection === item.id ? "true" : "false"}
            className="rail-link flex min-h-[76px] w-full flex-col items-center justify-center gap-2"
            href={`#${item.id}`}
            onClick={(event) => {
              event.preventDefault()
              onNavigate(item.id)
            }}
          >
            <span className="rail-index aero-mono text-[10px] font-semibold">
              {item.index}
            </span>
            <span className="rail-name text-[9px] uppercase tracking-[.13em]">
              {item.label}
            </span>
          </a>
        ))}
      </nav>
      <Button
        aria-label={motionLabel}
        aria-pressed={isMotionPaused}
        className="flex min-h-[82px] w-full flex-col justify-center gap-2 rounded-none border-0 border-t border-aero-brown bg-transparent px-0 text-aero-paper hover:bg-aero-sun/10 hover:text-aero-paper"
        onClick={onToggleMotion}
        title={motionLabel}
        type="button"
        variant="ghost"
      >
        <MotionIcon aria-hidden="true" className="h-4 w-4" />
        <span className="rail-name aero-mono text-[8px] uppercase tracking-[.1em]">
          {motionLabel}
        </span>
      </Button>
    </aside>
  )
}
