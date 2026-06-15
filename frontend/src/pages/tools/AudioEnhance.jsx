import { Typography } from "@mui/material"
import GraphicEqOutlinedIcon from "@mui/icons-material/GraphicEqOutlined"
import ToolRunner from "../../components/tools/ToolRunner"
import useDocumentTitle from "../../hooks/useDocumentTitle"

export default function ToolAudioEnhance() {
  useDocumentTitle("Enhance Audio")
  return (
    <ToolRunner
      title="Enhance Audio"
      description="Denoise hiss, normalize loudness, polish speech"
      icon={<GraphicEqOutlinedIcon fontSize="large" />}
      endpoint="/api/tools/audio-enhance"
    >
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Applies noise suppression, high-pass filtering, de-essing, and EBU R128
        loudness normalization to -16 LUFS. No configuration needed — the
        defaults work for 99% of talking-head content.
      </Typography>
    </ToolRunner>
  )
}
