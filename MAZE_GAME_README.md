# Maze Game with Neurofeedback Integration

## Overview

A web-based procedural maze game that integrates with your neurofeedback module. The game uses the Recursive Backtracker algorithm to generate mazes and adjusts difficulty based on performance and EEG metrics using the `eeg_enhanced` DDA algorithm.

## Features

- **Procedural Maze Generation**: Mazes generated using Recursive Backtracker algorithm
- **Difficulty Scaling**: Maze size and complexity scale from 7x7 (easy) to 21x21 (expert)
- **Neurofeedback Control**: Movement commands sent via REST API from external neurofeedback module
- **Real-time EEG Metrics**: Display attention, cognitive load, and relaxation levels
- **DDA Integration**: Uses `eeg_enhanced` algorithm to adjust difficulty between sessions

## Setup Instructions

### 1. Database Migration

Add the new maze fields to the database:

```bash
# Using Flask-Migrate (recommended)
flask db migrate -m "Add maze game fields"
flask db upgrade

# OR using raw SQL (if Flask-Migrate not set up)
sqlite3 instance/neurofeedback.db < migrations/add_maze_fields.sql
```

### 2. Seed Maze Game

```bash
python3 seed_maze_game.py
```

This creates a new game entry with:
- Name: "NeuroFeedback Maze"
- Slug: "neurofeedback-maze"
- Game Type: "maze"
- DDA Algorithm: "eeg_enhanced"
- Difficulty Range: 1-10

### 3. Start the Application

```bash
python3 main.py
```

Navigate to http://localhost:5000, login, and go to Games page.

## Architecture

### Backend Components

**Maze Generator** (`app/services/maze_generator.py`)
- `MazeGenerator` class with Recursive Backtracker algorithm
- Difficulty-based size mapping (1-10 → 7x7 to 21x21)
- Returns maze as 2D boolean array with start/goal positions

**API Endpoints** (`app/routes/api.py`)
- `POST /api/maze/session/start` - Create session, generate maze
- `POST /api/maze/command` - Process neurofeedback movement commands
- `GET /api/maze/session/<id>/state` - Get current game state
- `POST /api/maze/session/<id>/end` - End session, calculate score, run DDA

**Database** (`app/models/session.py`)
- Added fields: `maze_data`, `moves_count`, `current_position_x`, `current_position_y`

### Frontend

**Template** (`app/templates/games/maze.html`)
- 600x600px HTML5 Canvas for maze rendering
- Real-time stats panel (difficulty, moves, time)
- EEG feedback bars (attention, cognitive load, relaxation)
- JavaScript game controller with state polling

## Neurofeedback Module Integration

### Getting Session ID

When the maze game loads, the session ID is stored in `localStorage`:

```javascript
const sessionId = localStorage.getItem('maze_session_id');
```

### Sending Movement Commands

Your neurofeedback module should POST to `/api/maze/command`:

```bash
curl -X POST http://localhost:5000/api/maze/command \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<flask-session-cookie>" \
  -d '{
    "session_id": 123,
    "action": "move_left",
    "confidence": 0.85,
    "eeg_attention": 0.75,
    "eeg_cognitive_load": 0.5,
    "eeg_relaxation": 0.6
  }'
```

**Actions**: `move_up`, `move_down`, `move_left`, `move_right`

**Response**:
```json
{
  "valid": true,
  "message": "Moved successfully",
  "new_position": [3, 4],
  "reached_goal": false,
  "moves_count": 5,
  "confidence": 0.85
}
```

### Authentication

The neurofeedback module needs to authenticate to use the API:

**Option 1**: Share Flask session cookie
- Login via browser, extract session cookie
- Use cookie in API requests

**Option 2**: Implement API token authentication (future enhancement)

## Game Flow

1. User loads maze game → Frontend calls `/api/maze/session/start`
2. Backend generates maze, creates session, returns maze data
3. Frontend renders maze, stores session ID in localStorage
4. Neurofeedback module reads session ID from localStorage
5. Module sends movement commands to `/api/maze/command`
6. Backend validates moves, updates position, stores EEG data
7. Frontend polls `/api/maze/session/<id>/state` every 500ms
8. Frontend re-renders player position when state changes
9. When goal reached → Frontend calls `/api/maze/session/<id>/end`
10. Backend calculates score, runs DDA, returns next difficulty

## DDA Algorithm

Uses `eeg_enhanced` algorithm which considers:
- **Performance** (40%): Completion vs time limit
- **Efficiency** (30%): Actual moves vs optimal path
- **Brain State** (30%): Cognitive load and attention levels

**Difficulty Adjustment Rules**:
- High cognitive load (>0.75) → Decrease difficulty
- Low engagement (low load + high attention) → Increase difficulty
- Efficient completion → Increase difficulty
- Inefficient or incomplete → Decrease difficulty

## Maze Size Scaling

| Difficulty | Maze Size | Description |
|-----------|-----------|-------------|
| 1-2       | 7x7       | Easy - Quick to solve |
| 3         | 9x9       | Easy - Slightly larger |
| 4-5       | 11x11     | Medium - Moderate challenge |
| 6         | 13x13     | Medium - More complex |
| 7-8       | 15x15     | Hard - Significant challenge |
| 9         | 19x19     | Expert - Very challenging |
| 10        | 21x21     | Expert - Maximum difficulty |

## Testing

### Manual Testing

1. **Test Maze Generation**:
```python
python3 -c "from app.services.maze_generator import generate_maze; import json; print(json.dumps(generate_maze(5), indent=2))"
```

2. **Test API Endpoints** (requires running Flask app):
```bash
# Start session
curl -X POST http://localhost:5000/api/maze/session/start \
  -H "Content-Type: application/json" \
  -d '{"game_id": 1}' \
  -c cookies.txt

# Send command
curl -X POST http://localhost:5000/api/maze/command \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"session_id": 1, "action": "move_right", "confidence": 0.8, "eeg_attention": 0.7, "eeg_cognitive_load": 0.5}'

# Get state
curl http://localhost:5000/api/maze/session/1/state -b cookies.txt

# End session
curl -X POST http://localhost:5000/api/maze/session/1/end \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

3. **Test in Browser**:
- Login to app
- Navigate to Games page
- Click "Play Maze Game"
- Open browser console to see session ID
- Simulate commands using browser console:
```javascript
fetch('/api/maze/command', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    session_id: parseInt(localStorage.getItem('maze_session_id')),
    action: 'move_right',
    confidence: 0.85,
    eeg_attention: 0.75,
    eeg_cognitive_load: 0.5,
    eeg_relaxation: 0.6
  })
}).then(r => r.json()).then(console.log);
```

## Files Created/Modified

### New Files
- `app/services/maze_generator.py` - Maze generation service
- `app/templates/games/maze.html` - Maze game frontend
- `app/routes/games.py:play_maze_game` - Maze game route
- `migrations/add_maze_fields.sql` - Database migration
- `seed_maze_game.py` - Seed script
- `MAZE_GAME_README.md` - This documentation

### Modified Files
- `app/models/session.py` - Added maze fields to GameSession
- `app/routes/api.py` - Added 4 maze API endpoints
- `app/templates/games/list.html` - Added maze game support

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "ModuleNotFoundError: No module named 'flask'" | Activate venv: `source venv/bin/activate` or `venv\Scripts\activate` |
| "Table game_sessions has no column maze_data" | Run database migration (see Setup step 1) |
| "Game not found" | Run seed script: `python3 seed_maze_game.py` |
| API returns 401 Unauthorized | Ensure Flask session cookie is passed in requests |
| Maze not rendering | Check browser console for errors, verify session started successfully |
| Position not updating | Check state polling interval (500ms), verify neurofeedback commands are being sent |

## Next Steps

1. Run database migration
2. Seed the maze game
3. Test in browser
4. Integrate your neurofeedback module
5. Test end-to-end with real EEG data

## Support

For issues or questions, check the implementation files:
- Maze generation: `app/services/maze_generator.py`
- API endpoints: `app/routes/api.py` (lines with "MAZE GAME")
- Frontend: `app/templates/games/maze.html`
- Models: `app/models/session.py` (maze fields)
