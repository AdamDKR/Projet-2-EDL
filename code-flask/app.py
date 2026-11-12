import uuid
from urllib.parse import quote_plus

from flask import Flask, abort, redirect, render_template_string, request

from base import ouvrir_base
from regles import (
    TYPES_LOCAUX,
    RegleReservationException,
    calculer_semaine,
    generer_dates_hebdomadaires,
    valider_modification_capacite,
    valider_non_chevauchement,
    valider_non_chevauchement_personne,
    valider_reservation,
    valider_salle,
)

# Styles CSS partagés entre toutes les pages.
BASE_STYLES = """
  :root {
    --bg: #f1f5f9;
    --surface: #ffffff;
    --surface-muted: #f8fafc;
    --border: #e2e8f0;
    --text: #0f172a;
    --text-muted: #64748b;
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --danger: #dc2626;
    --danger-hover: #b91c1c;
    --success-bg: #f0fdf4;
    --success-border: #86efac;
    --success-text: #166534;
    --error-bg: #fef2f2;
    --error-border: #fca5a5;
    --error-text: #991b1b;
    --radius: 10px;
    --shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04);
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background-color: #eef2f7;
    color: var(--text);
    margin: 0;
    padding: 0 1rem 3rem;
    line-height: 1.5;
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
  }
  body::before,
  body::after {
    content: "";
    position: fixed;
    inset: -64px;
    pointer-events: none;
  }
  body::before {
    z-index: -2;
    background:
      radial-gradient(circle at 20% 20%, rgba(37, 99, 235, 0.22) 0%, transparent 45%),
      radial-gradient(circle at 80% 25%, rgba(14, 165, 233, 0.20) 0%, transparent 42%),
      radial-gradient(circle at 50% 80%, rgba(99, 102, 241, 0.18) 0%, transparent 48%);
    animation: floatAura 18s ease-in-out infinite alternate;
  }
  body::after {
    z-index: -1;
    background-image:
      linear-gradient(rgba(148, 163, 184, 0.14) 1px, transparent 1px),
      linear-gradient(90deg, rgba(148, 163, 184, 0.14) 1px, transparent 1px);
    background-size: 32px 32px;
    animation: driftGrid 24s linear infinite;
  }
  @keyframes floatAura {
    0% { transform: translate3d(0, 0, 0) scale(1); }
    50% { transform: translate3d(2%, -2%, 0) scale(1.06); }
    100% { transform: translate3d(-2%, 2%, 0) scale(1.03); }
  }
  @keyframes driftGrid {
    0% { transform: translate3d(0, 0, 0); }
    100% { transform: translate3d(32px, 32px, 0); }
  }
  @media (prefers-reduced-motion: reduce) {
    body::before,
    body::after {
      animation: none;
    }
  }
  .container { max-width: 1120px; margin: 1.5rem auto; }
  .container-narrow { max-width: 620px; margin: 2rem auto; }
  h1 { font-size: 1.75rem; margin: 0 0 1.25rem; color: var(--text); }
  h2 { font-size: 1.2rem; margin: 0 0 1rem; color: var(--text); }
  h3 { font-size: 1.05rem; margin: 1.25rem 0 0.75rem; color: var(--text); }
  .nav-top {
    background: rgba(255, 255, 255, 0.92);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    border-radius: var(--radius);
    padding: 0.85rem 1.25rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
  }
  .nav-brand { font-weight: 700; font-size: 1.05rem; color: var(--text); }
  .nav-link {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--primary);
    text-decoration: none;
    font-weight: 600;
    padding: 0.4rem 0.75rem;
    border-radius: 6px;
    background: #eff6ff;
  }
  .nav-link:hover { background: #dbeafe; }
  .card {
    background: rgba(255, 255, 255, 0.94);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
  }
  .grid-2 {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 1.5rem;
    align-items: start;
  }
  @media (max-width: 860px) {
    .grid-2 { grid-template-columns: 1fr; }
  }
  .alert-error, .alert-success {
    padding: 0.85rem 1rem;
    margin-bottom: 1.25rem;
    border-radius: 8px;
    border: 1px solid;
    border-left-width: 4px;
  }
  .alert-error { background: var(--error-bg); color: var(--error-text); border-color: var(--error-border); border-left-color: var(--danger); }
  .alert-success { background: var(--success-bg); color: var(--success-text); border-color: var(--success-border); border-left-color: #16a34a; }
  .form-group { margin-bottom: 0.9rem; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
  @media (max-width: 520px) { .form-row { grid-template-columns: 1fr; } }
  label { display: block; margin-bottom: 0.35rem; font-weight: 600; font-size: 0.9rem; color: var(--text); }
  input[type="text"], input[type="number"], input[type="date"], input[type="time"], input:not([type]), select {
    width: 100%;
    padding: 0.55rem 0.75rem;
    font-size: 0.95rem;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background: var(--surface);
    color: var(--text);
  }
  input:focus, select:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
  }
  .btn-primary {
    background: var(--primary);
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 0.6rem 1rem;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
  }
  .btn-primary:hover { background: var(--primary-hover); }
  .btn-secondary {
    display: inline-block;
    background: var(--surface-muted);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.55rem 0.95rem;
    font-size: 0.95rem;
    font-weight: 500;
    text-decoration: none;
  }
  .btn-secondary:hover { background: #e2e8f0; }
  .btn-delete {
    background: transparent;
    border: 1px solid #fecaca;
    color: var(--danger);
    cursor: pointer;
    padding: 0.28rem 0.6rem;
    border-radius: 5px;
    font-size: 0.85rem;
    font-weight: 600;
  }
  .btn-delete:hover { background: #fee2e2; color: var(--danger-hover); }
  .badge {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
  }
  .badge-blue { background: #dbeafe; color: #1e40af; }
  .badge-gray { background: #e2e8f0; color: #334155; }
  .badge-amber { background: #fef3c7; color: #92400e; }
  .filter-bar {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    background: var(--surface-muted);
    border: 1px solid var(--border);
    padding: 0.65rem 0.85rem;
    border-radius: 8px;
    margin-bottom: 1rem;
  }
  .filter-bar label { margin: 0; white-space: nowrap; }
  .filter-bar select { width: auto; min-width: 180px; }
  .room-list { list-style: none; padding: 0; margin: 0 0 1.25rem; display: flex; flex-direction: column; gap: 0.65rem; }
  .room-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.75rem 0.9rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-muted);
  }
  .room-meta { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .actions { display: flex; align-items: center; gap: 0.5rem; }
  .actions a { color: var(--primary); text-decoration: none; font-size: 0.88rem; font-weight: 600; }
  .actions a:hover { text-decoration: underline; }
  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { border-bottom: 1px solid var(--border); padding: 0.7rem 0.75rem; text-align: left; font-size: 0.92rem; }
  th { background: var(--surface-muted); color: var(--text-muted); font-weight: 700; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.03em; }
  tbody tr:hover { background: var(--surface-muted); }
  .muted { color: var(--text-muted); font-size: 0.9rem; }
"""

# Template de la page d'accueil.
PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Réservation de salles</title>
  <style>""" + BASE_STYLES + """</style>
</head>
<body>
  <div class="container">
    <div class="nav-top">
      <span class="nav-brand">🏛️ Système universitaire — Gestion des salles</span>
      <a class="nav-link" href="/planning">📅 Consulter le planning hebdomadaire</a>
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

    <div class="grid-2">
      <div class="card">
        <h2>Salles</h2>
        <form class="filter-bar" method="get" action="/">
          <label for="filtre_type_local">Type :</label>
          <select id="filtre_type_local" name="type_local" onchange="this.form.submit()">
            <option value="">Tous les types</option>
            {% for t in types_locaux %}
              <option value="{{ t }}" {% if type_filtre == t %}selected{% endif %}>{{ t }}</option>
            {% endfor %}
          </select>
          <button type="submit" class="btn-primary">Filtrer</button>
          {% if type_filtre %}
            <a class="btn-secondary" href="/">Réinitialiser</a>
          {% endif %}
        </form>

        {% if salles %}
          <ul class="room-list">
            {% for salle in salles %}
              <li class="room-item">
                <div class="room-meta">
                  <strong>{{ salle["nom"] }}</strong>
                  <span class="badge badge-blue">{{ salle["type_local"] }}</span>
                  <span class="muted">{{ salle["capacite"] }} pers.</span>
                  {% if salle["projecteur"] %}<span class="badge badge-gray">📽️ Projecteur</span>{% endif %}
                </div>
                <div class="actions">
                  <a href="/planning?salle_id={{ salle['id'] }}">Planning</a>
                  <a href="/salles/{{ salle['id'] }}/modifier">Modifier</a>
                  <form method="post" action="/salles/{{ salle['id'] }}/supprimer" style="display: inline;" onsubmit="return confirm('Supprimer cette salle supprimera également toutes ses réservations. Confirmer ?');">
                    <button type="submit" class="btn-delete">Supprimer</button>
                  </form>
                </div>
              </li>
            {% endfor %}
          </ul>
        {% else %}
          <p class="muted">Aucune salle enregistrée.</p>
        {% endif %}

        <h3>Ajouter une salle</h3>
        <form method="post" action="/salles" style="background: var(--surface-muted); border: 1px solid var(--border); padding: 1rem; border-radius: 8px;">
          <div class="form-row">
            <div class="form-group">
              <label for="nom_salle">Nom</label>
              <input id="nom_salle" name="nom" placeholder="ex: B204" required>
            </div>
            <div class="form-group">
              <label for="capacite_salle">Capacité</label>
              <input id="capacite_salle" name="capacite" type="number" min="1" placeholder="ex: 25" required>
            </div>
          </div>
          <div class="form-row" style="align-items: end;">
            <div class="form-group" style="margin-bottom: 0;">
              <label for="type_local_ajout">Type de local</label>
              <select id="type_local_ajout" name="type_local" required>
                {% for t in types_locaux %}
                  <option value="{{ t }}">{{ t }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="form-group" style="margin-bottom: 0; display: flex; align-items: center; justify-content: space-between; gap: 0.75rem;">
              <label style="font-weight: 500; margin: 0; display: flex; align-items: center; gap: 0.4rem;">
                <input name="projecteur" type="checkbox" value="1"> Projecteur
              </label>
              <button type="submit" class="btn-primary">Ajouter</button>
            </div>
          </div>
        </form>
      </div>

      <div class="card">
        <h2>Réserver une salle</h2>
        {% if toutes_salles %}
          <form method="post" action="/reservations">
            <div class="form-group">
              <label for="salle_id">Salle</label>
              <select id="salle_id" name="salle_id" required>
                {% for salle in toutes_salles %}
                  <option value="{{ salle['id'] }}">{{ salle['nom'] }} — {{ salle['type_local'] }} (max {{ salle['capacite'] }} pers.)</option>
                {% endfor %}
              </select>
            </div>

            <div class="form-group">
              <label for="personne">Nom de la personne</label>
              <input id="personne" name="personne" placeholder="ex: Alice" required>
            </div>

            <div class="form-group">
              <label for="date">Date</label>
              <input id="date" name="date" type="date" required>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="debut">Début (08:00–20:00)</label>
                <input id="debut" name="debut" type="time" min="08:00" max="20:00" required>
              </div>
              <div class="form-group">
                <label for="fin">Fin (08:00–20:00)</label>
                <input id="fin" name="fin" type="time" min="08:00" max="20:00" required>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="participants">Participants</label>
                <input id="participants" name="participants" type="number" min="1" required>
              </div>
              <div class="form-group">
                <label for="nb_semaines">Répétition (semaines)</label>
                <input id="nb_semaines" name="nb_semaines" type="number" min="1" max="52" value="1" required>
              </div>
            </div>

            <button type="submit" class="btn-primary" style="width: 100%; margin-top: 0.25rem;">Confirmer la réservation</button>
          </form>
        {% else %}
          <p class="muted"><em>Veuillez ajouter une salle avant de pouvoir réserver.</em></p>
        {% endif %}
      </div>
    </div>

    <div class="card">
      <h2>Réservations existantes</h2>
      {% if reservations %}
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Salle</th>
                <th>Type de local</th>
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
                  <td><strong>{{ r["salle_nom"] }}</strong></td>
                  <td><span class="badge badge-blue">{{ r["type_local"] }}</span></td>
                  <td>{{ r["personne"] }}</td>
                  <td>{{ r["date"] }}</td>
                  <td>
                    {{ r["debut"] }} - {{ r["fin"] }}
                    {% if r["serie_id"] %}<span class="badge badge-amber">Hebdo</span>{% endif %}
                  </td>
                  <td>{{ r["participants"] }}</td>
                  <td>
                    <div class="actions">
                      <form method="post" action="/reservations/{{ r['id'] }}/annuler" style="display:inline;" onsubmit="return confirm('Confirmer l\'annulation de cette réservation ?');">
                        <button type="submit" class="btn-delete">Annuler</button>
                      </form>
                      {% if r["serie_id"] %}
                        <form method="post" action="/reservations/serie/{{ r['serie_id'] }}/annuler" style="display:inline;" onsubmit="return confirm('Confirmer l\'annulation de toute la série ?');">
                          <button type="submit" class="btn-delete">Annuler la série</button>
                        </form>
                      {% endif %}
                    </div>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      {% else %}
        <p class="muted">Aucune réservation enregistrée.</p>
      {% endif %}
    </div>
  </div>
</body>
</html>
"""

# Template de modification d'une salle.
PAGE_MODIFIER_SALLE = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Modifier la salle {{ salle['nom'] }}</title>
  <style>""" + BASE_STYLES + """</style>
</head>
<body>
  <div class="container-narrow">
    <div class="nav-top">
      <span class="nav-brand">🏛️ Gestion des salles</span>
      <a class="nav-link" href="/">← Retour à l'accueil</a>
    </div>

    <div class="card">
      <h1>Modifier la salle « {{ salle['nom'] }} »</h1>

      {% if erreur %}
        <div class="alert-error">
          <strong>Erreur :</strong> {{ erreur }}
        </div>
      {% endif %}

      <form method="post" action="/salles/{{ salle['id'] }}/modifier">
        <div class="form-group">
          <label for="nom">Nom de la salle</label>
          <input type="text" id="nom" name="nom" value="{{ salle['nom'] }}" required>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="capacite">Capacité maximale</label>
            <input type="number" id="capacite" name="capacite" min="1" value="{{ salle['capacite'] }}" required>
          </div>
          <div class="form-group">
            <label for="type_local">Type de local</label>
            <select id="type_local" name="type_local" required>
              {% for t in types_locaux %}
                <option value="{{ t }}" {% if salle['type_local'] == t %}selected{% endif %}>{{ t }}</option>
              {% endfor %}
            </select>
          </div>
        </div>

        <div class="form-group">
          <label style="font-weight: 500; display: flex; align-items: center; gap: 0.45rem;">
            <input type="checkbox" name="projecteur" value="1" {% if salle['projecteur'] %}checked{% endif %}>
            Présence d'un projecteur
          </label>
        </div>

        <div style="display: flex; gap: 0.75rem; align-items: center; margin-top: 1.25rem;">
          <button type="submit" class="btn-primary">Enregistrer les modifications</button>
          <a class="btn-secondary" href="/">Annuler</a>
        </div>
      </form>
    </div>
  </div>
</body>
</html>
"""

# Template du planning hebdomadaire.
PAGE_PLANNING = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Planning hebdomadaire - {{ salle['nom'] }}</title>
  <style>""" + BASE_STYLES + """
    .form-filtres { display: flex; gap: 1.25rem; align-items: end; flex-wrap: wrap; }
    .form-filtres .form-group { margin-bottom: 0; min-width: 220px; }
    .nav-semaine { display: flex; justify-content: space-between; align-items: center; margin: 1.25rem 0; background: var(--surface); border: 1px solid var(--border); box-shadow: var(--shadow); padding: 0.85rem 1.25rem; border-radius: var(--radius); flex-wrap: wrap; gap: 0.75rem; }
    .nav-semaine a { text-decoration: none; color: var(--primary); font-weight: 600; padding: 0.35rem 0.65rem; border-radius: 6px; background: #eff6ff; }
    .nav-semaine a:hover { background: #dbeafe; }
    .grille-semaine { display: grid; grid-template-columns: repeat(7, 1fr); gap: 0.75rem; margin-top: 1rem; }
    @media (max-width: 960px) { .grille-semaine { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 540px) { .grille-semaine { grid-template-columns: 1fr; } }
    .jour-col { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); padding: 0.75rem; min-height: 240px; }
    .jour-header { font-weight: 700; text-align: center; border-bottom: 2px solid var(--primary); padding-bottom: 0.5rem; margin-bottom: 0.65rem; font-size: 0.92rem; color: var(--text); }
    .card-resa { background: #eff6ff; border-left: 3px solid var(--primary); padding: 0.5rem 0.65rem; margin-bottom: 0.55rem; border-radius: 6px; font-size: 0.84rem; }
    .card-resa strong { display: block; color: #1e40af; }
    .card-resa .horaires { font-weight: 700; color: var(--text); }
    .empty { color: var(--text-muted); font-size: 0.82rem; text-align: center; margin-top: 2rem; }
  </style>
</head>
<body>
  <div class="container">
    <div class="nav-top">
      <span class="nav-brand">📅 Planning hebdomadaire</span>
      <a class="nav-link" href="/">← Retour à l'accueil</a>
    </div>

    <h1>Planning d'une salle sur une semaine</h1>

    <div class="card">
      <form class="form-filtres" method="get" action="/planning">
        <div class="form-group">
          <label for="salle_id">Salle</label>
          <select id="salle_id" name="salle_id" onchange="this.form.submit()">
            {% for s in salles %}
              <option value="{{ s['id'] }}" {% if s['id'] == salle['id'] %}selected{% endif %}>
                {{ s['nom'] }} — {{ s['type_local'] }} (Capacité : {{ s['capacite'] }})
              </option>
            {% endfor %}
          </select>
        </div>

        <div class="form-group">
          <label for="date">Semaine contenant le</label>
          <input type="date" id="date" name="date" value="{{ date_selectionnee }}" onchange="this.form.submit()">
        </div>

        <noscript><button type="submit" class="btn-primary">Afficher</button></noscript>
      </form>
    </div>

    <div class="nav-semaine">
      <a href="/planning?salle_id={{ salle['id'] }}&date={{ info_semaine['date_prec'] }}">← Semaine précédente</a>
      <strong>Semaine du {{ info_semaine['jours'][0]['label'] }} au {{ info_semaine['jours'][6]['label'] }}</strong>
      <a href="/planning?salle_id={{ salle['id'] }}&date={{ info_semaine['date_suiv'] }}">Semaine suivante →</a>
    </div>

    <h2>
      Salle « {{ salle['nom'] }} »
      <span class="badge badge-blue">{{ salle['type_local'] }}</span>
      <span class="muted">— Capacité : {{ salle['capacite'] }} personne(s)</span>
      {% if salle['projecteur'] %}<span class="badge badge-gray">📽️ Projecteur inclus</span>{% endif %}
    </h2>

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
                <div class="muted">{{ r['participants'] }} participants</div>
              </div>
            {% endfor %}
          {% else %}
            <div class="empty">Libre</div>
          {% endif %}
        </div>
      {% endfor %}
    </div>
  </div>
</body>
</html>
"""

app = Flask(__name__)


def charger_donnees(conn, type_filtre=None):
    """Récupère les salles (filtrées ou non) et les réservations pour l'affichage."""
    toutes_salles = conn.execute(
        "SELECT id, nom, capacite, projecteur, type_local FROM salles ORDER BY nom"
    ).fetchall()

    if type_filtre:
        salles = [s for s in toutes_salles if s["type_local"] == type_filtre]
        reservations = conn.execute(
            """
            SELECT r.id, r.salle_id, s.nom AS salle_nom, s.type_local, r.personne, r.date, r.debut, r.fin, r.participants, r.serie_id
            FROM reservations r
            JOIN salles s ON s.id = r.salle_id
            WHERE s.type_local = ?
            ORDER BY r.date, r.debut
            """,
            [type_filtre],
        ).fetchall()
    else:
        salles = toutes_salles
        reservations = conn.execute(
            """
            SELECT r.id, r.salle_id, s.nom AS salle_nom, s.type_local, r.personne, r.date, r.debut, r.fin, r.participants, r.serie_id
            FROM reservations r
            JOIN salles s ON s.id = r.salle_id
            ORDER BY r.date, r.debut
            """
        ).fetchall()
    return salles, reservations, toutes_salles


def _render_accueil(conn, erreur=None, status=200, type_filtre=None):
    """Prépare les données et rend la page d'accueil."""
    salles, reservations, toutes_salles = charger_donnees(conn, type_filtre=type_filtre)
    return (
        render_template_string(
            PAGE,
            salles=salles,
            reservations=reservations,
            toutes_salles=toutes_salles,
            types_locaux=TYPES_LOCAUX,
            type_filtre=type_filtre,
            erreur=erreur,
        ),
        status,
    )


# Page d'accueil : lit les salles et réservations et affiche PAGE.
@app.get("/")
def accueil():
    type_filtre = request.args.get("type_local", "").strip() or None
    with ouvrir_base() as conn:
        return _render_accueil(conn, type_filtre=type_filtre)


# Affiche le planning hebdomadaire d'une salle (du lundi au dimanche).
@app.get("/planning")
def planning():
    with ouvrir_base() as conn:
        salles = conn.execute("SELECT id, nom, capacite, projecteur, type_local FROM salles ORDER BY nom").fetchall()
        if not salles:
            return redirect("/")

        salle_id_arg = request.args.get("salle_id")
        salle = None
        if salle_id_arg:
            try:
                salle = conn.execute(
                    "SELECT id, nom, capacite, projecteur, type_local FROM salles WHERE id = ?",
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
    type_local = request.form.get("type_local", "Salle de cours").strip()
    try:
        capacite = int(request.form.get("capacite", 0))
        valider_salle(nom, capacite, type_local)
    except (ValueError, RegleReservationException) as e:
        with ouvrir_base() as conn:
            return _render_accueil(conn, erreur=str(e), status=400)

    projecteur = 1 if "projecteur" in request.form else 0
    with ouvrir_base() as conn:
        conn.execute(
            "INSERT INTO salles (nom, capacite, projecteur, type_local) VALUES (?, ?, ?, ?)",
            [nom, capacite, projecteur, type_local],
        )
    return redirect("/?succes=Salle+ajoutée")


# Affiche le formulaire de modification d'une salle.
@app.get("/salles/<int:salle_id>/modifier")
def formulaire_modifier_salle(salle_id):
    with ouvrir_base() as conn:
        salle = conn.execute(
            "SELECT id, nom, capacite, projecteur, type_local FROM salles WHERE id = ?",
            [salle_id],
        ).fetchone()
    if not salle:
        abort(404)
    return render_template_string(PAGE_MODIFIER_SALLE, salle=salle, types_locaux=TYPES_LOCAUX)


# Traite la modification d'une salle.
@app.post("/salles/<int:salle_id>/modifier")
def modifier_salle(salle_id):
    nom = request.form.get("nom", "").strip()
    type_local = request.form.get("type_local", "Salle de cours").strip()
    projecteur = 1 if "projecteur" in request.form else 0

    with ouvrir_base() as conn:
        salle = conn.execute(
            "SELECT id, nom, capacite, projecteur, type_local FROM salles WHERE id = ?",
            [salle_id],
        ).fetchone()
        if not salle:
            abort(404)

        try:
            capacite = int(request.form.get("capacite", 0))
            valider_salle(nom, capacite, type_local)

            max_p = conn.execute(
                "SELECT COALESCE(MAX(participants), 0) AS max_p FROM reservations WHERE salle_id = ?",
                [salle_id],
            ).fetchone()["max_p"]
            valider_modification_capacite(capacite, max_p)

        except (ValueError, RegleReservationException) as e:
            return (
                render_template_string(
                    PAGE_MODIFIER_SALLE, salle=salle, types_locaux=TYPES_LOCAUX, erreur=str(e)
                ),
                400,
            )

        conn.execute(
            "UPDATE salles SET nom = ?, capacite = ?, projecteur = ?, type_local = ? WHERE id = ?",
            [nom, capacite, projecteur, type_local, salle_id],
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


# Annule toute une série de réservations répétées.
@app.post("/reservations/serie/<serie_id>/annuler")
def annuler_serie_reservations(serie_id):
    with ouvrir_base() as conn:
        conn.execute("DELETE FROM reservations WHERE serie_id = ?", [serie_id])
    return redirect("/?succes=" + quote_plus("Série de réservations annulée avec succès"))


# Reçoit le formulaire et réserve une salle (ponctuelle ou répétée chaque semaine).
@app.post("/reservations")
def reserver():
    salle_id = int(request.form["salle_id"])
    personne = request.form["personne"].strip()
    date = request.form["date"]
    debut = request.form["debut"]
    fin = request.form["fin"]
    participants = int(request.form["participants"])

    with ouvrir_base() as conn:
        salle = conn.execute("SELECT id, nom, capacite FROM salles WHERE id = ?", [salle_id]).fetchone()
        if not salle:
            return _render_accueil(conn, erreur="Salle introuvable.", status=400)

        try:
            nb_semaines = int(request.form.get("nb_semaines", 1))
            dates = generer_dates_hebdomadaires(date, nb_semaines)
            valider_reservation(
                personne=personne,
                capacite_salle=salle["capacite"],
                debut=debut,
                fin=fin,
                participants=participants,
                reservations_existantes=[],
                reservations_personne=[],
            )
        except (ValueError, RegleReservationException) as e:
            return _render_accueil(conn, erreur=str(e), status=400)

        serie_id = uuid.uuid4().hex if nb_semaines > 1 else None
        dates_creees = []
        dates_ignorees = []
        derniere_erreur_conflit = None

        for d in dates:
            reservations_existantes = conn.execute(
                "SELECT debut, fin FROM reservations WHERE salle_id = ? AND date = ?",
                [salle_id, d],
            ).fetchall()

            reservations_personne = conn.execute(
                "SELECT debut, fin FROM reservations WHERE LOWER(TRIM(personne)) = LOWER(?) AND date = ?",
                [personne, d],
            ).fetchall()

            try:
                valider_non_chevauchement(debut, fin, reservations_existantes)
                valider_non_chevauchement_personne(personne, debut, fin, reservations_personne)
            except RegleReservationException as e:
                dates_ignorees.append(d)
                derniere_erreur_conflit = str(e)
                continue

            conn.execute(
                """
                INSERT INTO reservations (salle_id, personne, date, debut, fin, participants, serie_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [salle_id, personne, d, debut, fin, participants, serie_id],
            )
            dates_creees.append(d)

        if not dates_creees:
            message = (
                derniere_erreur_conflit
                if nb_semaines == 1
                else "Aucune réservation créée : toutes les dates demandées sont en conflit (chevauchement)."
            )
            return _render_accueil(conn, erreur=message, status=400)

    if nb_semaines == 1:
        msg_succes = "Réservation enregistrée avec succès"
    elif dates_ignorees:
        msg_succes = (
            f"{len(dates_creees)} réservation(s) hebdomadaire(s) enregistrée(s) "
            f"({len(dates_ignorees)} date(s) ignorée(s) pour conflit : {', '.join(dates_ignorees)})"
        )
    else:
        msg_succes = f"{len(dates_creees)} réservations hebdomadaires enregistrées avec succès"

    return redirect("/?succes=" + quote_plus(msg_succes))


if __name__ == "__main__":
    app.run(debug=True)
