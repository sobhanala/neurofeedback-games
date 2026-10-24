"""REST API endpoints for mobile/external client integration."""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.game import Game
from app.models.session import GameSession, FeedbackLog
from app.services.dda_engine import get_dda_algorithm
from sqlalchemy import func
from datetime import datetime
from app.models.neurofeedback import NeuroFeedbackData

api_bp = Blueprint("api", __name__)


@api_bp.route("/games", methods=["GET"])
def list_games():
    games = Game.query.filter_by(is_active=True).all()
    return jsonify([{
        "id": g.id,
        "name": g.name,
        "slug": g.slug,
        "game_type": g.game_type,
        "description": g.description,
        "default_difficulty": g.default_difficulty,
        "dda_algorithm": g.dda_algorithm,
    } for g in games])


@api_bp.route("/user/stats", methods=["GET"])
@login_required
def user_stats():
    stats = db.session.query(
        func.count(GameSession.id).label("total_sessions"),
        func.sum(GameSession.total_trials).label("total_trials"),
        func.sum(GameSession.correct_trials).label("total_correct"),
        func.avg(GameSession.score).label("avg_score"),
        func.avg(GameSession.avg_reaction_time_ms).label("avg_rt"),
    ).filter(GameSession.user_id == current_user.id).first()

    return jsonify({
        "user_id": current_user.id,
        "username": current_user.username,
        "total_sessions": stats.total_sessions or 0,
        "total_trials": stats.total_trials or 0,
        "total_correct": stats.total_correct or 0,
        "accuracy": round((stats.total_correct or 0) / max(stats.total_trials or 1, 1) * 100, 1),
        "avg_score": round(stats.avg_score or 0, 2),
        "avg_reaction_time_ms": round(stats.avg_rt or 0, 1),
    })


@api_bp.route("/user/history", methods=["GET"])
@login_required
def user_history():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    sessions = GameSession.query.filter_by(user_id=current_user.id).order_by(
        GameSession.started_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "sessions": [{
            "id": s.id,
            "game_name": s.game.name if s.game else "Unknown",
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "score": s.score,
            "accuracy": round(s.accuracy * 100, 1),
            "avg_rt": round(s.avg_reaction_time_ms, 1) if s.avg_reaction_time_ms else None,
            "final_difficulty": s.final_difficulty,
            "dda_algorithm": s.dda_algorithm_used,
        } for s in sessions.items],
        "total": sessions.total,
        "pages": sessions.pages,
        "current_page": sessions.page,
    })


@api_bp.route("/session/<int:session_id>/details", methods=["GET"])
@login_required
def session_details(session_id):
    session_obj = GameSession.query.get_or_404(session_id)
    if session_obj.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    logs = FeedbackLog.query.filter_by(session_id=session_id).order_by(
        FeedbackLog.trial_number
    ).all()

    return jsonify({
        "session": {
            "id": session_obj.id,
            "game_name": session_obj.game.name if session_obj.game else "Unknown",
            "started_at": session_obj.started_at.isoformat() if session_obj.started_at else None,
            "ended_at": session_obj.ended_at.isoformat() if session_obj.ended_at else None,
            "initial_difficulty": session_obj.initial_difficulty,
            "final_difficulty": session_obj.final_difficulty,
            "total_trials": session_obj.total_trials,
            "correct_trials": session_obj.correct_trials,
            "score": session_obj.score,
            "dda_algorithm": session_obj.dda_algorithm_used,
        },
        "trials": [{
            "trial_number": log.trial_number,
            "reaction_time_ms": log.reaction_time_ms,
            "is_correct": log.is_correct,
            "difficulty_at_trial": log.difficulty_at_trial,
            "difficulty_after_trial": log.difficulty_after_trial,
        } for log in logs],
    })


@api_bp.route("/unity/session/start", methods=["POST"])
@login_required
def unity_session_start():
    """Start a new Unity game session."""
    data = request.get_json()
    game_id = data.get("game_id")
    
    game = Game.query.get_or_404(game_id)
    if not game.is_unity_game:
        return jsonify({"error": "Not a Unity game"}), 400
    
    session = GameSession(
        user_id=current_user.id,
        game_id=game_id,
        initial_difficulty=game.default_difficulty,
        dda_algorithm_used=game.dda_algorithm
    )
    db.session.add(session)
    db.session.commit()
    
    return jsonify({
        "session_id": session.id,
        "initial_difficulty": session.initial_difficulty,
        "min_difficulty": game.min_difficulty,
        "max_difficulty": game.max_difficulty,
    }), 201


@api_bp.route("/unity/trial/submit", methods=["POST"])
@login_required
def unity_trial_submit():
    """Submit trial data and get new difficulty."""
    data = request.get_json()
    session_id = data.get("session_id")
    trial_number = data.get("trial_number")
    is_correct = data.get("is_correct")
    reaction_time_ms = data.get("reaction_time_ms")
    eeg_attention = data.get("eeg_attention", 0.5)
    eeg_relaxation = data.get("eeg_relaxation", 0.5)
    eeg_cognitive_load = data.get("eeg_cognitive_load", 0.5)
    
    session = GameSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    last_log = FeedbackLog.query.filter_by(session_id=session_id).order_by(
        FeedbackLog.trial_number.desc()
    ).first()
    current_difficulty = last_log.difficulty_after_trial if last_log else session.initial_difficulty
    
    game = session.game
    dda = get_dda_algorithm(
        game.dda_algorithm,
        min_difficulty=game.min_difficulty,
        max_difficulty=game.max_difficulty
    )
    
    # Build history for DDA
    history = []
    logs = FeedbackLog.query.filter_by(session_id=session_id).order_by(
        FeedbackLog.trial_number
    ).all()
    for log in logs:
        history.append({
            "is_correct": log.is_correct,
            "reaction_time_ms": log.reaction_time_ms,
            "difficulty_at_trial": log.difficulty_at_trial,
            "eeg_cognitive_load": log.eeg_cognitive_load,
            "eeg_attention": log.eeg_attention,
            "eeg_relaxation": log.eeg_relaxation,
        })
    
    history.append({
        "is_correct": is_correct,
        "reaction_time_ms": reaction_time_ms,
        "difficulty_at_trial": current_difficulty,
        "eeg_cognitive_load": eeg_cognitive_load,
        "eeg_attention": eeg_attention,
        "eeg_relaxation": eeg_relaxation,
    })
    
    new_difficulty = dda.compute_new_difficulty(current_difficulty, history)
    
    # Save feedback log
    feedback = FeedbackLog(
        session_id=session_id,
        trial_number=trial_number,
        is_correct=is_correct,
        reaction_time_ms=reaction_time_ms,
        difficulty_at_trial=current_difficulty,
        difficulty_after_trial=new_difficulty,
        eeg_attention=eeg_attention,
        eeg_relaxation=eeg_relaxation,
        eeg_cognitive_load=eeg_cognitive_load
    )
    db.session.add(feedback)
    
    # Save neurofeedback data
    neuro_data = NeuroFeedbackData(
        session_id=session_id,
        trial_number=trial_number,
        attention_score=eeg_attention,
        relaxation_score=eeg_relaxation,
        cognitive_load=eeg_cognitive_load
    )
    db.session.add(neuro_data)
    
    # Update session stats
    session.total_trials += 1
    if is_correct:
        session.correct_trials += 1
    
    if session.avg_reaction_time_ms is None:
        session.avg_reaction_time_ms = reaction_time_ms
    else:
        session.avg_reaction_time_ms = (
            (session.avg_reaction_time_ms * (session.total_trials - 1) + reaction_time_ms) 
            / session.total_trials
        )
    
    db.session.commit()
    
    return jsonify({
        "new_difficulty": new_difficulty,
        "trial_number": trial_number,
        "session_stats": {
            "total_trials": session.total_trials,
            "accuracy": round(session.accuracy * 100, 1),
            "avg_reaction_time": round(session.avg_reaction_time_ms, 1)
        }
    })


@api_bp.route("/unity/eeg/metrics", methods=["POST"])
@login_required
def unity_eeg_metrics():
    """Store real-time EEG metrics (optional streaming endpoint)."""
    data = request.get_json()
    session_id = data.get("session_id")
    trial_number = data.get("trial_number")
    eeg_attention = data.get("eeg_attention")
    eeg_relaxation = data.get("eeg_relaxation")
    eeg_cognitive_load = data.get("eeg_cognitive_load")
    
    session = GameSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    neuro_data = NeuroFeedbackData(
        session_id=session_id,
        trial_number=trial_number,
        attention_score=eeg_attention,
        relaxation_score=eeg_relaxation,
        cognitive_load=eeg_cognitive_load
    )
    db.session.add(neuro_data)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "EEG metrics saved"}), 201


@api_bp.route("/unity/session/<int:session_id>/status", methods=["GET"])
@login_required
def unity_session_status(session_id):
    """Get current session status."""
    session = GameSession.query.get_or_404(session_id)
    if session.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    
    last_log = FeedbackLog.query.filter_by(session_id=session_id).order_by(
        FeedbackLog.trial_number.desc()
    ).first()
    current_difficulty = last_log.difficulty_after_trial if last_log else session.initial_difficulty
    
    # Get EEG averages
    eeg_data = NeuroFeedbackData.query.filter_by(session_id=session_id).all()
    avg_attention = sum(d.attention_score for d in eeg_data) / len(eeg_data) if eeg_data else 0
    avg_relaxation = sum(d.relaxation_score for d in eeg_data) / len(eeg_data) if eeg_data else 0
    avg_cognitive_load = sum(d.cognitive_load for d in eeg_data) / len(eeg_data) if eeg_data else 0
    
    return jsonify({
        "session_id": session.id,
        "current_difficulty": current_difficulty,
        "total_trials": session.total_trials,
        "accuracy": round(session.accuracy * 100, 1),
        "avg_reaction_time": round(session.avg_reaction_time_ms, 1) if session.avg_reaction_time_ms else None,
        "eeg_metrics": {
            "avg_attention": round(avg_attention, 2),
            "avg_relaxation": round(avg_relaxation, 2),
            "avg_cognitive_load": round(avg_cognitive_load, 2)
        }
    })


@api_bp.route("/unity/session/<int:session_id>/end", methods=["POST"])
@login_required
def unity_session_end(session_id):
    """End a Unity game session."""
    session = GameSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    if session.ended_at is None:
        session.ended_at = datetime.utcnow()
        
        last_log = FeedbackLog.query.filter_by(session_id=session_id).order_by(
            FeedbackLog.trial_number.desc()
        ).first()
        session.final_difficulty = last_log.difficulty_after_trial if last_log else session.initial_difficulty
        
        # Calculate final score (accuracy * 100 + difficulty bonus)
        session.score = session.accuracy * 100 + (session.final_difficulty * 5)
        
        db.session.commit()
    
    return jsonify({
        "status": "success",
        "message": "Session ended",
        "final_stats": {
            "score": round(session.score, 1),
            "accuracy": round(session.accuracy * 100, 1),
            "final_difficulty": session.final_difficulty,
            "total_trials": session.total_trials
        }
    })


# ============== MAZE GAME API ENDPOINTS ==============

@api_bp.route("/maze/session/start", methods=["POST"])
@login_required
def maze_session_start():
    """Start a new maze game session."""
    from app.services.maze_generator import generate_maze
    
    data = request.get_json()
    game_id = data.get("game_id")
    
    game = Game.query.get_or_404(game_id)
    if game.game_type != "maze":
        return jsonify({"error": "Not a maze game"}), 400
    
    # Get last difficulty for this user+game, or use default
    last_session = GameSession.query.filter_by(
        user_id=current_user.id, game_id=game_id
    ).filter(GameSession.ended_at.isnot(None)).order_by(GameSession.started_at.desc()).first()
    
    initial_difficulty = last_session.final_difficulty if last_session and last_session.final_difficulty else game.default_difficulty
    
    # Generate maze based on difficulty
    maze_data = generate_maze(initial_difficulty)
    
    # Create session
    session = GameSession(
        user_id=current_user.id,
        game_id=game_id,
        initial_difficulty=initial_difficulty,
        dda_algorithm_used=game.dda_algorithm,
        maze_data=maze_data,
        current_position_x=maze_data['start'][0],
        current_position_y=maze_data['start'][1],
        moves_count=0
    )
    db.session.add(session)
    db.session.commit()
    
    return jsonify({
        "session_id": session.id,
        "maze": maze_data['maze'],
        "start": maze_data['start'],
        "goal": maze_data['goal'],
        "size": maze_data['size'],
        "initial_difficulty": initial_difficulty,
        "min_difficulty": game.min_difficulty,
        "max_difficulty": game.max_difficulty,
    }), 201


@api_bp.route("/maze/command", methods=["POST"])
@login_required
def maze_command():
    """Process movement command from neurofeedback module."""
    data = request.get_json()
    session_id = data.get("session_id")
    action = data.get("action")  # move_up, move_left, move_right (no down)
    confidence = data.get("confidence", 0.5)
    eeg_attention = data.get("eeg_attention", 0.5)
    eeg_cognitive_load = data.get("eeg_cognitive_load", 0.5)
    
    session = GameSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    if session.ended_at:
        return jsonify({"error": "Session already ended"}), 400
    
    # Parse action and calculate new position
    action_map = {
        "move_up": (0, -1),
        "move_left": (-1, 0),
        "move_right": (1, 0)
    }
    
    if action not in action_map:
        return jsonify({"error": "Invalid action"}), 400
    
    dx, dy = action_map[action]
    current_x = session.current_position_x
    current_y = session.current_position_y
    new_x = current_x + dx
    new_y = current_y + dy
    
    # Check if move is valid (not a wall)
    maze = session.maze_data['maze']
    size = session.maze_data['size']
    
    if new_x < 0 or new_x >= size or new_y < 0 or new_y >= size:
        return jsonify({
            "valid": False,
            "message": "Out of bounds",
            "current_position": [current_x, current_y],
            "reached_goal": False
        }), 200
    
    if maze[new_y][new_x]:  # True means wall
        return jsonify({
            "valid": False,
            "message": "Wall collision",
            "current_position": [current_x, current_y],
            "reached_goal": False
        }), 200
    
    # Valid move - update position
    session.current_position_x = new_x
    session.current_position_y = new_y
    session.moves_count += 1
    
    # Check if goal reached
    goal = session.maze_data['goal']
    reached_goal = (new_x == goal[0] and new_y == goal[1])
    
    # Store EEG data
    neuro_data = NeuroFeedbackData(
        session_id=session_id,
        trial_number=session.moves_count,
        attention_score=eeg_attention,
        cognitive_load=eeg_cognitive_load,
        relaxation_score=data.get("eeg_relaxation", 0.5)
    )
    db.session.add(neuro_data)
    db.session.commit()
    
    return jsonify({
        "valid": True,
        "message": "Goal reached!" if reached_goal else "Moved successfully",
        "new_position": [new_x, new_y],
        "reached_goal": reached_goal,
        "moves_count": session.moves_count,
        "confidence": confidence
    }), 200


@api_bp.route("/maze/session/<int:session_id>/state", methods=["GET"])
@login_required
def maze_session_state(session_id):
    """Get current maze session state."""
    session = GameSession.query.get_or_404(session_id)
    if session.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Get latest EEG data
    latest_eeg = NeuroFeedbackData.query.filter_by(
        session_id=session_id
    ).order_by(NeuroFeedbackData.timestamp.desc()).first()
    
    # Calculate elapsed time
    elapsed_seconds = 0
    if session.started_at:
        if session.ended_at:
            elapsed_seconds = (session.ended_at - session.started_at).total_seconds()
        else:
            elapsed_seconds = (datetime.utcnow() - session.started_at).total_seconds()
    
    return jsonify({
        "session_id": session.id,
        "current_position": [session.current_position_x, session.current_position_y],
        "goal": session.maze_data['goal'],
        "moves_count": session.moves_count,
        "difficulty": session.final_difficulty or session.initial_difficulty,
        "elapsed_seconds": round(elapsed_seconds, 1),
        "is_ended": session.ended_at is not None,
        "eeg": {
            "attention": latest_eeg.attention_score if latest_eeg else 0.5,
            "cognitive_load": latest_eeg.cognitive_load if latest_eeg else 0.5,
            "relaxation": latest_eeg.relaxation_score if latest_eeg else 0.5
        } if latest_eeg else None
    }), 200


@api_bp.route("/maze/session/<int:session_id>/end", methods=["POST"])
@login_required
def maze_session_end(session_id):
    """End a maze game session and calculate score."""
    from app.services.maze_generator import MazeGenerator
    
    session = GameSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    if session.ended_at:
        return jsonify({"error": "Session already ended"}), 400
    
    session.ended_at = datetime.utcnow()
    
    # Check if goal was reached
    goal = session.maze_data['goal']
    goal_reached = (session.current_position_x == goal[0] and 
                    session.current_position_y == goal[1])
    
    # Calculate completion time
    completion_time_ms = (session.ended_at - session.started_at).total_seconds() * 1000
    
    # Calculate optimal moves
    optimal_moves = MazeGenerator.calculate_optimal_moves(
        session.maze_data['start'], 
        session.maze_data['goal']
    )
    
    # Calculate efficiency (actual moves vs optimal)
    efficiency = optimal_moves / max(session.moves_count, 1) if session.moves_count > 0 else 0
    
    # Get average EEG metrics
    avg_eeg = db.session.query(
        func.avg(NeuroFeedbackData.attention_score).label('avg_attention'),
        func.avg(NeuroFeedbackData.cognitive_load).label('avg_load')
    ).filter(NeuroFeedbackData.session_id == session_id).first()
    
    avg_attention = avg_eeg.avg_attention or 0.5
    avg_cognitive_load = avg_eeg.avg_load or 0.5
    
    # Run maze-specific DDA at the end of the maze session.
    # A full maze is one trial, so this decision is made once per maze.
    game = session.game
    current_difficulty = session.initial_difficulty
    expected_moves = max(optimal_moves * 1.8, optimal_moves + 4)
    efficient_completion = goal_reached and session.moves_count <= expected_moves

    if avg_cognitive_load >= 0.75:
        new_difficulty = max(game.min_difficulty, current_difficulty - 1)
        dda_reason = "Easier: cognitive load was high, so the next maze reduces pressure."
    elif not goal_reached:
        new_difficulty = max(game.min_difficulty, current_difficulty - 1)
        dda_reason = "Easier: goal was not reached before ending the maze."
    elif efficient_completion and avg_attention >= 0.6 and avg_cognitive_load <= 0.65:
        new_difficulty = min(game.max_difficulty, current_difficulty + 1)
        dda_reason = "Harder: you reached the goal efficiently with good attention and manageable load."
    elif session.moves_count > expected_moves:
        new_difficulty = max(game.min_difficulty, current_difficulty - 1)
        dda_reason = "Easier: too many moves were needed compared with the expected path."
    else:
        new_difficulty = current_difficulty
        dda_reason = "Same: performance and brain metrics were in the target zone."

    if new_difficulty > current_difficulty:
        dda_direction = "harder"
    elif new_difficulty < current_difficulty:
        dda_direction = "easier"
    else:
        dda_direction = "same"
    
    # Log the trial
    feedback = FeedbackLog(
        session_id=session_id,
        trial_number=1,
        reaction_time_ms=completion_time_ms,
        is_correct=goal_reached,
        difficulty_at_trial=current_difficulty,
        difficulty_after_trial=new_difficulty,
        stimulus_data={"maze_size": session.maze_data['size'], "optimal_moves": optimal_moves},
        response_data={"actual_moves": session.moves_count, "efficiency": efficiency, "dda_reason": dda_reason},
        eeg_attention=avg_attention,
        eeg_cognitive_load=avg_cognitive_load
    )
    db.session.add(feedback)
    
    # Update session
    session.total_trials = 1
    session.correct_trials = 1 if goal_reached else 0
    session.avg_reaction_time_ms = completion_time_ms
    session.final_difficulty = new_difficulty
    
    # Calculate score (efficiency * difficulty * goal_reached)
    session.score = round(efficiency * 100 * (current_difficulty / 10.0) * (1 if goal_reached else 0.5), 2)
    
    db.session.commit()
    
    return jsonify({
        "session_id": session.id,
        "goal_reached": goal_reached,
        "moves_count": session.moves_count,
        "optimal_moves": optimal_moves,
        "efficiency": round(efficiency * 100, 1),
        "completion_time_seconds": round(completion_time_ms / 1000, 1),
        "score": session.score,
        "current_difficulty": current_difficulty,
        "next_difficulty": new_difficulty,
        "dda_direction": dda_direction,
        "dda_reason": dda_reason,
        "avg_attention": round(avg_attention, 2),
        "avg_cognitive_load": round(avg_cognitive_load, 2)
    }), 200
