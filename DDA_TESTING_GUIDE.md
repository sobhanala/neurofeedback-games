# DDA Testing Guide for Maze Game

## Problems Fixed

1. **DDA persistence** - Now queries only completed sessions (`ended_at IS NOT NULL`)
2. **Display updates** - `ddaCurrent` now updates correctly on game start
3. **Console logging** - Added detailed logs to track DDA changes

## How to Test DDA Manually

### Method 1: Using the Test Script (Recommended)

```bash
# Activate virtual environment first
source venv/bin/activate  # or on Windows: venv\Scripts\activate

# Run the test script
python test_dda_manual.py
```

The script will:
- Show your current difficulty level
- Let you simulate GOOD/BAD/MEDIUM performance
- Create a completed session with the chosen outcome
- Show what the next difficulty should be

After running the script:
1. Refresh the maze game page in your browser
2. Open browser console (F12)
3. Look for "=== MAZE GAME STARTED ===" log
4. Check that "Initial Difficulty" matches what the script predicted

### Method 2: Play Through Naturally

1. Start the maze game
2. Open browser console (F12)
3. Play through the maze:
   - **For HARDER next time**: Finish quickly with few moves
   - **For EASIER next time**: Take many moves or don't finish
   - **For SAME**: Medium performance
4. Check console logs when game ends:
   ```
   === MAZE GAME ENDED ===
   Current Difficulty: 5
   Next Difficulty: 6
   DDA Direction: harder
   DDA Reason: ...
   ```
5. Click "Play again" or refresh page
6. Check console logs when new game starts:
   ```
   === MAZE GAME STARTED ===
   Initial Difficulty: 6  <-- Should match "Next Difficulty" from previous game
   ```

## Console Logs to Watch

### On Game Start
- `Session ID`: Current session identifier
- `Initial Difficulty`: The difficulty level (1-10)
- `Maze Size`: Grid dimensions (should increase with difficulty)
- `Start` and `Goal`: Position coordinates

### On Game End
- `Goal Reached`: true/false
- `Moves` vs `Optimal`: Your moves compared to shortest path
- `Efficiency`: Percentage (higher is better)
- `Current Difficulty`: Difficulty just played
- `Next Difficulty`: What next game will be
- `DDA Direction`: "harder", "easier", or "same"
- `DDA Reason`: Why DDA made this decision
- `Avg Attention`: Average attention score (0-1)
- `Avg Cognitive Load`: Average cognitive load (0-1)

## DDA Decision Rules

The maze DDA considers:
1. **Goal completion** (did you reach the goal?)
2. **Move efficiency** (moves vs optimal path)
3. **Attention level** (from EEG/neurofeedback)
4. **Cognitive load** (from EEG/neurofeedback)

### Goes HARDER if:
- Goal reached AND
- Efficiency > 85% AND
- Attention > 65%

### Goes EASIER if:
- Goal not reached OR
- Efficiency < 50% OR
- Attention < 40%

### Stays SAME otherwise

## Difficulty to Maze Size Mapping

| Difficulty | Maze Size |
|------------|-----------|
| 1-2        | 7×7       |
| 3          | 9×9       |
| 4-5        | 11×11     |
| 6          | 13×13     |
| 7-8        | 15×15     |
| 9          | 19×19     |
| 10         | 21×21     |

## Testing Checklist

- [ ] DDA increases after good performance
- [ ] DDA decreases after bad performance
- [ ] DDA stays same for medium performance
- [ ] Difficulty persists across page reloads
- [ ] Console logs show correct values
- [ ] Maze size changes with difficulty
- [ ] "Next Maze" display updates on game end
- [ ] "Current Difficulty" display updates on game start

## Troubleshooting

**Problem**: Difficulty always starts at 5
- Check that you have at least one completed session
- Run `python test_dda_manual.py` and choose option 4 to clear sessions, then option 1 to create a good session
- Verify console log shows correct "Initial Difficulty"

**Problem**: Metrics not showing correctly
- EEG metrics update from `/api/maze/session/<id>/state` endpoint
- Check that the state poller is running (look for periodic API calls in Network tab)
- Default values are 50% for attention/load/relaxation

**Problem**: DDA not changing
- Check browser console for "=== MAZE GAME ENDED ===" logs
- Verify "Next Difficulty" is different from "Current Difficulty"
- Make sure you're clicking "Play again" or refreshing after game ends
- Check that the previous session has `ended_at` set in database

## API Endpoints for Manual Testing

### Check Session State
```bash
curl -H "Content-Type: application/json" \
  http://localhost:5000/api/maze/session/<session_id>/state
```

### Send Manual Command
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"session_id": <id>, "action": "move_up", "confidence": 0.8, "eeg_attention": 0.7, "eeg_cognitive_load": 0.5}' \
  http://localhost:5000/api/maze/command
```
