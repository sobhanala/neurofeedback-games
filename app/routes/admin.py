from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.game import Game
from app.models.session import GameSession
from app.services.dda_engine import DDA_ALGORITHMS
from sqlalchemy import func
import re
import random

admin_bp = Blueprint("admin", __name__)


def staff_required(func_view):
    """Decorator to restrict access to admin and experimenter users."""
    @wraps(func_view)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff:
            flash("Staff access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return func_view(*args, **kwargs)
    return decorated


def admin_only(func_view):
    """Decorator to restrict access to admins only."""
    @wraps(func_view)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("admin.dashboard"))
        return func_view(*args, **kwargs)
    return decorated


def admin_required(func_view):
    """Decorator to restrict access to admins only."""
    @wraps(func_view)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("admin.dashboard"))
        return func_view(*args, **kwargs)
    return decorated


def _scope_user_query(base_query):
    if current_user.is_admin:
        return base_query
    if current_user.is_experimenter:
        return base_query.filter(User.experimenter_id == current_user.id)
    return base_query.filter(User.id == -1)


def _scope_session_query(base_query):
    if current_user.is_admin:
        return base_query
    if current_user.is_experimenter:
        return base_query.join(User, User.id == GameSession.user_id).filter(User.experimenter_id == current_user.id)
    return base_query.filter(GameSession.id == -1)


def _generate_experimenter_code(username):
    base = re.sub(r"[^A-Za-z0-9]", "", (username or "EXP").upper())[:6] or "EXP"
    for _ in range(50):
        candidate = f"EXP-{base}-{random.randint(100, 999)}"
        if not User.query.filter_by(experimenter_code=candidate).first():
            return candidate
    return f"EXP-{base}-{random.randint(1000, 9999)}"


@admin_bp.route("/")
@login_required
@staff_required
def dashboard():
    user_query = _scope_user_query(User.query.filter(User.is_experimenter.is_(False), User.is_admin.is_(False)))
    session_query = _scope_session_query(GameSession.query)

    total_users = user_query.count()
    total_sessions = session_query.count()
    total_games = Game.query.count()
    active_games = Game.query.filter_by(is_active=True).count()

    recent_sessions = session_query.order_by(GameSession.started_at.desc()).limit(20).all()

    summary = _scope_session_query(
        db.session.query(
            func.sum(GameSession.total_trials).label("total_trials"),
            func.sum(GameSession.correct_trials).label("total_correct"),
            func.avg(GameSession.score).label("avg_score"),
            func.avg(GameSession.avg_reaction_time_ms).label("avg_rt"),
        )
    ).first()

    total_trials = summary.total_trials or 0
    total_correct = summary.total_correct or 0
    accuracy_pct = round((total_correct / total_trials) * 100, 1) if total_trials else 0.0

    dashboard_stats = {
        "total_trials": total_trials,
        "total_correct": total_correct,
        "accuracy_pct": accuracy_pct,
        "avg_score": round(summary.avg_score or 0, 2),
        "avg_rt": round(summary.avg_rt or 0, 1),
    }

    game_stats = db.session.query(
        Game.name,
        func.count(GameSession.id).label("total_sessions"),
        func.count(func.distinct(GameSession.user_id)).label("unique_users"),
        func.avg(GameSession.score).label("avg_score"),
        func.avg(GameSession.avg_reaction_time_ms).label("avg_rt"),
    ).outerjoin(GameSession, Game.id == GameSession.game_id)

    if current_user.is_experimenter and not current_user.is_admin:
        game_stats = game_stats.outerjoin(User, User.id == GameSession.user_id).filter(
            (User.experimenter_id == current_user.id) | (User.id.is_(None))
        )

    game_stats = game_stats.group_by(Game.name).all()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_sessions=total_sessions,
        total_games=total_games,
        active_games=active_games,
        recent_sessions=recent_sessions,
        game_stats=game_stats,
        dashboard_stats=dashboard_stats,
    )


@admin_bp.route("/experimenters", methods=["GET", "POST"])
@login_required
@staff_required
@admin_only
def experimenters():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        code_input = request.form.get("experimenter_code", "").strip().upper()

        if not username or not email or not password:
            flash("Username, email, and password are required.", "danger")
            return redirect(url_for("admin.experimenters"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("admin.experimenters"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for("admin.experimenters"))

        if code_input:
            if User.query.filter_by(experimenter_code=code_input).first():
                flash("Experimenter code already exists.", "danger")
                return redirect(url_for("admin.experimenters"))
            experimenter_code = code_input
        else:
            experimenter_code = _generate_experimenter_code(username)

        experimenter = User(
            username=username,
            email=email,
            is_experimenter=True,
            experimenter_code=experimenter_code,
        )
        experimenter.set_password(password)

        db.session.add(experimenter)
        db.session.commit()
        flash(f"Experimenter '{username}' created with code '{experimenter_code}'.", "success")
        return redirect(url_for("admin.experimenters"))

    all_experimenters = User.query.filter_by(is_experimenter=True).order_by(User.created_at.desc()).all()
    return render_template("admin/experimenters.html", experimenters=all_experimenters)


@admin_bp.route("/users")
@login_required
@staff_required
def users():
    all_users = _scope_user_query(
        User.query.filter(User.is_admin.is_(False), User.is_experimenter.is_(False))
    ).order_by(User.created_at.desc()).all()

    rows = _scope_session_query(
        db.session.query(
            GameSession.user_id,
            func.count(GameSession.id).label("sessions"),
            func.sum(GameSession.total_trials).label("total_trials"),
            func.sum(GameSession.correct_trials).label("total_correct"),
            func.avg(GameSession.score).label("avg_score"),
            func.avg(GameSession.avg_reaction_time_ms).label("avg_rt"),
        ).group_by(GameSession.user_id)
    ).all()

    user_metrics = {}
    for row in rows:
        total_trials = row.total_trials or 0
        total_correct = row.total_correct or 0
        accuracy_pct = round((total_correct / total_trials) * 100, 1) if total_trials else 0.0
        user_metrics[row.user_id] = {
            "sessions": row.sessions or 0,
            "accuracy_pct": accuracy_pct,
            "avg_score": round(row.avg_score or 0, 2),
            "avg_rt": round(row.avg_rt or 0, 1),
        }

    return render_template("admin/users.html", users=all_users, user_metrics=user_metrics)


@admin_bp.route("/users/<int:user_id>")
@login_required
@staff_required
def user_detail(user_id):
    user_query = _scope_user_query(User.query)
    user = user_query.filter(User.id == user_id).first()
    if user is None:
        flash("User not found in your scope.", "danger")
        return redirect(url_for("admin.users"))

    sessions = _scope_session_query(GameSession.query.filter_by(user_id=user_id)).order_by(
        GameSession.started_at.desc()
    ).all()

    game_stats = db.session.query(
        Game.name,
        func.count(GameSession.id).label("sessions"),
        func.avg(GameSession.score).label("avg_score"),
        func.avg(GameSession.avg_reaction_time_ms).label("avg_rt"),
    ).join(Game, GameSession.game_id == Game.id).filter(GameSession.user_id == user_id)

    if current_user.is_experimenter and not current_user.is_admin:
        game_stats = game_stats.join(User, User.id == GameSession.user_id).filter(User.experimenter_id == current_user.id)

    game_stats = game_stats.group_by(Game.name).all()

    return render_template("admin/user_detail.html", user=user, sessions=sessions, game_stats=game_stats)


@admin_bp.route("/games")
@login_required
@staff_required
def games():
    all_games = Game.query.order_by(Game.created_at.desc()).all()
    return render_template("admin/games.html", games=all_games, algorithms=list(DDA_ALGORITHMS.keys()))


# @admin_bp.route("/games/create", methods=["GET", "POST"])
# @login_required
# @staff_required
# def create_game():
#     if request.method == "POST":
#         name = request.form.get("name", "").strip()
#         slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
#         description = request.form.get("description", "")
#         game_type = request.form.get("game_type", "reaction")
#         min_diff = int(request.form.get("min_difficulty", 1))
#         max_diff = int(request.form.get("max_difficulty", 10))
#         default_diff = int(request.form.get("default_difficulty", 5))
#         dda_algo = request.form.get("dda_algorithm", "threshold")

#         if Game.query.filter_by(slug=slug).first():
#             flash("A game with this slug already exists.", "danger")
#             return render_template("admin/create_game.html", algorithms=list(DDA_ALGORITHMS.keys()))

#         game = Game(
#             name=name,
#             slug=slug,
#             description=description,
#             game_type=game_type,
#             min_difficulty=min_diff,
#             max_difficulty=max_diff,
#             default_difficulty=default_diff,
#             dda_algorithm=dda_algo,
#             created_by=current_user.id,
#         )
#         db.session.add(game)
#         db.session.commit()
#         flash(f"Game '{name}' created successfully.", "success")
#         return redirect(url_for("admin.games"))

#     return render_template("admin/create_game.html", algorithms=list(DDA_ALGORITHMS.keys()))


# @admin_bp.route("/games/<int:game_id>/edit", methods=["GET", "POST"])
# @login_required
# @staff_required
# def edit_game(game_id):
#     game = Game.query.get_or_404(game_id)

#     if request.method == "POST":
#         game.name = request.form.get("name", game.name).strip()
#         game.description = request.form.get("description", game.description)
#         game.is_active = request.form.get("is_active") == "on"
#         game.min_difficulty = int(request.form.get("min_difficulty", game.min_difficulty))
#         game.max_difficulty = int(request.form.get("max_difficulty", game.max_difficulty))
#         game.default_difficulty = int(request.form.get("default_difficulty", game.default_difficulty))
#         game.dda_algorithm = request.form.get("dda_algorithm", game.dda_algorithm)
#         db.session.commit()
#         flash("Game updated successfully.", "success")
#         return redirect(url_for("admin.games"))

#     return render_template("admin/edit_game.html", game=game, algorithms=list(DDA_ALGORITHMS.keys()))


@admin_bp.route("/analytics")
@login_required
@staff_required
def analytics():
    from datetime import datetime, timedelta

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    daily_sessions = db.session.query(
        func.date(GameSession.started_at).label("date"),
        func.count(GameSession.id).label("count"),
    ).filter(GameSession.started_at >= thirty_days_ago)

    if current_user.is_experimenter and not current_user.is_admin:
        daily_sessions = daily_sessions.join(User, User.id == GameSession.user_id).filter(User.experimenter_id == current_user.id)

    daily_sessions = daily_sessions.group_by(func.date(GameSession.started_at)).order_by(func.date(GameSession.started_at)).all()

    algo_stats = db.session.query(
        GameSession.dda_algorithm_used,
        func.count(GameSession.id).label("sessions"),
        func.avg(GameSession.score).label("avg_score"),
        func.avg(GameSession.avg_reaction_time_ms).label("avg_rt"),
    )

    if current_user.is_experimenter and not current_user.is_admin:
        algo_stats = algo_stats.join(User, User.id == GameSession.user_id).filter(User.experimenter_id == current_user.id)

    algo_stats = algo_stats.group_by(GameSession.dda_algorithm_used).all()

    return render_template("admin/analytics.html", daily_sessions=daily_sessions, algo_stats=algo_stats)

@admin_bp.route('/games/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_game():
      if request.method == 'POST':
          name = request.form.get('name')
          slug = request.form.get('slug')
          description = request.form.get('description')
          game_type = request.form.get('game_type')
          is_unity_game = request.form.get('is_unity_game') == 'on'
          unity_build_path = request.form.get('unity_build_path') if is_unity_game else None
          dda_algorithm = request.form.get('dda_algorithm', 'threshold')
          min_difficulty = int(request.form.get('min_difficulty', 1))
          max_difficulty = int(request.form.get('max_difficulty', 10))
          default_difficulty = int(request.form.get('default_difficulty', 5))

          # Validate
          if Game.query.filter_by(slug=slug).first():
              flash('A game with this slug already exists.', 'error')
              return render_template('admin/create_game.html')

          game = Game(
              name=name,
              slug=slug,
              description=description,
              game_type=game_type,
              is_unity_game=is_unity_game,
              unity_build_path=unity_build_path,
              dda_algorithm=dda_algorithm,
              min_difficulty=min_difficulty,
              max_difficulty=max_difficulty,
              default_difficulty=default_difficulty,
              created_by=current_user.id
          )

          db.session.add(game)
          db.session.commit()

          flash(f'Game "{name}" created successfully!', 'success')
          return redirect(url_for('admin.games'))

      return render_template('admin/create_game.html')


@admin_bp.route('/games/<int:game_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_game(game_id):
    game = Game.query.get_or_404(game_id)

    if request.method == 'POST':
        game.name = request.form.get('name')
        game.description = request.form.get('description')
        game.game_type = request.form.get('game_type')
        game.is_unity_game = request.form.get('is_unity_game') == 'on'
        game.unity_build_path = request.form.get('unity_build_path') if game.is_unity_game else None
        game.dda_algorithm = request.form.get('dda_algorithm')
        game.min_difficulty = int(request.form.get('min_difficulty'))
        game.max_difficulty = int(request.form.get('max_difficulty'))
        game.default_difficulty = int(request.form.get('default_difficulty'))
        game.is_active = request.form.get('is_active') == 'on'

        db.session.commit()

        flash(f'Game "{game.name}" updated successfully!', 'success')
        return redirect(url_for('admin.games'))

    return render_template('admin/edit_game.html', game=game)


@admin_bp.route('/unity/games/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_unity_game():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
        description = request.form.get('description', '')
        unity_build_path = request.form.get('unity_build_path', '').strip()
        dda_algorithm = request.form.get('dda_algorithm', 'eeg_enhanced')
        min_difficulty = int(request.form.get('min_difficulty', 1))
        max_difficulty = int(request.form.get('max_difficulty', 10))
        default_difficulty = int(request.form.get('default_difficulty', 5))

        if not name or not slug:
            flash('Name and slug are required.', 'danger')
            return render_template('admin/create_game.html', algorithms=list(DDA_ALGORITHMS.keys()))

        if Game.query.filter_by(slug=slug).first():
            flash('A game with this slug already exists.', 'danger')
            return render_template('admin/create_game.html', algorithms=list(DDA_ALGORITHMS.keys()))

        game = Game(
            name=name,
            slug=slug,
            description=description,
            game_type='unity',
            is_unity_game=True,
            unity_build_path=unity_build_path,
            dda_algorithm=dda_algorithm,
            min_difficulty=min_difficulty,
            max_difficulty=max_difficulty,
            default_difficulty=default_difficulty,
            created_by=current_user.id,
        )

        db.session.add(game)
        db.session.commit()
        flash(f'Unity game "{name}" created successfully.', 'success')
        return redirect(url_for('admin.games'))

    return render_template('admin/create_game.html', algorithms=list(DDA_ALGORITHMS.keys()))
