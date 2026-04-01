import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    lesson_file: z.string().describe('Path to the lesson JSON file to export'),
    format: z
      .string()
      .describe('Export format (e.g. "pptx", "pdf", "docx", "html")'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const ExportTool = buildTool({
  name: 'export_lesson',
  searchHint: 'export lesson to pptx pdf docx',
  maxResultSizeChars: 50_000,
  async description() {
    return 'Export a lesson to a specific format (pptx, pdf, docx, html).'
  },
  userFacingName() {
    return 'Claw-ED Export'
  },
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isConcurrencySafe() {
    return true
  },
  isReadOnly() {
    return false
  },
  async checkPermissions(input) {
    return { behavior: 'allow', updatedInput: input }
  },
  async prompt() {
    return 'Export a lesson file. Provide the lesson file path and desired format.'
  },
  renderToolUseMessage(input) {
    return `Exporting: ${input.lesson_file ?? '...'} as ${input.format ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'export', input.lesson_file, '--format', input.format, '--json']
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.export })
    return { data: { result } }
  },
  mapToolResultToToolResultBlockParam(output, toolUseID) {
    return {
      tool_use_id: toolUseID,
      type: 'tool_result',
      content: JSON.stringify(output.result, null, 2),
    }
  },
} satisfies ToolDef<InputSchema, Output>)
