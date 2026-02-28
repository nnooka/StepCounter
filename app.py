"""
Flask application for MI Fitness step counter visualisation.
"""

import os
import tempfile

import pandas as pd
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
)
from werkzeug.utils import secure_filename

from parser.mi_fitness import (
    generate_sample_data,
    monthly_summary,
    parse_file,
    yearly_summary,
)

ALLOWED_EXTENSIONS = {"zip", "csv", "json"}

app = Flask(__name__)
app.secret_key = os.urandom(24)


def _allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def _load_session_df() -> pd.DataFrame | None:
    """Load the DataFrame stored in the session temp file, or None."""
    path = session.get("data_path")
    if not path or not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"])
        return df
    except Exception:
        return None


def _save_df_to_session(df: pd.DataFrame) -> None:
    """Persist DataFrame to a temp CSV and store the path in session."""
    # Clean up old temp file if present
    old_path = session.get("data_path")
    if old_path and os.path.exists(old_path):
        try:
            os.remove(old_path)
        except OSError:
            pass

    fd, path = tempfile.mkstemp(suffix=".csv", prefix="stepcounter_")
    os.close(fd)
    df.to_csv(path, index=False)
    session["data_path"] = path


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    df = _load_session_df()
    if df is None:
        return redirect(url_for("upload"))
    return redirect(url_for("dashboard"))


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part in the request.", "danger")
            return render_template("upload.html")

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected.", "danger")
            return render_template("upload.html")

        if not _allowed_file(file.filename):
            flash(
                "Unsupported file type. Please upload a ZIP, CSV, or JSON file.",
                "danger",
            )
            return render_template("upload.html")

        # Sanitize filename (also implicitly validates it has an extension)
        file.filename = secure_filename(file.filename)
        try:
            df = parse_file(file)
        except Exception as exc:
            flash(f"Could not parse file: {exc}", "danger")
            return render_template("upload.html")

        if df.empty:
            flash("Parsed file contains no data.", "danger")
            return render_template("upload.html")

        _save_df_to_session(df)
        return redirect(url_for("dashboard"))

    return render_template("upload.html")


@app.route("/demo")
def demo():
    df = generate_sample_data()
    _save_df_to_session(df)
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    df = _load_session_df()
    if df is None:
        flash("No data loaded. Please upload a file or try the demo.", "warning")
        return redirect(url_for("upload"))
    years = sorted(df["date"].dt.year.unique().tolist())
    return render_template("dashboard.html", years=years)


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@app.route("/api/data")
def api_data():
    df = _load_session_df()
    if df is None:
        return jsonify({"error": "No data"}), 404
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/yearly")
def api_yearly():
    df = _load_session_df()
    if df is None:
        return jsonify({"error": "No data"}), 404
    summary = yearly_summary(df)
    return jsonify(summary.to_dict(orient="records"))


@app.route("/api/monthly")
def api_monthly():
    df = _load_session_df()
    if df is None:
        return jsonify({"error": "No data"}), 404
    try:
        year = int(request.args.get("year", df["date"].dt.year.max()))
    except (TypeError, ValueError):
        year = int(df["date"].dt.year.max())
    summary = monthly_summary(df, year)
    return jsonify(summary.to_dict(orient="records"))


if __name__ == "__main__":
    # Enable debug mode only when explicitly requested via environment variable.
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug)
