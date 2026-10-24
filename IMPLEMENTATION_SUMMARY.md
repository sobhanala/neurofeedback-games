# Unity Neurofeedback Integration - Implementation Summary

## ✅ Completed Tasks

### 1. Database Schema ✅
All required models already existed:
- ✅ NeuroFeedbackData model (attention, relaxation, cognitive_load)
- ✅ Game model with Unity fields (is_unity_game, unity_build_path)
- ✅ FeedbackLog with EEG fields (eeg_attention, eeg_relaxation, eeg_cognitive_load)

### 2. EEGEnhancedDDA Algorithm ✅
**File**: `app/services/dda_engine.py`
- ✅ Added EEGEnhancedDDA class
- ✅ Hybrid algorithm: 40% accuracy + 30% reaction time + 30% cognitive load
- ✅ Special rules for high cognitive load (>0.75) and low engagement
- ✅ Registered in DDA_ALGORITHMS dictionary

### 3. Unity API Endpoints ✅
**File**: `app/routes/api.py`
- ✅ POST /api/unity/session/start - Create session
- ✅ POST /api/unity/trial/submit - Submit trial, get difficulty
- ✅ POST /api/unity/eeg/metrics - Stream EEG data
- ✅ GET /api/unity/session/<id>/status - Get session status
- ✅ POST /api/unity/session/<id>/end - End session

### 4. Unity Game Template ✅
**File**: `app/templates/games/unity_neurofeedback.html`
- ✅ WebGL iframe embedding
- ✅ Session stats display (trials, accuracy, difficulty, cognitive load)
- ✅ EEG progress bars (attention, relaxation, cognitive load)
- ✅ JavaScript bridge for Unity ↔ Flask communication
- ✅ Message handlers for trial completion, EEG updates, session end

### 5. Game Routes ✅
**File**: `app/routes/games.py`
- ✅ play_unity_game route (already existed)
- ✅ Checks if game is Unity type
- ✅ Renders unity_neurofeedback.html template

### 6. Admin Panel ✅
**Files**: `app/routes/admin.py`, `app/templates/admin/create_game.html`, `app/templates/admin/edit_game.html`
- ✅ Unity game checkbox in forms (already existed)
- ✅ Unity build path field (already existed)
- ✅ Create/edit game handlers support Unity fields (already existed)

### 7. Game List Template ✅
**File**: `app/templates/games/list.html`
- ✅ Unity badge display (already existed)
- ✅ Conditional routing (play_unity_game vs play_game) (already existed)

### 8. Directory Structure ✅
- ✅ Created `app/static/unity_builds/neurofeedback/` directory

### 9. Documentation ✅
- ✅ Created UNITY_INTEGRATION_README.md
- ✅ Created IMPLEMENTATION_SUMMARY.md

## 📋 Next Steps for Deployment

### 1. Database Migration
```bash
# If using Flask-Migrate
flask db migrate -m "Unity and EEG support"
flask db upgrade

# Or create tables directly
python3 << 'PYEOF'
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
PYEOF
```

### 2. Deploy Unity WebGL Build
1. Build Unity game for WebGL
2. Copy build to: `app/static/unity_builds/neurofeedback/`
3. Ensure structure:
   ```
   app/static/unity_builds/neurofeedback/
   ├── index.html
   ├── Build/
   │   ├── neurofeedback.data
   │   ├── neurofeedback.framework.js
   │   ├── neurofeedback.loader.js
   │   └── neurofeedback.wasm
   └── TemplateData/
       └── style.css
   ```

### 3. Create Unity Game in Admin
1. Login as admin
2. Go to Admin → Games → Create Game
3. Set:
   - Name: "Unity Neurofeedback Game"
   - Slug: "unity-neurofeedback"
   - Game Type: "unity"
   - ✅ Check "Unity Game"
   - Unity Build Path: "neurofeedback"
   - DDA Algorithm: "eeg_enhanced"
   - Difficulty: Min 1, Max 10, Default 5
4. Save

### 4. Test the Integration
1. Navigate to Games page
2. Click "Play Unity Game" on Unity game card
3. Verify:
   - ✅ Unity game loads in iframe
   - ✅ Session starts automatically
   - ✅ Stats update on trial completion
   - ✅ EEG bars update in real-time
   - ✅ Difficulty adjusts based on performance + brain metrics

## 🎮 Unity Game Requirements

Your Unity game must implement this messaging protocol:

### Receive from Flask:
```javascript
// SessionStarted
{
  type: "SessionStarted",
  sessionId: 123,
  initialDifficulty: 5,
  minDifficulty: 1,
  maxDifficulty: 10
}

// DifficultyUpdate
{
  type: "DifficultyUpdate",
  newDifficulty: 6
}
```

### Send to Flask:
```javascript
// Trial Complete
window.postMessage({
  type: "TRIAL_COMPLETE",
  trialNumber: 1,
  isCorrect: true,
  reactionTime: 523,
  eegAttention: 0.75,
  eegRelaxation: 0.60,
  eegCognitiveLoad: 0.45
}, "*");

// EEG Update (real-time)
window.postMessage({
  type: "EEG_UPDATE",
  trialNumber: 1,
  attention: 0.75,
  relaxation: 0.60,
  cognitiveLoad: 0.45
}, "*");

// Session End
window.postMessage({
  type: "SESSION_END"
}, "*");
```

## 🧠 EEG Metrics (0.0 - 1.0 range)
- **Attention**: Focus level (0 = distracted, 1 = highly focused)
- **Relaxation**: Calm state (0 = tense, 1 = very relaxed)
- **Cognitive Load**: Mental effort (0 = no effort, 1 = maximum stress)

## 📊 DDA Algorithm Behavior

**EEGEnhancedDDA** adjusts difficulty based on:
1. **Performance (40%)**: Accuracy vs target (70%)
2. **Speed (30%)**: Reaction time vs average
3. **Brain State (30%)**: Cognitive load + attention

**Special Rules**:
- Cognitive load > 0.75 → Decrease difficulty (reduce stress)
- Cognitive load < 0.3 AND attention > 0.7 → Increase difficulty (too easy)

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| Unity game not loading | Check build path, verify files exist |
| API 404 errors | Check Flask routes registered, verify login |
| EEG not updating | Check Unity postMessage calls, verify data format |
| Difficulty not changing | Verify DDA algorithm is "eeg_enhanced" |

## 📁 Files Changed

### Created:
- ✅ `app/templates/games/unity_neurofeedback.html`
- ✅ `app/static/unity_builds/neurofeedback/` (directory)
- ✅ `UNITY_INTEGRATION_README.md`
- ✅ `IMPLEMENTATION_SUMMARY.md`

### Modified:
- ✅ `app/services/dda_engine.py` - Added EEGEnhancedDDA class
- ✅ `app/routes/api.py` - Added 5 Unity endpoints

### Already Complete:
- ✅ All models (neurofeedback, game, session)
- ✅ All admin templates and routes
- ✅ Game routes (play_unity_game)
- ✅ Game list template

## ✨ Integration Complete!

The Unity Neurofeedback Game integration is fully implemented and ready for deployment. Follow the "Next Steps for Deployment" above to complete the setup.
