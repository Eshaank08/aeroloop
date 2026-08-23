import { ArrowRight } from "lucide-react"
import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { padStage } from "@/lib/formatters"
import type { Stage } from "@/types/aeroloop"

interface InspectionRecordProps {
  stages: Stage[]
  onOpenPlate: () => void
}

const resultClass = (result: Stage["result"]) => {
  if (result === "HOLD") return "bg-aero-amber text-aero-paper"
  if (result === "PASS") return "bg-aero-blue text-aero-paper"
  return "border border-aero-blue text-aero-blue"
}

export function InspectionRecord({ stages, onOpenPlate }: InspectionRecordProps) {
  const [selectedStageId, setSelectedStageId] = useState(4)
  const selectedStage = useMemo(
    () => stages.find((stage) => stage.id === selectedStageId) ?? stages[0],
    [selectedStageId, stages],
  )

  if (!selectedStage) return null

  return (
    <section
      aria-labelledby="record-title"
      className="relative border-b border-aero-blue/25 bg-aero-paper px-8 py-14"
      id="inspection-record"
    >
      <div className="mb-8 flex items-end justify-between border-b border-aero-blue/25 pb-4">
        <div>
          <p className="aero-mono text-[10px] uppercase tracking-[.2em] text-aero-blue">02 / Recorded inspection example</p>
          <h2 className="aero-display mt-2 text-[45px] font-semibold leading-none text-aero-navy" id="record-title">
            Inspection record
          </h2>
        </div>
        <div className="text-right aero-mono text-[10px] uppercase leading-5 text-aero-blue/70">
          AL-208 / A-17
          <br />
          <span className="text-aero-amber">HOLD · 2 findings</span>
        </div>
      </div>
      <div className="inspection-layout grid grid-cols-[.92fr_1.08fr] gap-8">
        <div aria-label="Seven inspection stages" className="relative pl-1">
          <div aria-hidden="true" className="absolute bottom-4 left-[18px] top-4 w-px bg-aero-blue/25" />
          {stages.map((stage) => (
            <Button
              aria-pressed={selectedStageId === stage.id}
              className={`stage-row relative flex min-h-[47px] w-full items-center justify-start gap-4 rounded-none border-0 border-b border-aero-blue/15 bg-transparent px-4 py-3 text-left text-aero-ink hover:text-aero-ink ${stage.status === "current" ? "stage-current min-h-[60px]" : ""} ${stage.status === "complete" ? "stage-complete" : ""} ${stage.status === "queued" ? "stage-queued" : ""}`}
              data-stage={stage.id}
              key={stage.id}
              onClick={() => setSelectedStageId(stage.id)}
              type="button"
              variant="ghost"
            >
              <span aria-hidden="true" className="stage-dot z-10 h-2.5 w-2.5 shrink-0 rounded-full" />
              <span className={`aero-mono w-6 text-[10px] ${stage.status === "current" ? "text-aero-amber" : "text-aero-blue"}`}>
                {padStage(stage.id)}
              </span>
              <span className="min-w-0">
                <strong className="block truncate text-[13px] font-semibold">{stage.title}</strong>
                {stage.description ? <small className="block truncate text-[11px] text-aero-muted">{stage.description}</small> : null}
              </span>
              <span className={`ml-auto shrink-0 aero-mono px-1 py-0.5 text-[9px] ${stage.status === "current" ? "text-aero-amber" : stage.result === "PASS" ? "text-aero-blue" : "text-aero-muted"}`}>
                {stage.result}
              </span>
            </Button>
          ))}
        </div>
        <article className="chamfer border-l-4 border-aero-blue bg-aero-mist p-6" id="stage-panel">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="aero-mono text-[9px] uppercase tracking-[.18em] text-aero-blue">
                CURRENT STAGE / <span>{padStage(selectedStage.id)}</span>
              </p>
              <h3 className="aero-display mt-2 text-[36px] font-semibold leading-none text-aero-navy">
                {selectedStage.title}
              </h3>
            </div>
            <span className={`aero-mono shrink-0 px-2 py-1 text-[9px] font-semibold uppercase ${resultClass(selectedStage.result)}`}>
              {selectedStage.result}
            </span>
          </div>
          <p className="mt-5 max-w-[460px] text-[13px] leading-5 text-aero-ink/75">{selectedStage.detail}</p>
          <div className="mt-6 grid grid-cols-2 gap-5 border-t border-aero-blue/25 pt-4">
            <div>
              <p className="aero-mono text-[9px] uppercase text-aero-blue/70">Telemetry</p>
              <p className="mt-1 text-[12px] font-semibold">{selectedStage.telemetry}</p>
            </div>
            <div>
              <p className="aero-mono text-[9px] uppercase text-aero-blue/70">Agent action</p>
              <p className="mt-1 text-[12px] font-semibold">{selectedStage.action}</p>
            </div>
          </div>
          <div className="mt-6 flex items-center justify-between gap-4 border-t border-aero-blue/25 pt-4">
            <span className="aero-mono text-[9px] uppercase text-aero-blue/65">
              STAGE {padStage(selectedStage.id)} OF 07 · 14:32:08 UTC
            </span>
            <Button
              className="h-auto shrink-0 rounded-none border-0 bg-transparent p-0 text-[12px] font-semibold text-aero-navy underline decoration-aero-blue underline-offset-4 hover:bg-transparent hover:text-aero-blue"
              onClick={onOpenPlate}
              type="button"
              variant="ghost"
            >
              Open plate
              <ArrowRight aria-hidden="true" className="ml-1 h-3.5 w-3.5" />
            </Button>
          </div>
        </article>
      </div>
    </section>
  )
}
