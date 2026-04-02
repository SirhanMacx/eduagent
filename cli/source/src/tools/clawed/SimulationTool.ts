import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    topic: z.string().describe('Simulation topic'),
    grade: z.string().describe('Grade level'),
    subject: z.string().describe('Subject area'),
    type: z
      .string()
      .optional()
      .describe('Simulation type (e.g. "physics", "chemistry", "math", "biology")'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const SimulationTool = buildTool({
  name: 'create_simulation',
  searchHint: 'simulation experiment explore interactive physics chemistry math biology',
  maxResultSizeChars: 200_000,
  async description() {
    return 'Generate an interactive HTML simulation for exploring scientific concepts.'
  },
  userFacingName() {
    return 'Claw-ED Simulation'
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
    return 'Generate an interactive simulation. Provide topic, grade, and subject. Optionally specify a type (physics, chemistry, math, biology).'
  },
  renderToolUseMessage(input) {
    return `Generating simulation: ${input.topic ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'simulate', 'create', input.topic, '-g', input.grade, '-s', input.subject]
    if (input.type) args.push('--type', input.type)
    args.push('--json')
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.simulate })
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
