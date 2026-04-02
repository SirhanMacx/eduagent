import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    lesson_file: z.string().describe('Path to the lesson JSON file'),
    format: z
      .string()
      .optional()
      .describe('Materials format (e.g. "handout", "slides", "worksheet")'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const MaterialsTool = buildTool({
  name: 'generate_materials',
  searchHint: 'handout worksheet supplemental materials resource printable',
  maxResultSizeChars: 200_000,
  async description() {
    return 'Generate supplemental materials (handouts, worksheets, slides) from a lesson.'
  },
  userFacingName() {
    return 'Claw-ED Materials'
  },
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isConcurrencySafe() {
    return true
  },
  isReadOnly() {
    return true
  },
  async checkPermissions(input) {
    return { behavior: 'allow', updatedInput: input }
  },
  async prompt() {
    return 'Generate supplemental materials from a lesson. Provide the lesson file path and optionally a format.'
  },
  renderToolUseMessage(input) {
    return `Generating materials: ${input.lesson_file ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'materials', '--lesson', input.lesson_file]
    if (input.format) args.push('--format', input.format)
    args.push('--json')
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.materials })
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
