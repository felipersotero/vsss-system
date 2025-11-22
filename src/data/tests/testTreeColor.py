import numpy as np

class ColorTree:
    def __init__(self, tol_hue=10, tol_sv=50):
        """
        tol_hue : tolerância em Hue (0-179)
        tol_sv  : tolerância em S e V (0-255)
        """
        self.tree = {}  # Estrutura: {time_name: {time_hsv_tuple: {'time_bounds':(lower,upper), 'robots': {robot_name: {'primary':(lower,upper), 'secondary':(lower,upper)}}}}}
        self.tol_hue = tol_hue
        self.tol_sv = tol_sv

    # -----------------------------
    # Métodos internos de cor
    # -----------------------------
    def _compute_bounds(self, hsv):
        """
        Calcula limites lower/upper de HSV usando tolerância da árvore
        """
        h, s, v = hsv
        lower = np.array([
            max(0, h - self.tol_hue),
            max(0, s - self.tol_sv),
            max(0, v - self.tol_sv)
        ], dtype=np.uint8)
        upper = np.array([
            min(179, h + self.tol_hue),
            min(255, s + self.tol_sv),
            min(255, v + self.tol_sv)
        ], dtype=np.uint8)
        return lower, upper

    def _color_in_range(self, hsv_values, lower, upper):
        """
        Verifica se HSV está dentro dos limites precomputados
        """
        hsv_values = np.atleast_2d(hsv_values).astype(np.uint16)
        lower = np.array(lower, dtype=np.uint16)
        upper = np.array(upper, dtype=np.uint16)

        # Caso faixa cruza 0° do Hue
        if lower[0] > upper[0]:
            mask_hue = ((hsv_values[:, 0] >= lower[0]) | (hsv_values[:, 0] <= upper[0]))
        else:
            mask_hue = ((hsv_values[:, 0] >= lower[0]) & (hsv_values[:, 0] <= upper[0]))
        mask_sat = ((hsv_values[:, 1] >= lower[1]) & (hsv_values[:, 1] <= upper[1]))
        mask_val = ((hsv_values[:, 2] >= lower[2]) & (hsv_values[:, 2] <= upper[2]))
        mask = mask_hue & mask_sat & mask_val
        return mask[0] if hsv_values.shape[0] == 1 else mask

    # -----------------------------
    # Adicionar cores na árvore
    # -----------------------------
    def add_robot(self, time_name, time_hsv, robot_name, primary_hsv, secondary_hsv):
        """
        Adiciona um robô e suas cores à árvore, calculando limites internamente
        """
        # Pré-calcular limites
        time_bounds = self._compute_bounds(time_hsv)
        primary_bounds = self._compute_bounds(primary_hsv)
        secondary_bounds = self._compute_bounds(secondary_hsv)

        if time_name not in self.tree:
            self.tree[time_name] = {}
        t_hsv_key = tuple(time_hsv)
        if t_hsv_key not in self.tree[time_name]:
            self.tree[time_name][t_hsv_key] = {'time_bounds': time_bounds, 'robots': {}}

        self.tree[time_name][t_hsv_key]['robots'][robot_name] = {
            'primary': primary_bounds,
            'secondary': secondary_bounds
        }

    # -----------------------------
    # Buscar robô pelas 3 cores
    # -----------------------------
    def find_robot_by_hsvs(self, time_hsv, primary_hsv, secondary_hsv):
        """
        Recebe as 3 cores detectadas e retorna o nome do robô correspondente.
        """
        for time_name, time_entries in self.tree.items():
            for t_hsv, data in time_entries.items():
                if self._color_in_range(time_hsv, *data['time_bounds']):
                    for robot_name, color_dict in data['robots'].items():
                        if self._color_in_range(primary_hsv, *color_dict['primary']) and \
                           self._color_in_range(secondary_hsv, *color_dict['secondary']):
                            return time_name, robot_name
        return None, None

    # -----------------------------
    # Limpar árvore
    # -----------------------------
    def reset_tree(self):
        self.tree = {}

# -----------------------------
# Teste rápido
# -----------------------------
tree = ColorTree()

# Adiciona robôs
tree.add_robot("time1", np.array([0,255,255]), "goleiro", np.array([10,200,200]), np.array([15,200,200]))
tree.add_robot("time1", np.array([0,255,255]), "atacante1", np.array([20,200,200]), np.array([25,200,200]))
tree.add_robot("time2", np.array([120,255,255]), "goleiro", np.array([130,200,200]), np.array([135,200,200]))

# Busca
detected_time, detected_robot = tree.find_robot_by_hsvs(
    np.array([0,250,250]),
    np.array([10,205,205]),
    np.array([14,198,200])
)
print(detected_time, detected_robot)  # Deve retornar: time1 goleiro
