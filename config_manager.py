#!/usr/bin/env python
"""
Configuration Management Analyzer for STEP Files
Analyse de gestion de configuration pour objets industriels
"""
import os
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.TopAbs import TopAbs_SOLID, TopAbs_COMPOUND
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPCAFControl import STEPCAFControl_Reader
from OCC.Core.TDF import TDF_Label, TDF_LabelSequence, TDF_Tool
from OCC.Core.TCollection import TCollection_AsciiString
from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.XCAFDoc import XCAFDoc_DocumentTool
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.Quantity import Quantity_Color
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
import re
import json
from datetime import datetime
from collections import defaultdict
import hashlib


class ConfigurationManager:
    """Gestionnaire de configuration pour produits industriels au format STEP"""
    
    def __init__(self, filename, silent=False):
        """Initialize avec un fichier STEP
        
        Args:
            filename: chemin vers le fichier STEP
            silent: si True, désactive tous les prints (pour MCP)
        """
        self.fname = filename
        self.silent = silent
        self.doc = None
        self.shape_tool = None
        self.color_tool = None
        self.bom = []  # Bill of Materials
        self.components_registry = {}  # Registre des composants
        self.metadata = {}
        self.geometric_props = {}
        self.dependency_graph = defaultdict(list)
        self.colors_registry = {}
        self.materials_registry = {}
        self.interfaces = []  # Interfaces entre composants
        
        # Load file
        self.load_file()
    
    def _log(self, message):
        """Log a message if not in silent mode"""
        if not self.silent:
            print(message)
        
    def load_file(self):
        """Charge le fichier STEP"""
        # Validate file exists
        if not os.path.exists(self.fname):
            raise FileNotFoundError(f"Fichier STEP introuvable: {self.fname}")
        
        # Validate file extension
        if not (self.fname.lower().endswith('.stp') or self.fname.lower().endswith('.step')):
            raise ValueError(f"Extension de fichier invalide. Attendu .stp ou .step, reçu: {self.fname}")
        
        try:
            # Create document
            self.doc = TDocStd_Document("pythonocc-config-manager")
            self.shape_tool = XCAFDoc_DocumentTool.ShapeTool(self.doc.Main())
            self.color_tool = XCAFDoc_DocumentTool.ColorTool(self.doc.Main())
            self.shape_tool.SetAutoNaming(True)
            
            # Read STEP file
            step_reader = STEPCAFControl_Reader()
            step_reader.SetColorMode(True)
            step_reader.SetLayerMode(True)
            step_reader.SetNameMode(True)
            step_reader.SetMatMode(True)
            
            status = step_reader.ReadFile(self.fname)
            if status == IFSelect_RetDone:
                step_reader.Transfer(self.doc)
                self._log(f"✓ Fichier '{self.fname}' chargé avec succès\n")
            else:
                raise RuntimeError(f"Échec du chargement du fichier STEP. Status: {status}")
                
            # Extract metadata
            self.extract_file_metadata()
            return True
            
        except Exception as e:
            self._log(f"✗ Exception: {e}")
            raise
    
    def extract_file_metadata(self):
        """Extract metadata from STEP file header"""
        try:
            with open(self.fname, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # FILE_DESCRIPTION
            file_desc = re.search(r"FILE_DESCRIPTION\('([^']+)'", content)
            if file_desc:
                self.metadata['description'] = file_desc.group(1)
            
            # FILE_NAME
            file_name_match = re.search(r"FILE_NAME\('([^']+)','([^']+)','([^']*)'", content)
            if file_name_match:
                self.metadata['filename'] = file_name_match.group(1)
                self.metadata['timestamp'] = file_name_match.group(2)
                self.metadata['author'] = file_name_match.group(3) if file_name_match.group(3) else "Unknown"
            
            # FILE_SCHEMA
            schema = re.search(r"FILE_SCHEMA\(\('([^']+)'\)\)", content)
            if schema:
                self.metadata['schema'] = schema.group(1)
            
            # PRODUCT entries
            products = re.findall(r"#(\d+)=PRODUCT\('([^']+)','([^']*)'", content)
            self.metadata['products'] = [
                {'id': p[0], 'name': p[1], 'description': p[2]} 
                for p in products
            ]
            
        except Exception as e:
            self._log(f"Warning: Metadata extraction error: {e}")
    
    def analyze_complete(self):
        """Analyse complète de gestion de configuration"""
        self._log("="*80)
        self._log("ANALYSE DE GESTION DE CONFIGURATION")
        self._log("="*80)
        self._log(f"Fichier: {self.fname}")
        self._log(f"Date d'analyse: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log("="*80)
        
        # 1. Product Information
        self.print_product_info()
        
        # 2. Build BOM
        self.build_bom()
        
        # 3. Analyze geometry
        self.analyze_geometry()
        
        # 4. Extract colors
        self.extract_colors()
        
        # 5. Build dependency graph
        self.build_dependency_graph()
        
        # 6. Configuration baseline
        self.create_configuration_baseline()
        
        # 7. Validation checks
        self.perform_validation_checks()
        
    def print_product_info(self):
        """Affiche les informations produit"""
        self._log("\n" + "="*80)
        self._log("1. INFORMATIONS PRODUIT")
        self._log("="*80)
        
        if self.metadata:
            self._log(f"  Description: {self.metadata.get('description', 'N/A')}")
            self._log(f"  Schéma STEP: {self.metadata.get('schema', 'N/A')}")
            self._log(f"  Date création: {self.metadata.get('timestamp', 'N/A')}")
            self._log(f"  Auteur: {self.metadata.get('author', 'N/A')}")
            
            if 'products' in self.metadata and self.metadata['products']:
                self._log(f"\n  Produits définis: {len(self.metadata['products'])}")
                for prod in self.metadata['products']:
                    self._log(f"    • {prod['name']}")
                    if prod['description']:
                        self._log(f"      Description: {prod['description']}")
    
    def build_bom(self):
        """Construit la nomenclature (Bill of Materials)"""
        self._log("\n" + "="*80)
        self._log("2. NOMENCLATURE (BOM)")
        self._log("="*80)
        
        labels = TDF_LabelSequence()
        self.shape_tool.GetShapes(labels)
        
        if labels.Length() == 0:
            self._log("  Aucun composant trouvé")
            return
        
        rootlabel = labels.Value(1)
        
        if self.shape_tool.IsAssembly(rootlabel):
            self.bom_level = 0
            self.bom_item_number = 1
            self._log(f"\n  {'Pos':<6} {'Niveau':<8} {'Qté':<6} {'Désignation':<40} {'Référence':<15}")
            self._log("  " + "-"*75)
            
            root_name = rootlabel.GetLabelName()
            self._log(f"  {self.bom_item_number:<6} {self.bom_level:<8} {1:<6} {root_name:<40}")
            
            self.bom.append({
                'position': self.bom_item_number,
                'level': self.bom_level,
                'quantity': 1,
                'name': root_name,
                'label_entry': self.get_entry(rootlabel),
                'type': 'Assembly'
            })
            
            self.bom_item_number += 1
            
            # Process components
            top_comps = TDF_LabelSequence()
            self.shape_tool.GetComponents(rootlabel, top_comps, False)
            self.process_bom_components(top_comps, 1)
        
        # Count instances
        self._log(f"\n  Total positions: {len(self.bom)}")
        self.count_component_instances()
    
    def process_bom_components(self, comps, level):
        """Process components for BOM"""
        self.bom_level = level
        indent = "  " * level
        
        for j in range(comps.Length()):
            c_label = comps.Value(j+1)
            if c_label.IsNull():
                continue
            
            ref_label = TDF_Label()
            is_ref = self.shape_tool.GetReferredShape(c_label, ref_label)
            
            if is_ref and not ref_label.IsNull():
                ref_name = ref_label.GetLabelName()
                ref_entry = self.get_entry(ref_label)
                
                is_assy = self.shape_tool.IsAssembly(ref_label)
                comp_type = "Assembly" if is_assy else "Part"
                
                self._log(f"  {self.bom_item_number:<6} {level:<8} {1:<6} {indent}{ref_name:<40}")
                
                self.bom.append({
                    'position': self.bom_item_number,
                    'level': level,
                    'quantity': 1,
                    'name': ref_name,
                    'label_entry': ref_entry,
                    'type': comp_type
                })
                
                # Store in registry
                if ref_entry not in self.components_registry:
                    self.components_registry[ref_entry] = {
                        'name': ref_name,
                        'type': comp_type,
                        'instances': []
                    }
                self.components_registry[ref_entry]['instances'].append(self.bom_item_number)
                
                self.bom_item_number += 1
                
                if is_assy:
                    ref_comps = TDF_LabelSequence()
                    self.shape_tool.GetComponents(ref_label, ref_comps, False)
                    if ref_comps.Length() > 0:
                        self.process_bom_components(ref_comps, level + 1)
    
    def count_component_instances(self):
        """Compte les instances de chaque composant"""
        self._log("\n  Comptage des composants:")
        for comp_name, data in sorted(self.components_registry.items()):
            self._log(f"    • {data['name']}: {len(data['instances'])} instance(s)")

    def analyze_geometry(self):
        """Analyse géométrique complète avec granularité au niveau composant"""
        self._log("\n" + "="*80)
        self._log("3. ANALYSE GÉOMÉTRIQUE & SPATIALE (Niveau Composant)")
        self._log("="*80)
        
        # S'assurer que la BOM est construite
        if not self.bom:
            self.build_bom()
        
        if not self.bom:
            self._log("  Aucun composant à analyser")
            return
        
        self._log(f"\n  {'Composant':<30} {'BBox (Lxlxh)':<25} {'Topo (Trous)'}")
        self._log("  " + "-"*90)
        
        # Analyser chaque composant de la BOM individuellement
        labels = TDF_LabelSequence()
        self.shape_tool.GetShapes(labels)
        
        # Créer un mapping entry -> label pour accès rapide
        label_map = {}
        for i in range(labels.Length()):
            label = labels.Value(i+1)
            if not label.IsNull():
                entry = self.get_entry(label)
                label_map[entry] = label
        
        # Parcourir la BOM et analyser chaque composant
        for bom_item in self.bom:
            entry = bom_item['label_entry']
            name = bom_item['name']
            is_root = (bom_item['level'] == 0)  # Détecter l'assemblage racine
            
            # Récupérer le label correspondant
            if entry not in label_map:
                continue
                
            label = label_map[entry]
            
            # Pour les assemblages, on récupère aussi les composants référencés
            if self.shape_tool.IsAssembly(label):
                # Analyser l'assemblage lui-même si c'est la racine
                if is_root:
                    self._analyze_single_component(label, is_root=True)
                
                # Pour un assemblage, analyser les sous-composants
                comps = TDF_LabelSequence()
                self.shape_tool.GetComponents(label, comps, False)
                
                for j in range(comps.Length()):
                    c_label = comps.Value(j+1)
                    if c_label.IsNull():
                        continue
                    
                    ref_label = TDF_Label()
                    if self.shape_tool.GetReferredShape(c_label, ref_label) and not ref_label.IsNull():
                        # Analyser le composant référencé
                        self._analyze_single_component(ref_label)
            else:
                # Composant simple (part)
                self._analyze_single_component(label)
        
        self._log(f"\n  Total analysé: {len(self.geometric_props)} composants")
        
        # Ajouter les noms uniques pour gérer les doublons
        self.add_unique_names_to_geometry()
    
    def _analyze_single_component(self, label, is_root=False):
        """Analyse un seul composant et stocke ses propriétés
        
        Args:
            label: Label du composant à analyser
            is_root: True si c'est l'assemblage racine
        """
        entry = self.get_entry(label)
        
        # Éviter de réanalyser le même composant
        if entry in self.geometric_props:
            return
        
        simple_name = label.GetLabelName()
        shape = self.shape_tool.GetShape(label)
        
        if shape.IsNull():
            if not self.silent:
                self._log(f"  Warning: Shape nulle pour {simple_name} (entry: {entry})")
            return
        
        try:
            # 1. Volume
            props = GProp_GProps()
            brepgprop.VolumeProperties(shape, props)
            volume = props.Mass()
            
            # 2. Surface area
            props_surface = GProp_GProps()
            brepgprop.SurfaceProperties(shape, props_surface)
            surface_area = props_surface.Mass()
            
            # 3. Center of gravity
            cog = props.CentreOfMass()
            
            # 4. Bounding Box
            bbox_data = self._get_bounding_box(shape)
            bbox_str = f"{bbox_data['dims'][0]}x{bbox_data['dims'][1]}x{bbox_data['dims'][2]}"
            
            # 5. Topologie (Trous & Faces)
            features = {}
            try:
                exp = TopExp_Explorer(shape, TopAbs_FACE)
                if exp.More():
                    features = self._extract_geometric_features(shape)
            except Exception as e:
                if not self.silent:
                    self._log(f"  Warning: Erreur analyse topo sur {simple_name}: {e}")

            # Résumé log
            holes_summary = ""
            if features.get('holes'):
                count = len(features['holes'])
                holes_summary = f"{count} trous"
            
            self.geometric_props[entry] = {
                'name': simple_name,
                'volume': volume,
                'surface_area': surface_area,
                'center_of_gravity': [cog.X(), cog.Y(), cog.Z()],
                'bbox': bbox_data,
                'features_signature': features
            }
            
            self._log(f"  {simple_name:<30} {bbox_str:<25} {holes_summary}")
            
        except Exception as e:
            if not self.silent:
                self._log(f"  Erreur lors de l'analyse de {simple_name}: {e}")


    def build_component_path(self, label):
        """Construit le chemin hiérarchique complet d'un composant
        
        Retourne une chaîne du type: "assembly > sub_assembly > part"
        pour identifier de manière unique chaque composant même avec nom dupliqué.
        """
        entry = self.get_entry(label)
        path_parts = []
        
        # Trouver le composant dans la BOM et remonter la hiérarchie
        bom_dict = {item['label_entry']: item for item in self.bom}
        
        if entry in bom_dict:
            current_item = bom_dict[entry]
            path_parts.insert(0, current_item['name'])
            
            # Trouver les parents en cherchant les niveaux inférieurs
            current_level = current_item['level']
            current_pos = current_item['position']
            
            # Parcourir la BOM en arrière pour trouver les parents
            for i in range(current_pos - 1, 0, -1):
                if i <= len(self.bom):
                    parent_item = self.bom[i-1]
                    if parent_item['level'] < current_level:
                        path_parts.insert(0, parent_item['name'])
                        current_level = parent_item['level']
                        if current_level == 0:
                            break
        
        return " > ".join(path_parts) if path_parts else label.GetLabelName()
    
    def add_unique_names_to_geometry(self):
        """Ajoute les noms uniques et chemins aux propriétés géométriques"""
        # Créer un mapping entry -> label
        labels = TDF_LabelSequence()
        self.shape_tool.GetShapes(labels)
        label_map = {}
        for i in range(labels.Length()):
            label = labels.Value(i+1)
            if not label.IsNull():
                entry = self.get_entry(label)
                label_map[entry] = label
        
        # Compter les occurrences de chaque nom
        name_counts = defaultdict(int)
        for props in self.geometric_props.values():
            name_counts[props['name']] += 1
        
        # Ajouter unique_name et path
        for entry, props in self.geometric_props.items():
            if entry in label_map:
                label = label_map[entry]
                simple_name = props['name']
                
                # Si nom dupliqué, utiliser le chemin complet
                if name_counts[simple_name] > 1:
                    path = self.build_component_path(label)
                    props['unique_name'] = path
                    props['path'] = path
                else:
                    props['unique_name'] = simple_name
                    props['path'] = self.build_component_path(label)

    
    def analyze_interfaces(self):
        """Analyse les interfaces et liaisons entre composants
        
        Détecte :
        - Vissages/boulonnages (trous alignés entre composants)
        - Encastrements (surfaces en contact)
        - Proximité spatiale (composants proches)
        
        Returns:
            Liste des interfaces détectées avec type et propriétés
        """
        self._log("\n" + "="*80)
        self._log("ANALYSE DES INTERFACES")
        self._log("="*80)
        
        # S'assurer que la géométrie est analysée
        if not self.geometric_props:
            self.analyze_geometry()
        
        interfaces = []
        components_list = list(self.geometric_props.items())
        
        self._log(f"\nAnalyse de {len(components_list)} composants...")
        
        # Comparer chaque paire de composants
        for i in range(len(components_list)):
            entry1, comp1 = components_list[i]
            
            for j in range(i + 1, len(components_list)):
                entry2, comp2 = components_list[j]
                
                # Ignorer si même composant ou si l'un est l'assemblage racine
                if entry1 == entry2:
                    continue
                
                # Analyser l'interface entre comp1 et comp2
                interface = self._analyze_component_pair(entry1, comp1, entry2, comp2)
                
                if interface:
                    interfaces.append(interface)
        
        self.interfaces = interfaces
        
        # Résumé
        self._log(f"\n  Total interfaces détectées: {len(interfaces)}")
        
        # Grouper par type
        from collections import Counter
        type_counts = Counter(iface['type'] for iface in interfaces)
        
        for iface_type, count in type_counts.items():
            self._log(f"    • {iface_type}: {count}")
        
        # Afficher les interfaces critiques (vissages)
        fasteners = [iface for iface in interfaces if iface['type'] == 'fastening']
        if fasteners:
            self._log(f"\n  Interfaces de fixation détectées:")
            for iface in fasteners[:5]:  # Afficher les 5 premières
                self._log(f"    • {iface['component1']} ↔ {iface['component2']}")
                self._log(f"      {iface['fastener_count']} fixations (Ø{iface['fastener_diameter']}mm)")
        
        return interfaces
    
    def _analyze_component_pair(self, entry1, comp1, entry2, comp2):
        """Analyse l'interface entre deux composants
        
        Returns:
            Dictionnaire décrivant l'interface ou None si pas d'interface
        """
        name1 = comp1.get('unique_name', comp1['name'])
        name2 = comp2.get('unique_name', comp2['name'])
        
        # 1. Vérifier proximité spatiale via bounding boxes
        bbox1 = comp1.get('bbox', {})
        bbox2 = comp2.get('bbox', {})
        
        if not bbox1 or not bbox2:
            return None
        
        # Distance entre centres (approximation rapide)
        cog1 = comp1.get('center_of_gravity', [0, 0, 0])
        cog2 = comp2.get('center_of_gravity', [0, 0, 0])
        
        distance = ((cog1[0] - cog2[0])**2 + 
                   (cog1[1] - cog2[1])**2 + 
                   (cog1[2] - cog2[2])**2)**0.5
        
        # Si trop éloignés, pas d'interface
        max_bbox_size = max(bbox1['dims'] + bbox2['dims'])
        if distance > max_bbox_size * 2:
            return None
        
        # 2. Analyser les trous pour détecter les fixations
        holes1 = comp1.get('features_signature', {}).get('holes', [])
        holes2 = comp2.get('features_signature', {}).get('holes', [])
        
        aligned_holes = self._find_aligned_holes(holes1, holes2)
        
        if aligned_holes:
            # Interface de type vissage/boulonnage
            # Grouper par diamètre
            diameters = {}
            for h1, h2 in aligned_holes:
                d = h1['d']
                if d not in diameters:
                    diameters[d] = []
                diameters[d].append((h1, h2))
            
            # Utiliser le diamètre le plus courant
            main_diameter = max(diameters.keys(), key=lambda d: len(diameters[d]))
            
            return {
                'type': 'fastening',
                'component1': name1,
                'component2': name2,
                'entry1': entry1,
                'entry2': entry2,
                'fastener_count': len(aligned_holes),
                'fastener_diameter': main_diameter,
                'fastener_positions': [
                    {'x': h1['x'], 'y': h1['y'], 'z': h1['z']} 
                    for h1, _ in aligned_holes
                ],
                'severity': 'critical',  # Vissage = critique pour assemblage
                'description': f"{len(aligned_holes)} fixation(s) Ø{main_diameter}mm"
            }
        
        # 3. Si composants proches mais pas de trous alignés
        # Vérifier si surfaces potentiellement en contact
        if distance < max_bbox_size * 0.3:
            # Contact ou encastrement probable
            return {
                'type': 'contact',
                'component1': name1,
                'component2': name2,
                'entry1': entry1,
                'entry2': entry2,
                'distance': round(distance, 2),
                'severity': 'major',
                'description': f"Contact/encastrement (distance: {distance:.1f}mm)"
            }
        
        # 4. Proximité sans contact direct
        if distance < max_bbox_size:
            return {
                'type': 'proximity',
                'component1': name1,
                'component2': name2,
                'entry1': entry1,
                'entry2': entry2,
                'distance': round(distance, 2),
                'severity': 'minor',
                'description': f"Proximité (distance: {distance:.1f}mm)"
            }
        
        return None
    
    def _find_aligned_holes(self, holes1, holes2, tolerance=2.0):
        """Trouve les paires de trous alignés entre deux composants
        
        Args:
            holes1: Liste des trous du composant 1
            holes2: Liste des trous du composant 2
            tolerance: Tolérance d'alignement en mm (défaut: 2mm)
        
        Returns:
            Liste de tuples (trou1, trou2) pour les trous alignés
        """
        aligned = []
        
        for h1 in holes1:
            for h2 in holes2:
                # Vérifier si même diamètre (±0.1mm)
                if abs(h1['d'] - h2['d']) > 0.1:
                    continue
                
                # Vérifier alignement spatial
                # Les trous doivent être alignés sur au moins 2 axes
                dx = abs(h1['x'] - h2['x'])
                dy = abs(h1['y'] - h2['y'])
                dz = abs(h1['z'] - h2['z'])
                
                # Compter les axes alignés
                aligned_axes = sum([dx < tolerance, dy < tolerance, dz < tolerance])
                
                # Si au moins 2 axes alignés (trous traversants ou coaxiaux)
                if aligned_axes >= 2:
                    # Distance 3D totale
                    dist_3d = (dx**2 + dy**2 + dz**2)**0.5
                    
                    # Si distance totale raisonnable
                    if dist_3d < tolerance * 2:
                        aligned.append((h1, h2))
                        break  # Éviter doublons
        
        return aligned


    def _get_bounding_box(self, shape):
            """Calcule la boîte englobante pour l'analyse d'encombrement (Clash Detection)"""
            bbox = Bnd_Box()
            brepbndlib.Add(shape, bbox)
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
            return {
                'dims': [round(xmax-xmin, 2), round(ymax-ymin, 2), round(zmax-zmin, 2)],
                'volume_bbox': round((xmax-xmin)*(ymax-ymin)*(zmax-zmin), 2)
            }

    def _extract_geometric_features(self, shape):
            """
            Extrait les signatures topologiques avec localisation spatiale.
            Retourne : { 'holes': [{'d': 3.0, 'x': 10.0, 'y': 5.0, ...}], 'planar_faces': n }
            """
            features = {
                'holes': [], 
                'planar_faces_count': 0
            }
            
            try:
                explorer = TopExp_Explorer(shape, TopAbs_FACE)
                while explorer.More():
                    try:
                        face = explorer.Current()
                        surf = BRepAdaptor_Surface(face, True)
                        type_surf = surf.GetType()
                        
                        if type_surf == GeomAbs_Cylinder:
                            cyl = surf.Cylinder()
                            radius = cyl.Radius()
                            loc = cyl.Location()
                            
                            # On stocke le Diamètre ET la Position (arrondis pour la stabilité)
                            # C'est la clé de la gestion d'assemblage : savoir OÙ est le trou.
                            features['holes'].append({
                                'd': round(radius * 2.0, 3), # Diamètre
                                'x': round(loc.X(), 1),
                                'y': round(loc.Y(), 1),
                                'z': round(loc.Z(), 1)
                            })
                        
                        elif type_surf == GeomAbs_Plane:
                            features['planar_faces_count'] += 1
                    except Exception as e:
                        # Skip face if error, but continue processing
                        if not self.silent:
                            print(f"    Warning: Error processing face: {e}")
                        pass
                        
                    explorer.Next()
                    
                # Tri pour garantir l'ordre déterministe (par diamètre puis position X)
                features['holes'].sort(key=lambda k: (k['d'], k['x'], k['y']))
            except Exception as e:
                if not self.silent:
                    print(f"    Warning: Error extracting features: {e}")
                
            return features
    def extract_colors(self):
        """Extrait les couleurs des composants"""
        self._log("\n" + "="*80)
        self._log("4. EXTRACTION DES COULEURS")
        self._log("="*80)
        
        labels = TDF_LabelSequence()
        self.shape_tool.GetShapes(labels)
        
        color_found = False
        
        self._log(f"\n  {'Composant':<40} {'Couleur RGB':<20}")
        self._log("  " + "-"*60)
        
        for i in range(labels.Length()):
            label = labels.Value(i+1)
            if label.IsNull():
                continue
            
            name = label.GetLabelName()
            color = Quantity_Color()
            
            # Try to get color (simple form without color type)
            try:
                if self.color_tool.GetColor(label, color):
                    r, g, b = int(color.Red()*255), int(color.Green()*255), int(color.Blue()*255)
                    color_str = f"({r}, {g}, {b})"
                    self._log(f"  {name:<40} {color_str:<20}")
                    
                    self.colors_registry[self.get_entry(label)] = {
                        'name': name,
                        'rgb': [r, g, b]
                    }
                    color_found = True
            except:
                # Try with shape if label method fails
                try:
                    shape = self.shape_tool.GetShape(label)
                    if not shape.IsNull():
                        # Colors might be on the shape
                        pass
                except:
                    pass
        
        if not color_found:
            self._log("  Aucune couleur définie dans le fichier STEP")
    
    def build_dependency_graph(self):
        """Construit le graphe de dépendances"""
        self._log("\n" + "="*80)
        self._log("5. GRAPHE DE DÉPENDANCES")
        self._log("="*80)
        
        labels = TDF_LabelSequence()
        self.shape_tool.GetShapes(labels)
        
        for i in range(labels.Length()):
            label = labels.Value(i+1)
            if label.IsNull() or not self.shape_tool.IsAssembly(label):
                continue
            
            parent_entry = self.get_entry(label)
            parent_name = label.GetLabelName()
            
            comps = TDF_LabelSequence()
            self.shape_tool.GetComponents(label, comps, False)
            
            for j in range(comps.Length()):
                c_label = comps.Value(j+1)
                if c_label.IsNull():
                    continue
                
                ref_label = TDF_Label()
                if self.shape_tool.GetReferredShape(c_label, ref_label) and not ref_label.IsNull():
                    child_entry = self.get_entry(ref_label)
                    child_name = ref_label.GetLabelName()
                    
                    self.dependency_graph[parent_entry].append({
                        'entry': child_entry,
                        'name': child_name
                    })
        
        # Print graph
        self._log("\n  Structure des dépendances:")
        for parent, children in self.dependency_graph.items():
            parent_name = self.get_name_from_entry(parent)
            self._log(f"\n  {parent_name} [{parent}]")
            for child in children:
                self._log(f"    └─ {child['name']} [{child['entry']}]")
    
    def create_configuration_baseline(self):
        """Crée une baseline de configuration"""
        self._log("\n" + "="*80)
        self._log("6. BASELINE DE CONFIGURATION")
        self._log("="*80)
        
        baseline = {
            'baseline_id': self.generate_config_id(),
            'timestamp': datetime.now().isoformat(),
            'file': self.fname,
            'metadata': self.metadata,
            'bom': self.bom,
            'component_registry': self.components_registry,
            'geometric_properties': self.geometric_props,
            'colors': self.colors_registry,
            'dependencies': dict(self.dependency_graph),
            'checksum': self.calculate_file_checksum()
        }
        
        # Save to JSON
        baseline_filename = f"config_baseline_{baseline['baseline_id']}.json"
        with open(baseline_filename, 'w', encoding='utf-8') as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)
        
        self._log(f"\n  Baseline ID: {baseline['baseline_id']}")
        self._log(f"  Date: {baseline['timestamp']}")
        self._log(f"  Checksum fichier: {baseline['checksum']}")
        self._log(f"  Nombre de composants: {len(self.bom)}")
        self._log(f"  ✓ Baseline sauvegardée: {baseline_filename}")
    
    def perform_validation_checks(self):
        """Effectue les vérifications de validation"""
        self._log("\n" + "="*80)
        self._log("7. VÉRIFICATIONS DE VALIDATION")
        self._log("="*80)
        
        issues = []
        warnings = []
        
        # Check 1: Tous les composants ont un nom
        unnamed = [item for item in self.bom if not item['name'] or item['name'].strip() == '']
        if unnamed:
            issues.append(f"Composants sans nom: {len(unnamed)}")
        else:
            self._log("  ✓ Tous les composants ont un nom")
        
        # Check 2: Metadata présente
        if not self.metadata:
            issues.append("Métadonnées manquantes")
        else:
            self._log("  ✓ Métadonnées présentes")
        
        # Check 3: Schema STEP valide
        valid_schemas = ['CONFIG_CONTROL_DESIGN', 'AUTOMOTIVE_DESIGN', 'AP203', 'AP214']
        schema = self.metadata.get('schema', '')
        if any(s in schema for s in valid_schemas):
            self._log(f"  ✓ Schéma STEP valide: {schema}")
        else:
            warnings.append(f"Schéma STEP non standard: {schema}")
        
        # Check 4: Hiérarchie non excessive
        max_depth = max([item['level'] for item in self.bom]) if self.bom else 0
        if max_depth > 10:
            warnings.append(f"Hiérarchie profonde: {max_depth} niveaux")
        else:
            self._log(f"  ✓ Profondeur hiérarchie acceptable: {max_depth} niveaux")
        
        # Check 5: Propriétés géométriques calculées
        if self.geometric_props:
            self._log(f"  ✓ Propriétés géométriques: {len(self.geometric_props)} composants")
        else:
            warnings.append("Propriétés géométriques non disponibles")
        
        # Check 6: Duplicate component names
        name_counts = defaultdict(int)
        for item in self.bom:
            name_counts[item['name']] += 1
        duplicates = {name: count for name, count in name_counts.items() if count > 1}
        if duplicates:
            warnings.append(f"Noms dupliqués détectés: {len(duplicates)}")
            self._log(f"  ⚠ Composants avec noms identiques: {len(duplicates)}")
        else:
            self._log("  ✓ Pas de noms de composants dupliqués")
        
        # Summary
        self._log("\n" + "="*80)
        self._log("RÉSUMÉ DE VALIDATION")
        self._log("="*80)
        
        if not issues and not warnings:
            self._log("  ✓ CONFORME - Aucun problème détecté")
            self._log("  Le produit répond à toutes les exigences de gestion de configuration")
        else:
            if issues:
                self._log(f"  ✗ PROBLÈMES CRITIQUES: {len(issues)}")
                for issue in issues:
                    self._log(f"    • {issue}")
            
            if warnings:
                self._log(f"  ⚠ AVERTISSEMENTS: {len(warnings)}")
                for warning in warnings:
                    self._log(f"    • {warning}")
    
    def generate_config_id(self):
        """Génère un ID de configuration unique"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_hash = hashlib.md5(self.fname.encode()).hexdigest()[:8]
        return f"CFG_{timestamp}_{file_hash}"
    
    def calculate_file_checksum(self):
        """Calcule le checksum du fichier"""
        sha256_hash = hashlib.sha256()
        with open(self.fname, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def get_entry(self, label):
        """Get label entry as string"""
        entry = TCollection_AsciiString()
        TDF_Tool.Entry(label, entry)
        return entry.ToCString() if entry.ToCString() else ""
    
    def get_name_from_entry(self, entry_str):
        """Get component name from entry"""
        for item in self.bom:
            if item['label_entry'] == entry_str:
                return item['name']
        return "Unknown"
    
    def build_component_path(self, label):
        """Construit le chemin hiérarchique complet d'un composant
        
        Retourne une chaîne du type: "assembly > sub_assembly > part"
        pour identifier de manière unique chaque composant même avec nom dupliqué.
        """
        entry = self.get_entry(label)
        path_parts = []
        
        # Trouver le composant dans la BOM et remonter la hiérarchie
        bom_dict = {item['label_entry']: item for item in self.bom}
        
        if entry in bom_dict:
            current_item = bom_dict[entry]
            path_parts.insert(0, current_item['name'])
            
            # Trouver les parents en cherchant les niveaux inférieurs
            current_level = current_item['level']
            current_pos = current_item['position']
            
            # Parcourir la BOM en arrière pour trouver les parents
            for i in range(current_pos - 1, 0, -1):
                if i <= len(self.bom):
                    parent_item = self.bom[i-1]
                    if parent_item['level'] < current_level:
                        path_parts.insert(0, parent_item['name'])
                        current_level = parent_item['level']
                        if current_level == 0:
                            break
        
        return " > ".join(path_parts) if path_parts else label.GetLabelName()
    
    def get_unique_component_name(self, label, entry):
        """Génère un nom unique pour un composant
        
        Utilise le chemin hiérarchique si des doublons existent,
        sinon retourne le nom simple.
        """
        name = label.GetLabelName()
        
        # Compter les occurrences de ce nom dans la BOM
        name_count = sum(1 for item in self.bom if item['name'] == name)
        
        if name_count > 1:
            # Il y a des doublons, utiliser le chemin complet
            return self.build_component_path(label)
        else:
            # Nom unique, retourner tel quel
            return name
    
    def export_to_csv(self):
        """Export BOM to CSV format"""
        import csv
        
        csv_filename = self.fname.replace('.stp', '_bom.csv')
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['Position', 'Niveau', 'Quantité', 'Désignation', 'Type', 'Référence'])
            
            for item in self.bom:
                writer.writerow([
                    item['position'],
                    item['level'],
                    item['quantity'],
                    item['name'],
                    item['type'],
                    item['label_entry']
                ])
        
        self._log(f"\n  ✓ BOM exportée: {csv_filename}")
        return csv_filename


def main():
    """Point d'entrée principal"""
    import sys
    
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "step/jaspair_v09.stp"
    
    print("\n" + "="*80)
    print("ANALYSEUR DE GESTION DE CONFIGURATION")
    print("Configuration Management Analyzer for Industrial Products")
    print("="*80)
    
    # Create manager
    cm = ConfigurationManager(filename)
    
    # Run complete analysis
    cm.analyze_complete()
    
    # Export BOM to CSV
    print("\n" + "="*80)
    print("8. EXPORT")
    print("="*80)
    cm.export_to_csv()
    
    print("\n" + "="*80)
    print("ANALYSE TERMINÉE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
