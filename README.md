# Serveur MCP pour Analyse STEP

## 🎯 Vue d'ensemble

Serveur MCP (Model Context Protocol) pour l'analyse et la comparaison de fichiers STEP (ISO 10303). Compatible avec Claude Desktop et autres clients MCP.

## ✨ Fonctionnalités

Le serveur expose 6 outils via le protocole MCP :

### 1. `analyze_step_file`
Analyse complète d'un fichier STEP : métadonnées, structure et géométrie
- **Paramètres** : 
  - `file_path` (optionnel) : chemin vers le fichier STEP
  - `file_content` (optionnel) : contenu binaire du fichier joint
- **Retour** : Métadonnées, BOM hiérarchique, composants détaillés, propriétés géométriques, dépendances, validation

### 2. `compare_step_files`
Compare deux fichiers STEP et détecte les différences critiques incluant les interfaces
- **Paramètres** : 
  - `file1_path` (optionnel) : chemin vers le premier fichier STEP
  - `file1_content` (optionnel) : contenu binaire du premier fichier
  - `file2_path` (optionnel) : chemin vers le second fichier STEP
  - `file2_content` (optionnel) : contenu binaire du second fichier
- **Retour** : Analyse d'impact (clash, assembly, interfaces), changements (BOM, géométrie, topologie, interfaces), statistiques

### 3. `extract_bom`
Extrait uniquement la nomenclature (Bill of Materials)
- **Paramètres** : 
  - `file_path` (optionnel) : chemin vers le fichier STEP
  - `file_content` (optionnel) : contenu binaire du fichier joint
- **Retour** : Liste hiérarchique des composants avec position, niveau, quantité, nom et type

### 4. `extract_geometry`
Extrait les propriétés géométriques détaillées
- **Paramètres** : 
  - `file_path` (optionnel) : chemin vers le fichier STEP
  - `file_content` (optionnel) : contenu binaire du fichier joint
  - `component_name` (optionnel) : nom du composant spécifique
- **Retour** : Propriétés géométriques et topologiques par composant et totaux agrégés

### 5. `validate_step_file`
Valide la conformité d'un fichier STEP selon les standards industriels
- **Paramètres** : 
  - `file_path` (optionnel) : chemin vers le fichier STEP
  - `file_content` (optionnel) : contenu binaire du fichier joint
- **Retour** : Statut global et détails des vérifications

### 6. `analyze_interfaces`
Analyse les interfaces et liaisons entre composants pour la gestion de configuration
- **Paramètres** : 
  - `file_path` (optionnel) : chemin vers le fichier STEP
  - `file_content` (optionnel) : contenu binaire du fichier joint
- **Retour** : Interfaces détectées (vissages, contacts, proximité), points critiques, graphe d'assemblage, recommandations

**Types d'interfaces détectés** :
- **Fixations (Fastening)** : Trous alignés → vissages/boulonnages (criticité ÉLEVÉE)
- **Contacts (Contact)** : Surfaces en contact → encastrements (criticité MOYENNE)
- **Proximité (Proximity)** : Composants proches (criticité FAIBLE)

## 🚀 Installation

### Option 1 : Avec Docker (Recommandé)

#### Prérequis
- Docker et Docker Compose installés
- Claude Desktop configuré

#### Configuration

Pour accéder aux fichiers STEP depuis Claude Desktop, vous devez combiner deux serveurs MCP :
1. **step-analyzer** : Pour l'analyse des fichiers STEP
2. **filesystem** : Pour l'accès aux fichiers depuis Claude Desktop

Créez/modifiez votre fichier de configuration MCP :

**macOS/Linux** (`~/.config/Claude/claude_desktop_config.json`) :
```json
{
  "mcpServers": {
    "step-analyzer": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--mount", "type=bind,src=/Chemin/Vers/Dossier/Step,dst=/step",
        "jchabas/mcp_stepanalyzer:0.0.3"
      ]
    },
    "filesystem": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--mount", "type=bind,src=/Chemin/Vers/Dossier/Step,dst=/step",
        "mcp/filesystem",
        "/step"
      ]
    }
  }
}

```

**Windows** (`%APPDATA%\Claude\claude_desktop_config.json`) :
```json
{
  "mcpServers": {
    "step-analyzer": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--mount", "type=bind,src=C:/Chemin/Vers/Dossier/Step,dst=/step",
        "jchabas/mcp_stepanalyzer:0.0.3"
      ]
    },
    "filesystem": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--mount", "type=bind,src=C:/Chemin/Vers/Dossier/Step,dst=/step",
        "mcp/filesystem",
        "/step"
      ]
    }
  }
}

```

**Important** : Remplacez `/chemin/vers/vos/fichiers/step` par le chemin réel vers votre dossier contenant les fichiers STEP.

#### Utilisation avec Claude Desktop

1. **Placez vos fichiers STEP** dans le dossier configuré (ex: `/chemin/vers/vos/fichiers/step/`)
2. **Demandez à Claude** de lister les fichiers disponibles :
   ```
   Quels fichiers STEP sont disponibles ?
   ```
3. **Demandez une analyse** :
   ```
   Analyse le fichier /workspace/step/product.stp
   ```

> 💡 **Astuce** : Le serveur filesystem permet à Claude de voir vos fichiers, et le serveur step-analyzer les analyse. Les deux travaillent ensemble !

### Option 2 : Installation locale

#### Prérequis
```bash
# Installer pythonocc-core (via conda recommandé)
conda install -c conda-forge pythonocc-core

# Installer FastMCP
pip install fastmcp
```

#### Configuration pour Claude Desktop

Ajoutez cette configuration :

**macOS/Linux** :
```json
{
  "mcpServers": {
    "step-analyzer": {
      "command": "python",
      "args": ["/chemin/absolu/vers/MCP_STEP.py"],
      "description": "Serveur MCP pour l'analyse de fichiers STEP"
    }
  }
}
```

**Windows** :
```json
{
  "mcpServers": {
    "step-analyzer": {
      "command": "python",
      "args": ["C:\\chemin\\vers\\MCP_STEP.py"],
      "description": "Serveur MCP pour l'analyse de fichiers STEP"
    }
  }
}
```

Remplacez le chemin par le chemin absolu vers le fichier.

## 📖 Utilisation

### Avec Claude Desktop

#### Scénario 1 : Analyser un fichier
```
Utilisateur : Quels fichiers STEP sont disponibles ?
Claude : [liste les fichiers via filesystem]

Utilisateur : Analyse le fichier /workspace/step/product.stp et extrais la nomenclature
Claude : [utilise analyze_step_file avec file_path]
```

#### Scénario 2 : Comparer deux versions
```
Utilisateur : Compare /workspace/step/product_v1.stp avec /workspace/step/product_v2.stp

Claude : [utilise compare_step_files avec les deux chemins]
```

#### Scénario 3 : Navigation intelligente
```
Utilisateur : Trouve tous les fichiers STEP dans le dossier et analyse le plus récent

Claude : [utilise filesystem pour lister, puis step-analyzer pour analyser]
```

### En ligne de commande (mode développement)

```bash
# Lancer le serveur en mode développement
python MCP_STEP.py dev

# Le serveur affichera une interface interactive
```

### Test manuel avec stdio

```bash
# Lancer le serveur
python MCP_STEP.py

# Envoyer une requête JSON-RPC
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python MCP_STEP.py
```

## 🔧 Structure du code

Le serveur utilise **FastMCP** qui simplifie grandement l'implémentation :

```python
from fastmcp import FastMCP
import base64

mcp = FastMCP("STEP Analyzer", version="2.0.0")

@mcp.tool()
def analyze_step_file(
    file_path: str = None, 
    file_content: str = None
) -> Dict[str, Any]:
    """Analyse complète d'un fichier STEP
    
    Accepte soit un chemin d'accès, soit le contenu du fichier en base64
    """
    # Le serveur gère automatiquement l'une ou l'autre approche
    ...
```

## 📊 Exemples

### Exemple 1 : Analyser un fichier

**Entrée Claude Desktop** :
```
Utilisateur : Liste les fichiers STEP disponibles dans /workspace/step
Claude : [utilise filesystem pour lister]

Utilisateur : Analyse jasper_v14.stp
Claude : [utilise step-analyzer pour analyser /workspace/step/jasper_v14.stp]
```

**Réponse** : Liste complète des composants avec hiérarchie

### Exemple 2 : Comparer deux versions

**Entrée Claude Desktop** :
```
Utilisateur : Compare /workspace/step/jasper_v09.stp avec /workspace/step/jasper_v14.stp
```

**Réponse** : 
```json
{
  "total_changes": 3,
  "impact": "CRITICAL_INTERFACE",
  "clash_risks": 1,
  "interface_changes": 2,
  "critical_joints": [
    {
      "component1": "housing",
      "component2": "bracket",
      "fastener_count": 4,
      "fastener_diameter": 5,
      "severity": "critical"
    }
  ]
}
```

### Exemple 3 : Analyser un fichier local

**Entrée CLI** :
```bash
python -c "
from config_manager import ConfigurationManager
cm = ConfigurationManager('step/jaspair_v09.stp')
cm.analyze_complete()
"
```

## 🐳 Configuration Docker Compose (optionnel)

Pour un déploiement plus avancé :

```yaml
# filepath: docker-compose.yml
version: '3.8'

services:
  mcp-step-analyzer:
    image: docker.io/jchabas/mcp_stepanalyzer:latest
    container_name: mcp_step_analyzer
    ports:
      - "3000:3000"  # Si exposé via HTTP
    volumes:
      - ./step:/app/step:ro  # Monter le répertoire des fichiers STEP (optionnel)
    environment:
      - LOG_LEVEL=info
    restart: unless-stopped
```

Lancez avec :
```bash
docker-compose up -d
```

## 🔍 Dépendances

- **fastmcp** : Framework pour créer des serveurs MCP
- **pythonocc-core** : Bibliothèque pour l'analyse de fichiers STEP
- **config_manager** : Module d'analyse de configuration
- **baseline_comparator** : Module de comparaison de baselines

## 📝 Notes

- **Montage de volume requis** : Les fichiers STEP doivent être montés dans le conteneur Docker via volumes
- Le serveur **filesystem** permet à Claude de naviguer dans vos fichiers
- Le serveur **step-analyzer** effectue l'analyse des fichiers STEP
- Les baselines sont sauvegardées avec un ID unique pour la traçabilité
- Le serveur gère automatiquement les erreurs et retourne des messages clairs
- Compatible avec le protocole MCP 2024-11-05
- **Nouveauté v2.0** : Analyse des interfaces et intégration avec filesystem

## 🐛 Dépannage

### Claude Desktop ne voit pas le serveur

**Avec Docker** :
```bash
# Vérifiez que l'image est disponible
docker images | grep mcp_stepanalyzer

# Redémarrez Docker Desktop
# Redémarrez Claude Desktop
```

**Local** :
1. Vérifiez le chemin absolu dans la configuration
2. Testez : `python MCP_STEP.py`
3. Redémarrez Claude Desktop
4. Vérifiez les logs dans `~/Library/Logs/Claude/` (macOS)

## 📄 Licence

Projet éducatif - Digital Challenge
