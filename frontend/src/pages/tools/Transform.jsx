import { useState } from "react"
import {
  Box, Typography, ToggleButtonGroup, ToggleButton, Stack, Slider,
} from "@mui/material"
import TransformIcon from "@mui/icons-material/Transform"
import ToolRunner from "../../components/tools/ToolRunner"
import useDocumentTitle from "../../hooks/useDocumentTitle"

const OPS = [
  { v: "flip_h", label: "Flip ◀▶" },
  { v: "flip_v", label: "Flip ▲▼" },
  { v: "rotate_cw", label: "Rotate ⟳" },
  { v: "rotate_ccw", label: "Rotate ⟲" },
  { v: "rotate_180", label: "Rotate 180°" },
  { v: "loop", label: "Loop" },
  { v: "volume", label: "Volume" },
]
const VOL_PRESETS = [
  { v: 0, label: "Mute" },
  { v: 0.5, label: "−50%" },
  { v: 1.5, label: "+50%" },
  { v: 2, label: "2×" },
]

export default function ToolTransform() {
  useDocumentTitle("Transform")
  const [operation, setOperation] = useState("flip_h")
  const [loopCount, setLoopCount] = useState(2)
  const [volume, setVolume] = useState(2)

  const amount = operation === "loop" ? String(loopCount) : operation === "volume" ? String(volume) : ""

  return (
    <ToolRunner
      title="Transform"
      description="Quick edits — flip, rotate, loop, or change a clip's volume"
      icon={<TransformIcon fontSize="large" />}
      endpoint="/api/tools/transform"
      fieldBuilder={() => ({ operation, amount })}
    >
      <Stack spacing={2}>
        <Box>
          <Typography variant="caption" sx={{ fontWeight: 600, display: "block", mb: 1 }}>Operation</Typography>
          <ToggleButtonGroup
            exclusive size="small" value={operation}
            onChange={(_e, v) => v && setOperation(v)}
            sx={{ flexWrap: "wrap", gap: 0.5, "& .MuiToggleButtonGroup-grouped": { border: 1, borderColor: "divider", borderRadius: "8px !important", mx: 0 } }}
          >
            {OPS.map((o) => <ToggleButton key={o.v} value={o.v} sx={{ textTransform: "none" }}>{o.label}</ToggleButton>)}
          </ToggleButtonGroup>
        </Box>

        {operation === "loop" && (
          <Box>
            <Typography variant="caption" sx={{ fontWeight: 600, display: "block", mb: 0.5 }}>
              Repeat the clip {loopCount}× (back-to-back)
            </Typography>
            <Slider value={loopCount} onChange={(_e, v) => setLoopCount(v)} min={2} max={20} step={1} marks valueLabelDisplay="auto" sx={{ maxWidth: 360 }} />
          </Box>
        )}

        {operation === "volume" && (
          <Box>
            <Typography variant="caption" sx={{ fontWeight: 600, display: "block", mb: 1 }}>Volume</Typography>
            <ToggleButtonGroup exclusive size="small" value={volume} onChange={(_e, v) => v !== null && setVolume(v)}>
              {VOL_PRESETS.map((p) => <ToggleButton key={p.v} value={p.v} sx={{ textTransform: "none" }}>{p.label}</ToggleButton>)}
            </ToggleButtonGroup>
          </Box>
        )}
      </Stack>
    </ToolRunner>
  )
}
