import { ArrowUpRight } from "lucide-react"
import { motion } from "motion/react"
import { useRef } from "react"
import { Button } from "@/components/ui/button"
import { useFlightMotion } from "@/hooks/useFlightMotion"
import type { SectionId } from "@/types/aeroloop"

interface HeroFlightRecorderProps {
  isMotionPaused: boolean
  onNavigate: (sectionId: SectionId) => void
  prefersReducedMotion: boolean
}

export function HeroFlightRecorder({
  isMotionPaused,
  onNavigate,
  prefersReducedMotion,
}: HeroFlightRecorderProps) {
  const heroRef = useRef<HTMLElement>(null)
  const { craftTransform, craftOpacity } = useFlightMotion(heroRef, {
    isMotionPaused,
    prefersReducedMotion,
  })

  return (
    <section
      ref={heroRef}
      className="hero-surface hero-grid relative min-h-[690px] overflow-clip border-b border-aero-blue text-aero-ink"
      id="active-run"
    >
      <img
        alt="Pale blue stratospheric sky above a minimal cloud horizon"
        className="hero-image absolute inset-0 h-full w-full object-cover opacity-60"
        decoding="async"
        loading="lazy"
        src="https://images.unsplash.com/photo-1428908728789-d2de25dbd4e2?auto=format&w=1400&q=80&fit=crop"
      />
      <div aria-hidden="true" className="hero-wash absolute inset-0" />
      <div className="absolute left-7 right-7 top-6 z-10 flex items-center justify-between border-b border-aero-blue/35 pb-3">
        <div className="flex items-center gap-3 aero-mono text-[10px] font-semibold uppercase tracking-[.19em] text-aero-blue">
          <span aria-hidden="true" className="h-2 w-2 bg-aero-amber" />
          AeroLoop / flight record
          <span className="tracking-normal text-aero-blue/65">/ 00:00:00</span>
        </div>
      </div>
      <svg
        aria-hidden="true"
        className="absolute inset-0 z-[2] h-full w-full"
        fill="none"
        viewBox="0 0 900 690"
      >
        <path d="M40 454H860" opacity=".4" stroke="var(--aero-blue)" strokeDasharray="3 10" />
        <path
          className="route-line"
          d="M58 558C132 508 158 424 270 440C356 454 365 380 430 352C500 322 516 388 578 348C642 308 640 240 706 228C760 218 786 250 842 188"
          opacity=".7"
          stroke="var(--aero-blue)"
          strokeWidth="1.8"
        />
        <path
          className="route-line route-hot"
          d="M58 558C132 508 158 424 270 440C356 454 365 380 430 352"
          opacity=".95"
        />
        <path
          className="registration-cross"
          d="M66 548v24M54 560h24M840 176v25M828 188h24M250 404h66M283 370v68M626 292h58M655 256v72"
        />
        <circle cx="430" cy="352" fill="var(--aero-amber)" r="5" />
        <circle cx="842" cy="188" fill="var(--aero-sun)" r="4" />
      </svg>
      <div className="craft-stage absolute inset-0 z-[5]" aria-hidden="true">
        <motion.div
          className="craft-wrap absolute left-[43%] top-[172px] w-[325px]"
          style={{ opacity: craftOpacity, transform: craftTransform }}
        >
          <svg
            aria-label="Layered 3D inspection aircraft graphic"
            className="craft-svg w-full"
            fill="none"
            role="img"
            viewBox="0 0 360 154"
          >
            <path className="craft-shadow" d="M37 88L129 112L296 100L333 86L279 76L120 79Z" />
            <path className="craft-side" d="M30 68L120 79L296 72L333 84L292 103L124 110L30 81Z" />
            <path className="craft-top" d="M30 68L127 44L281 49L333 84L296 72L120 79Z" />
            <path className="craft-top" d="M116 47L146 10L174 10L175 75L126 78Z" />
            <path className="craft-side" d="M124 108L78 139L108 140L159 103Z" />
            <path className="craft-top" d="M184 73L270 120L302 114L221 62Z" />
            <path className="craft-hot" d="M281 49L338 77L354 87L333 96L292 77Z" />
            <path className="craft-window" d="M63 67L113 52L136 54L112 70Z" />
            <path className="craft-light" d="M28 69L8 66L28 62Z" />
            <circle className="craft-light" cx="53" cy="76" r="5" />
            <circle className="craft-window" cx="237" cy="70" r="3" />
            <path d="M138 78L226 73" stroke="var(--aero-sun)" strokeWidth="2.4" />
            <path d="M154 80L254 79" opacity=".6" stroke="var(--aero-navy)" strokeWidth="1.2" />
            <text className="craft-label" x="96" y="28">AL-208 / INSPECTION CRAFT</text>
          </svg>
        </motion.div>
      </div>
      <div aria-hidden="true" className="cloud-shelf absolute inset-x-0 bottom-0 z-[3] h-[150px]" />
      <div aria-hidden="true" className="absolute bottom-[149px] left-0 right-0 z-[4] border-t border-aero-blue/30" />
      <div className="hero-copy absolute bottom-[78px] left-8 z-10 max-w-[470px]">
        <p className="aero-mono mb-4 text-[10px] uppercase tracking-[.2em] text-aero-blue">
          Drone engine inspection, powered by Devin
        </p>
        <h1 className="aero-display max-w-[450px] text-[78px] font-semibold leading-[.8] tracking-[-.04em] text-aero-navy">
          Inspect.
          <br />
          Record.
          <br />
          Decide.
        </h1>
        <p className="mt-4 max-w-[355px] text-[14px] leading-5 text-aero-ink/75">
          AeroLoop directs Devin through engine checks and keeps every finding tied to the run.
        </p>
        <div className="mt-5 flex items-center">
          <Button
            className="h-auto rounded-none border-0 border-l-4 border-aero-blue bg-aero-sun px-4 py-3 text-[13px] font-bold text-aero-navy hover:bg-aero-sun/85"
            onClick={() => onNavigate("engine")}
            type="button"
          >
            Review active run
            <ArrowUpRight aria-hidden="true" className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="hero-plate chamfer absolute bottom-[78px] right-6 z-10 w-[210px] border border-aero-blue bg-aero-paper p-4 text-aero-navy">
        <div className="flex items-center justify-between">
          <p className="aero-mono text-[9px] uppercase tracking-[.18em] text-aero-blue">Active run / sample</p>
          <span aria-hidden="true" className="h-2 w-2 bg-aero-amber" />
        </div>
        <p className="aero-display mt-3 text-[34px] font-semibold leading-none">AL-208</p>
        <p className="mt-1 text-[12px]">Turbofan 02</p>
        <div className="mt-3 border-t border-aero-blue/25 pt-2 text-[12px]">
          Combustor sweep <strong className="text-aero-amber">· HOLD</strong>
        </div>
      </div>
      <div className="absolute bottom-6 left-8 z-10 aero-mono text-[9px] uppercase tracking-[.15em] text-aero-blue/70">
        ALT 38,000 FT · ROUTE 04 / 07
      </div>
    </section>
  )
}
