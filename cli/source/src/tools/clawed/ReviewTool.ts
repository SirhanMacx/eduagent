import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    lesson_file: z.string().describe('Path to the lesson JSON file to review'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const ReviewTool = buildTool({
  name: 'review_output',
  searchHint: 'review and score lesson quality',
  maxResultSizeChars: 100_000,
  async description() {
    return 'Review and score a generated lesson for quality and alignment.'
  },
  userFacingName() {
    return 'Claw-ED Review'
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
    return 'Review a lesson file for quality. Provide the lesson file path.'
  },
  renderToolUseMessage(input) {
    return `Reviewing: ${input.lesson_file ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'review', input.lesson_file, '--json']
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.review })
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
