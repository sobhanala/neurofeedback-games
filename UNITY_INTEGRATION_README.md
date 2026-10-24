# Unity Neurofeedback Game Integration

## Overview
This integration adds support for Unity WebGL-based neurofeedback games with EEG device integration to the Flask platform.

## What's Been Implemented

### 1. Database Models ✅
- **NeuroFeedbackData**: Stores EEG metrics (attention, relaxation, cognitive load)
- **Game Model**: Extended with `is_unity_game` and `unity_build_path` fields
- **FeedbackLog**: Extended with EEG fields (`eeg_attention`, `eeg_relaxation`, `eeg_cognitive_load`)

### 2. DDA Algorithm ✅
- **EEGEnhancedDDA**: Hybrid algorithm combining brain activity with performance metrics
  - Accuracy weight: 40%
  - Reaction time weight: 30%
  - Cognitive load weight: 30%
  - Special rules for high cognitive load and low engagement

### 3. API Endpoints ✅
- `POST /api/unity/session/start` - Start new Unity game session
- `POST /api/unity/trial/submit` - Submit trial data and receive new difficulty
- `POST /api/unity/eeg/metrics` - Stream real-time EEG data (optional)
- `GET /api/unity/session/<id>/status` - Get current session status
- `POST /api/unity/session/<id>/end` - End game session

### 4. Frontend Templates ✅
- **unity_neurofeedback.html**: Unity WebGL game player with:
  - Iframe embedding
  - Real-time session stats display
  - EEG metrics visualization (progress bars)
  - JavaScript bridge for Unity ↔ Flask communication

### 5. Admin Panel ✅
- Unity game checkbox in create/edit forms
- Unity build path field
- Updated game list with Unity badge

### 6. Game Routes ✅
- `play_unity_game` route for Unity game playback
- Updated game list to differentiate Unity vs browser games

## Directory Structure

```
app/
├── models/
│   ├── neurofeedback.py          # NeuroFeedbackData model
│   ├── game.py                    # Game model with Unity fields
│   └── session.py                 # FeedbackLog with EEG fields
├── services/
│   └── dda_engine.py              # EEGEnhancedDDA algorithm
├── routes/
│   ├── api.py                     # Unity API endpoints
│   ├── games.py                   # Unity game routes
│   └── admin.py                   # Admin management
├── templates/
│   ├── games/
│   │   ├── unity_neurofeedback.html   # Unity game player
│   │   └── list.html                  # Game list with Unity support
│   └── admin/
│       ├── create_game.html       # Create game with Unity fields
│       └── edit_game.html         # Edit game with Unity fields
└── static/
    └── unity_builds/
        └── neurofeedback/         # Place Unity WebGL build here
            ├── index.html
            ├── Build/
            └── TemplateData/
```

## Next Steps

### 1. Install Dependencies
```bash
pip install flask flask-sqlalchemy flask-login flask-migrate
```

### 2. Initialize/Update Database
If using Flask-Migrate:
```bash
flask db init  # Only if not already initialized
flask db migrate -m "Add Unity and EEG support"
flask db upgrade
```

Or create tables directly:
```python
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
```

### 3. Deploy Unity WebGL Build
1. Build your Unity game for WebGL platform
2. Copy the build output to `app/static/unity_builds/neurofeedback/`
3. Ensure the following files exist:
   - `index.html`
   - `Build/` directory
   - `TemplateData/` directory

### 4. Create Unity Game in Admin Panel
1. Login as admin
2. Navigate to Admin → Games → Create Game
3. Fill in game details:
   - Name: "Unity Neurofeedback Game"
   - Slug: "unity-neurofeedback"
   - Game Type: "unity"
   - Check "Unity Game" checkbox
   - Unity Build Path: "neurofeedback"
   - DDA Algorithm: "eeg_enhanced"
   - Set difficulty range (e.g., 1-10, default 5)
4. Save

### 5. Unity Game Requirements

Your Unity game must implement the following JavaScript messaging:

#### Receive Messages from Flask:
```javascript
// In Unity C# script
void Start() {
    Application.ExternalCall("console.log", "Unity game ready");
}

// Listen for messages
void OnSessionStarted(string jsonData) {
    // Parse: sessionId, initialDifficulty, minDifficulty, maxDifficulty
}

void OnDifficultyUpdate(string jsonData) {
    // Parse: newDifficulty
    // Adjust game parameters
}
```

#### Send Messages to Flask:
```javascript
// Trial completion
Application.ExternalCall("window.postMessage", JSON.stringify({
    type: "TRIAL_COMPLETE",
    trialNumber: 1,
    isCorrect: true,
    reactionTime: 523,
    eegAttention: 0.75,
    eegRelaxation: 0.60,
    eegCognitiveLoad: 0.45
}), "*");

// EEG updates (real-time)
Application.ExternalCall("window.postMessage", JSON.stringify({
    type: "EEG_UPDATE",
    trialNumber: 1,
    attention: 0.75,
    relaxation: 0.60,
    cognitiveLoad: 0.45
}), "*");

// Session end
Application.ExternalCall("window.postMessage", JSON.stringify({
    type: "SESSION_END"
}), "*");
```

### 6. EEG Device Integration (Unity Side)
Your Unity game should:
1. Connect to EEG device via Bluetooth
2. Read raw EEG signals
3. Process signals into normalized metrics (0.0 - 1.0):
   - **Attention**: Focus level (higher = more focused)
   - **Relaxation**: Calm state (higher = more relaxed)
   - **Cognitive Load**: Mental effort (higher = more stressed)
4. Send metrics with each trial completion

## Testing

### Test Flow:
1. **Create Game**: Admin creates Unity game with `eeg_enhanced` algorithm
2. **Play Game**: User navigates to game, session starts automatically
3. **Trial Loop**: 
   - Unity sends trial data → Flask processes → Returns new difficulty
   - Unity adjusts game parameters based on new difficulty
4. **EEG Monitoring**: Real-time EEG bars update on page
5. **Session End**: Unity signals end → Flask saves final stats → Redirect to dashboard

### Manual Testing:
```bash
# Test API endpoints
curl -X POST http://localhost:5000/api/unity/session/start \
  -H "Content-Type: application/json" \
  -d '{"game_id": 1}'

curl -X POST http://localhost:5000/api/unity/trial/submit \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "trial_number": 1,
    "is_correct": true,
    "reaction_time_ms": 500,
    "eeg_attention": 0.7,
    "eeg_relaxation": 0.6,
    "eeg_cognitive_load": 0.5
  }'
```

## DDA Algorithm Details

### EEGEnhancedDDA Behavior:
- **High cognitive load (>0.75)**: Decreases difficulty immediately (stress relief)
- **Low engagement (load <0.3 AND attention >0.7)**: Increases difficulty (too easy)
- **Normal operation**: Combines accuracy, reaction time, and cognitive load
- Uses exponential moving average (EMA) for smooth adjustments

## Troubleshooting

### Issue: Unity game not loading
- Check Unity build path in database matches actual directory
- Verify all Unity build files are present
- Check browser console for errors

### Issue: API endpoints returning 404
- Ensure Flask app is running
- Check route registrations in `app/__init__.py`
- Verify login status (endpoints require authentication)

### Issue: EEG data not updating
- Check Unity is sending messages correctly
- Verify JavaScript console for postMessage errors
- Ensure EEG device is connected in Unity

### Issue: DDA not adjusting difficulty
- Check `dda_algorithm` is set to "eeg_enhanced" in game settings
- Verify EEG values are in 0.0-1.0 range
- Review trial history in database

## Files Modified/Created

### Created:
- `app/templates/games/unity_neurofeedback.html`
- `app/static/unity_builds/neurofeedback/` (directory)
- `UNITY_INTEGRATION_README.md` (this file)

### Modified:
- `app/services/dda_engine.py` - Added EEGEnhancedDDA class
- `app/routes/api.py` - Added 5 Unity API endpoints
- `app/routes/games.py` - Added play_unity_game route

### Already Existed (no changes needed):
- `app/models/neurofeedback.py` - NeuroFeedbackData model
- `app/models/game.py` - Game model with Unity fields
- `app/models/session.py` - FeedbackLog with EEG fields
- `app/templates/admin/create_game.html` - Unity form fields
- `app/templates/admin/edit_game.html` - Unity form fields
- `app/templates/games/list.html` - Unity badge display
- `app/routes/admin.py` - Unity game management

## Support

For issues or questions:
1. Check this README
2. Review plan.md for original specifications
3. Check database schema matches models
4. Verify Unity build is correctly deployed
