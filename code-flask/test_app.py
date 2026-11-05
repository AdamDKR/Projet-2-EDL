import pytest
from app import app
from base import ouvrir_base
from regles import (
    RegleReservationException,
    calculer_semaine,
    valider_modification_capacite,
    valider_reservation,
    valider_salle,
)


def test_accueil():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "Réservation de salles" in response.text


# =====================================================================
# Tests unitaires des règles métier (Tableau 6 de l'énoncé)
# Salle S1 de capacité 20, déjà réservée le lundi de 10 h à 12 h.
# =====================================================================

RESERVATIONS_S1 = [
    {"debut": "10:00", "fin": "12:00"}
]


def test_regle_chevauchement_refuse():
    """Lundi, 11 h à 13 h -> Refusée : chevauchement."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="11:00",
            fin="13:00",
            participants=10,
            reservations_existantes=RESERVATIONS_S1,
        )
    assert "chevauchement" in str(exc.value).lower()


def test_regle_creneau_adjacent_accepte():
    """Lundi, 12 h à 13 h -> Acceptée (finir à 12h et commencer à 12h est autorisé)."""
    valider_reservation(
        personne="Bob",
        capacite_salle=20,
        debut="12:00",
        fin="13:00",
        participants=10,
        reservations_existantes=RESERVATIONS_S1,
    )


def test_regle_creneau_adjacent_avant_accepte():
    """Lundi, 9 h à 10 h -> Acceptée (finir à 10h et commencer à 10h est autorisé)."""
    valider_reservation(
        personne="Bob",
        capacite_salle=20,
        debut="09:00",
        fin="10:00",
        participants=10,
        reservations_existantes=RESERVATIONS_S1,
    )


def test_regle_capacite_depassee_refuse():
    """Lundi, 14 h à 15 h, 25 participants -> Refusée : capacité dépassée."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="14:00",
            fin="15:00",
            participants=25,
            reservations_existantes=RESERVATIONS_S1,
        )
    assert "capacité" in str(exc.value).lower()


def test_regle_avant_8h_refuse():
    """Lundi, 7 h 30 à 9 h -> Refusée : avant 8 h."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="07:30",
            fin="09:00",
            participants=10,
            reservations_existantes=RESERVATIONS_S1,
        )
    assert "8 h" in str(exc.value)


def test_regle_apres_20h_refuse():
    """Une réservation doit se terminer au plus tard à 20 h."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="19:00",
            fin="20:30",
            participants=10,
            reservations_existantes=RESERVATIONS_S1,
        )
    assert "20 h" in str(exc.value)


def test_regle_moins_de_30min_refuse():
    """Mardi, 14 h à 14 h 20 -> Refusée : moins de 30 min."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="14:00",
            fin="14:20",
            participants=10,
            reservations_existantes=[],
        )
    assert "30 minutes" in str(exc.value)


def test_regle_plus_de_4h_refuse():
    """Mardi, 8 h à 13 h -> Refusée : plus de 4 h."""
    with pytest.raises(RegleReservationException) as exc:
        valider_reservation(
            personne="Bob",
            capacite_salle=20,
            debut="08:00",
            fin="13:00",
            participants=10,
            reservations_existantes=[],
        )
    assert "4 heures" in str(exc.value)


# =====================================================================
# Tests unitaires sur la validation des salles
# =====================================================================

def test_regle_salle_invalide():
    with pytest.raises(RegleReservationException):
        valider_salle("", 10)
    with pytest.raises(RegleReservationException):
        valider_salle("Salle Test", 0)


def test_regle_reduction_capacite_invalide():
    """Impossible de réduire la capacité en dessous des participants d'une réservation existante."""
    with pytest.raises(RegleReservationException):
        valider_modification_capacite(nouvelle_capacite=10, max_participants_existants=15)


# =====================================================================
# Tests d'intégration Flask (routes HTTP)
# =====================================================================

def test_route_reserver_succes_et_nettoyage():
    client = app.test_client()

    res = client.post(
        "/reservations",
        data={
            "salle_id": 1,
            "personne": "TestUserIntegration",
            "date": "2026-11-10",
            "debut": "14:00",
            "fin": "15:00",
            "participants": 5,
        },
    )
    assert res.status_code == 302

    with ouvrir_base() as conn:
        ligne = conn.execute(
            "SELECT * FROM reservations WHERE personne = 'TestUserIntegration'"
        ).fetchone()
        assert ligne is not None
        conn.execute("DELETE FROM reservations WHERE personne = 'TestUserIntegration'")


def test_route_reserver_conflit():
    client = app.test_client()

    # Salle 1 a déjà Alice de 10:00 à 12:00 le 2026-11-09
    res = client.post(
        "/reservations",
        data={
            "salle_id": 1,
            "personne": "ConflitUser",
            "date": "2026-11-09",
            "debut": "11:00",
            "fin": "12:30",
            "participants": 5,
        },
    )
    assert res.status_code == 400
    assert "chevauchement" in res.text.lower()


def test_route_modifier_salle():
    client = app.test_client()

    with ouvrir_base() as conn:
        conn.execute("INSERT INTO salles (nom, capacite, projecteur) VALUES ('Salle Modif', 15, 0)")
        salle_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    # Accès au formulaire
    get_res = client.get(f"/salles/{salle_id}/modifier")
    assert get_res.status_code == 200
    assert "Salle Modif" in get_res.text

    # Modification
    post_res = client.post(
        f"/salles/{salle_id}/modifier",
        data={"nom": "Salle Modifiée Renommée", "capacite": 30, "projecteur": "1"},
    )
    assert post_res.status_code == 302

    # Vérification
    with ouvrir_base() as conn:
        salle = conn.execute("SELECT * FROM salles WHERE id = ?", [salle_id]).fetchone()
        assert salle["nom"] == "Salle Modifiée Renommée"
        assert salle["capacite"] == 30
        assert salle["projecteur"] == 1
        # Nettoyage
        conn.execute("DELETE FROM salles WHERE id = ?", [salle_id])


def test_route_supprimer_salle_cascade():
    """Règle métier : Supprimer une salle supprime ses réservations."""
    client = app.test_client()

    # Création d'une salle temporaire et d'une réservation
    with ouvrir_base() as conn:
        conn.execute("INSERT INTO salles (nom, capacite, projecteur) VALUES ('Salle Cascade', 10, 0)")
        salle_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.execute(
            """
            INSERT INTO reservations (salle_id, personne, date, debut, fin, participants)
            VALUES (?, 'CascadeUser', '2026-11-12', '14:00', '15:00', 8)
            """,
            [salle_id],
        )

    # Suppression de la salle
    res = client.post(f"/salles/{salle_id}/supprimer")
    assert res.status_code == 302

    # Vérification que la salle ET la réservation ont disparu (cascade)
    with ouvrir_base() as conn:
        salle = conn.execute("SELECT * FROM salles WHERE id = ?", [salle_id]).fetchone()
        assert salle is None

        reservation = conn.execute(
            "SELECT * FROM reservations WHERE personne = 'CascadeUser'"
        ).fetchone()
        assert reservation is None


def test_route_annuler_reservation():
    """Vérifie l'annulation d'une réservation."""
    client = app.test_client()

    with ouvrir_base() as conn:
        conn.execute(
            """
            INSERT INTO reservations (salle_id, personne, date, debut, fin, participants)
            VALUES (1, 'UserToCancel', '2026-11-13', '09:00', '10:00', 4)
            """
        )
        res_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    # Annulation
    res = client.post(f"/reservations/{res_id}/annuler")
    assert res.status_code == 302

    # Vérification en base
    with ouvrir_base() as conn:
        reservation = conn.execute("SELECT * FROM reservations WHERE id = ?", [res_id]).fetchone()
        assert reservation is None


# =====================================================================
# Tests du planning hebdomadaire
# =====================================================================

def test_calculer_semaine_lundi_au_dimanche():
    """Règle métier : La semaine va du lundi au dimanche."""
    # Test avec un mercredi (11 novembre 2026)
    info = calculer_semaine("2026-11-11")
    assert info["lundi"] == "2026-11-09"
    assert info["dimanche"] == "2026-11-15"
    assert len(info["jours"]) == 7
    assert info["jours"][0]["nom_jour"] == "Lundi"
    assert info["jours"][0]["date"] == "2026-11-09"
    assert info["jours"][6]["nom_jour"] == "Dimanche"
    assert info["jours"][6]["date"] == "2026-11-15"
    assert info["date_prec"] == "2026-11-02"
    assert info["date_suiv"] == "2026-11-16"


def test_route_planning_affichage():
    client = app.test_client()

    # Affichage du planning de la salle 1 pour la semaine du 2026-11-09
    res = client.get("/planning?salle_id=1&date=2026-11-09")
    assert res.status_code == 200
    assert "Planning d'une salle sur une semaine" in res.text
    # Alice est réservée le lundi 2026-11-09 de 10:00 à 12:00
    assert "Alice" in res.text
    assert "10:00 - 12:00" in res.text
    assert "Lundi" in res.text
    assert "Dimanche" in res.text


