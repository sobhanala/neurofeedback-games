
  # Unity Neurofeedback Game Integration Plan

  ## Summary

  Integrate a Unity WebGL-based neurofeedback game into the existing Flask platform. The game will
  use Bluetooth-connected EEG devices to capture brain activity (attention, relaxation, cognitive
  load), transmit data to the backend via REST API, and dynamically adjust difficulty using a
  hybrid DDA algorithm that combines both brain metrics and performance metrics.

  ## Key Changes

  Backend Extensions

  - Add NeuroFeedbackData model to store aggregated EEG metrics (attention, relaxation,
    cognitive_load, session_id, timestamp)

  - Create new EEGEnhancedDDA algorithm class that combines brain activity signals with traditional
    performance metrics (accuracy, reaction time)

  - Add REST API endpoints: POST /api/unity/session/start, POST /api/unity/trial/submit, POST /api/
    unity/eeg/metrics, GET /api/unity/difficulty/<session_id>

  - Extend Game model with is_unity_game boolean flag and unity_build_path field

  Frontend Integration

  - Create app/templates/games/unity_neurofeedback.html template with embedded WebGL iframe
  - Add Unity WebGL build hosting directory at app/static/unity_builds/neurofeedback/
  - Create game listing UI that distinguishes Unity games from browser-based cognitive games

  Unity Game Interface

  - Unity game handles Bluetooth device connection and raw EEG data collection
  - Game aggregates raw signals into metrics (attention %, relaxation %, cognitive_load) every
    trial

  - Unity sends HTTP POST requests with trial data: {trial_number, is_correct, reaction_time_ms,
    eeg_attention, eeg_relaxation, eeg_cognitive_load}

  - Backend responds with new difficulty level; Unity adjusts game parameters accordingly

  DDA Algorithm - Brain + Performance Hybrid

  - EEGEnhancedDDA inherits from DDAAlgorithm base class
  - Combines 3 signals: performance accuracy (40% weight), reaction time (30% weight), EEG
    cognitive load (30% weight)

  - If cognitive_load > 0.75 (high stress) → decrease difficulty even if accuracy is good
  - If cognitive_load < 0.3 AND attention > 0.7 (low engagement, high attention) → increase
    difficulty

  - Uses exponential moving average for smooth adjustments

  ## Implementation Details

  Database Schema Changes

  - Add neurofeedback_data table with columns: id, session_id (FK), timestamp, attention_score (0-1
    float), relaxation_score (0-1 float), cognitive_load (0-1 float), trial_number

  - Alter games table: add is_unity_game BOOLEAN DEFAULT FALSE, unity_build_path VARCHAR(256)
  - Update feedback_logs table: add eeg_attention FLOAT, eeg_relaxation FLOAT, eeg_cognitive_load
    FLOAT (nullable for backward compatibility)

  API Endpoints

  - POST /api/unity/session/start → Create GameSession, return session_id + initial_difficulty
  - POST /api/unity/trial/submit → Save FeedbackLog with EEG data, run DDA, return new difficulty
  - POST /api/unity/eeg/metrics → Store real-time EEG samples (optional streaming endpoint)
  - GET /api/unity/session/<id>/status → Return current difficulty, trial count, session stats

  Unity Build Deployment

  - Unity exports WebGL build with files: index.html, Build/, TemplateData/
  - Flask serves Unity build from app/static/unity_builds/neurofeedback/
  - Template unity_neurofeedback.html embeds iframe pointing to /static/unity_builds/neurofeedback/
    index.html

  - Unity uses JavaScript Interop to call Flask API endpoints

  DDA Algorithm Logic

  EEGEnhancedDDA:
    - Maintain EMA for: accuracy, reaction_time, cognitive_load, attention
    - Compute performance_score = (accuracy - target_accuracy) * 0.4
    - Compute rt_score = (avg_rt - current_rt) / avg_rt * 0.3
    - Compute brain_score = (0.75 - cognitive_load) * 0.3 + (attention - 0.6) * 0.1
    - combined_signal = performance_score + rt_score + brain_score
    - If combined_signal > threshold: increase difficulty
    - If combined_signal < -threshold: decrease difficulty

  Admin Panel Updates

  - Add "Unity Game" checkbox to game creation form
  - Add "Unity Build Path" field for specifying WebGL build directory
  - Display EEG metrics in session detail view: attention graph, cognitive load graph
  - Analytics page shows correlation between brain metrics and performance

  ## Test Plan

  Unit Tests

  - Test EEGEnhancedDDA.compute_new_difficulty() with various brain metric combinations
  - Test API endpoints with mock Unity requests
  - Verify NeuroFeedbackData model saves and retrieves EEG metrics correctly

  Integration Tests

  - Create Unity game session via API, submit 10 trials with varying EEG data
  - Verify difficulty adjusts based on cognitive load even when accuracy is high
  - Test WebGL embedding: load template, verify iframe renders, check CORS headers

  Manual Testing

  - Admin creates Unity neurofeedback game entry with test build path
  - User navigates to game page, WebGL loads successfully
  - Simulate Bluetooth device data (mock EEG values), verify DDA responds correctly
  - Check session history displays EEG metrics alongside performance data

  ## Assumptions

  - Unity game handles all Bluetooth device communication internally (no Flask Bluetooth
    dependency)

  - EEG device outputs attention, relaxation, and cognitive load as normalized 0-1 values
  - Unity game will be pre-built as WebGL; Flask only hosts the static files
  - Existing 4 cognitive games remain unchanged; Unity game is added as 5th game type
  - CORS is configured to allow Unity WebGL to call Flask API on same domain/port
  - Admin manually uploads Unity WebGL build to app/static/unity_builds/neurofeedback/ directory