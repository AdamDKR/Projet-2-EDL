from flask import Flask, redirect, render_template_string, request

from base import ouvrir_base
from regles import RegleReservationException, valider_reservation

# Le HTML de la page.
PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Réservation de salles</title>
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
    h1, h2, h3 { color: #333; }
    .alert-error { background-color: #f8d7da; color: #721c24; padding: 12px; margin-bottom: 20px; border-radius: 4px; border: 1px solid #f5c6cb; }
    .alert-success { background-color: #d4edda; color: #155724; padding: 12px; margin-bottom: 20px; border-radius: 4px; border: 1px solid #c3e6cb; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background-color: #f4f4f4; }
    form { background: #fafafa; border: 1px solid #e0e0e0; padding: 15px; border-radius: 6px; margin-bottom: 2rem; }
    .form-group { margin-bottom: 10px; }
    label { display: inline-block; margin-bottom: 4px; font-weight: bold; }
    input, select, button { padding: 6px 10px; font-size: 1rem; }
    button { background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
    button:hover { background-color: #0056b3; }
  </style>
</head>
<body>
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
  <ul>
    {% for salle in salles %}
      <li>
        <strong>{{ salle["nom"] }}</strong> — Capacité : {{ salle["capacite"] }} personne(s)
        {% if salle["projecteur"] %}(avec projecteur){% endif %}
      </li>
    {% endfor %}
  </ul>

  <h3>Ajouter une salle</h3>
  <form method="post" action="/salles">
    <div class="form-group">
      <input name="nom" placeholder="Nom de la salle" required>
      <input name="capacite" type="number" min="1" placeholder="Capacité" required>
      <label style="font-weight: normal; margin-left: 10px;">
        <input name="projecteur" type="checkbox" value="1"> Projecteur
      </label>
      <button type="submit">Ajouter</button>
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
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>Aucune réservation enregistrée.</p>
  {% endif %}

  <h3>Réserver une salle</h3>
  <form method="post" action="/reservations">
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

    <button type="submit">Confirmer la réservation</button>
  </form>
</body>
</html>
"""

app = Flask(__name__)


def charger_donnees(conn):
    """Récupère les salles et les réservations pour l'affichage."""
    salles = conn.execute("SELECT id, nom, capacite, projecteur FROM salles").fetchall()
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


# Reçoit le formulaire et ajoute une salle.
@app.post("/salles")
def ajouter_salle():
    nom = request.form["nom"]
    capacite = int(request.form["capacite"])
    projecteur = 1 if "projecteur" in request.form else 0
    with ouvrir_base() as conn:
        conn.execute("INSERT INTO salles (nom, capacite, projecteur) VALUES (?, ?, ?)", [nom, capacite, projecteur])
    return redirect("/?succes=Salle+ajoutée")


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
        # Récupération de la salle pour vérifier la capacité
        salle = conn.execute("SELECT id, nom, capacite FROM salles WHERE id = ?", [salle_id]).fetchone()
        if not salle:
            salles, reservations = charger_donnees(conn)
            return render_template_string(PAGE, salles=salles, reservations=reservations, erreur="Salle introuvable."), 400

        # Récupération des réservations existantes de cette salle à cette date
        reservations_existantes = conn.execute(
            "SELECT debut, fin FROM reservations WHERE salle_id = ? AND date = ?",
            [salle_id, date],
        ).fetchall()

        # Validation des règles métier
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

        # Insertion de la réservation validée
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
