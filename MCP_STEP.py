#!/usr/bin/env python
"""
MCP Server for STEP File Analysis and Comparison
Serveur MCP pour l'analyse et la comparaison de fichiers STEP
"""

import json
import os
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from typing import Dict, List, Any

from fastmcp import FastMCP

# Import existing analyzers
from config_manager import ConfigurationManager
from baseline_comparator import BaselineComparator

# Create FastMCP server
mcp = FastMCP("STEP Analyzer", version="1.0.0")


@mcp.tool()
def analyze_step(file_path: str) -> Dict[str, Any]:
    """Analyse complète d'un fichier STEP avec génération de baseline
    
    Args:
        file_path: Chemin vers le fichier STEP à analyser
        
    Returns:
        Dictionnaire contenant les résultats de l'analyse incluant:
        - baseline_file: nom du fichier baseline généré
        - summary: résumé avec ID, checksum, nombre de composants, volumes
        - bom: nomenclature complète
        - geometric_properties: propriétés géométriques de chaque composant
    """
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Create configuration manager in silent mode
    cm = ConfigurationManager(file_path, silent=True)
    
    # Build BOM
    cm.build_bom()
    
    # Analyze geometry
    cm.analyze_geometry()
    
    # Extract colors
    cm.extract_colors()
    
    # Build dependency graph
    cm.build_dependency_graph()
    
    # Create baseline
    baseline = {
        'baseline_id': cm.generate_config_id(),
        'timestamp': datetime.now().isoformat(),
        'file': file_path,
        'metadata': cm.metadata,
        'bom': cm.bom,
        'component_registry': cm.components_registry,
        'geometric_properties': cm.geometric_props,
        'colors': cm.colors_registry,
        'dependencies': dict(cm.dependency_graph),
        'checksum': cm.calculate_file_checksum()
    }
    
    # Save baseline
    baseline_filename = f"config_baseline_{cm.generate_config_id()}.json"
    with open(baseline_filename, 'w', encoding='utf-8') as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)
    
    # Prepare summary
    total_volume = sum(p.get('volume', 0) for p in cm.geometric_props.values())
    total_surface = sum(p.get('surface_area', 0) for p in cm.geometric_props.values())
    
    return {
        "success": True,
        "baseline_file": baseline_filename,
        "summary": {
            "file": file_path,
            "baseline_id": baseline['baseline_id'],
            "timestamp": baseline['timestamp'],
            "checksum": baseline['checksum'],
            "components_count": len(cm.bom),
            "total_volume_mm3": round(total_volume, 2),
            "total_surface_mm2": round(total_surface, 2),
            "schema": cm.metadata.get('schema', 'Unknown')
        },
        "bom": cm.bom,
        "geometric_properties": cm.geometric_props
    }

@mcp.tool()
def compare_step(file1: str, file2: str) -> Dict[str, Any]:
    """Compare deux fichiers STEP et analyse l'impact (Clash, Interface, Fonctionnel)"""
    if not file1 or not os.path.exists(file1): raise FileNotFoundError(f"File not found: {file1}")
    if not file2 or not os.path.exists(file2): raise FileNotFoundError(f"File not found: {file2}")
    
    comparator = BaselineComparator(silent=True)
    
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        # Chargement intelligent
        baseline1 = comparator.generate_baseline_from_step(file1) if file1.endswith('.stp') else comparator.load_baseline(file1)
        baseline2 = comparator.generate_baseline_from_step(file2) if file2.endswith('.stp') else comparator.load_baseline(file2)
        
        comparator.baseline1 = baseline1
        comparator.baseline2 = baseline2
        comparator.compare()

    # --- ANALYSE D'IMPACT POUR LE LLM ---
    # On scanne les différences pour préparer un résumé exécutif
    impact_report = {
        "clash_risks": [],      # Encombrement augmenté
        "assembly_risks": [],   # Trous déplacés
        "retrofit_risks": []    # Diamètres modifiés
    }
    
    for item in comparator.changes.get('differences', []):
        comp = item['component']
        for diff in item['differences']:
            if "Encombrement" in diff:
                impact_report["clash_risks"].append(f"{comp}: {diff}")
            elif "Déplacé" in diff or "Supprimé" in diff:
                impact_report["assembly_risks"].append(f"{comp}: {diff}")
            elif "Ø Modifié" in diff:
                impact_report["retrofit_risks"].append(f"{comp}: {diff}")

    # Détermination du niveau d'alerte global
    overall_impact = "none"
    if impact_report["clash_risks"]: overall_impact = "CRITICAL_CLASH"
    elif impact_report["assembly_risks"]: overall_impact = "CRITICAL_ASSEMBLY"
    elif comparator.changes['components_removed']: overall_impact = "CRITICAL_MISSING_PART"
    elif impact_report["retrofit_risks"]: overall_impact = "MAJOR_RETROFIT"
    elif comparator.changes['components_added']: overall_impact = "MAJOR_BOM"
    elif comparator.changes.get('differences'): overall_impact = "MINOR_GEOMETRY"

    return {
        "success": True,
        "baseline1": comparator.baseline1.get('baseline_id'),
        "baseline2": comparator.baseline2.get('baseline_id'),
        "impact_level": overall_impact,
        "impact_analysis": impact_report,
        "changes_summary": {
            "components_added": len(comparator.changes['components_added']),
            "components_removed": len(comparator.changes['components_removed']),
            "geometry_issues": len(comparator.changes.get('differences', []))
        },
        # On inclut les détails complets si l'IA veut creuser
        "detailed_changes": comparator.changes.get('differences', [])
    }



@mcp.tool()
def get_bom(file_path: str) -> Dict[str, Any]:
    """Extrait la nomenclature (Bill of Materials) d'un fichier STEP
    
    Args:
        file_path: Chemin vers le fichier STEP
        
    Returns:
        Dictionnaire contenant:
        - bom: liste hiérarchique des composants
        - total_components: nombre total de composants
    """
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    cm = ConfigurationManager(file_path, silent=True)
    cm.build_bom()
    
    return {
        "success": True,
        "file": file_path,
        "bom": cm.bom,
        "total_components": len(cm.bom)
    }


@mcp.tool()
def get_geometry(file_path: str) -> Dict[str, Any]:
    """Extrait les propriétés géométriques d'un fichier STEP
    
    Args:
        file_path: Chemin vers le fichier STEP
        
    Returns:
        Dictionnaire contenant:
        - geometric_properties: propriétés de chaque composant (volume, surface, centre de gravité)
        - totals: totaux agrégés (volume_mm3, surface_mm2)
    """
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    cm = ConfigurationManager(file_path, silent=True)
    cm.analyze_geometry()
    cm.analyze_topology()
    
    total_volume = sum(p.get('volume', 0) for p in cm.geometric_props.values())
    total_surface = sum(p.get('surface_area', 0) for p in cm.geometric_props.values())
    
    return {
        "success": True,
        "file": file_path,
        "geometric_properties": cm.geometric_props,
        "totals": {
            "volume_mm3": round(total_volume, 2),
            "surface_mm2": round(total_surface, 2)
        }
    }


@mcp.tool()
def validate_step(file_path: str) -> Dict[str, Any]:
    """Valide la conformité d'un fichier STEP selon les standards industriels
    
    Args:
        file_path: Chemin vers le fichier STEP
        
    Returns:
        Dictionnaire contenant:
        - checks: liste des vérifications effectuées avec leur statut
        - overall_status: statut global (pass/warning/fail)
    """
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    cm = ConfigurationManager(file_path, silent=True)
    cm.build_bom()
    cm.analyze_geometry()
    cm.analyze_topology()
    
    validation_results = {
        "file": file_path,
        "checks": []
    }
    
    # Check 1: Metadata present
    if cm.metadata:
        validation_results["checks"].append({
            "name": "Metadata",
            "status": "pass",
            "message": "Métadonnées présentes"
        })
    else:
        validation_results["checks"].append({
            "name": "Metadata",
            "status": "warning",
            "message": "Métadonnées manquantes"
        })
    
    # Check 2: Valid schema
    valid_schemas = ['CONFIG_CONTROL_DESIGN', 'AUTOMOTIVE_DESIGN', 'AP203', 'AP214']
    schema = cm.metadata.get('schema', '')
    if any(s in schema for s in valid_schemas):
        validation_results["checks"].append({
            "name": "Schema",
            "status": "pass",
            "message": f"Schéma valide: {schema}"
        })
    else:
        validation_results["checks"].append({
            "name": "Schema",
            "status": "warning",
            "message": f"Schéma non standard: {schema}"
        })
    
    # Check 3: Hierarchy depth
    max_depth = max([item['level'] for item in cm.bom]) if cm.bom else 0
    if max_depth <= 10:
        validation_results["checks"].append({
            "name": "Hierarchy",
            "status": "pass",
            "message": f"Profondeur acceptable: {max_depth} niveaux"
        })
    else:
        validation_results["checks"].append({
            "name": "Hierarchy",
            "status": "warning",
            "message": f"Hiérarchie profonde: {max_depth} niveaux"
        })
    
    # Check 4: Geometry calculated
    if cm.geometric_props:
        validation_results["checks"].append({
            "name": "Geometry",
            "status": "pass",
            "message": f"{len(cm.geometric_props)} composants analysés"
        })
    else:
        validation_results["checks"].append({
            "name": "Geometry",
            "status": "fail",
            "message": "Propriétés géométriques non calculées"
        })
    
    # Overall status
    fail_count = sum(1 for c in validation_results["checks"] if c["status"] == "fail")
    warning_count = sum(1 for c in validation_results["checks"] if c["status"] == "warning")
    
    if fail_count > 0:
        validation_results["overall_status"] = "fail"
    elif warning_count > 0:
        validation_results["overall_status"] = "warning"
    else:
        validation_results["overall_status"] = "pass"
    
    return {
        "success": True,
        **validation_results
    }


@mcp.tool()
def list_components(file_path: str) -> Dict[str, Any]:
    """Liste tous les composants d'un assemblage STEP avec leurs propriétés
    
    Args:
        file_path: Chemin vers le fichier STEP
        
    Returns:
        Dictionnaire contenant:
        - components: liste des composants avec nom, type, niveau, quantité
        - total_count: nombre total de composants
        - assemblies: nombre d'assemblages
        - parts: nombre de pièces
    """
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    cm = ConfigurationManager(file_path, silent=True)
    cm.build_bom()
    
    components = []
    for item in cm.bom:
        components.append({
            "name": item['name'],
            "type": item['type'],
            "level": item['level'],
            "quantity": item.get('quantity', 1),
            "label_entry": item.get('label_entry', '')
        })
    
    return {
        "success": True,
        "file": file_path,
        "components": components,
        "total_count": len(components),
        "assemblies": len([c for c in components if c['type'] == 'Assembly']),
        "parts": len([c for c in components if c['type'] == 'Part'])
    }


if __name__ == "__main__":
    # Run the FastMCP server
    mcp.run()