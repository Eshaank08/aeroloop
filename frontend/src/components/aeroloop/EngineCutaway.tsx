import { ArrowUpRight } from "lucide-react"
import { Button } from "@/components/ui/button"

interface EngineCutawayProps {
  onReviewTelemetry: () => void
}

export function EngineCutaway({ onReviewTelemetry }: EngineCutawayProps) {
  return (
    <section className="engine-field relative overflow-clip border-b border-aero-navy px-8 py-12" id="engine">
      <div className="flex items-end justify-between border-b border-aero-paper/25 pb-4">
        <div>
          <p className="aero-mono text-[10px] uppercase tracking-[.2em] text-aero-sun">03 / Recorded engine plate</p>
          <h2 className="aero-display mt-2 text-[44px] font-semibold leading-none">Engine cutaway</h2>
        </div>
        <div className="text-right aero-mono text-[9px] uppercase leading-5 text-aero-paper/65">
          OPENED VIEW / SCALE 1:4
          <br />
          <span className="text-aero-sun">STAGE 04 ACTIVE</span>
        </div>
      </div>
      <div className="relative mt-7 min-h-[540px] border-t border-aero-paper/20 pt-6">
        <div className="chamfer absolute left-0 top-7 bg-aero-paper px-4 py-3 text-aero-navy">
          <p className="aero-mono text-[8px] uppercase tracking-[.16em] text-aero-blue">Open case / 62%</p>
          <p className="mt-1 text-[11px] font-semibold">Casing split</p>
          <p className="aero-mono mt-2 text-[9px]">250 kPa / clear</p>
        </div>
        <svg
          aria-labelledby="engine-title engine-description"
          className="block h-[500px] w-full"
          fill="none"
          role="img"
          viewBox="0 0 900 500"
        >
          <title id="engine-title">Axial turbofan engine cutaway</title>
          <desc id="engine-description">Inlet fan, staged compressor, annular combustor, turbine rows, bypass duct, and convergent exhaust nozzle.</desc>
          <defs>
            <pattern height="36" id="engine-blueprint-grid" patternUnits="userSpaceOnUse" width="36">
              <path d="M36 0H0V36" fill="none" stroke="rgba(173,219,255,.18)" strokeWidth="1" />
              <path d="M18 0V36M0 18H36" fill="none" opacity=".38" stroke="rgba(173,219,255,.14)" strokeWidth=".7" />
            </pattern>
            <pattern height="10" id="engine-section-hatch" patternUnits="userSpaceOnUse" width="10">
              <path d="M-2 10L10 -2M3 13L13 3" fill="none" stroke="rgba(255,248,237,.34)" strokeWidth="1" />
            </pattern>
            <linearGradient id="engine-casing" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0" stopColor="#ADDBFF" stopOpacity=".24" />
              <stop offset=".46" stopColor="#14293A" stopOpacity=".94" />
              <stop offset="1" stopColor="#4F3815" stopOpacity=".82" />
            </linearGradient>
            <radialGradient id="engine-hot-glow">
              <stop offset="0" stopColor="#FFCD82" stopOpacity=".84" />
              <stop offset=".46" stopColor="#C87522" stopOpacity=".4" />
              <stop offset="1" stopColor="#FFCD82" stopOpacity="0" />
            </radialGradient>
            <marker id="engine-flow-arrow" markerHeight="8" markerWidth="8" orient="auto" refX="7" refY="4" viewBox="0 0 8 8">
              <path d="M0 0L8 4L0 8Z" fill="var(--aero-sun)" />
            </marker>
          </defs>
          <rect fill="url(#engine-blueprint-grid)" height="500" opacity=".34" width="900" x="0" y="0" />
          <path className="engine-datum" d="M58 250H858M168 42V458M264 42V458M438 42V458M544 42V458M676 42V458M806 42V458" />
          <path d="M94 250C94 165 152 96 248 76H654C734 76 782 112 820 170L846 216V284L820 330C782 388 734 424 654 424H248C152 404 94 335 94 250Z" fill="url(#engine-hot-glow)" opacity=".16" />
          <path className="engine-outer" d="M104 250V222C116 166 154 128 218 108C276 90 344 90 420 94H638C706 96 764 120 806 170L834 214V250Z" fill="url(#engine-casing)" />
          <path className="engine-outer" d="M104 250V278C116 334 154 372 218 392C276 410 344 410 420 406H638C706 404 764 380 806 330L834 286V250Z" fill="rgba(20,41,58,.76)" />
          <path className="engine-section-cut" d="M112 250V224C128 172 166 138 226 118C284 100 348 100 424 104H636C690 106 740 126 780 168L812 210L780 230L716 194H270C210 196 158 214 132 250Z" />
          <path className="engine-shell-float" d="M112 250V276C128 328 166 362 226 382C284 400 348 400 424 396H636C690 394 740 374 780 332L812 290L780 270L716 306H270C210 304 158 286 132 250Z" />
          <path className="engine-shell" d="M132 250V224C158 202 194 190 240 184H700L770 214V250Z" />
          <path className="engine-shell" d="M132 250V276C158 298 194 310 240 316H700L770 286V250Z" />
          <path className="engine-shell-float" d="M142 216C170 190 208 174 258 168H700L758 194L728 208H258C210 210 172 220 150 238Z" opacity=".7" />
          <path className="engine-shell-float" d="M142 284C170 310 208 326 258 332H700L758 306L728 292H258C210 290 172 280 150 262Z" opacity=".7" />
          <path className="engine-flow-bypass" d="M224 142C350 116 544 118 678 146C726 156 754 174 780 196" />
          <path className="engine-flow-bypass" d="M224 358C350 384 544 382 678 354C726 344 754 326 780 304" />
          <path className="engine-flow-core" d="M150 250H814" />
          <path className="engine-shaft" d="M150 250H752" />
          <path className="engine-panel" d="M226 204C286 190 368 188 448 198L470 212V288L448 302C368 312 286 310 226 296Z" fill="rgba(0,80,143,.38)" />
          <path className="engine-line" d="M226 204C292 194 368 194 448 202M226 296C292 306 368 306 448 298" opacity=".7" />
          <path className="engine-alert-zone" d="M348 198C368 194 388 194 406 196L416 208V292L406 304C388 306 368 306 348 302L338 290V210Z" />
          <path className="engine-section-cut" d="M448 202C468 198 492 200 512 210L548 230V270L512 290C492 300 468 302 448 298L462 278H492L518 264V236L492 222H462Z" />
          <circle cx="190" cy="250" fill="rgba(20,41,58,.96)" r="80" stroke="var(--aero-paper)" strokeWidth="3" />
          <circle cx="190" cy="250" fill="none" r="66" stroke="var(--aero-sky)" strokeWidth="1.4" />
          <g className="engine-rotor">
            <path d="M190 250L166 190C184 195 198 216 201 242C198 247 194 249 190 250Z" />
            <path d="M190 250L166 190C184 195 198 216 201 242C198 247 194 249 190 250Z" transform="rotate(36 190 250)" />
            <path d="M190 250L166 190C184 195 198 216 201 242C198 247 194 249 190 250Z" transform="rotate(72 190 250)" />
            <path d="M190 250L166 190C184 195 198 216 201 242C198 247 194 249 190 250Z" transform="rotate(108 190 250)" />
            <path d="M190 250L166 190C184 195 198 216 201 242C198 247 194 249 190 250Z" transform="rotate(144 190 250)" />
            <path d="M190 250L166 190C184 195 198 216 201 242C198 247 194 249 190 250Z" transform="rotate(180 190 250)" />
            <path d="M190 250L166 190C184 195 198 216 201 242C198 247 194 249 190 250Z" transform="rotate(216 190 250)" />
            <path d="M190 250L166 190C184 195 198 216 201 242C198 247 194 249 190 250Z" transform="rotate(252 190 250)" />
            <path d="M190 250L166 190C184 195 198 216 201 242C198 247 194 249 190 250Z" transform="rotate(288 190 250)" />
            <path d="M190 250L166 190C184 195 198 216 201 242C198 247 194 249 190 250Z" transform="rotate(324 190 250)" />
          </g>
          <circle cx="190" cy="250" fill="var(--aero-navy)" r="28" stroke="var(--aero-paper)" strokeWidth="2.4" />
          <circle cx="190" cy="250" fill="var(--aero-amber)" r="11" stroke="var(--aero-sun)" strokeWidth="2" />
          <g className="engine-ring" opacity=".95">
            <ellipse cx="270" cy="250" rx="10" ry="45" />
            <ellipse cx="308" cy="250" rx="11" ry="43" />
            <ellipse cx="346" cy="250" rx="11" ry="41" />
            <ellipse cx="384" cy="250" rx="12" ry="39" />
            <ellipse cx="422" cy="250" rx="12" ry="37" />
          </g>
          <g className="engine-rotor">
            <path d="M264 250C266 230 272 212 282 202C286 220 285 238 279 250C285 262 286 280 282 298C272 288 266 270 264 250Z" />
            <path d="M264 250C266 230 272 212 282 202C286 220 285 238 279 250C285 262 286 280 282 298C272 288 266 270 264 250Z" transform="rotate(180 270 250)" />
            <path d="M302 250C304 231 310 214 320 204C324 221 323 239 317 250C323 261 324 279 320 296C310 286 304 269 302 250Z" />
            <path d="M302 250C304 231 310 214 320 204C324 221 323 239 317 250C323 261 324 279 320 296C310 286 304 269 302 250Z" transform="rotate(180 308 250)" />
            <path d="M340 250C342 232 348 216 358 206C362 222 361 240 355 250C361 260 362 278 358 294C348 284 342 268 340 250Z" />
            <path d="M340 250C342 232 348 216 358 206C362 222 361 240 355 250C361 260 362 278 358 294C348 284 342 268 340 250Z" transform="rotate(180 346 250)" />
            <path d="M378 250C380 233 386 218 396 208C400 223 399 241 393 250C399 259 400 277 396 292C386 282 380 267 378 250Z" />
            <path d="M378 250C380 233 386 218 396 208C400 223 399 241 393 250C399 259 400 277 396 292C386 282 380 267 378 250Z" transform="rotate(180 384 250)" />
            <path d="M416 250C418 234 424 220 434 210C438 224 437 242 431 250C437 258 438 276 434 290C424 280 418 266 416 250Z" />
            <path d="M416 250C418 234 424 220 434 210C438 224 437 242 431 250C437 258 438 276 434 290C424 280 418 266 416 250Z" transform="rotate(180 422 250)" />
          </g>
          <g className="engine-stator">
            <path d="M248 204L262 225L256 250L248 225Z" /><path d="M248 296L262 275L256 250L248 275Z" />
            <path d="M286 206L300 226L294 250L286 226Z" /><path d="M286 294L300 274L294 250L286 274Z" />
            <path d="M324 208L338 228L332 250L324 228Z" /><path d="M324 292L338 272L332 250L324 272Z" />
            <path d="M362 210L376 230L370 250L362 230Z" /><path d="M362 290L376 270L370 250L362 270Z" />
            <path d="M400 212L414 232L408 250L400 232Z" /><path d="M400 288L414 268L408 250L400 268Z" />
          </g>
          <path className="engine-hot" d="M466 208H506C522 208 540 218 550 232V268C540 282 522 292 506 292H466L480 278H506C516 278 524 272 530 264V236C524 228 516 222 506 222H480Z" />
          <path className="engine-core" d="M480 222H506C516 222 524 228 530 236V264C524 272 516 278 506 278H480L492 266H504C510 266 514 260 518 254V246C514 240 510 234 504 234H492Z" />
          <path className="engine-bracket" d="M472 208V188M488 208V184M504 208V188M520 218V194M472 292V312M488 292V316M504 292V312M520 282V306" />
          <circle className="engine-dot" cx="480" cy="188" r="4" /><circle className="engine-dot" cx="496" cy="184" r="4" /><circle className="engine-dot" cx="512" cy="188" r="4" />
          <g className="engine-hot-blade">
            <path d="M568 250C570 234 576 218 586 208C590 224 589 240 583 250C589 260 590 276 586 292C576 282 570 266 568 250Z" />
            <path d="M568 250C570 234 576 218 586 208C590 224 589 240 583 250C589 260 590 276 586 292C576 282 570 266 568 250Z" transform="rotate(180 574 250)" />
            <path d="M610 250C612 236 618 222 628 214C632 228 631 242 625 250C631 258 632 272 628 286C618 278 612 264 610 250Z" />
            <path d="M610 250C612 236 618 222 628 214C632 228 631 242 625 250C631 258 632 272 628 286C618 278 612 264 610 250Z" transform="rotate(180 616 250)" />
            <path d="M652 250C654 238 660 226 670 220C674 232 673 244 667 250C673 256 674 268 670 280C660 274 654 262 652 250Z" />
            <path d="M652 250C654 238 660 226 670 220C674 232 673 244 667 250C673 256 674 268 670 280C660 274 654 262 652 250Z" transform="rotate(180 658 250)" />
          </g>
          <g className="engine-stator" opacity=".8">
            <path d="M550 214L564 232L558 250L550 232Z" /><path d="M550 286L564 268L558 250L550 268Z" />
            <path d="M592 218L606 234L600 250L592 234Z" /><path d="M592 282L606 266L600 250L592 266Z" />
            <path d="M634 222L648 236L642 250L634 236Z" /><path d="M634 278L648 264L642 250L634 264Z" />
          </g>
          <path className="engine-nozzle" d="M696 214H738L774 228L800 238V262L774 272L738 286H696L720 268H752L774 258V242L752 232H720Z" />
          <path className="engine-nozzle-flap" d="M774 228L806 238L828 244V256L806 262L774 272L790 256V244Z" />
          <path className="engine-line" d="M790 244V256M802 241V259M814 244V256M826 247V253" opacity=".78" />
          <ellipse className="engine-nozzle-flap" cx="832" cy="250" rx="5" ry="13" />
          <circle className="engine-alert-mark" cx="394" cy="250" r="7" />
          <path className="engine-alert-mark" d="M394 232L398 242H390Z" />
          <path className="engine-callout" d="M190 184L152 92H72" /><circle className="engine-dot" cx="190" cy="184" r="4" />
          <path className="engine-callout" d="M394 176V92H274" /><circle className="engine-dot" cx="394" cy="176" r="4" />
          <path className="engine-callout" d="M510 188L556 92H706" /><circle className="engine-dot" cx="510" cy="188" r="4" />
          <path className="engine-callout" d="M634 310V408H536" /><circle className="engine-dot" cx="634" cy="310" r="4" />
          <path className="engine-callout" d="M820 250H858V366" /><circle className="engine-dot" cx="820" cy="250" r="4" />
          <text className="engine-caption" x="72" y="70">INLET / FAN</text><text className="engine-caption" x="72" y="86">12-BLADE ROTOR</text>
          <text className="engine-caption" x="274" y="70">LPC / HPC</text><text className="engine-caption-hot" x="274" y="86">STAGE 03 / ALERT</text>
          <text className="engine-caption-hot" x="556" y="70">ANNULAR COMBUSTOR</text><text className="engine-caption-hot" x="556" y="86">HOT SECTION / HOLD</text>
          <text className="engine-caption" x="536" y="430">HPT / LPT TURBINE ROWS</text>
          <text className="engine-caption-hot" x="720" y="382">CONVERGENT NOZZLE</text><text className="engine-caption-hot" x="720" y="398">CORE EXHAUST / 6.8 MM/S</text>
          <text className="engine-caption" x="152" y="430">CUTAWAY / CASING SPLIT</text><text className="engine-caption" x="152" y="446">BYPASS DUCT / COLD SECTION</text>
          <text className="engine-caption-hot" x="704" y="150">CORE FLOW  →  EXHAUST</text><text className="engine-caption-hot" x="704" y="166">BYPASS FLOW  →  FAN STREAM</text>
        </svg>
        <div className="chamfer absolute bottom-0 right-0 w-[205px] bg-aero-paper p-4 text-aero-navy">
          <p className="aero-mono text-[8px] uppercase tracking-[.16em] text-aero-amber">Anomaly / 02</p>
          <p className="mt-2 text-[12px] font-semibold">Compressor stage 3</p>
          <p className="aero-mono mt-2 text-[9px]">6.8 mm/s · limit 5.0</p>
          <Button
            className="mt-3 h-auto rounded-none border-0 bg-transparent p-0 text-[11px] font-semibold text-aero-navy underline decoration-aero-blue underline-offset-4 hover:bg-transparent hover:text-aero-blue"
            onClick={onReviewTelemetry}
            type="button"
            variant="ghost"
          >
            Review telemetry
            <ArrowUpRight aria-hidden="true" className="ml-1 h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between border-t border-aero-paper/25 pt-3 aero-mono text-[9px] uppercase tracking-[.12em] text-aero-paper/60">
        <span>OPEN CASE / 04 STATIONS CAPTURED</span>
        <span>REGISTRATION 14:32:08 UTC</span>
      </div>
    </section>
  )
}
