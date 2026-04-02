import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { spawnPython, TIMEOUT_BY_COMMAND } from './_bridge.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    n: z
      .number()
      .optional()
      .describe('Number of training iterations'),
    drive: z
      .string()
      .optional()
      .describe('Google Drive folder ID for training data'),
    path: z
      .string()
      .optional()
      .describe('Local path to training data'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

type Output = { result: unknown }

export const TrainTool = buildTool({
  name: 'train_model',
  searchHint: 'train benchmark fine-tune model calibrate improve',
  maxResultSizeChars: 100_000,
  async description() {
    return 'Train and benchmark the Claw-ED generation model.'
  },
  userFacingName() {
    return 'Claw-ED Train'
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
    return 'Train the model. Optionally provide iteration count, drive folder, or local path.'
  },
  renderToolUseMessage() {
    return 'Training model...'
  },
  async call(input) {
    const args = ['-m', 'clawed', 'train', '--benchmark']
    if (input.n) args.push('-n', String(input.n))
    if (input.drive) args.push('--drive', input.drive)
    if (input.path) args.push('--path', input.path)
    args.push('--json')
    const result = await spawnPython(args, { timeout: TIMEOUT_BY_COMMAND.train })
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
