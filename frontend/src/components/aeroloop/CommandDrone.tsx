import { motion, useAnimationFrame, useMotionValue, useReducedMotion, useTransform } from "motion/react"

interface CommandDroneProps {
  isVisible: boolean
  isMotionPaused: boolean
}

export function CommandDrone({ isVisible, isMotionPaused }: CommandDroneProps) {
  const prefersReducedMotion = Boolean(useReducedMotion())
  const patrolProgress = useMotionValue(0)
  const x = useTransform(patrolProgress, [0, 0.38, 0.58, 1], [0, 238, 148, 0])
  const y = useTransform(patrolProgress, [0, 0.38, 0.58, 1], [0, -2, 2, 0])
  const rotate = useTransform(patrolProgress, [0, 0.38, 0.58, 1], [0, 2, -2, 0])

  useAnimationFrame((_time, delta) => {
    if (!isVisible || isMotionPaused || prefersReducedMotion) return
    patrolProgress.set((patrolProgress.get() + Math.min(delta, 80) / 6200) % 1)
  })

  return (
    <motion.div
      aria-hidden="true"
      animate={{ opacity: isVisible ? 1 : 0 }}
      className="command-drone pointer-events-none absolute z-20"
      hidden={!isVisible}
      id="command-drone"
      initial={false}
      style={{
        display: isVisible ? "block" : "none",
        visibility: isVisible ? "visible" : "hidden",
        x: isVisible && !prefersReducedMotion ? x : 0,
        y: isVisible && !prefersReducedMotion ? y : 0,
        rotate: isVisible && !prefersReducedMotion ? rotate : 0,
      }}
      transition={{ duration: 0.18, ease: "easeOut" }}
    >
      <svg fill="none" viewBox="0 0 58 28">
        <path className="command-drone-arm" d="M18 10L8 5M18 18L8 23M40 10L50 5M40 18L50 23" />
        <circle className="command-drone-rotor" cx="7" cy="4.5" r="3.3" /><circle className="command-drone-rotor-ring" cx="7" cy="4.5" r="1.5" />
        <circle className="command-drone-rotor" cx="7" cy="23.5" r="3.3" /><circle className="command-drone-rotor-ring" cx="7" cy="23.5" r="1.5" />
        <circle className="command-drone-rotor" cx="51" cy="4.5" r="3.3" /><circle className="command-drone-rotor-ring" cx="51" cy="4.5" r="1.5" />
        <circle className="command-drone-rotor" cx="51" cy="23.5" r="3.3" /><circle className="command-drone-rotor-ring" cx="51" cy="23.5" r="1.5" />
        <path className="command-drone-shell" d="M17 9L27 6.5H35L43 9L47 14L43 19L35 21.5H27L17 19L13 14Z" />
        <path className="command-drone-panel" d="M24 8.5L29 7.5V20.5L24 19Z" /><path className="command-drone-panel" d="M34 7.5L39 8.5V19L34 20.5Z" />
        <path className="command-drone-window" d="M28 10H34L36 14L34 18H28L26 14Z" /><circle className="command-drone-lens" cx="31" cy="14" r="1.8" />
        <path className="command-drone-signal" d="M31 3V1M28 3L27 1M34 3L35 1" /><path d="M43 12L47 14L43 16" stroke="var(--aero-sun)" strokeWidth="1.2" />
      </svg>
    </motion.div>
  )
}
