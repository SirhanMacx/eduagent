import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() => z.strictObject({}))
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const StudentsTool = buildTool({
  name: 'get_students',
  searchHint: 'students roster class list learners groups',
  maxResultSizeChars: 50_000,
  async description() {
    return 'List students configured in the current workspace.'
  },
  userFacingName() {
    return 'Claw-ED Students'
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
    return 'List students in the current workspace. No inputs required.'
  },
  renderToolUseMessage() {
    return 'Fetching students...'
  },
  async call(input) {
    const args = ['-m', 'clawed', 'workspace', 'students', '--json']
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.students })
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
