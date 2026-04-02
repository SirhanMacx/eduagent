import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() => z.strictObject({}))
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const PersonaTool = buildTool({
  name: 'get_persona',
  searchHint: 'persona teacher profile role configuration style voice',
  maxResultSizeChars: 50_000,
  async description() {
    return 'Show the current teacher persona configuration.'
  },
  userFacingName() {
    return 'Claw-ED Persona'
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
    return 'Show the current teacher persona. No inputs required.'
  },
  renderToolUseMessage() {
    return 'Fetching persona...'
  },
  async call(input) {
    const args = ['-m', 'clawed', 'persona', 'show', '--json']
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.persona })
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
