from flask import Flask, abort, redirect, render_template_string, request

from base import ouvrir_base
from regles import (
    RegleReservationException,
    calculer_semaine,
    valider_modification_capacite,
    valider_reservation,
    valider_salle,
)

# Template de la page d'accueil.
PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Réservation de salles</title>
  <style>
    body { font-family: sans-serif; max-width: 850px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
    h1, h2, h3 { color: #333; }
    .alert-error { background-color: #f8d7da; color: #721c24; padding: 12px; margin-bottom: 20px; border-radius: 4px; border: 1px solid #f5c6cb; }
    .alert-success { background-color: #d4edda; color: #155724; padding: 12px; margin-bottom: 20px; border-radius: 4px; border: 1px solid #c3e6cb; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background-color: #f4f4f4; }
    form.box { background: #fafafa; border: 1px solid #e0e0e0; padding: 15px; border-radius: 6px; margin-bottom: 2rem; }
    .form-group { margin-bottom: 10px; }
    label { display: inline-block; margin-bottom: 4px; font-weight: bold; }
    input, select, button { padding: 6px 10px; font-size: 1rem; }
    button.btn-primary { background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
    button.btn-primary:hover { background-color: #0056b3; }
    .actions a { color: #007bff; text-decoration: none; margin-right: 8px; font-size: 0.95rem; }
    .actions a:hover { text-decoration: underline; }
    .btn-delete { background: none; border: none; color: #dc3545; cursor: pointer; text-decoration: underline; padding: 0; font-size: 0.95rem; }
    .btn-delete:hover { color: #bd2130; }
    .nav-top { margin-bottom: 1.5rem; background: #e9ecef; padding: 10px 15px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }
    .nav-top a { color: #007bff; text-decoration: none; font-weight: bold; }
  </style>
</head>
<body>
  <div class="nav-top">
    <span><strong>Système universitaire</strong></span>
    <a href="/planning">📅 Consulter le planning hebdomadaire</a>
  </div>

  <h1>Réservation de salles</h1>

  {% if erreur %}
    <div class="alert-error">
      <strong>Erreur :</strong> {{ erreur }}
    </div>
  {% endif %}

  {% if request.args.get('succes') %}
    <div class="alert-success">
      <strong>Succès :</strong> {{ request.args.get('succes') }}
    </div>
  {% endif %}

  <h2>Salles</h2>
  {% if salles %}
    <ul>
      {% for salle in salles %}
        <li style="margin-bottom: 8px;">
          <strong>{{ salle["nom"] }}</strong> — Capacité : {{ salle["capacite"] }} personne(s)
          {% if salle["projecteur"] %}(avec projecteur){% endif %}
          <span class="actions" style="margin-left: 10px;">
            <a href="/planning?salle_id={{ salle['id'] }}">Voir planning</a>
            <a href="/salles/{{ salle['id'] }}/modifier">Modifier</a>
            <form method="post" action="/salles/{{ salle['id'] }}/supprimer" style="display: inline;" onsubmit="return confirm('Supprimer cette salle supprimera également toutes ses réservations. Confirmer ?');">
              <button type="submit" class="btn-delete">Supprimer</button>
            </form>
          </span>
        </li>
      {% endfor %}
    </ul>
  {% else %}
    <p>Aucune salle enregistrée.</p>
  {% endif %}

  <h3>Ajouter une salle</h3>
  <form class="box" method="post" action="/salles">
    <div class="form-group">
      <input name="nom" placeholder="Nom de la salle" required>
      <input name="capacite" type="number" min="1" placeholder="Capacité" required>
      <label style="font-weight: normal; margin-left: 10px;">
        <input name="projecteur" type="checkbox" value="1"> Projecteur
      </label>
      <button type="submit" class="btn-primary">Ajouter</button>
    </div>
  </form>

  <h2>Réservations existantes</h2>
  {% if reservations %}
    <table>
      <thead>
        <tr>
          <th>Salle</th>
          <th>Personne</th>
          <th>Date</th>
          <th>Horaires</th>
          <th>Participants</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {% for r in reservations %}
          <tr>
            <td>{{ r["salle_nom"] }}</td>
            <td>{{ r["personne"] }}</td>
            <td>{{ r["date"] }}</td>
            <td>{{ r["debut"] }} - {{ r["fin"] }}</td>
            <td>{{ r["participants"] }}</td>
            <td>
              <form method="post" action="/reservations/{{ r['id'] }}/annuler" style="display:inline;" onsubmit="return confirm('Confirmer l\'annulation de cette réservation ?');">
                <button type="submit" class="btn-delete">Annuler</button>
              </form>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>Aucune réservation enregistrée.</p>
  {% endif %}

  <h3>Réserver une salle</h3>
  {% if salles %}
    <form class="box" method="post" action="/reservations">
      <div class="form-group">
        <label for="salle_id">Salle :</label><br>
        <select id="salle_id" name="salle_id" required>
          {% for salle in salles %}
            <option value="{{ salle['id'] }}">{{ salle['nom'] }} (capacité max : {{ salle['capacite'] }})</option>
          {% endfor %}
        </select>
      </div>

      <div class="form-group">
        <label for="personne">Nom de la personne :</label><br>
        <input id="personne" name="personne" placeholder="ex: Alice" required>
      </div>

      <div class="form-group">
        <label for="date">Date :</label><br>
        <input id="date" name="date" type="date" required>
      </div>

      <div class="form-group">
        <label for="debut">Heure de début (entre 08:00 et 20:00) :</label><br>
        <input id="debut" name="debut" type="time" min="08:00" max="20:00" required>
      </div>

      <div class="form-group">
        <label for="fin">Heure de fin (entre 08:00 et 20:00) :</label><br>
        <input id="fin" name="fin" type="time" min="08:00" max="20:00" required>
      </div>

      <div class="form-group">
        <label for="participants">Nombre de participants :</label><br>
        <input id="participants" name="participants" type="number" min="1" required>
      </div>

      <button type="submit" class="btn-primary">Confirmer la réservation</button>
    </form>
  {% else %}
    <p><em>Veuillez ajouter une salle avant de pouvoir réserver.</em></p>
  {% endif %}
</body>
</html>
"""

# Template de modification d'une salle.
PAGE_MODIFIER_SALLE = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Modifier la salle {{ salle['nom'] }}</title>
  <style>
    body { font-family: sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
    h1 { color: #333; }
    .alert-error { background-color: #f8d7da; color: #721c24; padding: 12px; margin-bottom: 20px; border-radius: 4px; border: 1px solid #f5c6cb; }
    form { background: #fafafa; border: 1px solid #e0e0e0; padding: 20px; border-radius: 6px; }
    .form-group { margin-bottom: 15px; }
    label { display: block; margin-bottom: 5px; font-weight: bold; }
    input[type="text"], input[type="number"] { width: 100%; box-sizing: border-box; padding: 8px; font-size: 1rem; }
    button { background-color: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-size: 1rem; cursor: pointer; }
    button:hover { background-color: #0056b3; }
    a { color: #666; text-decoration: none; margin-left: 10px; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>Modifier la salle « {{ salle['nom'] }} »</h1>

  {% if erreur %}
    <div class="alert-error">
      <strong>Erreur :</strong> {{ erreur }}
    </div>
  {% endif %}

  <form method="post" action="/salles/{{ salle['id'] }}/modifier">
    <div class="form-group">
      <label for="nom">Nom de la salle :</label>
      <input type="text" id="nom" name="nom" value="{{ salle['nom'] }}" required>
    </div>

    <div class="form-group">
      <label for="capacite">Capacité maximale :</label>
      <input type="number" id="capacite" name="capacite" min="1" value="{{ salle['capacite'] }}" required>
    </div>

    <div class="form-group">
      <label style="font-weight: normal;">
        <input type="checkbox" name="projecteur" value="1" {% if salle['projecteur'] %}checked{% endif %}>
        Présence d'un projecteur
      </label>
    </div>

    <button type="submit">Enregistrer les modifications</button>
    <a href="/">Annuler</a>
  </form>
</body>
</html>
"""

# Template du planning hebdomadaire.
PAGE_PLANNING = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Planning hebdomadaire - {{ salle['nom'] }}</title>
  <style>
    body { font-family: sans-serif; max-width: 1000px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
    h1, h2 { color: #333; }
    .form-filtres { background: #f8f9fa; border: 1px solid #ddd; padding: 12px 15px; border-radius: 6px; margin-bottom: 1.5rem; display: flex; gap: 20px; align-items: center; flex-wrap: wrap; }
    .form-filtres label { font-weight: bold; }
    .form-filtres select, .form-filtres input { padding: 6px 10px; font-size: 1rem; }
    .nav-semaine { display: flex; justify-content: space-between; align-items: center; margin: 1.5rem 0; background: #e9ecef; padding: 10px 15px; border-radius: 6px; }
    .nav-semaine a { text-decoration: none; color: #007bff; font-weight: bold; }
    .nav-semaine a:hover { text-decoration: underline; }
    .grille-semaine { display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; margin-top: 1rem; }
    .jour-col { background: #fafafa; border: 1px solid #ddd; border-radius: 6px; padding: 8px; min-height: 250px; }
    .jour-header { font-weight: bold; text-align: center; border-bottom: 2px solid #007bff; padding-bottom: 6px; margin-bottom: 8px; font-size: 0.95rem; }
    .card-resa { background: #e7f1ff; border-left: 3px solid #007bff; padding: 6px 8px; margin-bottom: 8px; border-radius: 3px; font-size: 0.85rem; }
    .card-resa strong { display: block; color: #0056b3; }
    .card-resa .horaires { font-weight: bold; color: #333; }
    .empty { color: #888; font-size: 0.8rem; text-align: center; margin-top: 30px; }
    a.back-link { display: inline-block; margin-top: 2rem; color: #007bff; text-decoration: none; font-weight: bold; }
    a.back-link:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>Planning d'une salle sur une semaine</h1>

  <div class="form-filtres">
    <form method="get" action="/planning" style="display: flex; gap: 15px; align-items: center; width: 100%;">
      <div>
        <label for="salle_id">Salle :</label>
        <select id="salle_id" name="salle_id" onchange="this.form.submit()">
          {% for s in salles %}
            <option value="{{ s['id'] }}" {% if s['id'] == salle['id'] %}selected{% endif %}>
              {{ s['nom'] }} (Capacité : {{ s['capacite'] }})
            </option>
          {% endfor %}
        </select>
      </div>

      <div>
        <label for="date">Semaine contenant le :</label>
        <input type="date" id="date" name="date" value="{{ date_selectionnee }}" onchange="this.form.submit()">
      </div>

      <noscript><button type="submit">Afficher</button></noscript>
    </form>
  </div>

  <div class="nav-semaine">
    <a href="/planning?salle_id={{ salle['id'] }}&date={{ info_semaine['date_prec'] }}">← Semaine précédente</a>
    <strong>Semaine du {{ info_semaine['jours'][0]['label'] }} au {{ info_semaine['jours'][6]['label'] }}</strong>
    <a href="/planning?salle_id={{ salle['id'] }}&date={{ info_semaine['date_suiv'] }}">Semaine suivante →</a>
  </div>

  <h2>Salle « {{ salle['nom'] }} » — Capacité : {{ salle['capacite'] }} personne(s) {% if salle['projecteur'] %}(Projecteur inclus){% endif %}</h2>

  <div class="grille-semaine">
    {% for jour in info_semaine['jours'] %}
      <div class="jour-col">
        <div class="jour-header">{{ jour['label'] }}</div>
        {% set resas_jour = reservations_par_jour.get(jour['date'], []) %}
        {% if resas_jour %}
          {% for r in resas_jour %}
            <div class="card-resa">
              <div class="horaires">{{ r['debut'] }} - {{ r['fin'] }}</div>
              <strong>{{ r['personne'] }}</strong>
              <div>{{ r['participants'] }} participants</div>
            </div>
          {% endfor %}
        {% else %}
          <div class="empty">Libre</div>
        {% endif %}
      </div>
    {% endfor %}
  </div>

  <a href="/" class="back-link">← Retour à l'accueil</a>
</body>
</html>
"""

app = Flask(__name__)


def charger_donnees(conn):
    """Récupère les salles et les réservations pour l'affichage."""
    salles = conn.execute("SELECT id, nom, capacite, projecteur FROM salles ORDER BY nom").fetchall()
    reservations = conn.execute(
        """
        SELECT r.id, r.salle_id, s.nom AS salle_nom, r.personne, r.date, r.debut, r.fin, r.participants
        FROM reservations r
        JOIN salles s ON s.id = r.salle_id
        ORDER BY r.date, r.debut
        """
    ).fetchall()
    return salles, reservations


# Page d'accueil : lit les salles et réservations et affiche PAGE.
@app.get("/")
def accueil():
    with ouvrir_base() as conn:
        salles, reservations = charger_donnees(conn)
    return render_template_string(PAGE, salles=salles, reservations=reservations)


# Affiche le planning hebdomadaire d'une salle (du lundi au dimanche).
@app.get("/planning")
def planning():
    with ouvrir_base() as conn:
        salles = conn.execute("SELECT id, nom, capacite, projecteur FROM salles ORDER BY nom").fetchall()
        if not salles:
            return redirect("/")

        salle_id_arg = request.args.get("salle_id")
        salle = None
        if salle_id_arg:
            try:
                salle = conn.execute(
                    "SELECT id, nom, capacite, projecteur FROM salles WHERE id = ?",
                    [int(salle_id_arg)],
                ).fetchone()
            except ValueError:
                salle = None
        if not salle:
            salle = salles[0]

        date_arg = request.args.get("date")
        info_semaine = calculer_semaine(date_arg)

        # Récupération des réservations de la salle sur la semaine du lundi au dimanche
        reservations = conn.execute(
            """
            SELECT id, personne, date, debut, fin, participants
            FROM reservations
            WHERE salle_id = ? AND date >= ? AND date <= ?
            ORDER BY debut
            """,
            [salle["id"], info_semaine["lundi"], info_semaine["dimanche"]],
        ).fetchall()

        reservations_par_jour = {}
        for r in reservations:
            reservations_par_jour.setdefault(r["date"], []).append(r)

    return render_template_string(
        PAGE_PLANNING,
        salles=salles,
        salle=salle,
        info_semaine=info_semaine,
        reservations_par_jour=reservations_par_jour,
        date_selectionnee=date_arg or info_semaine["lundi"],
    )


# Reçoit le formulaire et ajoute une salle.
@app.post("/salles")
def ajouter_salle():
    nom = request.form.get("nom", "").strip()
    try:
        capacite = int(request.form.get("capacite", 0))
        valider_salle(nom, capacite)
    except (ValueError, RegleReservationException) as e:
        with ouvrir_base() as conn:
            salles, reservations = charger_donnees(conn)
        return render_template_string(PAGE, salles=salles, reservations=reservations, erreur=str(e)), 400

    projecteur = 1 if "projecteur" in request.form else 0
    with ouvrir_base() as conn:
        conn.execute("INSERT INTO salles (nom, capacite, projecteur) VALUES (?, ?, ?)", [nom, capacite, projecteur])
    return redirect("/?succes=Salle+ajoutée")


# Affiche le formulaire de modification d'une salle.
@app.get("/salles/<int:salle_id>/modifier")
def formulaire_modifier_salle(salle_id):
    with ouvrir_base() as conn:
        salle = conn.execute("SELECT id, nom, capacite, projecteur FROM salles WHERE id = ?", [salle_id]).fetchone()
    if not salle:
        abort(404)
    return render_template_string(PAGE_MODIFIER_SALLE, salle=salle)


# Traite la modification d'une salle.
@app.post("/salles/<int:salle_id>/modifier")
def modifier_salle(salle_id):
    nom = request.form.get("nom", "").strip()
    projecteur = 1 if "projecteur" in request.form else 0

    with ouvrir_base() as conn:
        salle = conn.execute("SELECT id, nom, capacite, projecteur FROM salles WHERE id = ?", [salle_id]).fetchone()
        if not salle:
            abort(404)

        try:
            capacite = int(request.form.get("capacite", 0))
            valider_salle(nom, capacite)

            max_p = conn.execute(
                "SELECT COALESCE(MAX(participants), 0) AS max_p FROM reservations WHERE salle_id = ?",
                [salle_id],
            ).fetchone()["max_p"]
            valider_modification_capacite(capacite, max_p)

        except (ValueError, RegleReservationException) as e:
            return render_template_string(PAGE_MODIFIER_SALLE, salle=salle, erreur=str(e)), 400

        conn.execute(
            "UPDATE salles SET nom = ?, capacite = ?, projecteur = ? WHERE id = ?",
            [nom, capacite, projecteur, salle_id],
        )

    return redirect("/?succes=Salle+modifiée+avec+succès")


# Supprime une salle et ses réservations (en cascade).
@app.post("/salles/<int:salle_id>/supprimer")
def supprimer_salle(salle_id):
    with ouvrir_base() as conn:
        conn.execute("DELETE FROM salles WHERE id = ?", [salle_id])
    return redirect("/?succes=Salle+supprimée+avec+succès")


# Annule une réservation.
@app.post("/reservations/<int:reservation_id>/annuler")
def annuler_reservation(reservation_id):
    with ouvrir_base() as conn:
        conn.execute("DELETE FROM reservations WHERE id = ?", [reservation_id])
    return redirect("/?succes=Réservation+annulée+avec+succès")


# Reçoit le formulaire et réserve une salle en validant les règles métier.
@app.post("/reservations")
def reserver():
    salle_id = int(request.form["salle_id"])
    personne = request.form["personne"]
    date = request.form["date"]
    debut = request.form["debut"]
    fin = request.form["fin"]
    participants = int(request.form["participants"])

    with ouvrir_base() as conn:
        salle = conn.execute("SELECT id, nom, capacite FROM salles WHERE id = ?", [salle_id]).fetchone()
        if not salle:
            salles, reservations = charger_donnees(conn)
            return render_template_string(PAGE, salles=salles, reservations=reservations, erreur="Salle introuvable."), 400

        reservations_existantes = conn.execute(
            "SELECT debut, fin FROM reservations WHERE salle_id = ? AND date = ?",
            [salle_id, date],
        ).fetchall()

        try:
            valider_reservation(
                personne=personne,
                capacite_salle=salle["capacite"],
                debut=debut,
                fin=fin,
                participants=participants,
                reservations_existantes=reservations_existantes,
            )
        except RegleReservationException as e:
            salles, reservations = charger_donnees(conn)
            return render_template_string(PAGE, salles=salles, reservations=reservations, erreur=str(e)), 400

        conn.execute(
            """
            INSERT INTO reservations (salle_id, personne, date, debut, fin, participants)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [salle_id, personne, date, debut, fin, participants],
        )

    return redirect("/?succes=Réservation+enregistrée+avec+succès")


if __name__ == "__main__":
    app.run(debug=True)
