# Plan d'Implémentation Détaillé — Projet 2 : Réservation de Salles

> **Directives et Règles Absolues :**
> - **Règle absolue :** Ne jamais faire de `git commit` ou `git push` sans l'accord explicite et préalable de l'utilisateur (inscrit dans `AGENTS.md` et `agent.md`).
> - **Développement incrémental :** Une seule fonctionnalité à la fois, accompagnée de ses tests automatisés (`pytest`).
> - **Découplage strict :** Toutes les règles métier sont implémentées dans un module pur (`regles.py`), indépendant de Flask et de SQLite, testé unitairement.
> - **Isolation des données :** Les tests doivent impérativement s'exécuter sur une base de données isolée (en mémoire ou fichier temporaire) pour ne jamais polluer ou altérer `data.db`.

---

## 1. Choix Technologiques & Décisions d'Architecture

### 1.1 Framework Web : Flask (`code-flask`)
- **Justification :**
  - `Flask 3.1.3` est déjà installé et validé dans l'environnement Python.
  - Le test initial `test_accueil()` passe immédiatement (`1 passed in 0.32s`).
  - `code-streamlit` échoue actuellement car `streamlit` n'est pas installé (`ModuleNotFoundError`).
  - Le protocole et le `README.md` indiquent : *« Gardez un dossier et supprimez l'autre »*. Le choix naturel et le plus robuste est **Flask**.
  - `code-streamlit` sera supprimé ou conservé sans interférence lors de la suite du projet après validation par l'utilisateur.

### 1.2 Base de Données : SQLite & Intégrité Référentielle
- Fichier source du schéma : `base.sql`.
- Fichier de base de production locale : `data.db` (ignoré par Git dans `.gitignore`).
- **Cascade Delete :** La contrainte `REFERENCES salles(id) ON DELETE CASCADE` est définie dans `base.sql`. Pour que SQLite applique la cascade, `PRAGMA foreign_keys = ON;` est activé à chaque connexion (déjà présent dans `base.py`).

### 1.3 Mécanisme d'Isolation des Tests (Sans toucher `data.db`)
Pour garantir que les tests ne modifient jamais `data.db` :
- Dans `code-flask/base.py`, paramétrer `ouvrir_base(db_path=None)` :
  ```python
  import os, sqlite3
  from pathlib import Path

  RACINE = Path(__file__).parent.parent
  BASE = RACINE / "data.db"

  def ouvrir_base(path=None):
      cible = path or os.environ.get("DATABASE_PATH") or BASE
      conn = sqlite3.connect(cible)
      conn.row_factory = sqlite3.Row
      conn.execute("PRAGMA foreign_keys = ON")
      if cible == ":memory:" or not Path(cible).exists():
          conn.executescript((RACINE / "base.sql").read_text(encoding="utf-8"))
      return conn
  ```
- Dans les tests (`conftest.py` ou `test_app.py`), injecter une base temporaire ou en mémoire via `DATABASE_PATH = ":memory:"` ou un fichier temporaire initialisé avec `base.sql`.

### 1.4 Arborescence Cible du Projet
```text
Projet-2-EDL/
├── AGENTS.md                   # Règles de collaboration agent (règle push/commit)
├── agent.md                    # Alias miroir pour conformité avec la consigne
├── base.sql                    # Définition des tables (salles, reservations) et données initiales
├── PLAN_IMPLEMENTATION.md      # Ce document de référence
├── code-flask/
│   ├── app.py                  # Contrôleurs Flask, formulaires HTML (PAGE) et routage
│   ├── base.py                 # Connexion SQLite avec isolation possible pour les tests
│   ├── regles.py               # Logique métier pure (indépendante de tout framework)
│   ├── requirements.txt        # Flask, pytest
│   ├── test_regles.py          # Tests unitaires purs de la logique métier (Tableau 6)
│   └── test_app.py             # Tests d'intégration Flask (routes, cascade, requêtes HTTP)
└── .agents/
    └── skills/
        ├── ajouter-fonctionnalite/ # Skill standard d'ajout de feature avec tests
        ├── commit-push/            # Skill de commit avec validation humaine obligatoire
        └── expliquer-code/         # Skill de documentation (Mermaid, résumé)
```

---

## 2. Spécification des Règles Métier (`regles.py`)

Toute la logique de validation est centralisée dans `regles.py`. Chaque fonction retourne `(valide: bool, message_erreur: str | None)`.

1. **Format des Heures & Dates :**
   - Heures : format strict `HH:MM` (ex: `"08:00"`, `"14:30"`).
   - Dates : format strict `YYYY-MM-DD`.
   - Ordre chronologique : `debut < fin`.
2. **Plage Horaire d'Ouverture :**
   - Par défaut : entre `08:00` et `20:00` inclus.
   - Règle : `debut >= ouverture` et `fin <= fermeture`.
   - Refus si `debut < "08:00"` (ex: `07:30 - 09:00` -> Refusée : avant 8 h).
3. **Durée de Réservation :**
   - Durée minimale : 30 minutes (`duree_minutes >= 30`).
   - Durée maximale : 4 heures (240 minutes) (`duree_minutes <= 240`).
   - Refus si moins de 30 min (ex: `14:00 - 14:20` = 20 min -> Refusée).
   - Refus si plus de 4 h (ex: `08:00 - 13:00` = 5 h -> Refusée).
4. **Capacité de la Salle :**
   - `participants > 0`.
   - `participants <= salle_capacite`.
   - Refus si `participants > capacite` (ex: 25 participants dans une salle de capacité 20 -> Refusée).
5. **Non-Chevauchement :**
   - Pour une même salle et une même date :
     Deux créneaux `[d1, f1]` et `[d2, f2]` se chevauchent si et seulement si :
     $$d_1 < f_2 \quad \text{et} \quad f_1 > d_2$$
   - **Cas contigu autorisé :** Finir à 12 h et commencer à 12 h est explicitement autorisé ($f_1 = d_2 \implies d_1 < d_2 \text{ et } d_2 > d_2 \text{ faux} \implies$ pas de chevauchement).
   - Lors d'une modification d'une réservation existante, l'ID de la réservation actuelle est exclu du test de chevauchement.
6. **Calcul de la Semaine :**
   - La semaine commence le **lundi** et finit le **dimanche**.
   - À partir d'une date $D$, le lundi correspondant est calculé via :
     $$\text{lundi} = D - \text{timedelta}(\text{days} = D.\text{weekday}())$$
     $$\text{dimanche} = \text{lundi} + \text{timedelta}(\text{days} = 6)$$

---

## 3. Découpage par Étapes Séquentielles

Conformément à `AGENTS.md` (*« Une fonctionnalité à la fois. Ajouter ou mettre à jour les tests à chaque fonctionnalité, puis lancer pytest »*) :

### Étape 0 : Environnement & Fixture de Test Isolée
- **Actions :**
  1. Vérifier la présence de `pytest` (`pytest` version 9.2.0 déjà installé).
  2. Adapter `code-flask/base.py` pour supporter `DATABASE_PATH` ou une base en mémoire.
  3. Mettre en place la fixture de base de test dans `code-flask/test_app.py` pour garantir l'indépendance vis-à-vis de `data.db`.
- **Validation :** `python -m pytest` s'exécute avec succès sans modifier `data.db`.

---

### Étape 1 : Module Métier Pur (`regles.py` + `test_regles.py`)
- **Actions :**
  1. Écrire les fonctions métier pures :
     - `valider_creneau(debut, fin, ouverture="08:00", fermeture="20:00")`
     - `valider_capacite(participants, capacite_salle)`
     - `verifier_chevauchement(debut, fin, reservations_existantes, reservation_id=None)`
     - `calculer_semaine(date_str)`
  2. Écrire les tests unitaires couvrant l'ensemble du **Tableau 6 du protocole** :
     - Salle S1 (capacité 20), occupée lundi 10h-12h :
       - Lundi 11h-13h : Refusée (chevauchement)
       - Lundi 12h-13h : **Acceptée** (contiguïté exacte)
       - Lundi 14h-15h, 25 participants : Refusée (capacité dépassée)
       - Lundi 07h30-09h : Refusée (avant 8h)
       - Mardi 14h-14h20 : Refusée (durée 20 min < 30 min)
       - Mardi 08h-13h : Refusée (durée 5 h > 4 h)
     - Cas limites supplémentaires : horaires inversés (`15:00` à `14:00`), participants nuls ou négatifs, formats mal formés.
- **Validation :** 100% des tests de `test_regles.py` passent sous `pytest`.

---

### Étape 2 : CRUD des Salles (`app.py` & `test_app.py`)
- **Fonctionnalités :**
  - Afficher la liste des salles avec nom, capacité, présence d'un projecteur (Oui/Non).
  - Ajouter une salle (`POST /salles`) avec nom, capacité $\ge 1$ et projecteur (0 ou 1).
  - Modifier une salle (`POST /salles/<id>/modifier`).
  - Supprimer une salle (`POST /salles/<id>/supprimer`) et vérifier que ses réservations sont supprimées en cascade grâce à la contrainte SQLite `ON DELETE CASCADE`.
- **Tests associés :**
  - Ajout avec succès / Rejet si nom vide ou capacité $< 1$.
  - Modification des propriétés d'une salle.
  - Suppression d'une salle et confirmation que ses réservations associées sont supprimées.
- **Validation :** Tests d'intégration Flask validés via `app.test_client()`.

---

### Étape 3 : Réservation & Annulation d'une Salle
- **Fonctionnalités :**
  - Formulaire de réservation : choix de la salle, nom de la personne, date (`YYYY-MM-DD`), heure de début (`HH:MM`), heure de fin (`HH:MM`), nombre de participants.
  - Contrôle des règles avant insertion : appel à `regles.py`.
  - En cas de succès : insertion dans `reservations` et message de confirmation.
  - En cas de refus : rejet de l'opération et affichage d'un message d'erreur clair et précis (ex : *« Chevauchement avec une autre réservation »*, *« Capacité dépassée (max 20) »*).
  - Annulation d'une réservation (`POST /reservations/<id>/annuler`) : suppression de la ligne et libération immédiate du créneau.
- **Tests associés :**
  - Réservation valide -> statut 200/302, réservation présente en base.
  - Rejet pour chaque règle métier (chevauchement, capacité, plage horaire, durée).
  - Annulation -> réservation supprimée, créneau redevenu libre.
- **Validation :** Tests d'intégration Flask validés via `app.test_client()`.

---

### Étape 4 : Affichage du Planning Hebdomadaire (Lundi au Dimanche)
- **Fonctionnalités :**
  - Sélecteur de salle et de date de référence.
  - Calcul de la semaine (du lundi au dimanche) contenant la date choisie.
  - Récupération de toutes les réservations de la salle comprises entre le lundi et le dimanche.
  - Rendu HTML sous forme de tableau ou grille hebdomadaire :
    - Colonnes : Lundi, Mardi, Mercredi, Jeudi, Vendredi, Samedi, Dimanche (avec dates exactes).
    - Lignes ou blocs : réservations ordonnées avec horaires, personne et nombre de participants.
- **Tests associés :**
  - Réservations de la semaine affichées au bon jour.
  - Réservations de la semaine précédente ou suivante exclues.
  - Comportement avec une salle sans réservation (planning vide).
- **Validation :** Tests de rendu Flask validés.

---

### Étape 5 : Intégration des Skills IA & Création du Skill de Documentation
- **Actions :**
  1. Organiser le dossier standard `.agents/skills/` :
     - `.agents/skills/ajouter-fonctionnalite/SKILL.md`
     - `.agents/skills/commit-push/SKILL.md`
  2. **Garde-fou strict dans `commit-push` :** Le skill doit explicitement demander l'accord préalable de l'utilisateur avant d'exécuter `git commit` ou `git push`.
  3. **Créer le skill de documentation** `.agents/skills/expliquer-code/SKILL.md` (demandé dans le protocole) :
     - Lit `git diff`.
     - Résume les changements en 5 lignes claires.
     - Génère un diagramme de séquence Mermaid.
     - Génère un diagramme d'activité (flowchart) Mermaid.
- **Validation :** Inspection et test du skill.

---

### Étape 6 : Évolution de Séance ("Chaque salle a ses propres horaires d'ouverture")
- **Contexte :** Demande surprise annoncée pendant la séance (Section 5.1 & 5.2 du protocole).
- **Actions :**
  1. Évolution de la table `salles` : ajout des colonnes `ouverture TEXT NOT NULL DEFAULT '08:00'` et `fermeture TEXT NOT NULL DEFAULT '20:00'`.
  2. Mise à jour de `regles.py` pour valider : `debut >= salle['ouverture']` et `fin <= salle['fermeture']`.
  3. Mise à jour des formulaires d'ajout/modification de salle pour permettre de définir les horaires spécifiques.
  4. Ajout des tests unitaires et d'intégration dédiés.
- **Validation :** Tests unitaires avec des salles ayant des horaires spécifiques (ex: 09h00-18h00).

---

### Étape 7 : Fonctionnalités Bonus ("Si vous avez fini")
1. **Recherche de salle libre :** Formulaire saisissant date, heure début, heure fin, participants min et besoin projecteur -> liste des salles candidates disponibles.
2. **Taux d'occupation :** Calcul du ratio $\frac{\text{heures réservées}}{\text{heures ouvrées}}\times 100$ par salle sur la semaine.
3. **Export du planning :** Génération d'un fichier CSV ou téléchargement des réservations hebdomadaires.

---

## 4. Matrice de Traçabilité & Vérifications du Protocole

| Règle / Cas à tester | Données de test (Salle S1, cap. 20, résa lun 10h-12h) | Résultat attendu | Niveau de test |
|---|---|---|---|
| Chevauchement | Lundi, 11 h à 13 h | **Refusée** (chevauchement) | Unitaire (`test_regles.py`) + Route Flask (`test_app.py`) |
| Contiguïté exacte | Lundi, 12 h à 13 h | **Acceptée** | Unitaire (`test_regles.py`) + Route Flask (`test_app.py`) |
| Dépassement capacité | Lundi, 14 h à 15 h, 25 participants | **Refusée** (capacité 25 > 20) | Unitaire (`test_regles.py`) + Route Flask (`test_app.py`) |
| Hors plage d'ouverture | Lundi, 7 h 30 à 9 h | **Refusée** (avant 8 h) | Unitaire (`test_regles.py`) + Route Flask (`test_app.py`) |
| Durée trop courte | Mardi, 14 h à 14 h 20 | **Refusée** (20 min < 30 min) | Unitaire (`test_regles.py`) + Route Flask (`test_app.py`) |
| Durée trop longue | Mardi, 8 h à 13 h | **Refusée** (5 h > 4 h) | Unitaire (`test_regles.py`) + Route Flask (`test_app.py`) |
| Inversion des heures | Début 16 h, Fin 14 h | **Refusée** (incohérence) | Unitaire (`test_regles.py`) |
| Participants invalides | 0 ou -3 participants | **Refusée** ($\le 0$) | Unitaire (`test_regles.py`) |
| Cascade de suppression | Supprimer S1 | Réservations associées supprimées | Test d'intégration DB (`test_app.py`) |
| Planning hebdo | Réservation mercredi et dimanche | Visibles dans la vue Lundi-Dimanche | Test de rendu (`test_app.py`) |
| Évolution horaires | Salle ouverte 09h-17h, résa à 08h30 | **Refusée** (hors ouverture salle) | Unitaire + Intégration |
