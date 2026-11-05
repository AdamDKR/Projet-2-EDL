---
name: commit-push
description: Vérifie le travail, écrit un message de commit clair, puis pousse sur GitHub. À utiliser quand on demande de faire un commit ou de pousser.
---

1. Regarde `git status` et `git diff`. Si un fichier ne doit pas être versionné (`data.db`, `.venv`, `.pytest_cache`, logs), arrête-toi et avertis l'utilisateur.
2. Lance `pytest` dans le dossier de code. Si un test échoue, arrête-toi immédiatement et affiche l'erreur.
3. **RÈGLE ABSOLUE & STRICTE :** Demande obligatoirement l'accord explicite et préalable de l'utilisateur AVANT d'effectuer le commit. Présente un résumé clair des fichiers modifiés et la proposition de message de commit. Ne procède à `git add` et `git commit` QUE si l'utilisateur valide formellement.
4. Si la branche existe déjà sur le dépôt distant, effectue `git pull --no-rebase --no-edit`. En cas de conflit, arrête-toi sans résoudre seul et liste les fichiers en conflit.
5. **RÈGLE ABSOLUE & STRICTE :** Demande obligatoirement l'accord explicite et préalable de l'utilisateur AVANT de pousser sur GitHub. Ne fais JAMAIS `git push` sans son accord formel.
