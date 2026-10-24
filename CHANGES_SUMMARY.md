# Maze Game Fixes Summary

## Issues Fixed

### 1. DDA Difficulty Not Persisting Across Games ✓

**Problem**: When a game ended and user clicked "Play again", the new game always started at difficulty 5 instead of using the DDA-adjusted difficulty.

**Root Cause**: The query for `last_session` was not filtering for completed sessions, so it could pick up incomplete sessions or the wrong session.

**Fix**:
- Added `.filter(GameSession.ended_at.isnot(None))` to both:
  - `app/routes/api.py` → `maze_session_start()` line 359
  - `app/routes/games.py` → `play_maze_game()` line 167
- Updated `initGame()` to set `ddaCurrent` display from API response
- Added console logging to track difficulty changes

**Files Changed**:
- `app/routes/api.py`
- `app/routes/games.py`
- `app/templates/games/maze.html`

### 2. Layout: Dot and Maze Not Visible Without Scrolling ✓

**Problem**: The attention dot, maze canvas, and sidebar cards were too large, requiring scrolling to see everything.

**Fix**:
- Reduced page header from `h2` to `h4`, removed description
- Changed column ratio from 8:4 to 7:5
- Shrunk canvas from 600×600 to 420×420 pixels
- Reduced attention dot from 76px to 50px diameter
- Compacted all sidebar cards (smaller padding, headers, text)
- Used `d-flex` for horizontal stat layout
- Reduced progress bar heights from 25px to 20px

**Files Changed**:
- `app/templates/games/maze.html`

### 3. Metrics Not Showing Correctly

**Context**: The metrics (Attention, Cognitive Load, Relaxation) are updated by the state poller via `/api/maze/session/<id>/state` endpoint. Default values are 50% until neurofeedback data is received.

**Console Logging Added**:
- Game start logs: Session ID, Initial Difficulty, Maze Size, Start/Goal positions
- Game end logs: Goal reached, Moves, Efficiency, Score, DDA changes, EEG metrics

## New Files Created

### 1. `test_dda_manual.py`
Interactive script to test DDA without playing through the game:
- Simulates GOOD/BAD/MEDIUM performance
- Creates completed sessions with specific outcomes
- Shows expected next difficulty
- Can delete all test sessions

**Usage**:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
python test_dda_manual.py
```

### 2. `DDA_TESTING_GUIDE.md`
Complete testing guide with:
- Step-by-step testing instructions
- Console log reference
- DDA decision rules
- Difficulty-to-size mapping
- Troubleshooting tips
- API endpoint examples

## How to Test

### Quick Test (5 minutes)
1. Run `python test_dda_manual.py`, choose option 1 (GOOD performance)
2. Refresh maze game page
3. Open browser console (F12)
4. Check "Initial Difficulty" in console log (should be 6 if default was 5)
5. Check maze size increased

### Full Test (15 minutes)
1. Clear all sessions: `python test_dda_manual.py`, option 4
2. Create GOOD session: option 1 → should go from 5 to 6
3. Refresh game, verify difficulty 6 in console
4. Create BAD session with script → should go from 6 to 5
5. Refresh game, verify difficulty 5 in console
6. Play through naturally, check console logs
7. Verify "Play again" persists difficulty

## Console Logs Example

### Game Start:
```
=== MAZE GAME STARTED ===
Session ID: 123
Initial Difficulty: 6
Maze Size: 13
Start: [1, 11] Goal: [11, 1]
```

### Game End:
```
=== MAZE GAME ENDED ===
Goal Reached: true
Moves: 15 / Optimal: 12
Efficiency: 80%
Score: 48
Current Difficulty: 6
Next Difficulty: 7
DDA Direction: harder
DDA Reason: Harder: excellent performance and high attention.
Avg Attention: 0.75
Avg Cognitive Load: 0.50
```

## DDA Logic Reference

The maze game uses custom DDA logic (not the standard DDA algorithms):

```python
# Goes HARDER if:
goal_reached AND efficiency > 0.85 AND avg_attention > 0.65

# Goes EASIER if:
NOT goal_reached OR efficiency < 0.5 OR avg_attention < 0.4

# Otherwise STAYS SAME
```

Difficulty range: 1-10
Maze sizes: 7×7 (easy) to 21×21 (hard)

## Troubleshooting

**Issue**: Difficulty still starts at 5
- Solution: Check browser console for "Initial Difficulty" log. Run test script to verify database has completed sessions. Check that `ended_at` is set in database.

**Issue**: Metrics stuck at 50%
- Solution: Metrics update from state poller. Check Network tab for `/api/maze/session/<id>/state` requests. Send EEG data via neurofeedback module or manually test with curl.

**Issue**: Layout still requires scrolling
- Solution: Check that changes were applied (canvas should be 420×420, dot should be 50px). Try different screen sizes. Navbar and footer take some vertical space.

## Technical Details

### Canvas Sizing
- Old: 600×600px → cellSize = 600 / mazeSize
- New: 420×420px → cellSize = 420 / mazeSize
- Scales dynamically based on maze size

### Query Change
```python
# Before:
last_session = GameSession.query.filter_by(
    user_id=current_user.id, game_id=game_id
).order_by(GameSession.started_at.desc()).first()

# After:
last_session = GameSession.query.filter_by(
    user_id=current_user.id, game_id=game_id
).filter(GameSession.ended_at.isnot(None)).order_by(GameSession.started_at.desc()).first()
```

This ensures only completed sessions are considered for DDA.

## Next Steps

1. Test with real neurofeedback data
2. Verify DDA thresholds are appropriate for your use case
3. Consider adding more granular difficulty levels if needed
4. Monitor user performance metrics to tune DDA parameters
