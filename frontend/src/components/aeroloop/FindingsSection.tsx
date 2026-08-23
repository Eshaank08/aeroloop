import { ArrowRight, ArrowUpRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { Finding } from "@/types/aeroloop"

interface FindingsSectionProps {
  findings: Finding[]
  onAttachContext: (label: string) => void
  onPrefill: (value: string) => void
  onReviewTelemetry: () => void
}

export function FindingsSection({
  findings,
  onAttachContext,
  onPrefill,
  onReviewTelemetry,
}: FindingsSectionProps) {
  const vibration = findings.find((finding) => finding.kind === "vibration")
  const temperature = findings.find((finding) => finding.kind === "temperature")

  return (
    <section className="border-b border-aero-blue/25 bg-aero-paper px-8 py-14" id="findings">
      <div className="mb-8 flex items-end justify-between border-b border-aero-blue/25 pb-4">
        <div>
          <p className="aero-mono text-[10px] uppercase tracking-[.2em] text-aero-blue">04 / Evidence</p>
          <h2 className="aero-display mt-2 text-[45px] font-semibold leading-none text-aero-navy">Findings on record</h2>
        </div>
        <span className="aero-mono border border-aero-amber px-3 py-2 text-[9px] uppercase text-aero-amber">SAMPLE DATA · 02 FINDINGS</span>
      </div>
      <div className="finding-layout grid grid-cols-[1.25fr_.75fr] gap-5">
        {vibration ? (
          <article className="evidence-sheet evidence-alert chamfer p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="aero-mono text-[9px] uppercase tracking-[.18em] text-aero-blue">Evidence sheet / {vibration.id}</p>
                <h3 className="aero-display mt-2 text-[33px] font-semibold leading-none text-aero-navy">{vibration.title}</h3>
              </div>
              <span className="aero-mono shrink-0 border border-aero-amber px-2 py-1 text-[9px] uppercase text-aero-amber">{vibration.status}</span>
            </div>
            <div className="mt-5 grid grid-cols-3 gap-4 border-t border-aero-blue/25 pt-4">
              <div>
                <p className="aero-mono text-[8px] uppercase text-aero-blue/70">Component</p>
                <p className="mt-1 text-[12px] font-semibold">{vibration.component}</p>
              </div>
              <div>
                <p className="aero-mono text-[8px] uppercase text-aero-blue/70">Observed / threshold</p>
                <p className="mt-1 text-[12px] font-semibold">{vibration.observed}</p>
              </div>
              <div>
                <p className="aero-mono text-[8px] uppercase text-aero-blue/70">Captured</p>
                <p className="mt-1 text-[12px] font-semibold">{vibration.captured}</p>
              </div>
            </div>
            <div className="mt-5 flex items-center gap-5 border-t border-aero-blue/25 pt-4">
              <Button
                className="h-auto rounded-none border-0 bg-aero-blue px-4 py-3 text-[12px] font-semibold text-aero-paper hover:bg-aero-blue/85"
                onClick={onReviewTelemetry}
                type="button"
              >
                Review evidence
                <ArrowUpRight aria-hidden="true" className="ml-2 h-3.5 w-3.5" />
              </Button>
              <Button
                className="h-auto rounded-none border-0 bg-transparent p-0 text-[12px] font-semibold text-aero-navy underline decoration-aero-blue underline-offset-4 hover:bg-transparent hover:text-aero-blue"
                onClick={() => onPrefill("Inspect compressor stage 3 again.")}
                type="button"
                variant="ghost"
              >
                Inspect again
                <ArrowRight aria-hidden="true" className="ml-1 h-3.5 w-3.5" />
              </Button>
            </div>
          </article>
        ) : null}
        {temperature ? (
          <article className="evidence-sheet chamfer p-6">
            <p className="aero-mono text-[9px] uppercase tracking-[.18em] text-aero-blue">Evidence sheet / {temperature.id}</p>
            <h3 className="aero-display mt-2 text-[30px] font-semibold leading-none text-aero-navy">{temperature.title}</h3>
            <div className="mt-5 border-t border-aero-blue/25 pt-4">
              <p className="aero-mono text-[10px] leading-5">
                {temperature.observed}
                <br />
                {temperature.threshold}
                <br />
                {temperature.captured}
              </p>
            </div>
            <Button
              className="mt-7 h-auto rounded-none border-0 bg-transparent p-0 text-[12px] font-semibold text-aero-navy underline decoration-aero-blue underline-offset-4 hover:bg-transparent hover:text-aero-blue"
              onClick={() => {
                onAttachContext("Temperature attached")
                onReviewTelemetry()
              }}
              type="button"
              variant="ghost"
            >
              Open temperature window
              <ArrowRight aria-hidden="true" className="ml-1 h-3.5 w-3.5" />
            </Button>
          </article>
        ) : null}
      </div>
    </section>
  )
}
