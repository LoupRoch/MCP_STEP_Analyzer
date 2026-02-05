#!/usr/bin/env python
"""
Baseline Comparator - Compare two configuration baselines
Détecte les changements entre deux versions d'un produit
"""

import json
import sys
import os
from datetime import datetime
from difflib import unified_diff
import io
from contextlib import redirect_stdout
from config_manager import ConfigurationManager
from collections import Counter


class BaselineComparator:
    """Compare deux baselines de configuration"""
    
    def __init__(self, silent=True):
        """Initialize comparator
        
        Args:
            silent: si True, désactive tous les prints (pour MCP)
        """
        self.silent = silent
        self.baseline1_path = None
        self.baseline2_path = None
        self.baseline1 = None
        self.baseline2 = None
        self._reset_changes()
    
    def _log(self, message):
        """Log a message if not in silent mode"""
        if not self.silent:
            print(message)    
    def _reset_changes(self):
        """Reset changes dictionary"""
        self.changes = {
            'bom': [],
            'geometry': [],
            'metadata': [],
            'differences': [],
            'components_added': [],
            'components_removed': [],
            'components_modified': []
        }        
    def load_baselines(self):
        """Charge les deux baselines (génère si fichiers STEP)"""
        try:
            # Check if files are STEP files
            if self.baseline1_path.endswith('.stp') or self.baseline1_path.endswith('.step'):
                self._log(f"Génération de la baseline pour {self.baseline1_path}...")
                self.baseline1 = self.generate_baseline_from_step(self.baseline1_path)
            else:
                with open(self.baseline1_path, 'r', encoding='utf-8') as f:
                    self.baseline1 = json.load(f)
            
            if self.baseline2_path.endswith('.stp') or self.baseline2_path.endswith('.step'):
                self._log(f"Génération de la baseline pour {self.baseline2_path}...")
                self.baseline2 = self.generate_baseline_from_step(self.baseline2_path)
            else:
                with open(self.baseline2_path, 'r', encoding='utf-8') as f:
                    self.baseline2 = json.load(f)
            
            return True
        except Exception as e:
            self._log(f"Erreur lors du chargement: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_baseline_from_step(self, step_file):
        """Génère une baseline à partir d'un fichier STEP"""
        if not os.path.exists(step_file):
            raise FileNotFoundError(f"Fichier STEP introuvable: {step_file}")
        
        try:
            # Suppress all output during baseline generation
            with redirect_stdout(io.StringIO()):
                cm = ConfigurationManager(step_file, silent=True)
                cm.build_bom()
                cm.analyze_geometry()
                cm.extract_colors()
                cm.build_dependency_graph()
                
            self._log(f"  ✓ Baseline générée pour {step_file}")
            
            # Build baseline data structure
            baseline = {
                'baseline_id': cm.generate_config_id(),
                'timestamp': datetime.now().isoformat(),
                'file': step_file,
                'metadata': cm.metadata,
                'bom': cm.bom,
                'component_registry': cm.components_registry,
                'geometric_properties': cm.geometric_props,
                'colors': cm.colors_registry,
                'dependencies': dict(cm.dependency_graph),
                'checksum': cm.calculate_file_checksum()
            }
            
            return baseline
            
        except Exception as e:
            raise RuntimeError(f"Échec de la génération de baseline pour {step_file}: {e}")
    
    def compare(self):
        """Effectue la comparaison complète"""
        # Validate baselines are loaded
        if self.baseline1 is None or self.baseline2 is None:
            if not self.load_baselines():
                raise RuntimeError("Impossible de charger les baselines")
        
        # Validate baseline structure
        required_keys = ['baseline_id', 'timestamp', 'file', 'checksum', 'bom', 'geometric_properties']
        for key in required_keys:
            if key not in self.baseline1:
                raise ValueError(f"Baseline 1 invalide: clé manquante '{key}'")
            if key not in self.baseline2:
                raise ValueError(f"Baseline 2 invalide: clé manquante '{key}'")
        
        # Reset changes for new comparison
        self._reset_changes()
        
        self._log("="*80)
        self._log("COMPARAISON DE BASELINES DE CONFIGURATION")
        self._log("="*80)
        self._log(f"\nBaseline 1: {self.baseline1['baseline_id']}")
        self._log(f"  Date: {self.baseline1['timestamp']}")
        self._log(f"  Fichier: {self.baseline1['file']}")
        self._log(f"  Checksum: {self.baseline1['checksum'][:16]}...")
        
        self._log(f"\nBaseline 2: {self.baseline2['baseline_id']}")
        self._log(f"  Date: {self.baseline2['timestamp']}")
        self._log(f"  Fichier: {self.baseline2['file']}")
        self._log(f"  Checksum: {self.baseline2['checksum'][:16]}...")
        
        # Check if same file
        if self.baseline1['checksum'] == self.baseline2['checksum']:
            self._log("\n✓ IDENTIQUE - Les fichiers sont identiques (même checksum)")
            return True
        
        # Compare components
        self.compare_bom()
        self.compare_geometry()
        self.compare_topology()
        self.compare_metadata()
        
        # Generate report
        self.generate_report()
        
        return True
    
    def compare_bom(self):
        """Compare les nomenclatures"""
        self._log("\n" + "="*80)
        self._log("1. COMPARAISON BOM")
        self._log("="*80)
        
        bom1_dict = {item['name']: item for item in self.baseline1['bom']}
        bom2_dict = {item['name']: item for item in self.baseline2['bom']}
        
        # Components in baseline1 but not in baseline2 (removed)
        removed = set(bom1_dict.keys()) - set(bom2_dict.keys())
        # Components in baseline2 but not in baseline1 (added)
        added = set(bom2_dict.keys()) - set(bom1_dict.keys())
        # Common components
        common = set(bom1_dict.keys()) & set(bom2_dict.keys())
        
        if removed:
            self._log(f"\n✗ Composants SUPPRIMÉS ({len(removed)}):")
            for comp in sorted(removed):
                comp_data = bom1_dict[comp]
                self._log(f"  - {comp}")
                self.changes['components_removed'].append({
                    'name': comp,
                    'level': comp_data.get('level'),
                    'type': comp_data.get('type'),
                    'label_entry': comp_data.get('label_entry')
                })
        
        if added:
            self._log(f"\n✓ Composants AJOUTÉS ({len(added)}):")
            for comp in sorted(added):
                comp_data = bom2_dict[comp]
                self._log(f"  + {comp}")
                self.changes['components_added'].append({
                    'name': comp,
                    'level': comp_data.get('level'),
                    'type': comp_data.get('type'),
                    'label_entry': comp_data.get('label_entry')
                })
        
        # Check for modifications in common components
        modified = []
        for comp_name in common:
            item1 = bom1_dict[comp_name]
            item2 = bom2_dict[comp_name]
            
            changes_found = []
            if item1.get('level') != item2.get('level'):
                changes_found.append(f"niveau: {item1['level']} → {item2['level']}")
            if item1.get('type') != item2.get('type'):
                changes_found.append(f"type: {item1['type']} → {item2['type']}")
            
            if changes_found:
                modified.append({
                    'name': comp_name,
                    'label_entry': item1.get('label_entry'),
                    'level': item2.get('level'),
                    'type': item2.get('type'),
                    'changes': changes_found
                })
        
        if modified:
            self._log(f"\n⚠ Composants MODIFIÉS ({len(modified)}):")
            for item in modified:
                self._log(f"  ~ {item['name']}")
                for change in item['changes']:
                    self._log(f"      {change}")
                self.changes['components_modified'].append(item)
        
        if not removed and not added and not modified:
            self._log("\n✓ BOM identique")
        
        # Summary
        self._log(f"\nRésumé BOM:")
        self._log(f"  Baseline 1: {len(bom1_dict)} composants")
        self._log(f"  Baseline 2: {len(bom2_dict)} composants")
        self._log(f"  Différence: {len(bom2_dict) - len(bom1_dict):+d}")
    
    def compare_geometry(self):
        """Compare les propriétés géométriques"""
        self._log("\n" + "="*80)
        self._log("2. COMPARAISON GÉOMÉTRIE")
        self._log("="*80)
        
        geom1 = self.baseline1.get('geometric_properties', {})
        geom2 = self.baseline2.get('geometric_properties', {})
        
        if not geom1 or not geom2:
            self._log("  Propriétés géométriques non disponibles")
            return
        
        # Get component registries for more specific names
        comp_reg1 = self.baseline1.get('component_registry', {})
        comp_reg2 = self.baseline2.get('component_registry', {})
        
        # Compare volumes
        for entry, props1 in geom1.items():
            if entry in geom2:
                props2 = geom2[entry]
                
                vol1 = props1.get('volume', 0)
                vol2 = props2.get('volume', 0)
                surf1 = props1.get('surface_area', 0)
                surf2 = props2.get('surface_area', 0)
                
                vol_diff = vol2 - vol1
                surf_diff = surf2 - surf1
                
                if abs(vol_diff) > 0.01 or abs(surf_diff) > 0.01:
                    # Try to get more specific name from component registry
                    component_name = props1['name']
                    if entry in comp_reg1:
                        component_name = comp_reg1[entry].get('name', component_name)
                    
                    # Build full path for lowest-level component
                    full_path = component_name
                    if entry in comp_reg1:
                        parent_entry = comp_reg1[entry].get('parent_entry')
                        path_parts = [component_name]
                        
                        # Walk up the hierarchy to build full path
                        while parent_entry and parent_entry in comp_reg1:
                            parent_name = comp_reg1[parent_entry].get('name', '')
                            if parent_name and parent_name != component_name:
                                path_parts.insert(0, parent_name)
                            parent_entry = comp_reg1[parent_entry].get('parent_entry')
                        
                        # Use format: assembly->subassembly->part
                        if len(path_parts) > 1:
                            full_path = '->'.join(path_parts)
                    
                    self._log(f"\n  {full_path}:")
                    if abs(vol_diff) > 0.01:
                        self._log(f"    Volume: {vol1:.2f} → {vol2:.2f} mm³ ({vol_diff:+.2f})")
                    if abs(surf_diff) > 0.01:
                        self._log(f"    Surface: {surf1:.2f} → {surf2:.2f} mm² ({surf_diff:+.2f})")
                    
                    self.changes['geometry'].append({
                        'component': component_name,
                        'full_path': full_path,
                        'entry': entry,
                        'volume_change': vol_diff,
                        'surface_change': surf_diff,
                        'volume_before': vol1,
                        'volume_after': vol2,
                        'surface_before': surf1,
                        'surface_after': surf2
                    })
        
        if not self.changes['geometry']:
            self._log("  ✓ Propriétés géométriques identiques")
    
    def compare_topology(self):
        """
        Comparaison Topologique Robuste.
        Accepte les doublons et filtre par coordonnées spatiales uniques.
        """
        self._log("\nComparaison Topologique et Spatiale...")
        
        # Initialisation propre de la liste des différences
        if 'differences' not in self.changes:
            self.changes['differences'] = []

        common_components = set(self.baseline1['geometric_properties'].keys()) & \
                            set(self.baseline2['geometric_properties'].keys())
        
        for entry in common_components:
            props1 = self.baseline1['geometric_properties'][entry]
            props2 = self.baseline2['geometric_properties'][entry]
            name = props1['name']
            diffs = []
            
            # 1. Check Encombrement (BBox)
            # On tolère 0.1mm de différence pour éviter le bruit
            d1 = props1.get('bbox', {}).get('dims', [0,0,0])
            d2 = props2.get('bbox', {}).get('dims', [0,0,0])
            
            if abs(d1[0]-d2[0]) > 0.1 or abs(d1[1]-d2[1]) > 0.1 or abs(d1[2]-d2[2]) > 0.1:
                 diffs.append(f"Encombrement: {d1} -> {d2}")

            # 2. Check Trous (Holes)
            h1 = props1.get('features_signature', {}).get('holes', [])
            h2 = props2.get('features_signature', {}).get('holes', [])
            
            # Transformation en SET de tuples (x, y, z, diameter)
            # Cela élimine automatiquement les doublons exacts (même position, même taille)
            set1 = set((h['x'], h['y'], h['z'], h['d']) for h in h1)
            set2 = set((h['x'], h['y'], h['z'], h['d']) for h in h2)
            
            if set1 != set2:
                removed = list(set1 - set2)
                added = list(set2 - set1)
                
                # Mapping intelligent "Suppression vs Modification"
                mapped_changes = []
                
                # On essaie de lier les éléments supprimés aux éléments ajoutés
                # Copie de travail pour 'added'
                work_added = added[:] 
                
                for r in removed:
                    rx, ry, rz, rd = r
                    found = False
                    
                    # Recherche d'un trou au même endroit (Tolérance 0.5mm)
                    for i, a in enumerate(work_added):
                        ax, ay, az, ad = a
                        dist = ((rx-ax)**2 + (ry-ay)**2 + (rz-az)**2)**0.5
                        
                        if dist < 0.5: # Même position
                            mapped_changes.append(f"Ø Modifié @({rx},{ry}): {rd} -> {ad}")
                            work_added.pop(i)
                            found = True
                            break
                    
                    if not found:
                        # Recherche d'un trou de même taille déplacé
                        for i, a in enumerate(work_added):
                            ax, ay, az, ad = a
                            if rd == ad: # Même diamètre
                                mapped_changes.append(f"Déplacé (Ø{rd}): vers ({ax},{ay})")
                                work_added.pop(i)
                                found = True
                                break
                                
                    if not found:
                        mapped_changes.append(f"Supprimé Ø{rd} @({rx},{ry})")
                
                # Ce qui reste dans work_added sont les vrais ajouts
                for a in work_added:
                    mapped_changes.append(f"Ajouté Ø{a[3]} @({a[0]},{a[1]})")
                
                if mapped_changes:
                    # On limite l'affichage à 5 messages pour ne pas saturer le rapport si gros assemblage
                    if len(mapped_changes) > 10:
                        preview = " | ".join(mapped_changes[:5])
                        diffs.append(f"{preview} ... (+{len(mapped_changes)-5} autres)")
                    else:
                        diffs.append(" | ".join(mapped_changes))

            if diffs:
                change_desc = f"{name}: " + " | ".join(diffs)
                self.changes['differences'].append({
                    'component': name,
                    'entry': entry,
                    'differences': diffs,
                    'description': change_desc
                })
                self._log(f"  ⚠ {change_desc}")

    def compare_metadata(self):
        """Compare les métadonnées"""
        self._log("\n" + "="*80)
        self._log("3. COMPARAISON MÉTADONNÉES")
        self._log("="*80)
        
        meta1 = self.baseline1.get('metadata', {})
        meta2 = self.baseline2.get('metadata', {})
        
        # Compare schema
        schema1 = meta1.get('schema', '')
        schema2 = meta2.get('schema', '')
        
        if schema1 != schema2:
            self._log(f"  Schéma STEP: {schema1} → {schema2}")
            self.changes['metadata'].append(f"Schéma: {schema1} → {schema2}")
        else:
            self._log(f"  ✓ Schéma STEP identique: {schema1}")
        
        # Compare products
        prods1 = {p['name']: p for p in meta1.get('products', [])}
        prods2 = {p['name']: p for p in meta2.get('products', [])}
        
        prod_added = set(prods2.keys()) - set(prods1.keys())
        prod_removed = set(prods1.keys()) - set(prods2.keys())
        
        if prod_added:
            self._log(f"\n  Produits ajoutés: {', '.join(prod_added)}")
        if prod_removed:
            self._log(f"  Produits supprimés: {', '.join(prod_removed)}")
        
        if not prod_added and not prod_removed and schema1 == schema2:
            self._log("  ✓ Métadonnées identiques")
    
    def generate_report(self):
        """Génère le rapport de changements avec catégorisation avancée (CM)"""
        self._log("\n" + "="*80)
        self._log("RÉSUMÉ DES CHANGEMENTS (Analyse d'Impact)")
        self._log("="*80)
        
        # Recalcul des compteurs basé sur la nouvelle structure
        # On utilise .get() pour éviter les erreurs si une clé est vide
        total_changes = (len(self.changes.get('components_added', [])) +
                        len(self.changes.get('components_removed', [])) +
                        len(self.changes.get('components_modified', [])) +
                        len(self.changes.get('differences', [])) + 
                        len(self.changes.get('metadata', [])))
        
        if total_changes == 0:
            self._log("\n✓ AUCUN CHANGEMENT DÉTECTÉ")
            return

        # --- CLASSIFICATION DES IMPACTS ---
        clash_alerts = []      # Problème d'encombrement
        interface_alerts = []  # Déplacements / Suppressions de trous
        functional_alerts = [] # Changement de Diamètre
        volume_alerts = []     # Juste changement de masse

        # Analyse sémantique des différences générées
        # On parcourt la liste 'differences' générée par compare_topology
        for item in self.changes.get('differences', []):
            comp_name = item['component']
            for diff in item['differences']:
                msg = f"{comp_name}: {diff}"
                
                if "Encombrement" in diff:
                    clash_alerts.append(msg)
                elif "Déplacé" in diff or "Supprimé" in diff: 
                    # Supprimer un trou ou le bouger = Interface rompue
                    interface_alerts.append(msg)
                elif "Ø Modifié" in diff or "Ajouté" in diff:
                    # Changer un diamètre = Changement fonctionnel (vis)
                    functional_alerts.append(msg)
                else:
                    # Changement de volume simple sans détail topologique
                    volume_alerts.append(msg)

        # --- AFFICHAGE LOGS POUR LE CLIENT MCP ---
        self._log(f"\n⚠ TOTAL: {total_changes} changement(s)")
        
        # On affiche d'abord les ajouts/suppressions de composants (impact BOM)
        if self.changes.get('components_removed'):
            self._log(f"\n[!!!] ALERTE BOM (Composants supprimés): {len(self.changes['components_removed'])}")
        
        # Ensuite les impacts géométriques critiques
        if clash_alerts:
            self._log(f"\n[!!!] ALERTE ENCOMBREMENT (Risque Clash): {len(clash_alerts)}")
            for msg in clash_alerts: self._log(f"  ► {msg}")
            
        if interface_alerts:
            self._log(f"\n[!!] ALERTE INTERFACE (Montage impossible): {len(interface_alerts)}")
            for msg in interface_alerts: self._log(f"  ► {msg}")
            
        if functional_alerts:
            self._log(f"\n[!] ALERTE FONCTIONNELLE (Fixations): {len(functional_alerts)}")
            for msg in functional_alerts: self._log(f"  ► {msg}")

        # Calcul du score d'impact global pour le JSON
        impact_score = "NONE"
        if self.changes.get('components_removed'): impact_score = "CRITICAL_MISSING_PART"
        elif clash_alerts: impact_score = "CRITICAL_CLASH"
        elif interface_alerts: impact_score = "CRITICAL_INTERFACE"
        elif functional_alerts: impact_score = "MAJOR_FUNCTIONAL"
        elif volume_alerts: impact_score = "MINOR_GEOMETRY"
        elif self.changes.get('components_added'): impact_score = "MAJOR_BOM"

        # Construction du rapport final
        report_filename = f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            'baseline1': self.baseline1.get('baseline_id', 'Unknown'),
            'baseline2': self.baseline2.get('baseline_id', 'Unknown'),
            'comparison_date': datetime.now().isoformat(),
            'impact_assessment': impact_score,
            'summary': {
                'total_changes': total_changes,
                'clash_count': len(clash_alerts),
                'interface_issues': len(interface_alerts),
                'functional_changes': len(functional_alerts)
            },
            'alerts': {
                'clash': clash_alerts,
                'interface': interface_alerts,
                'functional': functional_alerts,
                'volume': volume_alerts
            },
            'raw_changes': self.changes
        }
            
        # Sauvegarde
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self._log(f"\n✓ Rapport de comparaison sauvegardé: {report_filename}")


def main():
    """Point d'entrée principal"""
    if len(sys.argv) < 3:
        print("Usage: python baseline_comparator.py <fichier1> <fichier2>")
        print("")
        print("Les fichiers peuvent être:")
        print("  - Des fichiers JSON de baseline (config_baseline_*.json)")
        print("  - Des fichiers STEP (.stp ou .step)")
        print("")
        print("Exemples:")
        print("  python baseline_comparator.py baseline1.json baseline2.json")
        print("  python baseline_comparator.py product_v1.stp product_v2.stp")
        print("  python baseline_comparator.py baseline1.json product_v2.stp")
        sys.exit(1)
    
    baseline1 = sys.argv[1]
    baseline2 = sys.argv[2]
    
    # Check files exist
    if not os.path.exists(baseline1):
        print(f"Erreur: Le fichier '{baseline1}' n'existe pas")
        sys.exit(1)
    
    if not os.path.exists(baseline2):
        print(f"Erreur: Le fichier '{baseline2}' n'existe pas")
        sys.exit(1)
    
    comparator = BaselineComparator(baseline1, baseline2)
    comparator.compare()
    
    print("\n" + "="*80)
    print("COMPARAISON TERMINÉE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
