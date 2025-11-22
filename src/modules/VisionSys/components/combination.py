import numpy as np
from typing import Tuple, Optional, Dict, Any

# Conveniência: OpenCV hue range é [0,179]
HUE_MAX = 180

def clamp_uv(v: int) -> int:
    return max(0, min(255, int(v)))

def create_color_bounds(color_array: np.ndarray,
                        hue_tol: int = 10,
                        sat_tol: int = 50,
                        val_tol: int = 50) -> Tuple[np.ndarray, np.ndarray]:
    h = int(color_array[0]) % HUE_MAX
    s = clamp_uv(int(color_array[1]))
    v = clamp_uv(int(color_array[2]))

    low_h = (h - hue_tol) % HUE_MAX
    high_h = (h + hue_tol) % HUE_MAX

    lower = np.array([low_h, max(0, s - sat_tol), max(0, v - val_tol)], dtype=int)
    upper = np.array([high_h, min(255, s + sat_tol), min(255, v + val_tol)], dtype=int)
    return lower, upper


def hue_circ_dist(h1: int, h2: int) -> int:
    """Distância circular entre dois H (inteiro 0..179). Retorna 0..90 approx."""
    d = abs(int(h1) - int(h2))
    if d > HUE_MAX // 2:
        d = HUE_MAX - d
    return d


class TreeColors:
    """
    Estrutura em memória para guardar cores dos robôs e buscar correspondências.

    Cada robô tem:
      - id_key: identificador (p.ex. enum ID_Robots)
      - team (opcional)
      - colors: dict('main', 'primary', 'secondary') -> HSV numpy arrays (h,s,v)
      - bounds: precomputed (lower, upper) para cada cor
      - meta: permissões/tolerances/custom data

    Modo de uso:
      tree = TreeColors()
      tree.add_robot(robot_id, team, main, primary, secondary)
      match = tree.find_by_colors(main_cand, prim_cand, sec_cand)
      colors = tree.get_colors(robot_id)  # retorna [main, primary, secondary]
    """

    def __init__(self):
            # dict: (team_id, robot_id) -> record
            self._store: Dict[Tuple[Any, Any], Dict[str, Any]] = {}

    def add_robot(self, team_id: Any, robot_id: Any,
                  main_hsv: np.ndarray,
                  primary_hsv: np.ndarray,
                  secondary_hsv: np.ndarray,
                  hue_tol: int = 10, sat_tol: int = 50, val_tol: int = 50,
                  replace: bool = True):
        """
        Adiciona (ou atualiza) o registro de cores do robô e pré-calcula bounds.
        main_hsv etc devem ser arrays/list [H,S,V] (H em 0..179).
        """
        key = (team_id, robot_id)

        rec = {
            'team': team_id,
            'robot_id': robot_id,
            'colors': {
                'main': self.ensure_hsv_array(main_hsv),
                'primary': self.ensure_hsv_array(primary_hsv),
                'secondary': self.ensure_hsv_array(secondary_hsv),
            },
            'bounds': {},
            'tolerances': {
                'hue_tol': int(hue_tol),
                'sat_tol': int(sat_tol),
                'val_tol': int(val_tol)
            }
        }

        # precompute bounds per color
        for key_color in ('main', 'primary', 'secondary'):
            lower, upper = create_color_bounds(rec['colors'][key_color],
                                               hue_tol=hue_tol,
                                               sat_tol=sat_tol,
                                               val_tol=val_tol)
            rec['bounds'][key_color] = (lower, upper)

        if (key in self._store) and not replace:
            raise KeyError(f"Robot {robot_id} already exists in team {team_id}. Use replace=True to overwrite.")

        self._store[key] = rec


    def ensure_hsv_array(self, hsv: Any) -> np.ndarray:
        arr = np.asarray(hsv, dtype=int)
        if arr.shape == ():  # escalar
            raise ValueError(f"HSV value {hsv} não é uma lista/array de 3 elementos")
        if arr.size != 3:
            raise ValueError(f"HSV value {hsv} deve ter exatamente 3 elementos")
        return arr

    def update_robot_colors(self, team_id: Any, robot_id: Any,
                            main_hsv: Optional[np.ndarray] = None,
                            primary_hsv: Optional[np.ndarray] = None,
                            secondary_hsv: Optional[np.ndarray] = None):
        key = (team_id, robot_id)
        if key not in self._store:
            raise KeyError(f"Robot {robot_id} not found in team {team_id}.")

        rec = self._store[key]
        hue_tol = rec['tolerances']['hue_tol']
        sat_tol = rec['tolerances']['sat_tol']
        val_tol = rec['tolerances']['val_tol']

        if main_hsv is not None:
            rec['colors']['main'] = np.asarray(main_hsv, dtype=int)
        if primary_hsv is not None:
            rec['colors']['primary'] = np.asarray(primary_hsv, dtype=int)
        if secondary_hsv is not None:
            rec['colors']['secondary'] = np.asarray(secondary_hsv, dtype=int)

        for key_color in ('main', 'primary', 'secondary'):
            lower, upper = create_color_bounds(rec['colors'][key_color],
                                               hue_tol=hue_tol,
                                               sat_tol=sat_tol,
                                               val_tol=val_tol)
            rec['bounds'][key_color] = (lower, upper)

    def get_colors(self, team_id: Any, robot_id: Any) -> Optional[np.ndarray]:
        key = (team_id, robot_id)
        rec = self._store.get(key)
        if rec is None:
            return None
        return np.array([rec['colors']['main'],
                         rec['colors']['primary'],
                         rec['colors']['secondary']], dtype=int)
    # -------------------------
    # Matching rápido
    # -------------------------
    def _in_bounds(self, color_hsv: np.ndarray, bound_low: np.ndarray, bound_high: np.ndarray) -> bool:
        """
        Checagem por bounds. Hue precisa de tratamento especial (wrap).
        bound_low/high são arrays [H_low, S_low, V_low] e [H_high, S_high, V_high].
        """
        h, s, v = int(color_hsv[0]) % HUE_MAX, int(color_hsv[1]), int(color_hsv[2])

        hl, sl, vl = int(bound_low[0]) % HUE_MAX, int(bound_low[1]), int(bound_low[2])
        hh, sh, vh = int(bound_high[0]) % HUE_MAX, int(bound_high[1]), int(bound_high[2])

        # Saturation and Value straightforward
        if s < sl or s > sh or v < vl or v > vh:
            return False

        # Hue: if low <= high (normal) then check direct; if low > high (wrap) check circular
        if hl <= hh:
            return (hl <= h <= hh)
        else:
            # wrap case: allowed [hl..179] U [0..hh]
            return (h >= hl) or (h <= hh)
        
    def print_store(self):
        """
        Imprime de forma legível todos os robôs cadastrados na base.
        - team_id 0: aliados
        - team_id 1: inimigos
        - robot_id: 0=goleiro, 1=atacante1, 2=atacante2
        """
        if not self._store:
            print("TreeColors: nenhum robô cadastrado.")
            return

        print("TreeColors: robôs cadastrados:")
        for (team_id, robot_id), rec in sorted(self._store.items(), key=lambda x: (x[0][0], x[0][1])):
            team_label = "Aliado" if team_id == 0 else "Inimigo"
            role_label = {0: "Goleiro", 1: "Atacante 1", 2: "Atacante 2"}.get(robot_id, f"Robot {robot_id}")
            print(f"  {team_label} - {role_label} (Team: {team_id}, Robot ID: {robot_id})")
            for key_color in ('main', 'primary', 'secondary'):
                color = rec['colors'][key_color]
                bounds = rec['bounds'][key_color]
                print(f"    {key_color.capitalize()} HSV: {color}  Bounds: low={bounds[0]}, high={bounds[1]}")
            print("-" * 50)


    def _score_distance(self, cand_colors: Tuple[np.ndarray, np.ndarray, np.ndarray],
                        rec_colors: Tuple[np.ndarray, np.ndarray, np.ndarray]) -> float:
        """
        Métrica de similaridade (menor = melhor).
        Combina distância circular do H e diferença relativa S/V.
        Só chamada depois do filtro por bounds; aplicada em poucos candidatos.
        """
        score = 0.0
        # pesos (são heurísticos; ajustar conforme necessidade)
        w_hue, w_sat, w_val = 1.0, 0.02, 0.02

        for c_cand, c_rec in zip(cand_colors, rec_colors):
            # H distance normalized in [0..90] -> keep raw
            dh = hue_circ_dist(int(c_cand[0]) % HUE_MAX, int(c_rec[0]) % HUE_MAX)
            ds = abs(int(c_cand[1]) - int(c_rec[1]))  # 0..255
            dv = abs(int(c_cand[2]) - int(c_rec[2]))

            score += (w_hue * dh) + (w_sat * ds) + (w_val * dv)

        return score
    
    def find_by_colors(self,
                    main_hsv: np.ndarray,
                    primary_hsv: np.ndarray,
                    secondary_hsv: np.ndarray,
                    max_candidates: int = 5,
                    score_threshold: float = 200.0) -> Optional[Dict[str, Any]]:
        """
        Procura o robô mais provável que corresponda à combinação (main, primary, secondary).
        Retorna um dict com {'robot_id', 'team', 'score', 'colors'} ou None se nenhum passar o threshold.
        """
        cand = []
        cand_colors = (np.asarray(main_hsv, dtype=int),
                    np.asarray(primary_hsv, dtype=int),
                    np.asarray(secondary_hsv, dtype=int))

        # 1) filtro por bounds
        for key, rec in self._store.items():  # key = (team_id, robot_id)
            bounds = rec['bounds']
            ok_main = self._in_bounds(cand_colors[0], bounds['main'][0], bounds['main'][1])
            ok_pri  = self._in_bounds(cand_colors[1], bounds['primary'][0], bounds['primary'][1])
            ok_sec  = self._in_bounds(cand_colors[2], bounds['secondary'][0], bounds['secondary'][1])

            if ok_main and ok_pri and ok_sec:
                cand.append((key, rec))

        # Relaxar se nenhum passou (apenas main + primary)
        if not cand:
            for key, rec in self._store.items():
                bounds = rec['bounds']
                ok_main = self._in_bounds(cand_colors[0], bounds['main'][0], bounds['main'][1])
                ok_pri  = self._in_bounds(cand_colors[1], bounds['primary'][0], bounds['primary'][1])
                if ok_main and ok_pri:
                    cand.append((key, rec))

        if not cand:
            return None

        # 2) score candidates
        scored = []
        for key, rec in cand:
            rec_cols = (rec['colors']['main'], rec['colors']['primary'], rec['colors']['secondary'])
            s = self._score_distance(cand_colors, rec_cols)
            scored.append((s, key, rec))

        scored.sort(key=lambda t: t[0])
        best_score, best_key, best_rec = scored[0]
        best_team_id, best_robot_id = best_key

        if best_score > score_threshold:
            return None

        return {
            'robot_id': best_robot_id,
            'team': best_team_id,
            'score': float(best_score),
            'colors': np.array([best_rec['colors']['main'],
                                best_rec['colors']['primary'],
                                best_rec['colors']['secondary']], dtype=int)
        }


    # utilitários
    def remove_robot(self, team_id: Any, robot_id: Any):
        key = (team_id, robot_id)
        if key in self._store:
            del self._store[key]


    def list_robots(self):
        return list(self._store.keys())

    def clear(self):
        self._store.clear()
