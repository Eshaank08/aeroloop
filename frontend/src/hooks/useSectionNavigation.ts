import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react"
import type { SectionId } from "@/types/aeroloop"

const swipeThreshold = 72

export function useSectionNavigation(sectionIds: SectionId[], isMotionPaused: boolean) {
  const [activeSection, setActiveSection] = useState<SectionId>(sectionIds[0] ?? "active-run")
  const swipeStart = useRef<{ x: number; y: number; pointerId: number } | null>(null)

  const setCurrent = useCallback((sectionId: SectionId) => setActiveSection(sectionId), [])

  const scrollToSection = useCallback((sectionId: SectionId) => {
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: isMotionPaused ? "auto" : "smooth",
      block: "start",
      inline: "nearest",
    })
    setCurrent(sectionId)
  }, [isMotionPaused, setCurrent])

  useEffect(() => {
    const observedSections = sectionIds
      .map((id) => document.getElementById(id))
      .filter((section): section is HTMLElement => Boolean(section))
    if (!observedSections.length) return

    const observer = new IntersectionObserver(
      (entries) => entries.forEach((entry) => {
        if (entry.isIntersecting) setCurrent(entry.target.id as SectionId)
      }),
      { rootMargin: "-22% 0px -64% 0px", threshold: 0 },
    )
    observedSections.forEach((section) => observer.observe(section))
    return () => observer.disconnect()
  }, [sectionIds, setCurrent])

  const onPointerDown = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    if (event.button !== 0) return
    if ((event.target as HTMLElement).closest("a,button,textarea,input,select,[data-no-swipe]")) return
    swipeStart.current = { x: event.clientX, y: event.clientY, pointerId: event.pointerId }
    event.currentTarget.setPointerCapture?.(event.pointerId)
  }, [])

  const onPointerMove = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    const start = swipeStart.current
    if (!start || event.pointerId !== start.pointerId) return
    const deltaX = event.clientX - start.x
    const deltaY = event.clientY - start.y
    if (deltaX <= swipeThreshold || Math.abs(deltaX) <= Math.abs(deltaY) * 1.2) return

    const currentIndex = sectionIds.indexOf(activeSection)
    const nextSection = sectionIds[Math.min(sectionIds.length - 1, Math.max(0, currentIndex + 1))]
    swipeStart.current = null
    if (nextSection && nextSection !== activeSection) scrollToSection(nextSection)
  }, [activeSection, scrollToSection, sectionIds])

  const onPointerUp = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    if (swipeStart.current?.pointerId === event.pointerId) swipeStart.current = null
  }, [])

  return {
    activeSection,
    scrollToSection,
    swipeHandlers: { onPointerDown, onPointerMove, onPointerUp },
  }
}
