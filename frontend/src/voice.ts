export type StopMicrophoneStream = () => Promise<void>

type MicrophoneStreamOptions = {
  socket: WebSocket
  targetSampleRate: number
}

function downsampleBuffer(input: Float32Array, inputSampleRate: number, outputSampleRate: number): Int16Array {
  if (outputSampleRate > inputSampleRate) {
    throw new Error('Output sample rate must be lower than or equal to the input sample rate.')
  }

  if (outputSampleRate === inputSampleRate) {
    const directBuffer = new Int16Array(input.length)
    for (let index = 0; index < input.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, input[index]))
      directBuffer[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
    }
    return directBuffer
  }

  const sampleRateRatio = inputSampleRate / outputSampleRate
  const outputLength = Math.round(input.length / sampleRateRatio)
  const outputBuffer = new Int16Array(outputLength)
  let outputIndex = 0
  let inputIndex = 0

  while (outputIndex < outputLength) {
    const nextInputIndex = Math.round((outputIndex + 1) * sampleRateRatio)
    let accumulatedValue = 0
    let sampleCount = 0

    for (let index = inputIndex; index < nextInputIndex && index < input.length; index += 1) {
      accumulatedValue += input[index]
      sampleCount += 1
    }

    const averagedSample = sampleCount > 0 ? accumulatedValue / sampleCount : 0
    const clampedSample = Math.max(-1, Math.min(1, averagedSample))
    outputBuffer[outputIndex] = clampedSample < 0 ? clampedSample * 0x8000 : clampedSample * 0x7fff

    outputIndex += 1
    inputIndex = nextInputIndex
  }

  return outputBuffer
}

function encodePcmChunk(channelData: Float32Array, inputSampleRate: number, outputSampleRate: number): ArrayBuffer {
  const downsampledBuffer = downsampleBuffer(channelData, inputSampleRate, outputSampleRate)
  return downsampledBuffer.buffer.slice(0)
}

export async function startMicrophoneStreaming(options: MicrophoneStreamOptions): Promise<StopMicrophoneStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('Microphone capture is not available in this browser.')
  }

  const mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  })

  const audioContext = new AudioContext()
  await audioContext.resume()

  const source = audioContext.createMediaStreamSource(mediaStream)
  const processor = audioContext.createScriptProcessor(4096, 1, 1)
  const silentGain = audioContext.createGain()
  silentGain.gain.value = 0

  processor.onaudioprocess = (event) => {
    if (options.socket.readyState !== WebSocket.OPEN) {
      return
    }

    const pcmChunk = encodePcmChunk(event.inputBuffer.getChannelData(0), audioContext.sampleRate, options.targetSampleRate)
    if (pcmChunk.byteLength > 0) {
      options.socket.send(pcmChunk)
    }
  }

  source.connect(processor)
  processor.connect(silentGain)
  silentGain.connect(audioContext.destination)

  return async () => {
    processor.onaudioprocess = null
    processor.disconnect()
    source.disconnect()
    silentGain.disconnect()
    mediaStream.getTracks().forEach((track) => track.stop())
    if (audioContext.state !== 'closed') {
      await audioContext.close()
    }
  }
}