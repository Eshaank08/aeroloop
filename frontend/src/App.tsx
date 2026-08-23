import { AeroLoopShell } from "@/components/aeroloop/AeroLoopShell"
import { aeroLoopData } from "@/data/aeroloop"
import type { AeroLoopAppProps } from "@/types/aeroloop"

function App({ data = aeroLoopData }: AeroLoopAppProps) {
  return <AeroLoopShell data={data} />
}

export default App
