import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    topic: z.string().describe('Unit topic'),
    grade: z.string().describe('Grade level'),
    subject: z.string().describe('Subject area'),
    weeks: z
      .number()
      .optional()
      .describe('Number of weeks for the unit (default: 2)'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const UnitTool = buildTool({
  name: 'generate_unit',
  searchHint: 'unit plan multi-week scope sequence curriculum map',
  maxResultSizeChars: 300_000,
  async description() {
    return 'Generate a multi-week unit plan using the Claw-ED engine.'
  },
  userFacingName() {
    return 'Claw-ED Unit'
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
    return 'Generate a unit plan. Provide topic, grade, subject, and optionally the number of weeks.'
  },
  renderToolUseMessage(input) {
    return `Generating unit: ${input.topic ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'unit', input.topic, '-g', input.grade, '-s', input.subject]
    if (input.weeks) args.push('--weeks', String(input.weeks))
    args.push('--json')
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.unit })
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
