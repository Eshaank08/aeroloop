export const padStage = (value: number) => String(value).padStart(2, "0")

export const utcTime = (date: Date) =>
  date.toLocaleTimeString("en-GB", { hour12: false }).slice(0, 8)

export const stageLabel = (value: number) => `STAGE ${padStage(value)}`

export const escapeHtml = (value: string) =>
  value.replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }
    return entities[character] ?? character
  })
