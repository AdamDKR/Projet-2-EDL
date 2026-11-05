---
name: commit-push
description: Vérifie le travail, écrit un message de commit clair, puis pousse sur GitHub. À utiliser quand on demande de faire un commit ou de pousser.
---

1. Regarde `git status` et `git diff`. Si un fichier ne doit pas partir (mot de passe, `data.db`, `.venv`), arrête-toi et préviens.
2. Lance `pytest` dans le dossier de code. Si un test échoue, arrête-toi et donne le résultat.
3. RÈGLE STRICTE : Demande obligatoirement l'accord explicite de l'utilisateur AVANT d'effectuer le commit. Présente-lui le résumé des modifications et le message de commit proposé. Ne fais `git add -A` et `git commit` QUE si l'utilisateur valide expressément.
4. Si la branche existe déjà sur GitHub, fais `git pull --no-rebase --no-edit`. En cas de conflit, arrête-toi et liste les fichiers, sans rien résoudre seul.
5. RÈGLE STRICTE : Demande obligatoirement l'accord explicite de l'utilisateur AVANT de pousser sur GitHub. Ne fais jamais `git push` sans son accord formel.