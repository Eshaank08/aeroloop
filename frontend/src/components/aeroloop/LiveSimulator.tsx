import { LoaderCircle, Radio } from "lucide-react"
import { forwardRef } from "react"
import type { SimulatorState } from "@/types/aeroloop"

interface LiveSimulatorProps {
  message: string
  state: SimulatorState
}

const stateLabels: Record<SimulatorState, string> = {
  idle: "Connecting",
  ready: "Ready",
  starting: "Planning",
  running: "Flying",
  complete: "Verified",
  failed: "Safe stop",
}

export const LiveSimulator = forwardRef<HTMLIFrameElement, LiveSimulatorProps>(
  function LiveSimulator({ message, state }, ref) {
    const active = state === "starting" || state === "running"

    return (
      <section className="live-simulator border-b border-aero-navy bg-aero-paper px-8 py-10" id="live-simulator">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-aero-blue/25 pb-4">
          <div>
            <p className="aero-mono text-[10px] uppercase tracking-[.2em] text-aero-blue">01 / Live proving loop</p>
            <h2 className="aero-display mt-2 text-[46px] font-semibold leading-none text-aero-navy">Main simulator</h2>
            <p className="mt-3 max-w-[650px] text-[13px] leading-5 text-aero-ink/70">
              Use Mission Control on the right to plan, fly, and verify here. Devin chooses bounded actions;
              the safety envelope executes them and the independent verifier decides the result.
            </p>
          </div>
          <span className="aero-mono border border-aero-blue bg-aero-navy px-4 py-3 text-[10px] uppercase tracking-[.12em] text-aero-paper">Single mission workspace</span>
        </div>

        <div className="mt-5 border border-aero-navy bg-aero-navy">
          <div className="simulator-frame-wrap relative min-h-[620px] overflow-hidden bg-[#d8e3ed]">
            <iframe
              allow="microphone"
              className="absolute inset-0 h-full w-full border-0"
              ref={ref}
              src="/mission_view.html?embedded=1"
              title="Live AeroLoop 3D simulator"
            />
            {active ? (
              <div className="pointer-events-none absolute left-4 top-4 flex items-center gap-2 border border-aero-sun bg-aero-navy/95 px-3 py-2 text-aero-paper shadow-lg">
                <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin text-aero-sun" />
                <span className="aero-mono text-[9px] uppercase tracking-[.13em]">{stateLabels[state]}</span>
              </div>
            ) : null}
            <div className="pointer-events-none absolute right-4 top-4 max-w-[280px] border border-aero-paper/25 bg-aero-navy/95 px-4 py-3 text-aero-paper shadow-lg">
              <div className="flex items-center gap-2 text-aero-sun">
                <Radio aria-hidden="true" className={`h-3.5 w-3.5 ${active ? "animate-pulse" : ""}`} />
                <span className="aero-mono text-[9px] uppercase tracking-[.16em]">{stateLabels[state]}</span>
              </div>
              <p aria-live="polite" className="mt-2 text-[11px] leading-4 text-aero-paper/70">{message}</p>
            </div>
          </div>
        </div>
        <p className="aero-mono mt-3 text-[8px] uppercase leading-5 tracking-[.12em] text-aero-ink/45">
          Safety executes validated actions only. Visual, audio and obstacle inputs are synthetic and seeded in this simulator.
        </p>
      </section>
    )
  },
)
