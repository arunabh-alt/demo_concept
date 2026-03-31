# Frontend

## Purpose

This frontend is a React TypeScript app for authenticated digital-twin voice commands.

Implemented features:

- signup form
- signin form
- JWT token persistence in local storage
- authenticated current-user fetch
- signout flow
- microphone capture and websocket streaming
- live transcript view for Amazon Transcribe output
- typed fallback command input for local testing
- structured digital-twin response panel

## Tech Stack

- React 19
- TypeScript 5
- Vite 6
- React Compiler via `babel-plugin-react-compiler`
- CSS for styling

## App Behavior

The frontend talks to the backend API at:

- `http://127.0.0.1:8000/api`

It also opens an authenticated websocket to:

- `ws://127.0.0.1:8000/api/voice/pipeline/ws?token=<jwt>`

Override with an environment variable if needed:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

## Install

```powershell
Set-Location frontend
npm install
```

## Run

```powershell
Set-Location frontend
npm run dev
```

Default local server:

- `http://127.0.0.1:5173`

## Build

```powershell
Set-Location frontend
npm run build
```

## Important Files

- `src/App.tsx`
- `src/api.ts`
- `src/voice.ts`
- `vite.config.ts`
- `package.json`