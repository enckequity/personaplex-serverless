# PersonaPlex Serverless Worker

RunPod Serverless worker for real-time voice AI using NVIDIA PersonaPlex.

## Features

- Full-duplex speech-to-speech conversation
- WebSocket streaming for low latency
- Persona customization via text prompts
- Voice selection (multiple natural and variety voices)

## Deployment

1. Push to GitHub (triggers build via Actions)
2. Add `HF_TOKEN` secret to GitHub repo settings
3. Create RunPod Serverless endpoint with the image
4. Configure TCP port 8998 exposure

## Environment Variables

- `HF_TOKEN` - HuggingFace token (required for model download)

## API

WebSocket endpoint: `wss://<worker-ip>:<port>/api/chat?text_prompt=<persona>&voice_prompt=<voice>`

### Parameters

- `text_prompt` - Persona description (URL encoded)
- `voice_prompt` - Voice ID (NATF0-3, NATM0-3, VARF0-4, VARM0-4)
