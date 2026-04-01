import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    lesson_file: z.string().describe('Path to the lesson JSON file to differentiate'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const DifferentiateTool = buildTool({
  name: 'differentiate_lesson',
  searchHint: 'adapt lesson for different learner levels',
  maxResultSizeChars: 200_000,
  async description() {
    return 'Differentiate a lesson for various learner levels.'
  },
  userFacingName() {
    return 'Claw-ED Differentiate'
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
    return 'Differentiate a lesson for multiple learner levels. Provide the lesson file path.'
  },
  renderToolUseMessage(input) {
    return `Differentiating: ${input.lesson_file ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'differentiate', input.lesson_file, '--json']
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.differentiate })
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
