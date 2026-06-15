import { Typography } from "@mui/material"
import AspectRatioOutlinedIcon from "@mui/icons-material/AspectRatioOutlined"
import ToolRunner from "../../components/tools/ToolRunner"
import useDocumentTitle from "../../hooks/useDocumentTitle"

export default function ToolReframe() {
  useDocumentTitle("Reframe to Vertical")
  return (
    <ToolRunner
      title="Reframe to Vertical"
      description="Convert 16:9 landscape to 9:16 with face-tracking"
      icon={<AspectRatioOutlinedIcon fontSize="large" />}
      endpoint="/api/tools/reframe"
    >
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Auto-detects speakers using MediaPipe Face Detection and keeps them
        centered. Falls back to a static center crop if no face is found.
        Already-portrait videos are returned unchanged.
      </Typography>
    </ToolRunner>
  )
}
