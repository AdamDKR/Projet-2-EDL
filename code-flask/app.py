import csv
import io
from datetime import date, datetime, timedelta
from flask import Flask, flash, redirect, render_template_string, request, Response, url_for

from base import ouvrir_base
from regles import (
    calculer_semaine,
    valider_capacite,
    valider_creneau,
    valider_format_date,
    valider_horaires_salle,
    verifier_chevauchement,
)

app = Flask(__name__)
app.secret_key = "projet-2-edl-secret-key"

PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Réservation de Salles — EDL</title>
  <style>
    :root {
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --danger: #dc2626;
      --danger-hover: #b91c1c;
      --success: #16a34a;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #1e293b;
      --border: #e2e8f0;
      --muted: #64748b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 1.5rem;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    header { margin-bottom: 2rem; border-bottom: 2px solid var(--border); padding-bottom: 1rem; }
    h1 { font-size: 1.8rem; color: #0f172a; }
    h2 { font-size: 1.3rem; margin-bottom: 1rem; color: #334155; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem; }
    @media (max-width: 850px) { .grid { grid-template-columns: 1fr; } }
    .card {
      background: var(--card-bg);
      border-radius: 8px;
      padding: 1.25rem;
      border: 1px solid var(--border);
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .full-width { grid-column: 1 / -1; }
    
    /* Alerts */
    .alerts { margin-bottom: 1.5rem; }
    .alert {
      padding: 0.85rem 1rem;
      border-radius: 6px;
      margin-bottom: 0.5rem;
      font-weight: 500;
      font-size: 0.95rem;
    }
    .alert-error { background-color: #fee2e2; color: #991b1b; border: 1px solid #f87171; }
    .alert-success { background-color: #dcfce7; color: #166534; border: 1px solid #86efac; }
    
    /* Forms */
    form { display: flex; flex-direction: column; gap: 0.8rem; }
    .form-row { display: flex; gap: 0.8rem; flex-wrap: wrap; }
    .form-group { display: flex; flex-direction: column; flex: 1; min-width: 140px; }
    label { font-size: 0.85rem; font-weight: 600; color: #475569; margin-bottom: 0.25rem; }
    input, select, button {
      padding: 0.55rem 0.75rem;
      border-radius: 6px;
      border: 1px solid var(--border);
      font-size: 0.95rem;
    }
    input:focus, select:focus { outline: none; border-color: var(--primary); ring: 2px var(--primary); }
    .checkbox-group { display: flex; align-items: center; gap: 0.5rem; margin-top: 1.5rem; }
    .checkbox-group input { width: 1.1rem; height: 1.1rem; cursor: pointer; }
    
    /* Buttons */
    button, .btn {
      cursor: pointer;
      font-weight: 600;
      transition: background-color 0.15s ease;
      text-align: center;
      text-decoration: none;
      display: inline-block;
    }
    .btn-primary { background: var(--primary); color: white; border: none; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-danger { background: var(--danger); color: white; border: none; padding: 0.35rem 0.65rem; font-size: 0.85rem; border-radius: 4px; }
    .btn-danger:hover { background: var(--danger-hover); }
    .btn-secondary { background: #e2e8f0; color: #334155; border: 1px solid #cbd5e1; padding: 0.35rem 0.65rem; font-size: 0.85rem; border-radius: 4px; }
    .btn-secondary:hover { background: #cbd5e1; }
    
    /* Tables */
    table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; font-size: 0.9rem; }
    th, td { text-align: left; padding: 0.65rem 0.75rem; border-bottom: 1px solid var(--border); }
    th { background: #f1f5f9; color: #475569; font-weight: 600; }
    tr:hover { background: #f8fafc; }
    .badge {
      display: inline-block;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .badge-yes { background: #dcfce7; color: #15803d; }
    .badge-no { background: #f1f5f9; color: #64748b; }
    
    /* Planning Calendar */
    .calendar-grid {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 0.5rem;
      margin-top: 1rem;
    }
    @media (max-width: 950px) { .calendar-grid { grid-template-columns: 1fr; } }
    .cal-day {
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.6rem;
      min-height: 140px;
    }
    .cal-day-header {
      font-weight: 700;
      font-size: 0.85rem;
      padding-bottom: 0.4rem;
      border-bottom: 1px solid var(--border);
      margin-bottom: 0.5rem;
      color: #334155;
      text-align: center;
    }
    .cal-event {
      background: #e0e7ff;
      border-left: 3px solid var(--primary);
      border-radius: 4px;
      padding: 0.4rem;
      margin-bottom: 0.4rem;
      font-size: 0.8rem;
    }
    .cal-time { font-weight: 700; color: #1e40af; }
    .cal-title { font-weight: 600; }
    .cal-meta { color: var(--muted); font-size: 0.75rem; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Système de Réservation de Salles</h1>
      <p style="color: var(--muted);">Gestion autonome sans conflit et dans la limite des capacités.</p>
    </header>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <div class="alerts">
          {% for category, message in messages %}
            <div class="alert alert-{{ category }}">{{ message }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}

    <div class="grid">
      <!-- Section Salles -->
      <div class="card">
        <h2>🏢 Salles Disponibles</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Nom</th>
              <th>Capacité</th>
              <th>Projecteur</th>
              <th>Horaires</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {% for s in salles %}
              <tr>
                <td>#{{ s["id"] }}</td>
                <td><strong>{{ s["nom"] }}</strong></td>
                <td>{{ s["capacite"] }} pers.</td>
                <td>
                  {% if s["projecteur"] == 1 %}
                    <span class="badge badge-yes">Oui</span>
                  {% else %}
                    <span class="badge badge-no">Non</span>
                  {% endif %}
                </td>
                <td><small>{{ s["ouverture"] }} - {{ s["fermeture"] }}</small></td>
                <td>
                  <form method="post" action="/salles/{{ s['id'] }}/supprimer" style="display:inline;" onsubmit="return confirm('Supprimer cette salle et toutes ses réservations ?');">
                    <button class="btn-danger" type="submit">Supprimer</button>
                  </form>
                </td>
              </tr>
              <!-- Formulaire de modification rapide -->
              <tr>
                <td colspan="6" style="padding-top: 0.2rem; padding-bottom: 0.8rem; background: #fafafa;">
                  <details>
                    <summary style="cursor:pointer; font-size: 0.8rem; color: var(--primary);">Modifier la salle {{ s["nom"] }}</summary>
                    <form method="post" action="/salles/{{ s['id'] }}/modifier" style="margin-top: 0.5rem;">
                      <div class="form-row">
                        <div class="form-group">
                          <label>Nom</label>
                          <input name="nom" value="{{ s['nom'] }}" required>
                        </div>
                        <div class="form-group" style="max-width: 100px;">
                          <label>Capacité</label>
                          <input name="capacite" type="number" min="1" value="{{ s['capacite'] }}" required>
                        </div>
                        <div class="form-group" style="max-width: 100px;">
                          <label>Ouverture</label>
                          <input name="ouverture" type="time" value="{{ s['ouverture'] }}" required>
                        </div>
                        <div class="form-group" style="max-width: 100px;">
                          <label>Fermeture</label>
                          <input name="fermeture" type="time" value="{{ s['fermeture'] }}" required>
                        </div>
                        <div class="checkbox-group">
                          <label><input type="checkbox" name="projecteur" value="1" {% if s["projecteur"] == 1 %}checked{% endif %}> Projecteur</label>
                        </div>
                        <div class="form-group" style="justify-content: flex-end;">
                          <button class="btn btn-secondary" type="submit">Enregistrer</button>
                        </div>
                      </div>
                    </form>
                  </details>
                </td>
              </tr>
            {% endfor %}
          </tbody>
        </table>

        <h3 style="margin-top: 1.5rem; font-size: 1.1rem; color: #334155;">Ajouter une nouvelle salle</h3>
        <form method="post" action="/salles" style="margin-top: 0.8rem;">
          <div class="form-row">
            <div class="form-group">
              <label>Nom de la salle</label>
              <input name="nom" placeholder="Ex: S3, Amphi A" required>
            </div>
            <div class="form-group">
              <label>Capacité</label>
              <input name="capacite" type="number" min="1" placeholder="Ex: 25" required>
            </div>
            <div class="form-group">
              <label>Ouverture</label>
              <input name="ouverture" type="time" value="08:00" required>
            </div>
            <div class="form-group">
              <label>Fermeture</label>
              <input name="fermeture" type="time" value="20:00" required>
            </div>
            <div class="checkbox-group">
              <label><input type="checkbox" name="projecteur" value="1"> Projecteur</label>
            </div>
          </div>
          <button class="btn btn-primary" type="submit">Ajouter la salle</button>
        </form>
      </div>

      <!-- Section Réservation -->
      <div class="card">
        <h2>📅 Réserver une Salle</h2>
        <form method="post" action="/reservations">
          <div class="form-row">
            <div class="form-group">
              <label>Salle</label>
              <select name="salle_id" required>
                {% for s in salles %}
                  <option value="{{ s['id'] }}" {% if selected_salle_id == s['id'] %}selected{% endif %}>
                    {{ s["nom"] }} (cap. {{ s["capacite"] }}{% if s["projecteur"] %}, projecteur{% endif %})
                  </option>
                {% endfor %}
              </select>
            </div>
            <div class="form-group">
              <label>Nom de la personne</label>
              <input name="personne" placeholder="Ex: Alice, Bob" required>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Date</label>
              <input name="date" type="date" value="{{ ref_date }}" required>
            </div>
            <div class="form-group">
              <label>Nombre de participants</label>
              <input name="participants" type="number" min="1" placeholder="Ex: 10" required>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Heure de début</label>
              <input name="debut" type="time" value="09:00" required>
            </div>
            <div class="form-group">
              <label>Heure de fin</label>
              <input name="fin" type="time" value="10:30" required>
            </div>
          </div>
          <button class="btn btn-primary" type="submit">Valider la réservation</button>
        </form>

        <h3 style="margin-top: 1.5rem; font-size: 1.1rem; color: #334155;">Annuler une réservation</h3>
        <p style="font-size: 0.85rem; color: var(--muted); margin-bottom: 0.5rem;">Dernières réservations enregistrées :</p>
        <table>
          <thead>
            <tr>
              <th>Salle</th>
              <th>Personne</th>
              <th>Date</th>
              <th>Créneau</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {% for r in toutes_reservations %}
              <tr>
                <td><strong>{{ r["salle_nom"] }}</strong></td>
                <td>{{ r["personne"] }} ({{ r["participants"] }}p)</td>
                <td>{{ r["date"] }}</td>
                <td>{{ r["debut"] }} - {{ r["fin"] }}</td>
                <td>
                  <form method="post" action="/reservations/{{ r['id'] }}/annuler" style="display:inline;">
                    <button class="btn-danger" type="submit">Annuler</button>
                  </form>
                </td>
              </tr>
            {% else %}
              <tr><td colspan="5" style="text-align:center; color: var(--muted);">Aucune réservation en cours.</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <!-- Section Planning Hebdomadaire -->
      <div class="card full-width">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <h2>🗓️ Planning Hebdomadaire (du Lundi au Dimanche)</h2>
          <div>
            {% if planning_salle %}
              <a class="btn btn-secondary" href="/planning/export?salle_id={{ planning_salle['id'] }}&date={{ ref_date }}">📥 Exporter en CSV</a>
            {% endif %}
          </div>
        </div>
        
        <form method="get" action="/" style="margin-bottom: 1rem;">
          <div class="form-row" style="align-items: flex-end;">
            <div class="form-group">
              <label>Choisir la salle</label>
              <select name="salle_id" onchange="this.form.submit()">
                {% for s in salles %}
                  <option value="{{ s['id'] }}" {% if planning_salle and planning_salle['id'] == s['id'] %}selected{% endif %}>
                    {{ s["nom"] }} (cap. {{ s["capacite"] }})
                  </option>
                {% endfor %}
              </select>
            </div>
            <div class="form-group">
              <label>Date de référence</label>
              <input name="date" type="date" value="{{ ref_date }}" onchange="this.form.submit()">
            </div>
            <div class="form-group" style="flex: 0;">
              <button class="btn btn-secondary" type="submit">Afficher</button>
            </div>
          </div>
        </form>

        {% if planning_salle %}
          <div style="display: flex; gap: 2rem; margin-bottom: 0.5rem; font-size: 0.95rem;">
            <span>Semaine du <strong>{{ lundi_str }}</strong> au <strong>{{ dimanche_str }}</strong></span>
            <span>Salle sélectionnée : <strong>{{ planning_salle["nom"] }}</strong> (Capacité : {{ planning_salle["capacite"] }} pers., Horaires : {{ planning_salle["ouverture"] }} - {{ planning_salle["fermeture"] }})</span>
            <span>Taux d'occupation : <strong>{{ taux_occupation }}%</strong></span>
          </div>

          <div class="calendar-grid">
            {% for jour in semaine_jours %}
              <div class="cal-day">
                <div class="cal-day-header">{{ jour["nom"] }}<br><span style="font-weight: normal; font-size: 0.75rem;">{{ jour["date"] }}</span></div>
                {% for ev in jour["reservations"] %}
                  <div class="cal-event">
                    <div class="cal-time">{{ ev["debut"] }} - {{ ev["fin"] }}</div>
                    <div class="cal-title">{{ ev["personne"] }}</div>
                    <div class="cal-meta">{{ ev["participants"] }} pers.</div>
                    <form method="post" action="/reservations/{{ ev['id'] }}/annuler" style="margin-top: 0.3rem;">
                      <button class="btn-danger" style="padding: 0.15rem 0.4rem; font-size: 0.7rem;" type="submit">Annuler</button>
                    </form>
                  </div>
                {% else %}
                  <p style="font-size: 0.75rem; color: var(--muted); text-align: center; margin-top: 1rem;">Libre</p>
                {% endfor %}
              </div>
            {% endfor %}
          </div>
        {% else %}
          <p style="color: var(--muted);">Aucune salle disponible.</p>
        {% endif %}
      </div>

      <!-- Section Bonus : Recherche de Salle Libre -->
      <div class="card full-width">
        <h2>🔍 Bonus : Rechercher une Salle Libre</h2>
        <form method="get" action="/recherche" style="margin-bottom: 1rem;">
          <div class="form-row">
            <div class="form-group">
              <label>Date</label>
              <input name="date" type="date" value="{{ search_date or ref_date }}" required>
            </div>
            <div class="form-group">
              <label>Heure de début</label>
              <input name="debut" type="time" value="{{ search_debut or '14:00' }}" required>
            </div>
            <div class="form-group">
              <label>Heure de fin</label>
              <input name="fin" type="time" value="{{ search_fin or '16:00' }}" required>
            </div>
            <div class="form-group">
              <label>Participants minimum</label>
              <input name="participants" type="number" min="1" value="{{ search_participants or '1' }}" required>
            </div>
            <div class="checkbox-group">
              <label><input type="checkbox" name="projecteur" value="1" {% if search_projecteur %}checked{% endif %}> Projecteur requis</label>
            </div>
            <div class="form-group" style="justify-content: flex-end;">
              <button class="btn btn-primary" type="submit">Rechercher</button>
            </div>
          </div>
        </form>

        {% if search_results is not none %}
          <h3 style="font-size: 1rem; color: #334155; margin-bottom: 0.5rem;">Résultats disponibles :</h3>
          <table>
            <thead>
              <tr>
                <th>Nom</th>
                <th>Capacité</th>
                <th>Projecteur</th>
                <th>Horaires</th>
              </tr>
            </thead>
            <tbody>
              {% for s in search_results %}
                <tr>
                  <td><strong>{{ s["nom"] }}</strong></td>
                  <td>{{ s["capacite"] }} personnes</td>
                  <td>{% if s["projecteur"] == 1 %}<span class="badge badge-yes">Oui</span>{% else %}<span class="badge badge-no">Non</span>{% endif %}</td>
                  <td>{{ s["ouverture"] }} - {{ s["fermeture"] }}</td>
                </tr>
              {% else %}
                <tr><td colspan="4" style="text-align: center; color: var(--danger);">Aucune salle disponible pour ce créneau et ces critères.</td></tr>
              {% endfor %}
            </tbody>
          </table>
        {% endif %}
      </div>
    </div>
  </div>
</body>
</html>
"""


def get_salle_by_id(conn, salle_id: int):
    return conn.execute("SELECT * FROM salles WHERE id = ?", [salle_id]).fetchone()


def get_planning_context(conn, salle_id_arg=None, date_arg=None):
    """Prépare toutes les données nécessaires à l'affichage du planning et des formulaires."""
    ref_date = date_arg or "2026-11-09"
    if not valider_format_date(ref_date):
        ref_date = "2026-11-09"

    salles = conn.execute("SELECT * FROM salles ORDER BY nom").fetchall()

    planning_salle = None
    if salle_id_arg:
        try:
            planning_salle = get_salle_by_id(conn, int(salle_id_arg))
        except (ValueError, TypeError):
            pass
    if not planning_salle and salles:
        planning_salle = salles[0]

    lundi, dimanche = calculer_semaine(ref_date)
    lundi_str = lundi.strftime("%Y-%m-%d")
    dimanche_str = dimanche.strftime("%Y-%m-%d")

    reservations_semaine = []
    if planning_salle:
        reservations_semaine = conn.execute(
            """
            SELECT * FROM reservations
            WHERE salle_id = ? AND date >= ? AND date <= ?
            ORDER BY date, debut
            """,
            [planning_salle["id"], lundi_str, dimanche_str],
        ).fetchall()

    jours_noms = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    semaine_jours = []
    for i in range(7):
        j_date = lundi + timedelta(days=i)
        j_str = j_date.strftime("%Y-%m-%d")
        evs = [r for r in reservations_semaine if r["date"] == j_str]
        semaine_jours.append({
            "nom": jours_noms[i],
            "date": j_str,
            "reservations": evs,
        })

    taux_occupation = 0.0
    if planning_salle:
        try:
            t_ouv = datetime.strptime(planning_salle["ouverture"], "%H:%M")
            t_fer = datetime.strptime(planning_salle["fermeture"], "%H:%M")
            minutes_ouvertes_jour = max(0, (t_fer - t_ouv).total_seconds() / 60)
            minutes_ouvertes_semaine = minutes_ouvertes_jour * 7
            minutes_reservees = 0
            for r in reservations_semaine:
                d_r = datetime.strptime(r["debut"], "%H:%M")
                f_r = datetime.strptime(r["fin"], "%H:%M")
                minutes_reservees += (f_r - d_r).total_seconds() / 60
            if minutes_ouvertes_semaine > 0:
                taux_occupation = round((minutes_reservees / minutes_ouvertes_semaine) * 100, 1)
        except Exception:
            taux_occupation = 0.0

    toutes_reservations = conn.execute(
        """
        SELECT r.*, s.nom as salle_nom
        FROM reservations r
        JOIN salles s ON s.id = r.salle_id
        ORDER BY r.date DESC, r.debut DESC
        LIMIT 15
        """
    ).fetchall()

    return {
        "salles": salles,
        "planning_salle": planning_salle,
        "ref_date": ref_date,
        "lundi_str": lundi_str,
        "dimanche_str": dimanche_str,
        "semaine_jours": semaine_jours,
        "toutes_reservations": toutes_reservations,
        "selected_salle_id": planning_salle["id"] if planning_salle else None,
        "taux_occupation": min(100.0, taux_occupation),
    }


@app.get("/")
def accueil():
    with ouvrir_base() as conn:
        ctx = get_planning_context(
            conn,
            salle_id_arg=request.args.get("salle_id"),
            date_arg=request.args.get("date"),
        )
    return render_template_string(PAGE, **ctx, search_results=None)


# ----------------------------------------------------
# GESTION DES SALLES (CRUD & CASCADE)
# ----------------------------------------------------

@app.post("/salles")
def ajouter_salle():
    nom = request.form.get("nom", "").strip()
    capacite_raw = request.form.get("capacite", "").strip()
    projecteur = 1 if request.form.get("projecteur") in ("1", "on", "true") else 0
    ouverture = request.form.get("ouverture", "08:00").strip() or "08:00"
    fermeture = request.form.get("fermeture", "20:00").strip() or "20:00"

    if not nom:
        flash("Erreur : Nom obligatoire pour la salle.", "error")
        return redirect("/")

    try:
        capacite = int(capacite_raw)
        if capacite <= 0:
            raise ValueError()
    except ValueError:
        flash("Erreur : Capacité invalide (doit être un entier > 0).", "error")
        return redirect("/")

    valide_h, err_h = valider_horaires_salle(ouverture, fermeture)
    if not valide_h:
        flash(f"Erreur horaires : {err_h}", "error")
        return redirect("/")

    with ouvrir_base() as conn:
        conn.execute(
            "INSERT INTO salles (nom, capacite, projecteur, ouverture, fermeture) VALUES (?, ?, ?, ?, ?)",
            [nom, capacite, projecteur, ouverture, fermeture],
        )
    flash(f"Salle '{nom}' ajoutée avec succès.", "success")
    return redirect("/")


@app.post("/salles/<int:salle_id>/modifier")
def modifier_salle(salle_id: int):
    nom = request.form.get("nom", "").strip()
    capacite_raw = request.form.get("capacite", "").strip()
    projecteur = 1 if request.form.get("projecteur") in ("1", "on", "true") else 0
    ouverture = request.form.get("ouverture", "08:00").strip() or "08:00"
    fermeture = request.form.get("fermeture", "20:00").strip() or "20:00"

    if not nom:
        flash("Erreur : Le nom de la salle ne peut pas être vide.", "error")
        return redirect(f"/?salle_id={salle_id}")

    try:
        capacite = int(capacite_raw)
        if capacite <= 0:
            raise ValueError()
    except ValueError:
        flash("Erreur : Capacité invalide.", "error")
        return redirect(f"/?salle_id={salle_id}")

    valide_h, err_h = valider_horaires_salle(ouverture, fermeture)
    if not valide_h:
        flash(f"Erreur horaires : {err_h}", "error")
        return redirect(f"/?salle_id={salle_id}")

    with ouvrir_base() as conn:
        salle = get_salle_by_id(conn, salle_id)
        if not salle:
            flash("Salle introuvable.", "error")
            return redirect("/")

        # Vérifier si des réservations existantes dépassent la nouvelle capacité
        row_max = conn.execute(
            "SELECT MAX(participants) as m FROM reservations WHERE salle_id = ?",
            [salle_id],
        ).fetchone()
        max_part = row_max["m"] if row_max else None
        if max_part and max_part > capacite:
            flash(
                f"Erreur : Impossible de réduire la capacité à {capacite}. Une réservation existante compte {max_part} participants.",
                "error",
            )
            return redirect(f"/?salle_id={salle_id}")

        # Vérifier si des réservations existantes sortent des nouveaux horaires
        resas_salle = conn.execute(
            "SELECT * FROM reservations WHERE salle_id = ?",
            [salle_id],
        ).fetchall()
        for r in resas_salle:
            val_c, _ = valider_creneau(r["debut"], r["fin"], ouverture=ouverture, fermeture=fermeture)
            if not val_c:
                flash(
                    f"Erreur horaires : Une réservation existante ({r['debut']} - {r['fin']} pour {r['personne']}) serait hors des nouveaux horaires ({ouverture} - {fermeture}).",
                    "error",
                )
                return redirect(f"/?salle_id={salle_id}")

        conn.execute(
            """
            UPDATE salles
            SET nom = ?, capacite = ?, projecteur = ?, ouverture = ?, fermeture = ?
            WHERE id = ?
            """,
            [nom, capacite, projecteur, ouverture, fermeture, salle_id],
        )
    flash("Salle mise à jour avec succès.", "success")
    return redirect(f"/?salle_id={salle_id}")


@app.post("/salles/<int:salle_id>/supprimer")
def supprimer_salle(salle_id: int):
    with ouvrir_base() as conn:
        cur = conn.execute("DELETE FROM salles WHERE id = ?", [salle_id])
        if cur.rowcount == 0:
            flash("Salle introuvable.", "error")
            return redirect("/")
    flash("Salle supprimée (et ses réservations associées supprimées en cascade).", "success")
    return redirect("/")


# ----------------------------------------------------
# RESERVATIONS & ANNULATIONS
# ----------------------------------------------------

@app.post("/reservations")
def creer_reservation():
    salle_id_raw = request.form.get("salle_id")
    personne = request.form.get("personne", "").strip()
    date_str = request.form.get("date", "").strip()
    debut = request.form.get("debut", "").strip()
    fin = request.form.get("fin", "").strip()
    participants_raw = request.form.get("participants", "").strip()

    dest_url = f"/?date={date_str}"
    if salle_id_raw:
        dest_url = f"/?salle_id={salle_id_raw}&date={date_str}"

    if not personne:
        flash("Erreur : Le nom de la personne est requis.", "error")
        return redirect(dest_url)

    if not valider_format_date(date_str):
        flash("Erreur : Format de date invalide (attendu AAAA-MM-JJ).", "error")
        return redirect(dest_url)

    with ouvrir_base() as conn:
        try:
            salle_id = int(salle_id_raw)
            salle = get_salle_by_id(conn, salle_id)
        except (ValueError, TypeError):
            salle = None

        if not salle:
            flash("Erreur : Salle inexistante.", "error")
            return redirect(dest_url)

        # Règle créneau & horaires (avec prise en compte des horaires de la salle)
        ouv = salle["ouverture"] if "ouverture" in salle.keys() else "08:00"
        fer = salle["fermeture"] if "fermeture" in salle.keys() else "20:00"
        valide_creneau, err_creneau = valider_creneau(debut, fin, ouverture=ouv, fermeture=fer)
        if not valide_creneau:
            flash(err_creneau, "error")
            return redirect(f"/?salle_id={salle_id}&date={date_str}")

        # Règle capacité
        valide_cap, err_cap = valider_capacite(participants_raw, salle["capacite"])
        if not valide_cap:
            flash(err_cap, "error")
            return redirect(f"/?salle_id={salle_id}&date={date_str}")
        participants = int(participants_raw)

        # Règle non-chevauchement
        resas_existantes = conn.execute(
            "SELECT * FROM reservations WHERE salle_id = ? AND date = ?",
            [salle_id, date_str],
        ).fetchall()
        resas_list = [dict(r) for r in resas_existantes]

        valide_chev, err_chev = verifier_chevauchement(debut, fin, resas_list)
        if not valide_chev:
            flash(err_chev, "error")
            return redirect(f"/?salle_id={salle_id}&date={date_str}")

        # Insertion
        conn.execute(
            """
            INSERT INTO reservations (salle_id, personne, date, debut, fin, participants)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [salle_id, personne, date_str, debut, fin, participants],
        )

    flash("Réservation enregistrée avec succès !", "success")
    return redirect(f"/?salle_id={salle_id}&date={date_str}")


@app.post("/reservations/<int:resa_id>/annuler")
def annuler_reservation(resa_id: int):
    with ouvrir_base() as conn:
        r = conn.execute("SELECT * FROM reservations WHERE id = ?", [resa_id]).fetchone()
        if not r:
            flash("Réservation introuvable.", "error")
            return redirect("/")
        salle_id = r["salle_id"]
        date_str = r["date"]
        conn.execute("DELETE FROM reservations WHERE id = ?", [resa_id])

    flash("Réservation annulée avec succès.", "success")
    url = f"/?salle_id={salle_id}&date={date_str}"
    return redirect(url)


# ----------------------------------------------------
# EXPORT DU PLANNING (BONUS)
# ----------------------------------------------------

@app.get("/planning/export")
def exporter_planning():
    salle_id_raw = request.args.get("salle_id")
    ref_date = request.args.get("date", "2026-11-09")
    if not valider_format_date(ref_date):
        ref_date = "2026-11-09"

    with ouvrir_base() as conn:
        try:
            salle = get_salle_by_id(conn, int(salle_id_raw))
        except (ValueError, TypeError):
            salle = None

        if not salle:
            flash("Salle introuvable pour l'export.", "error")
            return redirect("/")

        lundi, dimanche = calculer_semaine(ref_date)
        resas = conn.execute(
            """
            SELECT * FROM reservations
            WHERE salle_id = ? AND date >= ? AND date <= ?
            ORDER BY date, debut
            """,
            [salle["id"], lundi.strftime("%Y-%m-%d"), dimanche.strftime("%Y-%m-%d")],
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Salle", "Date", "Heure Début", "Heure Fin", "Personne", "Participants"])
    for r in resas:
        writer.writerow([salle["nom"], r["date"], r["debut"], r["fin"], r["personne"], r["participants"]])

    filename = f"planning_{salle['nom']}_{lundi.strftime('%Y%m%d')}.csv"
    csv_bytes = ("\ufeff" + output.getvalue()).encode("utf-8")
    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ----------------------------------------------------
# RECHERCHE DE SALLE LIBRE (BONUS)
# ----------------------------------------------------

@app.get("/recherche")
def recherche_salle():
    date_str = request.args.get("date", "").strip()
    debut = request.args.get("debut", "").strip()
    fin = request.args.get("fin", "").strip()
    participants_raw = request.args.get("participants", "1").strip()
    proj_req = request.args.get("projecteur") in ("1", "on", "true")

    try:
        nb_part = int(participants_raw) if participants_raw else 1
    except ValueError:
        nb_part = 1

    search_performed = bool(date_str and debut and fin)
    search_results = [] if search_performed else None

    with ouvrir_base() as conn:
        if search_performed:
            if not valider_format_date(date_str):
                flash("Erreur : Format de date invalide pour la recherche.", "error")
            else:
                salles = conn.execute("SELECT * FROM salles").fetchall()
                for s in salles:
                    if s["capacite"] < nb_part:
                        continue
                    if proj_req and s["projecteur"] != 1:
                        continue
                    ouv = s["ouverture"]
                    fer = s["fermeture"]
                    valide_c, _ = valider_creneau(debut, fin, ouverture=ouv, fermeture=fer)
                    if not valide_c:
                        continue
                    resas = conn.execute(
                        "SELECT * FROM reservations WHERE salle_id = ? AND date = ?",
                        [s["id"], date_str],
                    ).fetchall()
                    valide_chev, _ = verifier_chevauchement(debut, fin, [dict(r) for r in resas])
                    if valide_chev:
                        search_results.append(s)

        ctx = get_planning_context(
            conn,
            salle_id_arg=request.args.get("salle_id"),
            date_arg=date_str if valider_format_date(date_str) else None,
        )

    return render_template_string(
        PAGE,
        **ctx,
        search_results=search_results,
        search_date=date_str,
        search_debut=debut,
        search_fin=fin,
        search_participants=nb_part,
        search_projecteur=proj_req,
    )


if __name__ == "__main__":
    app.run(debug=True)
