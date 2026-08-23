import type { MetricItem } from "@/types/aeroloop"

interface MissionMetricsProps {
  metrics: MetricItem[]
}

export function MissionMetrics({ metrics }: MissionMetricsProps) {
  return (
    <section
      aria-label="Mission status"
      className="mission-metrics flex items-stretch border-b border-aero-navy bg-aero-navy text-aero-paper"
    >
      {metrics.map((metric, index) => (
        <div
          className={`mission-metric ${index === 0 || index === metrics.length - 1 ? "w-40" : "flex-1"} ${index < metrics.length - 1 ? "border-r border-aero-paper/25" : ""} px-6 py-5`}
          key={metric.label}
        >
          <p className={`aero-mono text-[9px] uppercase tracking-[.14em] ${index === 0 ? "text-aero-sun" : "text-aero-paper/55"}`}>
            {metric.label}
          </p>
          <p className={`aero-display mt-2 leading-none ${index === 0 ? "text-[25px]" : index === 1 ? "mt-1 text-[43px]" : index === 2 ? "text-[26px]" : "text-[36px]"} ${metric.emphasis ? "text-aero-sun" : ""}`}>
            {metric.value}
            {metric.detail && index === 1 ? (
              <span className="ml-1 text-[20px] text-aero-paper/55">{metric.detail}</span>
            ) : null}
          </p>
          {metric.detail && index !== 1 ? (
            <p className={`aero-mono mt-1 text-[9px] uppercase ${metric.emphasis ? "text-aero-paper/55" : "text-aero-paper/55"}`}>
              {metric.detail}
            </p>
          ) : null}
        </div>
      ))}
    </section>
  )
}
