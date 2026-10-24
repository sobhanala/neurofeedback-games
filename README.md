# Neurofeedback Cognitive Games

A Flask application for cognitive games, session tracking, and dynamic difficulty adjustment. It includes reaction-time, memory, Stroop, N-back, and maze tasks, plus integration points for EEG metrics and Unity WebGL clients.

## Run locally

Use Python 3.10 or newer. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:FLASK_ENV = 'development'
$env:SECRET_KEY = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe seed_maze_game.py
.\.venv\Scripts\python.exe -m flask --app main run --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000`. The application creates the local SQLite tables at startup. The seed scripts add demonstration accounts, including `admin/admin123` and `testuser/test123`; use them only for local demos and change them before sharing an instance.

## Structure

| Path | Purpose |
| --- | --- |
| `app/models/` | Users, games, sessions, and neurofeedback records |
| `app/routes/` | Authentication, dashboards, admin controls, games, and JSON API |
| `app/services/` | Difficulty strategies and maze generation |
| `app/templates/` | Browser interface |
| `config/settings.py` | Development, production, and test configuration |
| `migrations/` | Schema migration files |
| `tests/` | Existing maze and manual DDA check scripts |

The difficulty engine includes threshold, moving-average, Elo-inspired, rule-based, performance-zone, and EEG-enhanced strategies. See the implementation for the inputs and behavior of each strategy.

## Integration guides

- [Maze game and command API](MAZE_GAME_README.md)
- [Unity WebGL integration](UNITY_INTEGRATION_README.md)
- [DDA checks](DDA_TESTING_GUIDE.md)
- [Related EEG processing project](https://github.com/sobhanala/neurofeedback-bci)

Unity builds, EEG devices, and compatible external clients must be supplied separately where required by the integration. Source code alone does not demonstrate clinical effectiveness or classifier accuracy.

## Configuration and checks

Set `SECRET_KEY` and `DATABASE_URL` outside version control. `FLASK_ENV=development` selects SQLite by default; production configuration supports PostgreSQL. Review the development fallbacks in `config/settings.py` before deployment.

The explicit Flask command above binds to localhost. Running `python main.py` instead starts debug mode on all network interfaces.

The files under `tests/` include manual scripts as well as maze checks. Review their imports and database requirements before running them against a disposable local database. There is no verified, comprehensive test command for this snapshot.

## Public source copy

This repository was prepared from the Project application with fresh Git history. Historical experiment logs, prediction logs, and the project proposal document are excluded. No license has been assigned by this cleanup.
