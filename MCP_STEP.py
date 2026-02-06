#!/usr/bin/env python
"""
MCP Server for STEP File Analysis and Comparison
Serveur MCP pour l'analyse et la comparaison de fichiers STEP

Utiliser avec le serveur MCP Filesystem pour accéder aux fichiers depuis Claude Desktop
"""

import json
import os
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastmcp import FastMCP

# Import existing analyzers
from config_manager import ConfigurationManager
from baseline_comparator import BaselineComparator

# Create FastMCP server
mcp = FastMCP("STEP Analyzer", version="2.0.0")


# ============================================================================
# UTILITY FUNCTIONS FOR FILE HANDLING
# ============================================================================

def _validate_file_path(file_path: str) -> str:
    """Validate file path exists and has correct extension
    
    Args:
        file_path: Path to STEP file (local or Docker volume mounted)
        
    Returns:
        Validated file path
        
    Raises:
        FileNotFoundError: If file not found
        ValueError: If invalid file extension
    """
    if not file_path:
        raise ValueError(
            "Vous devez fournir 'file_path'. "
            "Utilisez le serveur MCP filesystem pour accéder à vos fichiers."
        )
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Fichier introuvable: {file_path}\n"
            f"Vérifiez que le volume Docker est correctement monté ou que le fichier existe."
        )
    
    if not (file_path.lower().endswith('.stp') or file_path.lower().endswith('.step')):
        raise ValueError(f"Extension invalide. Attendu .stp ou .step, reçu: {file_path}")
    
    return file_path


# ============================================================================
# CORE ANALYSIS TOOLS
# ============================================================================

@mcp.tool()
def analyze_step_file(file_path: str) -> Dict[str, Any]:
    """Analyse complète d'un fichier STEP : métadonnées, structure et géométrie
    
    Retourne toutes les informations essentielles sur le fichier STEP incluant
    la nomenclature (BOM), les propriétés géométriques et topologiques, les
    métadonnées du fichier et le graphe de dépendances.
    
    Utilisez le serveur MCP filesystem pour lister et accéder à vos fichiers.
    
    Args:
        file_path: Chemin vers le fichier STEP à analyser (ex: /workspace/step/product.stp)
        
    Returns:
        Dictionnaire structuré contenant:
        - metadata: informations du header STEP (schéma, auteur, date)
        - bom: nomenclature hiérarchique des composants
        - components: registre détaillé des composants avec instances
        - geometry: propriétés géométriques (volume, surface, bbox, features)
        - dependencies: graphe de dépendances entre composants
        - validation: résultat des vérifications de conformité
    """
    try:
        # Resolve and validate file path
        resolved_path = _validate_file_path(file_path)
        
        # Create configuration manager in silent mode
        cm = ConfigurationManager(resolved_path, silent=True)
        
        # Perform all analyses
        cm.build_bom()
        cm.analyze_geometry()
        cm.extract_colors()
        cm.build_dependency_graph()
        
        # Validation checks
        validation = _perform_validation(cm)
        
        # Calculate totals
        total_volume = sum(p.get('volume', 0) for p in cm.geometric_props.values())
        total_surface = sum(p.get('surface_area', 0) for p in cm.geometric_props.values())
        
        return {
            "file": file_path or "fichier_joint",
            "checksum": cm.calculate_file_checksum(),
            "analyzed_at": datetime.now().isoformat(),
            
            "metadata": {
                "description": cm.metadata.get('description'),
                "schema": cm.metadata.get('schema'),
                "timestamp": cm.metadata.get('timestamp'),
                "author": cm.metadata.get('author'),
                "products": cm.metadata.get('products', [])
            },
            
            "bom": {
                "items": cm.bom,
                "total_count": len(cm.bom),
                "max_depth": max([item['level'] for item in cm.bom]) if cm.bom else 0
            },
            
            "components": {
                "registry": cm.components_registry,
                "total_unique": len(cm.components_registry)
            },
            
            "geometry": {
                "properties": cm.geometric_props,
                "totals": {
                    "volume_mm3": round(total_volume, 2),
                    "surface_mm2": round(total_surface, 2)
                }
            },
            
            "colors": cm.colors_registry,
            
            "dependencies": dict(cm.dependency_graph),
            
            "validation": validation
        }
    except Exception as e:
        raise ValueError(f"Erreur lors de l'analyse du fichier STEP: {e}")


@mcp.tool()
def compare_step_files(file1_path: str, file2_path: str) -> Dict[str, Any]:
    """Compare deux fichiers STEP et détecte les différences critiques
    
    Effectue une comparaison détaillée incluant l'analyse d'impact pour
    détecter les risques de collision (clash), les problèmes d'assemblage
    et les changements fonctionnels. Inclut également l'analyse des interfaces.
    
    Utilisez le serveur MCP filesystem pour lister et accéder à vos fichiers.
    
    Args:
        file1_path: Chemin vers le premier fichier STEP (ex: /workspace/step/v1.stp)
        file2_path: Chemin vers le second fichier STEP (ex: /workspace/step/v2.stp)
        
    Returns:
        Dictionnaire contenant:
        - baselines: IDs et checksums des deux versions
        - impact: analyse d'impact avec niveaux de sévérité
        - changes: différences détaillées (BOM, géométrie, topologie, interfaces)
        - summary: statistiques des changements
    """
    try:
        # Resolve and validate both file paths
        resolved_path1 = _validate_file_path(file1_path)
        resolved_path2 = _validate_file_path(file2_path)
        
        comparator = BaselineComparator(silent=True)
        
        # Suppress output during baseline generation
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            baseline1 = comparator.generate_baseline_from_step(resolved_path1)
            baseline2 = comparator.generate_baseline_from_step(resolved_path2)
            
            comparator.baseline1 = baseline1
            comparator.baseline2 = baseline2
            comparator.compare()
        
        # Analyser les interfaces pour les deux versions
        cm1 = ConfigurationManager(resolved_path1, silent=True)
        cm1.analyze_geometry()
        interfaces1 = cm1.analyze_interfaces()
        
        cm2 = ConfigurationManager(resolved_path2, silent=True)
        cm2.analyze_geometry()
        interfaces2 = cm2.analyze_interfaces()
        
        # Comparer les interfaces
        interface_changes = _compare_interfaces(interfaces1, interfaces2)
        
        # Analyze impact (incluant interfaces)
        impact_analysis = _analyze_impact(comparator.changes, interface_changes)
        
        return {
            "baselines": {
                "baseline1": {
                    "id": baseline1.get('baseline_id'),
                    "file": file1_path or "fichier_joint",
                    "checksum": baseline1.get('checksum'),
                    "timestamp": baseline1.get('timestamp')
                },
                "baseline2": {
                    "id": baseline2.get('baseline_id'),
                    "file": file2_path or "fichier_joint",
                    "checksum": baseline2.get('checksum'),
                    "timestamp": baseline2.get('timestamp')
                }
            },
            
            "impact": impact_analysis,
            
            "changes": {
                "bom": {
                    "added": comparator.changes.get('components_added', []),
                    "removed": comparator.changes.get('components_removed', []),
                    "modified": comparator.changes.get('components_modified', [])
                },
                "geometry": comparator.changes.get('geometry', []),
                "topology": comparator.changes.get('differences', []),
                "metadata": comparator.changes.get('metadata', []),
                "interfaces": interface_changes
            },
            
            "summary": {
                "total_changes": (
                    len(comparator.changes.get('components_added', [])) +
                    len(comparator.changes.get('components_removed', [])) +
                    len(comparator.changes.get('components_modified', [])) +
                    len(comparator.changes.get('differences', [])) +
                    len(interface_changes.get('added', [])) +
                    len(interface_changes.get('removed', [])) +
                    len(interface_changes.get('modified', []))
                ),
                "components_added": len(comparator.changes.get('components_added', [])),
                "components_removed": len(comparator.changes.get('components_removed', [])),
                "geometry_changes": len(comparator.changes.get('differences', [])),
                "interface_changes": len(interface_changes.get('added', [])) + 
                                    len(interface_changes.get('removed', [])) + 
                                    len(interface_changes.get('modified', []))
            }
        }
    except Exception as e:
        raise ValueError(f"Erreur lors de la comparaison: {e}")


# ============================================================================
# SPECIALIZED QUERY TOOLS
# ============================================================================

@mcp.tool()
def extract_bom(file_path: str) -> List[Dict[str, Any]]:
    """Extrait uniquement la nomenclature (Bill of Materials) d'un fichier STEP
    
    Retourne une liste structurée des composants sans les propriétés
    géométriques ni les analyses supplémentaires.
    
    Args:
        file_path: Chemin vers le fichier STEP (ex: /workspace/step/product.stp)
        
    Returns:
        Liste des composants avec position, niveau, quantité, nom et type
    """
    try:
        resolved_path = _validate_file_path(file_path)
        
        cm = ConfigurationManager(resolved_path, silent=True)
        cm.build_bom()
        
        return cm.bom
    except Exception as e:
        raise ValueError(f"Erreur lors de l'extraction de la BOM: {e}")


@mcp.tool()
def extract_geometry(
    file_path: str,
    component_name: Optional[str] = None
) -> Dict[str, Any]:
    """Extrait les propriétés géométriques d'un fichier STEP
    
    Retourne les propriétés géométriques et topologiques pour tous les
    composants ou pour un composant spécifique.
    
    Args:
        file_path: Chemin vers le fichier STEP (ex: /workspace/step/product.stp)
        component_name: Nom du composant spécifique (optionnel)
                       Peut être le nom simple ('beak') ou le chemin complet ('jasper_v13 > beak')
        
    Returns:
        Dictionnaire avec propriétés par composant et totaux agrégés
    """
    try:
        resolved_path = _validate_file_path(file_path)
        
        cm = ConfigurationManager(resolved_path, silent=True)
        cm.analyze_geometry()
        
        # Filter by component if specified
        if component_name:
            # Chercher par nom simple ou nom unique/chemin
            filtered = {
                k: v for k, v in cm.geometric_props.items()
                if v.get('name') == component_name or 
                   v.get('unique_name') == component_name or
                   v.get('path') == component_name
            }
            if not filtered:
                # Construire message d'erreur avec suggestions
                available_names = set()
                for props in cm.geometric_props.values():
                    available_names.add(props.get('name'))
                    if props.get('unique_name') != props.get('name'):
                        available_names.add(props.get('unique_name'))
                
                suggestions = sorted(available_names)[:10]
                raise ValueError(
                    f"Composant '{component_name}' introuvable.\n"
                    f"Composants disponibles: {', '.join(suggestions)}"
                    + (f"\n... et {len(available_names) - 10} autres" if len(available_names) > 10 else "")
                )
            return {"components": filtered}
        
        # Calculate totals
        total_volume = sum(p.get('volume', 0) for p in cm.geometric_props.values())
        total_surface = sum(p.get('surface_area', 0) for p in cm.geometric_props.values())
        
        return {
            "components": cm.geometric_props,
            "totals": {
                "volume_mm3": round(total_volume, 2),
                "surface_mm2": round(total_surface, 2),
                "component_count": len(cm.geometric_props)
            }
        }
    except Exception as e:
        raise ValueError(f"Erreur lors de l'extraction de la géométrie: {e}")


@mcp.tool()
def validate_step_file(file_path: str) -> Dict[str, Any]:
    """Valide la conformité d'un fichier STEP selon les standards industriels
    
    Effectue une série de vérifications sur le fichier STEP pour détecter
    les problèmes de conformité, les incohérences et les avertissements.
    
    Args:
        file_path: Chemin vers le fichier STEP (ex: /workspace/step/product.stp)
        
    Returns:
        Dictionnaire avec statut global et détails des vérifications
    """
    try:
        resolved_path = _validate_file_path(file_path)
        
        cm = ConfigurationManager(resolved_path, silent=True)
        cm.build_bom()
        cm.analyze_geometry()
        
        return _perform_validation(cm)
    except Exception as e:
        raise ValueError(f"Erreur lors de la validation: {e}")


@mcp.tool()
def analyze_interfaces(file_path: str) -> Dict[str, Any]:
    """Analyse les interfaces et liaisons entre composants d'un assemblage STEP
    
    Détecte automatiquement les types de liaisons mécaniques entre composants :
    - Vissages/boulonnages : trous alignés avec même diamètre
    - Encastrements/contacts : surfaces en contact ou proximité immédiate
    - Proximité : composants proches pouvant interagir
    
    Cette analyse est essentielle pour la gestion de configuration car elle
    identifie les points critiques d'assemblage qui peuvent être impactés
    par des modifications géométriques.
    
    Args:
        file_path: Chemin vers le fichier STEP (ex: /workspace/step/product.stp)
        
    Returns:
        Dictionnaire contenant:
        - interfaces: liste détaillée de toutes les interfaces détectées
        - summary: statistiques par type d'interface
        - critical_joints: interfaces critiques (vissages) nécessitant attention
        - assembly_graph: graphe des connexions entre composants
    """
    try:
        resolved_path = _validate_file_path(file_path)
        
        cm = ConfigurationManager(resolved_path, silent=True)
        cm.build_bom()
        cm.analyze_geometry()
        interfaces = cm.analyze_interfaces()
        
        # Grouper par type
        from collections import defaultdict
        by_type = defaultdict(list)
        for iface in interfaces:
            by_type[iface['type']].append(iface)
        
        # Identifier les interfaces critiques (vissages)
        critical_joints = [
            iface for iface in interfaces 
            if iface['type'] == 'fastening'
        ]
        
        # Construire le graphe d'assemblage
        assembly_graph = {}
        for iface in interfaces:
            comp1 = iface['component1']
            comp2 = iface['component2']
            
            if comp1 not in assembly_graph:
                assembly_graph[comp1] = []
            if comp2 not in assembly_graph:
                assembly_graph[comp2] = []
            
            assembly_graph[comp1].append({
                'connected_to': comp2,
                'type': iface['type'],
                'severity': iface['severity']
            })
            assembly_graph[comp2].append({
                'connected_to': comp1,
                'type': iface['type'],
                'severity': iface['severity']
            })
        
        return {
            "file": file_path or "fichier_joint",
            "analyzed_at": datetime.now().isoformat(),
            
            "interfaces": interfaces,
            
            "summary": {
                "total_interfaces": len(interfaces),
                "by_type": {
                    "fastening": len(by_type['fastening']),
                    "contact": len(by_type['contact']),
                    "proximity": len(by_type['proximity'])
                },
                "by_severity": {
                    "critical": sum(1 for i in interfaces if i['severity'] == 'critical'),
                    "major": sum(1 for i in interfaces if i['severity'] == 'major'),
                    "minor": sum(1 for i in interfaces if i['severity'] == 'minor')
                }
            },
            
            "critical_joints": critical_joints,
            
            "assembly_graph": assembly_graph,
            
            "recommendations": _generate_interface_recommendations(interfaces)
        }
    except Exception as e:
        raise ValueError(f"Erreur lors de l'analyse des interfaces: {e}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _perform_validation(cm: ConfigurationManager) -> Dict[str, Any]:
    """Effectue les vérifications de validation"""
    checks = []
    
    # Check 1: Metadata
    if cm.metadata:
        checks.append({
            "name": "metadata",
            "status": "pass",
            "message": "Métadonnées présentes et valides"
        })
    else:
        checks.append({
            "name": "metadata",
            "status": "warning",
            "message": "Métadonnées manquantes ou incomplètes"
        })
    
    # Check 2: Schema
    valid_schemas = ['CONFIG_CONTROL_DESIGN', 'AUTOMOTIVE_DESIGN', 'AP203', 'AP214']
    schema = cm.metadata.get('schema', '')
    if any(s in schema for s in valid_schemas):
        checks.append({
            "name": "schema",
            "status": "pass",
            "message": f"Schéma STEP valide: {schema}"
        })
    else:
        checks.append({
            "name": "schema",
            "status": "warning",
            "message": f"Schéma STEP non standard: {schema}"
        })
    
    # Check 3: Hierarchy depth
    max_depth = max([item['level'] for item in cm.bom]) if cm.bom else 0
    if max_depth <= 10:
        checks.append({
            "name": "hierarchy",
            "status": "pass",
            "message": f"Profondeur hiérarchique acceptable: {max_depth} niveaux"
        })
    else:
        checks.append({
            "name": "hierarchy",
            "status": "warning",
            "message": f"Hiérarchie excessive: {max_depth} niveaux"
        })
    
    # Check 4: Components named
    unnamed = [item for item in cm.bom if not item['name'] or item['name'].strip() == '']
    if unnamed:
        checks.append({
            "name": "naming",
            "status": "fail",
            "message": f"{len(unnamed)} composants sans nom"
        })
    else:
        checks.append({
            "name": "naming",
            "status": "pass",
            "message": "Tous les composants sont nommés"
        })
    
    # Check 5: Geometry
    if cm.geometric_props:
        checks.append({
            "name": "geometry",
            "status": "pass",
            "message": f"{len(cm.geometric_props)} composants avec propriétés géométriques"
        })
    else:
        checks.append({
            "name": "geometry",
            "status": "fail",
            "message": "Propriétés géométriques non calculées"
        })
    
    # Check 6: Duplicate names
    from collections import defaultdict
    name_counts = defaultdict(int)
    for item in cm.bom:
        name_counts[item['name']] += 1
    duplicates = {name: count for name, count in name_counts.items() if count > 1}
    
    if duplicates:
        checks.append({
            "name": "duplicates",
            "status": "warning",
            "message": f"{len(duplicates)} noms de composants dupliqués"
        })
    else:
        checks.append({
            "name": "duplicates",
            "status": "pass",
            "message": "Pas de noms dupliqués"
        })
    
    # Overall status
    fail_count = sum(1 for c in checks if c["status"] == "fail")
    warning_count = sum(1 for c in checks if c["status"] == "warning")
    
    if fail_count > 0:
        overall_status = "fail"
        overall_message = f"{fail_count} vérification(s) échouée(s)"
    elif warning_count > 0:
        overall_status = "warning"
        overall_message = f"{warning_count} avertissement(s)"
    else:
        overall_status = "pass"
        overall_message = "Toutes les vérifications réussies"
    
    return {
        "overall_status": overall_status,
        "overall_message": overall_message,
        "checks": checks,
        "statistics": {
            "total_checks": len(checks),
            "passed": sum(1 for c in checks if c["status"] == "pass"),
            "warnings": warning_count,
            "failures": fail_count
        }
    }


def _analyze_impact(changes: Dict[str, List], interface_changes: Dict = None) -> Dict[str, Any]:
    """Analyse l'impact des changements détectés"""
    impact_report = {
        "clash_risks": [],
        "assembly_risks": [],
        "retrofit_risks": [],
        "bom_changes": [],
        "interface_risks": []
    }
    
    # Analyze topology differences
    for item in changes.get('differences', []):
        comp = item['component']
        for diff in item['differences']:
            if "Encombrement" in diff:
                impact_report["clash_risks"].append({
                    "component": comp,
                    "issue": diff,
                    "severity": "critical"
                })
            elif "Déplacé" in diff or "Supprimé" in diff:
                impact_report["assembly_risks"].append({
                    "component": comp,
                    "issue": diff,
                    "severity": "critical"
                })
            elif "Ø Modifié" in diff:
                impact_report["retrofit_risks"].append({
                    "component": comp,
                    "issue": diff,
                    "severity": "major"
                })
    
    # Analyze BOM changes
    if changes.get('components_removed'):
        for comp in changes['components_removed']:
            impact_report["bom_changes"].append({
                "type": "removed",
                "component": comp['name'],
                "severity": "critical"
            })
    
    if changes.get('components_added'):
        for comp in changes['components_added']:
            impact_report["bom_changes"].append({
                "type": "added",
                "component": comp['name'],
                "severity": "major"
            })
    
    # Analyze interface changes
    if interface_changes:
        for iface in interface_changes.get('removed', []):
            if iface['type'] == 'fastening':
                impact_report["interface_risks"].append({
                    "type": "removed_fastening",
                    "components": f"{iface['component1']} ↔ {iface['component2']}",
                    "issue": f"Fixation supprimée ({iface['fastener_count']} vis Ø{iface['fastener_diameter']}mm)",
                    "severity": "critical"
                })
            else:
                impact_report["interface_risks"].append({
                    "type": "removed_interface",
                    "components": f"{iface['component1']} ↔ {iface['component2']}",
                    "issue": f"Interface {iface['type']} supprimée",
                    "severity": "major"
                })
        
        for iface in interface_changes.get('modified', []):
            impact_report["interface_risks"].append({
                "type": "modified_interface",
                "components": f"{iface['component1']} ↔ {iface['component2']}",
                "issue": iface['change_description'],
                "severity": "major" if iface['type'] == 'fastening' else "minor"
            })
    
    # Determine overall impact level
    if impact_report["interface_risks"]:
        critical_interface = any(
            risk['severity'] == 'critical' 
            for risk in impact_report["interface_risks"]
        )
        if critical_interface:
            impact_level = "critical_interface"
            impact_message = "Modifications critiques des interfaces d'assemblage"
        elif impact_report["clash_risks"]:
            impact_level = "critical_clash"
            impact_message = "Risques de collision détectés"
        else:
            impact_level = "major_interface"
            impact_message = "Modifications des interfaces d'assemblage"
    elif impact_report["clash_risks"]:
        impact_level = "critical_clash"
        impact_message = "Risques de collision détectés"
    elif impact_report["assembly_risks"]:
        impact_level = "critical_assembly"
        impact_message = "Problèmes d'assemblage détectés"
    elif changes.get('components_removed'):
        impact_level = "critical_missing"
        impact_message = "Composants manquants"
    elif impact_report["retrofit_risks"]:
        impact_level = "major_retrofit"
        impact_message = "Modifications fonctionnelles majeures"
    elif changes.get('components_added'):
        impact_level = "major_bom"
        impact_message = "Ajouts significatifs à la BOM"
    elif changes.get('differences'):
        impact_level = "minor_geometry"
        impact_message = "Changements géométriques mineurs"
    else:
        impact_level = "none"
        impact_message = "Aucun changement significatif"
    
    return {
        "level": impact_level,
        "message": impact_message,
        "details": impact_report,
        "statistics": {
            "clash_risks": len(impact_report["clash_risks"]),
            "assembly_risks": len(impact_report["assembly_risks"]),
            "retrofit_risks": len(impact_report["retrofit_risks"]),
            "bom_changes": len(impact_report["bom_changes"]),
            "interface_risks": len(impact_report["interface_risks"])
        }
    }


def _compare_interfaces(interfaces1: List[Dict], interfaces2: List[Dict]) -> Dict[str, List]:
    """Compare deux listes d'interfaces pour détecter ajouts, suppressions et modifications"""
    def make_key(iface):
        comps = sorted([iface['component1'], iface['component2']])
        return f"{comps[0]}||{comps[1]}||{iface['type']}"
    
    ifaces1_dict = {make_key(iface): iface for iface in interfaces1}
    ifaces2_dict = {make_key(iface): iface for iface in interfaces2}
    
    keys1 = set(ifaces1_dict.keys())
    keys2 = set(ifaces2_dict.keys())
    
    added = [ifaces2_dict[key] for key in (keys2 - keys1)]
    removed = [ifaces1_dict[key] for key in (keys1 - keys2)]
    
    modified = []
    for key in (keys1 & keys2):
        iface1 = ifaces1_dict[key]
        iface2 = ifaces2_dict[key]
        changes = []
        
        if iface1['type'] == 'fastening':
            if iface1['fastener_count'] != iface2['fastener_count']:
                changes.append(
                    f"Nombre de fixations: {iface1['fastener_count']} → {iface2['fastener_count']}"
                )
            if iface1['fastener_diameter'] != iface2['fastener_diameter']:
                changes.append(
                    f"Diamètre: Ø{iface1['fastener_diameter']}mm → Ø{iface2['fastener_diameter']}mm"
                )
        
        if iface1['type'] in ['contact', 'proximity']:
            dist1 = iface1.get('distance', 0)
            dist2 = iface2.get('distance', 0)
            if abs(dist1 - dist2) > 1.0:
                changes.append(
                    f"Distance: {dist1:.1f}mm → {dist2:.1f}mm"
                )
        
        if changes:
            modified.append({
                **iface2,
                'change_description': '; '.join(changes),
                'previous_state': iface1
            })
    
    return {
        'added': added,
        'removed': removed,
        'modified': modified
    }


def _generate_interface_recommendations(interfaces: List[Dict]) -> List[str]:
    """Génère des recommandations basées sur l'analyse des interfaces"""
    recommendations = []
    
    fastening_count = sum(1 for i in interfaces if i['type'] == 'fastening')
    if fastening_count == 0:
        recommendations.append(
            "⚠️ Aucune fixation détectée. Vérifier que l'assemblage est correctement contraint."
        )
    elif fastening_count < 3:
        recommendations.append(
            f"⚠️ Seulement {fastening_count} interface(s) de fixation. "
            "Considérer d'ajouter des points de fixation pour la rigidité."
        )
    
    from collections import defaultdict
    comp_fasteners = defaultdict(int)
    for iface in interfaces:
        if iface['type'] == 'fastening':
            comp_fasteners[iface['component1']] += 1
            comp_fasteners[iface['component2']] += 1
    
    critical_comps = {comp: count for comp, count in comp_fasteners.items() if count >= 3}
    if critical_comps:
        recommendations.append(
            f"🔧 Composants critiques (≥3 fixations): {', '.join(list(critical_comps.keys())[:3])}"
        )
    
    all_comps = set()
    for iface in interfaces:
        all_comps.add(iface['component1'])
        all_comps.add(iface['component2'])
    
    fastened_comps = set(comp_fasteners.keys())
    isolated_comps = all_comps - fastened_comps
    
    if isolated_comps and len(isolated_comps) <= 5:
        recommendations.append(
            f"⚠️ Composants sans fixation directe: {', '.join(list(isolated_comps)[:3])}"
        )
    
    diameters = set()
    for iface in interfaces:
        if iface['type'] == 'fastening':
            diameters.add(iface['fastener_diameter'])
    
    if len(diameters) > 3:
        recommendations.append(
            f"💡 {len(diameters)} diamètres de vis différents utilisés. "
            "Considérer la standardisation pour réduire la variété."
        )
    
    if not recommendations:
        recommendations.append("✅ Configuration d'assemblage cohérente détectée.")
    
    return recommendations


if __name__ == "__main__":
    mcp.run()