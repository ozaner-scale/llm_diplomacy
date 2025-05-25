# Diplomacy Web - Unified Frontend Application

This is a unified web application for Diplomacy that runs entirely as a single Python web app using FastAPI.

## Features

- Single-language implementation (Python)
- No separate frontend/backend - everything runs in one process
- Web-based UI using FastAPI with HTMX for interactivity
- **Play against AI bots** - Choose your power and play against 6 bot opponents
- **Solitaire mode** - Control all powers yourself
- **Interactive SVG map** - Visual game board showing units and territories
- **Multiple game variants** - Standard, France vs Austria, Germany vs Italy
- Deployable to Vercel or any Python hosting service

## Running Locally

### Install dependencies
```bash
uv sync
```

### Run the application
```bash
uv run diplomacy-web
```

Or alternatively:
```bash
uv run python main.py
```

The application will be available at http://localhost:8000

## How to Play

### Creating a Game

1. Visit the home page and click "Create New Game"
2. Give your game a name
3. Select a map variant:
   - **Standard** - Classic 7-player Diplomacy
   - **France vs Austria** - 2-player variant
   - **Germany vs Italy** - 2-player variant
4. Choose your power (or select Random)
5. Select game rules:
   - **CD_DUMMIES** (recommended) - Bots process turns immediately
   - **SOLITAIRE** - Control all powers yourself
   - **NO_PRESS** - No communication between players
   - **NO_CHECK** - Accept invalid orders (like face-to-face play)
   - And many more with helpful descriptions

### Playing the Game

1. **Movement Phase**: Submit orders for your units
   - Click "Possible Orders" to see valid moves
   - Bots will hold all their units by default
2. **Process Phase**: Click the green "Process Phase" button
3. **View Results**: See the outcome of all orders
4. **Continue**: Game advances to next phase automatically

### Game Modes

- **Single Player vs Bots**: You control one power, AI controls the rest
- **Solitaire**: You control all powers (good for learning or testing strategies)

## Bot Behavior

With the CD_DUMMIES rule enabled:
- Bots process their turns immediately
- In movement phases: all units HOLD
- In retreat phases: all units DISBAND
- In build phases: builds are WAIVED

This creates a passive opponent that maintains board presence but doesn't actively compete.

## Map Visualization

The game includes the original SVG maps from Diplomacy:
- Territory ownership shown by color
- Units displayed on the map
- Supply centers marked
- Interactive elements for order entry (coming soon)

## Game Storage

Currently, games are stored in-memory, which means they'll be lost when the server restarts. Future improvements could include:
- Persistent storage (SQLite, PostgreSQL)
- Game state serialization to JSON files
- Browser local storage for client-side persistence

## Deployment to Vercel

1. Install Vercel CLI: `npm i -g vercel`
2. Run `vercel` in the project directory
3. Follow the prompts to deploy

The application uses serverless Python functions on Vercel.

## Future Enhancements

- **Smarter AI**: Implement actual Diplomacy AI strategies
- **Multiplayer**: WebSocket support for real-time multiplayer
- **Order Drawing**: Click on map to create orders
- **Negotiations**: Chat system for games without NO_PRESS
- **Statistics**: Track game history and player performance
- **Mobile App**: Progressive Web App for mobile play

## Architecture

The application is structured as:
- `main.py` - FastAPI application with all routes
- `templates/` - Jinja2 HTML templates
- `static/` - Static assets (CSS, JS, images)
- `diplomacy/` - Core game engine (unchanged from original)

The game engine remains unchanged, allowing for easy updates and compatibility with existing game logic. 