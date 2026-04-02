import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    grade: z.string().describe('Grade level'),
    subject: z.string().describe('Subject area'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const StandardsTool = buildTool({
  name: 'get_standards',
  searchHint: 'list curriculum standards for grade and subject',
  maxResultSizeChars: 100_000,
  async description() {
    return 'List curriculum standards for a given grade and subject.'
  },
  userFacingName() {
    return 'Claw-ED Standards'
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
    return 'List curriculum standards. Provide grade and subject.'
  },
  renderToolUseMessage(input) {
    return `Fetching standards: grade ${input.grade ?? '...'}, ${input.subject ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'standards', 'list', '-g', input.grade, '-s', input.subject, '--json']
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.standards })
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
