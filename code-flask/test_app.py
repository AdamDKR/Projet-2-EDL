import pytest
from app import app
from base import ouvrir_base


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    with app.test_client() as client:
        yield client


# ====================================================
# TESTS SALLES & CASCADE (ÉTAPE 2)
# ====================================================

def test_accueil(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "S1" in html
    assert "S2" in html


def test_ajouter_salle_succes(client):
    res = client.post(
        "/salles",
        data={"nom": "S3", "capacite": "15", "projecteur": "1"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    with ouvrir_base() as conn:
        salle = conn.execute("SELECT * FROM salles WHERE nom = 'S3'").fetchone()
        assert salle is not None
        assert salle["capacite"] == 15
        assert salle["projecteur"] == 1


def test_ajouter_salle_invalide(client):
    # Capacité <= 0
    res = client.post(
        "/salles",
        data={"nom": "S_invalide", "capacite": "0"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "Capacité invalide" in res.data.decode("utf-8") or "erreur" in res.data.decode("utf-8").lower()
    with ouvrir_base() as conn:
        salle = conn.execute("SELECT * FROM salles WHERE nom = 'S_invalide'").fetchone()
        assert salle is None

    # Nom vide
    res = client.post(
        "/salles",
        data={"nom": "   ", "capacite": "10"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "Nom obligatoire" in res.data.decode("utf-8") or "erreur" in res.data.decode("utf-8").lower()


def test_modifier_salle(client):
    res = client.post(
        "/salles/1/modifier",
        data={"nom": "S1_Renommee", "capacite": "30", "projecteur": "0"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    with ouvrir_base() as conn:
        salle = conn.execute("SELECT * FROM salles WHERE id = 1").fetchone()
        assert salle["nom"] == "S1_Renommee"
        assert salle["capacite"] == 30
        assert salle["projecteur"] == 0


def test_supprimer_salle_cascade(client):
    # Vérifier d'abord que la salle 1 et sa réservation existent
    with ouvrir_base() as conn:
        assert conn.execute("SELECT * FROM salles WHERE id = 1").fetchone() is not None
        assert conn.execute("SELECT * FROM reservations WHERE salle_id = 1").fetchone() is not None

    # Supprimer la salle 1
    res = client.post("/salles/1/supprimer", follow_redirects=True)
    assert res.status_code == 200

    # Vérifier que la salle a été supprimée
    with ouvrir_base() as conn:
        assert conn.execute("SELECT * FROM salles WHERE id = 1").fetchone() is None
        # CASCADE : la réservation associée doit être automatiquement supprimée !
        resas = conn.execute("SELECT * FROM reservations WHERE salle_id = 1").fetchall()
        assert len(resas) == 0


# ====================================================
# TESTS RESERVATIONS & ANNULATIONS (ÉTAPE 3)
# ====================================================

def test_reserver_valide(client):
    # Réserver S1 le lundi 2026-11-09 de 14:00 à 15:30 (hors conflit Alice 10h-12h)
    res = client.post(
        "/reservations",
        data={
            "salle_id": "1",
            "personne": "Bob",
            "date": "2026-11-09",
            "debut": "14:00",
            "fin": "15:30",
            "participants": "10",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "Réservation enregistrée avec succès" in res.data.decode("utf-8")

    with ouvrir_base() as conn:
        resa = conn.execute("SELECT * FROM reservations WHERE personne = 'Bob'").fetchone()
        assert resa is not None
        assert resa["debut"] == "14:00"
        assert resa["fin"] == "15:30"
        assert resa["participants"] == 10


def test_reserver_rejet_chevauchement(client):
    # Alice a déjà S1 le 2026-11-09 de 10:00 à 12:00.
    # Tentative de réserver de 11:00 à 13:00 -> doit échouer pour chevauchement !
    res = client.post(
        "/reservations",
        data={
            "salle_id": "1",
            "personne": "Charlie",
            "date": "2026-11-09",
            "debut": "11:00",
            "fin": "13:00",
            "participants": "5",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "chevauchement" in html.lower()

    with ouvrir_base() as conn:
        resa = conn.execute("SELECT * FROM reservations WHERE personne = 'Charlie'").fetchone()
        assert resa is None


def test_reserver_accept_contiguite(client):
    # Alice a S1 jusqu'à 12:00. Réserver de 12:00 à 13:00 est contigu et donc autorisé.
    res = client.post(
        "/reservations",
        data={
            "salle_id": "1",
            "personne": "David",
            "date": "2026-11-09",
            "debut": "12:00",
            "fin": "13:00",
            "participants": "8",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    with ouvrir_base() as conn:
        resa = conn.execute("SELECT * FROM reservations WHERE personne = 'David'").fetchone()
        assert resa is not None


def test_reserver_rejet_capacite(client):
    # S1 a une capacité de 20. Tentative avec 25 participants -> Rejeté !
    res = client.post(
        "/reservations",
        data={
            "salle_id": "1",
            "personne": "Eve",
            "date": "2026-11-09",
            "debut": "14:00",
            "fin": "15:00",
            "participants": "25",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "capacité dépassée" in res.data.decode("utf-8").lower()
    with ouvrir_base() as conn:
        resa = conn.execute("SELECT * FROM reservations WHERE personne = 'Eve'").fetchone()
        assert resa is None


def test_reserver_rejet_horaires_et_durees(client):
    # Avant 8h
    res = client.post(
        "/reservations",
        data={"salle_id": "1", "personne": "F", "date": "2026-11-09", "debut": "07:30", "fin": "09:00", "participants": "5"},
        follow_redirects=True,
    )
    assert "avant" in res.data.decode("utf-8").lower()

    # Moins de 30 min (20 min)
    res = client.post(
        "/reservations",
        data={"salle_id": "1", "personne": "G", "date": "2026-11-10", "debut": "14:00", "fin": "14:20", "participants": "5"},
        follow_redirects=True,
    )
    assert "30 minutes" in res.data.decode("utf-8").lower()

    # Plus de 4 heures (5 h)
    res = client.post(
        "/reservations",
        data={"salle_id": "1", "personne": "H", "date": "2026-11-10", "debut": "08:00", "fin": "13:00", "participants": "5"},
        follow_redirects=True,
    )
    assert "4 heures" in res.data.decode("utf-8").lower()


def test_annuler_reservation(client):
    # Réservation initiale id=1 pour Alice
    with ouvrir_base() as conn:
        assert conn.execute("SELECT * FROM reservations WHERE id = 1").fetchone() is not None

    res = client.post("/reservations/1/annuler", follow_redirects=True)
    assert res.status_code == 200
    assert "annulée" in res.data.decode("utf-8").lower()

    with ouvrir_base() as conn:
        assert conn.execute("SELECT * FROM reservations WHERE id = 1").fetchone() is None

    # Le créneau 10:00 - 12:00 peut maintenant être réservé sans conflit !
    res2 = client.post(
        "/reservations",
        data={
            "salle_id": "1",
            "personne": "Nouveau",
            "date": "2026-11-09",
            "debut": "10:00",
            "fin": "12:00",
            "participants": "10",
        },
        follow_redirects=True,
    )
    assert res2.status_code == 200
    with ouvrir_base() as conn:
        assert conn.execute("SELECT * FROM reservations WHERE personne = 'Nouveau'").fetchone() is not None


# ====================================================
# TESTS PLANNING HEBDOMADAIRE (ÉTAPE 4)
# ====================================================

def test_planning_hebdomadaire_lundi_au_dimanche(client):
    # Consultation du planning pour la salle 1 et le mercredi 11 novembre 2026
    res = client.get("/?salle_id=1&date=2026-11-11")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Vérifie que la semaine affichée débute le lundi 2026-11-09 et termine le dimanche 2026-11-15
    assert "2026-11-09" in html
    assert "2026-11-15" in html
    assert "Lundi" in html
    assert "Dimanche" in html

    # Vérifie que la réservation d'Alice du lundi 9 novembre est présente
    assert "Alice" in html
    assert "10:00 - 12:00" in html


# ====================================================
# TESTS ÉVOLUTION : HORAIRES PAR SALLE (ÉTAPE 6)
# ====================================================

def test_salle_horaires_specifiques(client):
    # Créer une salle ouverte de 09:00 à 17:00
    res = client.post(
        "/salles",
        data={
            "nom": "SalleLabo",
            "capacite": "12",
            "projecteur": "0",
            "ouverture": "09:00",
            "fermeture": "17:00",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    with ouvrir_base() as conn:
        labo = conn.execute("SELECT * FROM salles WHERE nom = 'SalleLabo'").fetchone()
        assert labo is not None
        labo_id = labo["id"]

    # Tentative avant ouverture de cette salle spécifique (08:30 à 09:30) -> Refusée !
    res_t1 = client.post(
        "/reservations",
        data={
            "salle_id": str(labo_id),
            "personne": "Chercheur1",
            "date": "2026-11-12",
            "debut": "08:30",
            "fin": "09:30",
            "participants": "4",
        },
        follow_redirects=True,
    )
    assert "avant" in res_t1.data.decode("utf-8").lower()

    # Tentative après fermeture de cette salle spécifique (16:30 à 17:30) -> Refusée !
    res_t2 = client.post(
        "/reservations",
        data={
            "salle_id": str(labo_id),
            "personne": "Chercheur2",
            "date": "2026-11-12",
            "debut": "16:30",
            "fin": "17:30",
            "participants": "4",
        },
        follow_redirects=True,
    )
    assert "après" in res_t2.data.decode("utf-8").lower()

    # Réservation dans les plages de la salle (10:00 à 11:30) -> Acceptée !
    res_ok = client.post(
        "/reservations",
        data={
            "salle_id": str(labo_id),
            "personne": "ChercheurOK",
            "date": "2026-11-12",
            "debut": "10:00",
            "fin": "11:30",
            "participants": "4",
        },
        follow_redirects=True,
    )
    assert "succès" in res_ok.data.decode("utf-8").lower()


# ====================================================
# TESTS BONUS (ÉTAPE 7)
# ====================================================

def test_recherche_salle_libre(client):
    # Le lundi 2026-11-09 de 10:30 à 11:30, S1 est occupée par Alice (10:00-12:00).
    # S2 (capacité 8, sans projecteur) est libre.
    # Recherche pour 5 participants sans projecteur -> S2 doit apparaître, S1 ne doit PAS apparaître.
    res = client.get("/recherche?date=2026-11-09&debut=10:30&fin=11:30&participants=5")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "S2" in html


def test_export_csv_planning(client):
    res = client.get("/planning/export?salle_id=1&date=2026-11-09")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("Content-Type", "")
    content = res.data.decode("utf-8-sig")
    assert "Salle;Date;Heure Début;Heure Fin;Personne;Participants" in content
    assert "Alice" in content
    assert "10:00" in content
    assert res.data.startswith(b"\xef\xbb\xbf")


def test_recherche_sans_parametres_ne_plante_pas(client):
    """Accéder à /recherche sans paramètres ne doit pas planter (évite UnboundLocalError) ni afficher d'erreur prématurée."""
    res = client.get("/recherche")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Rechercher une Salle Libre" in html
    assert "Aucune salle disponible pour ce créneau" not in html


def test_recherche_affiche_planning_et_reservations(client):
    """Vérifie que la page de recherche affiche correctement le planning de la semaine avec les réservations existantes."""
    res = client.get("/recherche?date=2026-11-09&debut=14:00&fin=15:00&participants=5")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    # La réservation d'Alice du lundi 9 novembre doit être visible dans le calendrier de la page de recherche
    assert "Alice" in html
    assert "10:00 - 12:00" in html


def test_modifier_salle_inexistante(client):
    res = client.post(
        "/salles/9999/modifier",
        data={"nom": "Inconnue", "capacite": "10"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "introuvable" in res.data.decode("utf-8").lower()


def test_supprimer_salle_inexistante(client):
    res = client.post("/salles/9999/supprimer", follow_redirects=True)
    assert res.status_code == 200
    assert "introuvable" in res.data.decode("utf-8").lower()


def test_annuler_reservation_inexistante(client):
    res = client.post("/reservations/9999/annuler", follow_redirects=True)
    assert res.status_code == 200
    assert "introuvable" in res.data.decode("utf-8").lower()


def test_modifier_salle_conflit_capacite_existante(client):
    # S1 a une réservation pour Alice avec 12 participants.
    # Tenter de réduire la capacité de S1 à 5 doit être refusé pour protéger la cohérence des données.
    res = client.post(
        "/salles/1/modifier",
        data={"nom": "S1", "capacite": "5", "ouverture": "08:00", "fermeture": "20:00"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "impossible de réduire la capacité" in html.lower()
    with ouvrir_base() as conn:
        salle = conn.execute("SELECT * FROM salles WHERE id = 1").fetchone()
        assert salle["capacite"] == 20  # Inchangée


def test_modifier_salle_conflit_horaires_existants(client):
    # S1 a une réservation d'Alice de 10:00 à 12:00.
    # Modifier les horaires d'ouverture à 13:00 - 18:00 placerait Alice hors de la plage autorisée.
    res = client.post(
        "/salles/1/modifier",
        data={"nom": "S1", "capacite": "20", "ouverture": "13:00", "fermeture": "18:00"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "hors des nouveaux horaires" in html.lower()
    with ouvrir_base() as conn:
        salle = conn.execute("SELECT * FROM salles WHERE id = 1").fetchone()
        assert salle["ouverture"] == "08:00"  # Inchangée


def test_export_csv_nom_avec_espaces_et_bom(client):
    client.post("/salles", data={"nom": "Grand Amphi", "capacite": "100"}, follow_redirects=True)
    with ouvrir_base() as conn:
        s = conn.execute("SELECT id FROM salles WHERE nom = 'Grand Amphi'").fetchone()
        grand_amphi_id = s["id"]
    res = client.get(f"/planning/export?salle_id={grand_amphi_id}&date=2026-11-09")
    assert res.status_code == 200
    disposition = res.headers.get("Content-Disposition", "")
    assert 'filename="planning_Grand Amphi_20261109.csv"' in disposition

