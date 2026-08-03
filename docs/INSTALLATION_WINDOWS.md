# Guide d'installation et de lancement — Windows

Ce guide explique comment relancer le projet depuis zéro sur une machine Windows (par exemple après un redémarrage, ou sur un autre PC). Il suppose que vous ouvrez le dossier `smart-lighting-decision-tool` dans **Visual Studio Code**.

Toutes les commandes ci-dessous s'exécutent dans le terminal intégré de VS Code (menu **Terminal → Nouveau terminal**, un terminal **PowerShell**).

## 1. Prérequis (déjà installés sur cette machine)

| Outil | Vérifier avec | Version installée |
|---|---|---|
| Python | `python --version` | 3.12.10 |
| Node.js / npm | `node --version` / `npm --version` | 24.18.0 / 11.16.0 |
| Git | `git --version` | 2.55.0 |
| PostgreSQL | Service Windows "postgresql-x64-18" | 18 |

Si l'une de ces commandes échoue avec "terme non reconnu", fermez et rouvrez le terminal (le PATH Windows n'est parfois chargé qu'à l'ouverture d'un nouveau terminal).

## 2. Vérifier que PostgreSQL tourne

```powershell
Get-Service postgresql-x64-18
```

Le `Status` doit être `Running`. Si ce n'est pas le cas :

```powershell
Start-Service postgresql-x64-18
```

## 3. Backend (API FastAPI)

Ouvrez un terminal PowerShell **dans le dossier `backend/`** :

```powershell
cd backend
```

### 3.1. Créer/activer l'environnement virtuel Python

Si le dossier `.venv` n'existe pas encore :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

S'il existe déjà, passez directement à l'étape suivante.

### 3.2. Configurer le fichier `.env`

Le fichier `backend/.env` contient la chaîne de connexion à la base de données (avec le mot de passe réel). Il **n'est jamais envoyé sur Git** (protégé par `.gitignore`). S'il n'existe pas (nouvelle machine), copiez `backend/.env.example` vers `backend/.env` et complétez `DATABASE_URL` avec le mot de passe de l'utilisateur `lighting_app`.

### 3.3. Appliquer les migrations (si nouvelle base)

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

### 3.4. Importer les données (si base vide)

```powershell
.\.venv\Scripts\python.exe scripts\run_initial_import.py
```

### 3.5. Lancer le serveur

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Le backend est démarré quand vous voyez `Uvicorn running on http://127.0.0.1:8000`.

- Documentation interactive (Swagger) : http://127.0.0.1:8000/docs
- Vérification rapide : http://127.0.0.1:8000/api/health doit répondre `{"status":"ok",...}`

**Laissez ce terminal ouvert** — fermer le terminal arrête le serveur.

### 3.6. Lancer les tests backend

Dans un **autre terminal**, dossier `backend/` :

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -v
```

## 4. Frontend (interface React)

Ouvrez un **nouveau terminal** PowerShell (Terminal → Nouveau terminal), dans le dossier `frontend/` :

```powershell
cd frontend
```

### 4.1. Installer les dépendances (si `node_modules` n'existe pas)

```powershell
npm install
```

### 4.2. Configurer le fichier `.env`

Le fichier `frontend/.env` contient l'adresse du backend. S'il n'existe pas, copiez `frontend/.env.example` :

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### 4.3. Lancer le serveur de développement

```powershell
npm run dev
```

Ouvrez ensuite votre navigateur à l'adresse indiquée (par défaut **http://localhost:5173**).

**Le backend doit être démarré en même temps** (voir étape 3.5) pour que les pages affichent des données.

### 4.4. Lancer les tests frontend

```powershell
npm run test
```

## 5. Arrêter les serveurs

Dans chaque terminal, appuyez sur `Ctrl+C` pour arrêter le serveur.

## 6. Résumé — démarrage quotidien

Une fois tout installé une première fois, le lancement quotidien tient en 2 terminaux :

**Terminal 1 (backend) :**
```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 (frontend) :**
```powershell
cd frontend
npm run dev
```

Puis ouvrez http://localhost:5173 dans votre navigateur.

## 7. Problèmes fréquents

| Symptôme | Cause probable | Solution |
|---|---|---|
| `python`/`node`/`git` non reconnu | Terminal ouvert avant l'installation | Fermer/rouvrir le terminal |
| Le frontend affiche des erreurs réseau | Backend non démarré | Vérifier que le terminal backend tourne et que http://127.0.0.1:8000/api/health répond |
| `psql`/connexion refusée | Service PostgreSQL arrêté | `Start-Service postgresql-x64-18` |
| Erreur `password authentication failed` | Mauvais mot de passe dans `backend/.env` | Vérifier `DATABASE_URL` |
| Page blanche dans le navigateur | Cache du navigateur / build cassé | Rafraîchir avec Ctrl+F5, vérifier la console (F12) |
