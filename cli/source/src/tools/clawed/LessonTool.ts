import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    topic: z.string().describe('Lesson topic'),
    grade: z.string().describe('Grade level (e.g. "3", "K", "9-12")'),
    subject: z.string().describe('Subject area (e.g. "math", "science", "ela")'),
    format: z
      .string()
      .optional()
      .describe('Output format (e.g. "5e", "workshop", "direct")'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const LessonTool = buildTool({
  name: 'generate_lesson',
  searchHint: 'lesson plan teach create make unit handout worksheet',
  maxResultSizeChars: 200_000,
  async description() {
    return 'Generate a standards-aligned lesson plan using the Claw-ED engine.'
  },
  userFacingName() {
    return 'Claw-ED Lesson'
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
    return 'Generate a lesson plan. Provide topic, grade, and subject. Optionally specify a format (5e, workshop, direct).'
  },
  renderToolUseMessage(input) {
    return `Generating lesson: ${input.topic ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'lesson', input.topic, '-g', input.grade, '-s', input.subject]
    if (input.format) args.push('--format', input.format)
    args.push('--json')
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.lesson })
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
