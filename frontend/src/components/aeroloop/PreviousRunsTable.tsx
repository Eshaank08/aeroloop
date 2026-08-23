import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { PreviousRun } from "@/types/aeroloop"

interface PreviousRunsTableProps {
  previousRuns: PreviousRun[]
}

export function PreviousRunsTable({ previousRuns }: PreviousRunsTableProps) {
  return (
    <section className="border-b border-aero-brown bg-aero-brown px-8 py-12 text-aero-paper" id="previous-runs">
      <div className="mb-8 flex items-end justify-between border-b border-aero-paper/25 pb-4">
        <div>
          <p className="aero-mono text-[10px] uppercase tracking-[.2em] text-aero-sun">05 / Archive</p>
          <h2 className="aero-display mt-2 text-[45px] font-semibold leading-none">Previous runs</h2>
        </div>
        <div className="text-right aero-mono text-[9px] uppercase leading-5 text-aero-paper/60">
          Comparison ledger
          <br />
          Sample simulation records
        </div>
      </div>
      <div className="overflow-x-auto">
        <Table className="min-w-[680px] border-collapse text-left text-[11px]">
          <TableHeader>
            <TableRow className="border-b border-aero-paper/25 hover:bg-transparent">
              {['Run / engine', 'Health', 'Readiness', 'Elapsed', 'Findings', 'Captured'].map((label) => (
                <TableHead className="h-auto px-3 py-3 aero-mono text-[9px] uppercase tracking-[.12em] text-aero-paper/55 first:pl-0" key={label}>
                  {label}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {previousRuns.map((run) => (
              <TableRow className={`border-b border-aero-paper/20 hover:bg-aero-blue/80 ${run.current ? "bg-aero-blue" : ""}`} key={run.id}>
                <TableHead className={`px-3 py-4 text-left first:pl-0 ${run.current ? "text-aero-sun" : "text-aero-paper"}`}>
                  {run.current ? "CURRENT · " : ""}{run.id}
                  <span className="ml-2 block text-[9px] font-normal text-aero-paper/50">{run.engine}</span>
                </TableHead>
                <TableCell className="px-3 py-4 aero-mono">{run.health}</TableCell>
                <TableCell className="px-3 py-4 aero-mono text-aero-sun">{run.readiness}</TableCell>
                <TableCell className="px-3 py-4 aero-mono">{run.elapsed}</TableCell>
                <TableCell className="px-3 py-4 aero-mono">{run.findings}</TableCell>
                <TableCell className="px-3 py-4 aero-mono">{run.captured}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="mt-6 flex items-center justify-between aero-mono text-[9px] uppercase tracking-[.13em] text-aero-paper/55">
        <span>All times UTC / first column pinned</span>
        <span>Archive index 04 / 18</span>
      </div>
    </section>
  )
}
