import { ExternalLink, LoaderCircle, Radio, ShieldCheck } from "lucide-react"
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
            <h2 className="aero-display mt-2 text-[46px] font-semibold leading-none text-aero-navy">Fly the verified simulator</h2>
            <p className="mt-3 max-w-[650px] text-[13px] leading-5 text-aero-ink/70">
              Commands from the right-hand drawer enter the real AeroLoop backend. Devin chooses bounded actions;
              the safety envelope executes them and the independent verifier decides the result.
            </p>
          </div>
          <a
            className="aero-mono inline-flex items-center gap-2 border border-aero-blue bg-aero-navy px-4 py-3 text-[10px] uppercase tracking-[.12em] text-aero-paper transition-colors hover:bg-aero-blue"
            href="/mission_view.html"
            rel="noreferrer"
            target="_blank"
          >
            Open full simulator <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
          </a>
        </div>

        <div className="mt-5 grid grid-cols-[minmax(0,1fr)_220px] border border-aero-navy bg-aero-navy max-[760px]:grid-cols-1">
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
          </div>

          <aside className="border-l border-aero-paper/20 p-5 text-aero-paper max-[760px]:border-l-0 max-[760px]:border-t">
            <div className="flex items-center gap-2 text-aero-sun">
              <Radio aria-hidden="true" className={`h-4 w-4 ${active ? "animate-pulse" : ""}`} />
              <span className="aero-mono text-[9px] uppercase tracking-[.16em]">{stateLabels[state]}</span>
            </div>
            <p aria-live="polite" className="mt-4 text-[13px] leading-5 text-aero-paper/75">{message}</p>
            <div className="mt-8 border-t border-aero-paper/20 pt-5">
              <ShieldCheck aria-hidden="true" className="h-5 w-5 text-aero-sun" />
              <p className="aero-display mt-3 text-[25px] font-semibold leading-none">Agent proposes. Safety executes.</p>
              <p className="mt-3 text-[11px] leading-5 text-aero-paper/55">
                The model never writes raw motor signals. Every requested action must match the allow-list,
                geometry, speed, clearance, and evidence rules before the controller receives it.
              </p>
            </div>
            <div className="mt-8 border-t border-aero-paper/20 pt-4 aero-mono text-[8px] uppercase leading-5 tracking-[.12em] text-aero-paper/45">
              Visual, audio and obstacle inputs shown here are synthetic and seeded. Real sensor integration is the next hardware phase.
            </div>
          </aside>
        </div>
      </section>
    )
  },
)
