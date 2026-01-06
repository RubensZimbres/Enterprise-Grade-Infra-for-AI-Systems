import '@testing-library/jest-dom'
import { TextEncoder, TextDecoder } from 'util'
import { ReadableStream, TransformStream } from 'stream/web'

Object.assign(global, { TextEncoder, TextDecoder, ReadableStream, TransformStream })