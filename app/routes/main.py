from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.session import GameSession, FeedbackLog
from app.models.game import Game
from app.extensions import db
from sqlalchemy import func

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    # User performance summary
    total_sessions = GameSession.query.filter_by(user_id=current_user.id).count()
    recent_sessions = GameSession.query.filter_by(user_id=current_user.id).order_by(
        GameSession.started_at.desc()
    ).limit(10).all()

    # Aggregate stats
    stats = db.session.query(
        func.avg(GameSession.avg_reaction_time_ms).label("avg_rt"),
        func.avg(GameSession.score).label("avg_score"),
        func.sum(GameSession.total_trials).label("total_trials"),
        func.sum(GameSession.correct_trials).label("total_correct"),
    ).filter(GameSession.user_id == current_user.id).first()

    games = Game.query.filter_by(is_active=True).all()

    return render_template("dashboard.html",
                           total_sessions=total_sessions,
                           recent_sessions=recent_sessions,
                           stats=stats,
                           games=games)


@main_bp.route("/profile")
@login_required
def profile():
    sessions = GameSession.query.filter_by(user_id=current_user.id).order_by(
        GameSession.started_at.desc()
    ).all()

    # Per-game stats
    game_stats = db.session.query(
        Game.name,
        func.count(GameSession.id).label("sessions"),
        func.avg(GameSession.score).label("avg_score"),
        func.avg(GameSession.avg_reaction_time_ms).label("avg_rt"),
    ).join(Game, GameSession.game_id == Game.id).filter(
        GameSession.user_id == current_user.id
    ).group_by(Game.name).all()

    return render_template("profile.html", sessions=sessions, game_stats=game_stats)


from flask import redirect, url_for
