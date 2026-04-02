import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    path: z.string().describe('Path to file or directory to ingest'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const IngestTool = buildTool({
  name: 'ingest_files',
  searchHint: 'ingest curriculum files into knowledge base',
  maxResultSizeChars: 100_000,
  async description() {
    return 'Ingest curriculum files into the Claw-ED knowledge base.'
  },
  userFacingName() {
    return 'Claw-ED Ingest'
  },
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  isConcurrencySafe() {
    return false
  },
  isReadOnly() {
    return false
  },
  async checkPermissions(input) {
    return { behavior: 'allow', updatedInput: input }
  },
  async prompt() {
    return 'Ingest curriculum files. Provide the path to a file or directory.'
  },
  renderToolUseMessage(input) {
    return `Ingesting: ${input.path ?? '...'}`
  },
  async call(input) {
    const args = ['-m', 'clawed', 'ingest', input.path, '--json']
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.ingest })
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
