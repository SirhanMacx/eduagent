import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    query: z.string().describe('Search query for curriculum content'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const SearchCurriculumTool = buildTool({
  name: 'search_curriculum',
  searchHint: 'search find curriculum knowledge base look up topic',
  maxResultSizeChars: 100_000,
  async description() {
    return 'Search the ingested curriculum knowledge base.'
  },
  userFacingName() {
    return 'Claw-ED Search'
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
    return 'Search curriculum content. Provide a search query.'
  },
  renderToolUseMessage(input) {
    return `Searching: ${input.query ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'search', input.query, '--json']
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.search })
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
