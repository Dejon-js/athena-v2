# ATHENA v2.2 Frontend

React-based dashboard for the ATHENA NFL DFS optimizer system.

## Features

- Real-time system status monitoring
- Live thought stream from backend modules
- Conversational AI interface ("Ask ATHENA")
- Performance metrics and analytics
- Lineup optimization controls

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start the development server:
```bash
npm start
```

The application will open at http://localhost:3000

## Environment Variables

- `REACT_APP_API_URL`: Backend API URL (default: http://localhost:8000)
- `REACT_APP_WS_URL`: WebSocket URL (default: ws://localhost:8000)

## Architecture

- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **Recharts** for data visualization
- **Lucide React** for icons
- **WebSocket** for real-time updates

## Components

- `Dashboard`: Main overview with metrics and charts
- `StatusPanel`: Detailed system and module status
- `ChatInterface`: Conversational AI interface
- `ThoughtStream`: Real-time activity feed
- `ApiService`: Backend API integration
- `WebSocketService`: Real-time communication
