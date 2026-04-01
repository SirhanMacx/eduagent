import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    topic: z.string().describe('Game topic'),
    grade: z.string().describe('Grade level'),
    subject: z.string().describe('Subject area'),
    style: z
      .string()
      .optional()
      .describe('Game style (e.g. "quiz", "matching", "adventure")'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const GameTool = buildTool({
  name: 'generate_game',
  searchHint: 'create educational game for a topic',
  maxResultSizeChars: 200_000,
  async description() {
    return 'Generate an educational game using the Claw-ED engine.'
  },
  userFacingName() {
    return 'Claw-ED Game'
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
    return 'Generate an educational game. Provide topic, grade, and subject. Optionally specify a style.'
  },
  renderToolUseMessage(input) {
    return `Generating game: ${input.topic ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'game', 'create', input.topic, '-g', input.grade, '-s', input.subject]
    if (input.style) args.push('--style', input.style)
    args.push('--json')
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.game })
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
