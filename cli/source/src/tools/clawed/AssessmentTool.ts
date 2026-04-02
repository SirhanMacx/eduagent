import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    type: z
      .string()
      .describe('Assessment type (e.g. "formative", "summative", "diagnostic")'),
    topic: z.string().describe('Assessment topic'),
    grade: z.string().describe('Grade level'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const AssessmentTool = buildTool({
  name: 'generate_assessment',
  searchHint: 'test quiz assessment exam evaluate formative summative diagnostic',
  maxResultSizeChars: 200_000,
  async description() {
    return 'Generate an assessment (formative, summative, or diagnostic).'
  },
  userFacingName() {
    return 'Claw-ED Assessment'
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
    return 'Generate an assessment. Provide the type, topic, and grade level.'
  },
  renderToolUseMessage(input) {
    return `Generating ${input.type ?? ''} assessment: ${input.topic ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'assess', input.type, input.topic, '-g', input.grade, '--json']
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.assess })
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
