"""Servicio de Fotogrametría de Corto Alcance y Cubicación de Acopios - MAMA-Vial.

Permite calcular el volumen métrico preciso (m³) y tonelaje de acopios de áridos,
suelos o material fresado (RAP) a partir de nubes de puntos densas generadas por visión
artificial (Structure-from-Motion / Estéreo), resolviendo la escala métrica mediante
dianas o barras de referencia y segmentando el terreno base mediante RANSAC plano 3D,
sin requerir posicionamiento satelital GNSS RTK de alta precisión.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.spatial import ConvexHull, Delaunay

logger = logging.getLogger("MariPhotogrammetry")


@dataclass
class StockpileMetrics:
    """Métricas volumétricas y geométricas del acopio vial."""
    volumen_m3: float
    area_base_m2: float
    altura_maxima_m: float
    altura_media_m: float
    tonelaje_estimado: float
    material: str
    densidad_t_m3: float
    puntos_totales: int
    puntos_acopio: int
    plano_terreno_coeficientes: Tuple[float, float, float, float]


class StockpilePhotogrammetryService:
    """Motor de cálculo volumétrico TIN 2.5D y reconocimiento de terreno para fotogrametría."""

    # Densidades aparentes estándar de laboratorio vial (t/m³)
    DENSIDADES_MATERIALES: Dict[str, float] = {
        "piedra_partida": 1.55,
        "grava": 1.60,
        "arena": 1.65,
        "fresado_rap": 2.15,
        "mezcla_asfaltica": 2.35,
        "suelo_seleccionado": 1.80,
        "estabilizado_granular": 2.10,
    }

    def __init__(self, noise_threshold_m: float = 0.03, max_edge_len_m: float = 0.50) -> None:
        """
        Args:
            noise_threshold_m: Altura mínima sobre el terreno para integrar volumen (filtro de ruido del suelo).
            max_edge_len_m: Longitud máxima de arista en la triangulación TIN para evitar interpolar fuera del acopio.
        """
        self.noise_threshold = noise_threshold_m
        self.max_edge_len = max_edge_len_m

    def fit_ground_plane_ransac(
        self,
        points: np.ndarray,
        distance_threshold: float = 0.05,
        max_iterations: int = 1000,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Ajusta el plano del terreno base mediante RANSAC sobre el tercio inferior del acopio.

        Ecuación del plano: Ax + By + Cz + D = 0, con ||(A, B, C)|| = 1.
        """
        if len(points) < 10:
            raise ValueError("Puntos insuficientes para calcular el plano del terreno.")

        # Tomamos los puntos del percentil inferior en Z como candidatos principales a piso
        z_vals = points[:, 2]
        lower_threshold = np.percentile(z_vals, 35)
        floor_candidates = points[z_vals <= lower_threshold]
        if len(floor_candidates) < 10:
            floor_candidates = points

        best_inliers = np.array([], dtype=int)
        best_plane = np.array([0.0, 0.0, 1.0, 0.0])
        n_points = len(floor_candidates)

        for _ in range(max_iterations):
            idx = np.random.choice(n_points, 3, replace=False)
            p1, p2, p3 = floor_candidates[idx]

            v1 = p2 - p1
            v2 = p3 - p1
            normal = np.cross(v1, v2)
            norm = np.linalg.norm(normal)
            if norm < 1e-6:
                continue
            normal = normal / norm

            # Garantizar que la normal apunte hacia arriba (+Z)
            if normal[2] < 0:
                normal = -normal

            d = -np.dot(normal, p1)
            distances = np.abs(np.dot(floor_candidates, normal) + d)
            inliers = np.where(distances < distance_threshold)[0]

            if len(inliers) > len(best_inliers):
                best_inliers = inliers
                best_plane = np.append(normal, d)

        # Refinamiento por mínimos cuadrados con los mejores inliers
        if len(best_inliers) >= 3:
            pts = floor_candidates[best_inliers]
            centroid = np.mean(pts, axis=0)
            _, _, vh = np.linalg.svd(pts - centroid)
            normal = vh[2, :]
            if normal[2] < 0:
                normal = -normal
            d = -np.dot(normal, centroid)
            best_plane = np.append(normal, d)

        return best_plane, best_inliers

    def calculate_volume_tin(
        self,
        points: np.ndarray,
        material: str = "piedra_partida",
        scale_factor: float = 1.0,
    ) -> StockpileMetrics:
        """Calcula el volumen exacto integrando prismas triangulares TIN (Delaunay 2.5D) nivelados."""
        # 1. Aplicar escala métrica absoluta si se deriva de dianas/mira
        pts = points * scale_factor

        # 2. Reconocimiento y ajuste del plano base del terreno mediante RANSAC
        plane, _ = self.fit_ground_plane_ransac(pts)
        normal = plane[:3]
        d = plane[3]

        # 3. Matriz de rotación de Rodrigues para nivelar el terreno horizontalmente (normal = [0, 0, 1])
        target_normal = np.array([0.0, 0.0, 1.0])
        v = np.cross(normal, target_normal)
        c = np.dot(normal, target_normal)
        s = np.linalg.norm(v)

        if s < 1e-6:
            r_mat = np.eye(3)
        else:
            kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
            r_mat = np.eye(3) + kmat + np.matmul(kmat, kmat) * ((1 - c) / (s**2))

        # Rotar y desplazar para que el plano del terreno sea Z = 0
        rotated_pts = np.dot(pts, r_mat.T)
        z_offset = -d
        rotated_pts[:, 2] -= z_offset

        # 4. Aislar puntos que pertenecen al cuerpo del acopio (por encima del umbral de ruido)
        stockpile_mask = rotated_pts[:, 2] >= self.noise_threshold
        stockpile_pts = rotated_pts[stockpile_mask]

        if len(stockpile_pts) < 10:
            raise ValueError("No se detectó relieve suficiente sobre el plano del terreno.")

        # 5. Triangulación de Delaunay 2.5D en el plano horizontal XY
        xy_pts = stockpile_pts[:, :2]
        z_pts = stockpile_pts[:, 2]

        tri = Delaunay(xy_pts)
        simplices = tri.simplices

        # Coordenadas de los 3 vértices de cada triángulo
        p1 = xy_pts[simplices[:, 0]]
        p2 = xy_pts[simplices[:, 1]]
        p3 = xy_pts[simplices[:, 2]]

        # Longitudes de aristas para filtrar triángulos exteriores espurios
        d12 = np.linalg.norm(p1 - p2, axis=1)
        d23 = np.linalg.norm(p2 - p3, axis=1)
        d31 = np.linalg.norm(p3 - p1, axis=1)
        valid_triangles = (d12 <= self.max_edge_len) & (d23 <= self.max_edge_len) & (d31 <= self.max_edge_len)

        p1 = p1[valid_triangles]
        p2 = p2[valid_triangles]
        p3 = p3[valid_triangles]
        simplices_valid = simplices[valid_triangles]

        # Área 2D de cada triángulo
        areas = 0.5 * np.abs(
            p1[:, 0] * (p2[:, 1] - p3[:, 1])
            + p2[:, 0] * (p3[:, 1] - p1[:, 1])
            + p3[:, 0] * (p1[:, 1] - p2[:, 1])
        )

        # Altura media sobre el plano base para cada prisma triangular
        z_means = (
            z_pts[simplices_valid[:, 0]]
            + z_pts[simplices_valid[:, 1]]
            + z_pts[simplices_valid[:, 2]]
        ) / 3.0

        # Volumen total: suma de prismas triangulares truncados
        volume_m3 = float(np.sum(areas * z_means))

        # Huella del acopio mediante Convex Hull
        try:
            hull = ConvexHull(xy_pts)
            area_base_m2 = float(hull.volume)
        except Exception:
            area_base_m2 = float(np.sum(areas))

        altura_max_m = float(np.max(z_pts))
        altura_media_m = float(np.average(z_means, weights=areas)) if len(areas) > 0 else 0.0

        densidad = self.DENSIDADES_MATERIALES.get(material.lower(), 1.55)
        tonelaje = volume_m3 * densidad

        return StockpileMetrics(
            volumen_m3=round(volume_m3, 3),
            area_base_m2=round(area_base_m2, 2),
            altura_maxima_m=round(altura_max_m, 2),
            altura_media_m=round(altura_media_m, 2),
            tonelaje_estimado=round(tonelaje, 2),
            material=material,
            densidad_t_m3=densidad,
            puntos_totales=len(pts),
            puntos_acopio=len(stockpile_pts),
            plano_terreno_coeficientes=(
                round(float(plane[0]), 4),
                round(float(plane[1]), 4),
                round(float(plane[2]), 4),
                round(float(plane[3]), 4),
            ),
        )

    @staticmethod
    def detect_aruco_scale_factor(
        image_bytes: bytes,
        real_marker_size_m: float = 0.20,
    ) -> Optional[float]:
        """Detecta un marcador ArUco en la imagen para resolver la escala métrica absoluta sin GNSS."""
        try:
            import cv2
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                return None

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100)
            parameters = cv2.aruco.DetectorParameters()
            detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
            corners, ids, _ = detector.detectMarkers(gray)

            if ids is not None and len(corners) > 0:
                # Perímetro medio en píxeles del marcador detectado
                pts = corners[0][0]
                side_px = np.mean([
                    np.linalg.norm(pts[0] - pts[1]),
                    np.linalg.norm(pts[1] - pts[2]),
                    np.linalg.norm(pts[2] - pts[3]),
                    np.linalg.norm(pts[3] - pts[0]),
                ])
                # Factor de escala (metros reales por píxel a la distancia del marcador)
                return real_marker_size_m / float(side_px)
        except Exception as exc:
            logger.warning("No se pudo detectar marcador ArUco: %s", exc)
        return None

    @staticmethod
    def load_point_cloud_from_text(file_content: str) -> np.ndarray:
        """Carga una nube de puntos desde formato plano CSV, XYZ o TXT (X, Y, Z)."""
        lines = file_content.strip().splitlines()
        points = []
        for line in lines:
            line_str = line.strip().replace(",", " ")
            parts = [p for p in line_str.split() if p]
            if len(parts) >= 3:
                try:
                    points.append([float(parts[0]), float(parts[1]), float(parts[2])])
                except ValueError:
                    continue
        if not points:
            raise ValueError("No se pudieron parsear coordenadas 3D válidas del archivo.")
        return np.array(points, dtype=np.float64)
