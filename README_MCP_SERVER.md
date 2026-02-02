# Serveur MCP pour Analyse STEP

## 🎯 Vue d'ensemble

Serveur MCP (Model Context Protocol) pour l'analyse et la comparaison de fichiers STEP (ISO 10303). Compatible avec Claude Desktop et autres clients MCP.

## ✨ Fonctionnalités

Le serveur expose 6 outils via le protocole MCP :

### 1. `analyze_step`
Analyse complète d'un fichier STEP avec génération de baseline
- **Paramètre** : `file_path` (chemin vers le fichier STEP)
- **Retour** : Baseline, BOM, propriétés géométriques, métadonnées

### 2. `compare_step`
Compare deux fichiers STEP ou baselines et détecte les différences
- **Paramètres** : 
  - `file1` : premier fichier (STEP ou JSON baseline)
  - `file2` : deuxième fichier (STEP ou JSON baseline)
- **Retour** : Différences géométriques, BOM, métadonnées avec niveau d'impact

### 3. `get_bom`
Extrait la nomenclature (Bill of Materials)
- **Paramètre** : `file_path`
- **Retour** : Liste hiérarchique des composants

### 4. `get_geometry`
Extrait les propriétés géométriques
- **Paramètre** : `file_path`
- **Retour** : Volume, surface, centre de gravité pour chaque composant

### 5. `validate_step`
Valide la conformité d'un fichier STEP
- **Paramètre** : `file_path`
- **Retour** : Statut de validation avec détails des vérifications

### 6. `list_components`
Liste tous les composants d'un assemblage
- **Paramètre** : `file_path`
- **Retour** : Liste des composants avec type, niveau, quantité

## 🚀 Installation

### Prérequis
```bash
# Installer pythonocc-core (via conda recommandé)
conda install -c conda-forge pythonocc-core

# Installer FastMCP
pip install fastmcp
```

### Configuration pour Claude Desktop

Ajoutez cette configuration dans `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) ou `%APPDATA%\Claude\claude_desktop_config.json` (Windows) :

```json
{
  "mcpServers": {
    "step-analyzer": {
      "command": "python",
      "args": [
        "/chemin/absolu/vers/MCP_STEP.py"
      ],
      "description": "Serveur MCP pour l'analyse et la comparaison de fichiers STEP"
    }
  }
}
```

Remplacez `/chemin/absolu/vers/MCP_STEP.py` par le chemin absolu vers le fichier.

## 📖 Utilisation

### Avec Claude Desktop

Une fois configuré, vous pouvez utiliser les outils directement dans Claude :

```
Compare les fichiers step/jaspair_v09.stp et step/jaspair_v10.stp
```

Claude utilisera automatiquement l'outil `compare_step` du serveur MCP.

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

mcp = FastMCP("STEP Analyzer", version="1.0.0")

@mcp.tool()
def analyze_step(file_path: str) -> Dict[str, Any]:
    """Analyse complète d'un fichier STEP"""
    # Implémentation...
    return results
```

## 📊 Exemple de comparaison

### Entrée
```python
compare_step(
    file1="step/jaspair_v09.stp",
    file2="step/jaspair_v10.stp"
)
```

### Sortie
```json
{
  "success": true,
  "baseline1": "CFG_20260127_132735_d4b307c8",
  "baseline2": "CFG_20260127_132743_ea5020d4",
  "total_changes": 1,
  "impact_level": "moderate",
  "changes": {
    "geometry": [
      {
        "component": "jasper_v09",
        "volume_change": 3823.22,
        "surface_change": 373.96,
        "volume_before": 186490.64,
        "volume_after": 190313.86
      }
    ]
  }
}
```

## 🔍 Dépendances

- **fastmcp** : Framework pour créer des serveurs MCP
- **pythonocc-core** : Bibliothèque pour l'analyse de fichiers STEP
- **config_manager** : Module d'analyse de configuration
- **baseline_comparator** : Module de comparaison de baselines

## 📝 Notes

- Les fichiers STEP sont automatiquement convertis en baselines JSON lors de la comparaison
- Les baselines sont sauvegardées avec un ID unique pour la traçabilité
- Le serveur gère automatiquement les erreurs et retourne des messages clairs
- Compatible avec le protocole MCP 2024-11-05

## 🐛 Dépannage

### Le serveur ne démarre pas
Vérifiez que tous les modules sont installés :
```bash
python -c "from fastmcp import FastMCP; print('OK')"
python -c "from OCC.Core.STEPControl import STEPControl_Reader; print('OK')"
```

### Erreur d'import
Assurez-vous d'être dans le bon environnement conda/venv avec pythonocc-core installé.

### Claude Desktop ne voit pas le serveur
1. Vérifiez le chemin absolu dans la configuration
2. Redémarrez Claude Desktop
3. Vérifiez les logs dans `~/Library/Logs/Claude/` (macOS)

## 🤝 Contribution

Ce serveur fait partie d'un système complet d'analyse STEP. Consultez également :
- [GUIDE_RAPIDE.md](GUIDE_RAPIDE.md) - Guide de démarrage
- [README_CONFIG_MANAGEMENT.md](README_CONFIG_MANAGEMENT.md) - Documentation technique
- [SYNTHESE_PROJET.md](SYNTHESE_PROJET.md) - Vue d'ensemble du projet

## 📄 Licence

Projet éducatif - Digital Challenge
