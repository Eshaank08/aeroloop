import { ArrowUpRight, Bot, Braces, FileCheck2, Gauge, ShieldCheck } from "lucide-react"

const workflow = [
  ["01", "Trigger", "A work order describes the asset, inspection region and operating limits."],
  ["02", "Devin decides", "Devin reads mission state and requests one bounded inspection action."],
  ["03", "Safety executes", "The validator and flight controller reject unsafe geometry, speed or clearance."],
  ["04", "Verifier judges", "Evidence is scored independently. Gaps become targeted re-capture requests."],
  ["05", "Artifact ships", "The run ends with a hashed inspection record, not an uncheckable AI answer."],
] as const

export function ProjectStory() {
  return (
    <>
      <section className="border-b border-aero-navy bg-aero-paper px-10 py-20 text-aero-navy" id="problem">
        <p className="aero-mono text-[10px] uppercase tracking-[.2em] text-aero-blue">02 / The problem</p>
        <div className="mt-4 grid grid-cols-[1.1fr_.9fr] gap-14 max-[760px]:grid-cols-1">
          <div>
            <h2 className="aero-display max-w-[720px] text-[64px] font-semibold leading-[.92] tracking-[-.03em]">Physical inspections lose the software feedback loop.</h2>
            <p className="mt-6 max-w-[620px] text-[17px] leading-7 text-aero-ink/70">A drone can collect images, but people still decide where to fly, notice missing evidence, request another capture and assemble the final record. AeroLoop turns that sequence into a loop the system can run and test itself.</p>
          </div>
          <div className="border-l border-aero-blue/25 pl-8 max-[760px]:border-l-0 max-[760px]:border-t max-[760px]:pl-0 max-[760px]:pt-8">
            {["Routes are manually adjusted", "Evidence gaps appear after landing", "AI suggestions lack an automatic verdict"].map((item, index) => (
              <div className="flex gap-5 border-b border-aero-blue/25 py-5" key={item}>
                <span className="aero-mono text-[11px] text-aero-amber">0{index + 1}</span>
                <p className="aero-display text-[27px] font-semibold leading-none">{item}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-aero-navy px-10 py-20 text-aero-paper" id="workflow">
        <div className="flex flex-wrap items-end justify-between gap-5 border-b border-aero-paper/20 pb-5">
          <div>
            <p className="aero-mono text-[10px] uppercase tracking-[.2em] text-aero-sun">03 / The autonomous loop</p>
            <h2 className="aero-display mt-3 text-[58px] font-semibold leading-none">Nobody sits between trigger and artifact.</h2>
          </div>
          <span className="aero-mono border border-aero-sun px-3 py-2 text-[9px] uppercase tracking-[.14em] text-aero-sun">Agent proposes · safety executes</span>
        </div>
        <div className="mt-8 grid grid-cols-5 border border-aero-paper/20 max-[980px]:grid-cols-2 max-[640px]:grid-cols-1">
          {workflow.map(([number, title, description]) => (
            <article className="min-h-[240px] border-r border-aero-paper/20 p-5 last:border-r-0 max-[980px]:border-b" key={number}>
              <p className="aero-mono text-[10px] text-aero-sun">{number}</p>
              <h3 className="aero-display mt-10 text-[28px] font-semibold leading-none">{title}</h3>
              <p className="mt-4 text-[12px] leading-5 text-aero-paper/60">{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-b border-aero-blue/25 bg-aero-mist px-10 py-20 text-aero-navy" id="proof">
        <p className="aero-mono text-[10px] uppercase tracking-[.2em] text-aero-blue">04 / What actually runs</p>
        <h2 className="aero-display mt-3 max-w-[820px] text-[58px] font-semibold leading-none">A working autonomy layer—not a prepared animation.</h2>
        <div className="mt-10 grid grid-cols-3 gap-5 max-[760px]:grid-cols-1">
          <article className="evidence-sheet p-6">
            <Bot className="h-6 w-6 text-aero-blue" />
            <h3 className="aero-display mt-5 text-[29px] font-semibold">Agent decisions</h3>
            <p className="mt-3 text-[13px] leading-5 text-aero-ink/65">The backend can trigger live Devin sessions for bounded mission decisions, with a deterministic test pilot available for reproducible judging.</p>
          </article>
          <article className="evidence-sheet p-6">
            <ShieldCheck className="h-6 w-6 text-aero-blue" />
            <h3 className="aero-display mt-5 text-[29px] font-semibold">Independent checks</h3>
            <p className="mt-3 text-[13px] leading-5 text-aero-ink/65">Safety validation and evidence scoring are deterministic. The decision maker cannot declare its own work correct.</p>
          </article>
          <article className="evidence-sheet p-6">
            <FileCheck2 className="h-6 w-6 text-aero-blue" />
            <h3 className="aero-display mt-5 text-[29px] font-semibold">Industry artifact</h3>
            <p className="mt-3 text-[13px] leading-5 text-aero-ink/65">Every mission produces a traceable, hashed JSON record containing actions, evidence, retries and final disposition.</p>
          </article>
        </div>
        <div className="mt-8 grid grid-cols-3 border border-aero-blue bg-aero-paper max-[640px]:grid-cols-1">
          <div className="p-5"><Braces className="h-5 w-5 text-aero-amber" /><strong className="aero-display mt-3 block text-[36px]">151</strong><span className="aero-mono text-[9px] uppercase text-aero-blue">Automated tests</span></div>
          <div className="border-x border-aero-blue/25 p-5 max-[640px]:border-x-0 max-[640px]:border-y"><Gauge className="h-5 w-5 text-aero-amber" /><strong className="aero-display mt-3 block text-[36px]">Seeded</strong><span className="aero-mono text-[9px] uppercase text-aero-blue">Repeatable disturbances</span></div>
          <div className="p-5"><FileCheck2 className="h-5 w-5 text-aero-amber" /><strong className="aero-display mt-3 block text-[36px]">PASS / STOP</strong><span className="aero-mono text-[9px] uppercase text-aero-blue">Machine-verifiable outcome</span></div>
        </div>
        <p className="mt-5 border-l-4 border-aero-amber pl-4 text-[12px] leading-5 text-aero-ink/60"><strong>Honest boundary:</strong> flight physics and sensor evidence are simulated today. The autonomy contract, safety gates, verification loop and artifacts are the software intended to connect to real hardware.</p>
      </section>

      <section className="relative overflow-hidden bg-aero-sun px-10 py-20 text-aero-navy" id="demo">
        <div aria-hidden="true" className="absolute -right-24 -top-24 h-80 w-80 rounded-full border-[60px] border-aero-blue/10" />
        <p className="aero-mono text-[10px] uppercase tracking-[.2em] text-aero-blue">05 / Technical demo</p>
        <div className="relative mt-4 grid grid-cols-[1fr_360px] items-end gap-12 max-[760px]:grid-cols-1">
          <div>
            <h2 className="aero-display max-w-[760px] text-[70px] font-semibold leading-[.88] tracking-[-.03em]">Now watch the loop close.</h2>
            <p className="mt-6 max-w-[620px] text-[16px] leading-6 text-aero-ink/70">The simulator opens as a separate full-screen workspace. Choose a mission, watch the decision stream, inject repeatable conditions and wait for the verifier’s result.</p>
          </div>
          <div>
            <a className="flex items-center justify-between border-l-4 border-aero-blue bg-aero-navy px-6 py-5 text-[15px] font-bold text-aero-paper transition-transform hover:-translate-y-1" href="/mission_view.html">
              Launch full simulator <ArrowUpRight className="h-5 w-5" />
            </a>
            <p className="aero-mono mt-3 text-[9px] uppercase leading-4 text-aero-blue">Try: inspect top side, light wind, seed 606076</p>
          </div>
        </div>
      </section>
    </>
  )
}
