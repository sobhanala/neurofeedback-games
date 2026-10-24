# Maze Game Updates - No Down Movement

## Changes Made

### 1. Flickering Dot Indicator
- Added a red flickering dot above the player (blue circle)
- Flickers every 300ms to indicate upward movement direction
- Visual cue helps guide player toward the goal at the top

### 2. Removed Down Movement
- **API**: Removed `move_down` from action_map in `/api/maze/command`
- **Allowed movements**: `move_up`, `move_left`, `move_right` only
- **Frontend**: Updated instructions to clarify no down movement

### 3. Maze Generation Updated
- **Start position**: Bottom of maze (row near size-2)
- **Goal position**: Top of maze (row near 1)
- **Validation**: All generated mazes are verified to be solvable using only up/left/right
- **Fallback**: If random generation fails, forces a guaranteed upward-solvable path

## Technical Details

**Maze Layout**
```
#######
#    G#  <- Goal (top, green star)
##### #
#     #
# #####
#S    #  <- Start (bottom, blue circle + flickering red dot above)
#######
```

**Movement Commands**
```json
{
  "session_id": 123,
  "action": "move_up",      // Valid
  "action": "move_left",    // Valid  
  "action": "move_right",   // Valid
  "action": "move_down",    // INVALID - returns error
  "confidence": 0.85,
  "eeg_attention": 0.75,
  "eeg_cognitive_load": 0.5,
  "eeg_relaxation": 0.6
}
```

**API Response for Invalid Action**
```json
{
  "error": "Invalid action"
}
```

## Files Modified

1. `app/templates/games/maze.html`
   - Added flickering dot rendering logic
   - Added `startFlicker()` function
   - Updated instructions section

2. `app/routes/api.py`
   - Removed `"move_down": (0, 1)` from action_map
   - Updated comment to reflect allowed movements

3. `app/services/maze_generator.py`
   - Complete rewrite with no-down-movement constraint
   - Start at bottom, goal at top
   - Added `_is_solvable_no_down()` validation using BFS
   - Added `_force_upward_path()` fallback

## Testing Results

All difficulty levels (1-10) generate mazes that are:
- ✓ Solvable using only up/left/right movements
- ✓ Start positioned at bottom
- ✓ Goal positioned at top
- ✓ Valid paths (not walls)

## Neurofeedback Integration

Your neurofeedback module should:
1. Only send `move_up`, `move_left`, or `move_right` actions
2. Avoid sending `move_down` (will return 400 error)
3. Watch for the flickering red dot as visual feedback for upward direction

## Example Usage

```bash
# Valid command
curl -X POST http://localhost:5000/api/maze/command \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "session_id": 1,
    "action": "move_up",
    "confidence": 0.85,
    "eeg_attention": 0.75,
    "eeg_cognitive_load": 0.5
  }'

# Invalid command (will fail)
curl -X POST http://localhost:5000/api/maze/command \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "session_id": 1,
    "action": "move_down",  # ERROR
    "confidence": 0.85
  }'
```

## Visual Indicators

- **Blue Circle**: Player position
- **Red Flickering Dot**: Above player, indicates "move up" direction
- **Green Star**: Goal at top of maze
- **Black/Gray**: Walls
- **White**: Paths

The flickering dot helps users understand they need to navigate upward to reach the goal.
