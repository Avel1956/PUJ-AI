# Semana 11 — Fundamentos de Optimización

---

## 1. La Narrativa del Ingeniero

### El Problema: Diseño de un Tanque a Presión

Se trabaja en una planta petroquímica. Se necesita diseñar un contenedor a presión cilíndrico para almacenar $50\text{ m}^3$ de gas. El jefe de planta quiere **minimizar el costo** del material, pero el ingeniero de seguridad exige que el tanque soporte la presión interna sin fallar.

### La Limitación Analítica

En cálculo de primer semestre se aprende a derivar, igualar a cero y despejar $x$. Pero en la ingeniería real:

1. Hay **múltiples variables** de diseño (Radio $r$, Altura $h$, Espesor $t$)
2. Las ecuaciones de costo y seguridad **compiten entre sí** (objetivos en conflicto)
3. A menudo no se tiene una fórmula $f(x)$, sino una **simulación** (FEM, CFD) que devuelve un valor — no se puede "derivar" manualmente

### La Solución Computacional

Se necesita un algoritmo que actúe como un explorador en una montaña con niebla: que palpe el terreno (**gradiente**) y dé pasos iterativos hacia el valle más profundo (**costo mínimo**). Este es el corazón del diseño ingenieril y, además, es el mismo algoritmo que entrena las IAs modernas: el **Descenso de Gradiente**.

---

## 2. Fundamento Teórico

### 2.1 El Gradiente ($\nabla J$)

Vector de derivadas parciales que apunta hacia la dirección de **máximo crecimiento** de la función:

$$\nabla J(\mathbf{x}) = \left[ \frac{\partial J}{\partial x_1}, \frac{\partial J}{\partial x_2}, \dots, \frac{\partial J}{\partial x_n} \right]^T$$

### 2.2 Descenso de Gradiente (Gradient Descent)

Si se quiere **minimizar** el costo, se debe avanzar en la dirección **opuesta** al gradiente:

$$\mathbf{x}_{\text{nuevo}} = \mathbf{x}_{\text{viejo}} - \alpha \nabla J(\mathbf{x}_{\text{viejo}})$$

Donde $\alpha$ es la **tasa de aprendizaje** (*learning rate*):

| $\alpha$ muy pequeño | $\alpha$ muy grande |
|:---|:---|
| Convergencia lenta (muchas iteraciones) | Rebotes y divergencia (*overshooting*) |
| Puede quedar atrapado en mínimos locales | Puede "saltar" sobre el mínimo y divergir |

### 2.3 El Hessiano ($H$)

Matriz de segundas derivadas que informa sobre la **curvatura** del terreno:

$$H_{ij} = \frac{\partial^2 J}{\partial x_i \partial x_j}$$

- **Valle estrecho** → curvatura alta → paso pequeño
- **Llanura amplia** → curvatura baja → paso puede ser grande

Métodos como **Newton-Raphson para optimización** utilizan el Hessiano para dar pasos más informados.

### 2.4 Métodos de Optimización — Comparación

| Método | Usa Gradiente | Usa Hessiano | Robustez | Velocidad |
|:---|:---:|:---:|:---:|:---:|
| **Descenso de Gradiente** | ✓ | ✗ | Media | Lenta |
| **Newton-Raphson** | ✓ | ✓ | Baja | Rápida (cuadrática) |
| **Nelder-Mead** (Simplex) | ✗ | ✗ | Alta | Media |
| **BFGS** (Quasi-Newton) | ✓ | Aproximado | Media-Alta | Rápida |

---

## 3. Implementación en Python

### 3.1 Definición del Problema de Ingeniería

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize

# Parámetros del problema
V_target = 50.0    # Volumen deseado (m³)
C_material = 10.0  # Costo del acero ($/m²)
Penalty = 1000.0   # Penalización por desviación de volumen

def engineering_cost(params):
    """
    Costo total: material + penalización por error de volumen.
    params: [radio, altura]
    """
    r, h = params
    if r <= 0 or h <= 0:
        return 1e6  # Penalización para valores no físicos
    
    # Área superficial (tapas + cuerpo)
    area = 2 * np.pi * r**2 + 2 * np.pi * r * h
    cost_mat = area * C_material
    
    # Volumen actual
    vol = np.pi * r**2 * h
    
    # Función de costo con penalización (Penalty Method)
    total_cost = cost_mat + Penalty * (vol - V_target)**2
    return total_cost
```

### 3.2 Visualización del "Terreno" de Costo

```python
# Mapa de contorno del espacio de diseño
r_vals = np.linspace(1, 4, 100)
h_vals = np.linspace(1, 10, 100)
R, H = np.meshgrid(r_vals, h_vals)
Z = np.array([[engineering_cost([r, h]) for r in r_vals] for h in h_vals])

plt.figure(figsize=(10, 6))
cp = plt.contourf(R, H, np.log(Z), levels=30, cmap='viridis')
plt.colorbar(cp, label='Log(Costo)')
plt.title('Mapa de Costo del Diseño (Espacio de Búsqueda)')
plt.xlabel('Radio (m)')
plt.ylabel('Altura (m)')
plt.scatter([2], [4], c='red', marker='x', s=100, label='Adivinanza inicial')
plt.legend()
plt.show()
```

### 3.3 Descenso de Gradiente Manual

```python
def get_gradient(func, params, h=1e-5):
    """Gradiente numérico por diferencias finitas centrales"""
    grad = np.zeros_like(params)
    for i in range(len(params)):
        p_plus = params.copy()
        p_minus = params.copy()
        p_plus[i] += h
        p_minus[i] -= h
        grad[i] = (func(p_plus) - func(p_minus)) / (2 * h)
    return grad

learning_rate = 0.0001
iterations = 100
current = np.array([3.5, 8.0])  # Diseño inicial malo

path = [current.copy()]
for i in range(iterations):
    grad = get_gradient(engineering_cost, current)
    current = current - learning_rate * grad   # ← El núcleo del algoritmo
    path.append(current.copy())

path = np.array(path)
print(f"Final: r={current[0]:.2f}m, h={current[1]:.2f}m, Costo=${engineering_cost(current):.2f}")

# Visualizar trayectoria
plt.figure(figsize=(10, 6))
plt.contourf(R, H, np.log(Z), levels=30, cmap='viridis')
plt.plot(path[:, 0], path[:, 1], 'w.-', markersize=4, label='Trayectoria')
plt.plot(path[0, 0], path[0, 1], 'ro', label='Inicio')
plt.plot(path[-1, 0], path[-1, 1], 'r*', markersize=15, label='Óptimo')
plt.legend()
plt.show()
```

### 3.4 Solución Profesional con SciPy

```python
res = minimize(engineering_cost, [3.5, 8.0], method='Nelder-Mead')
print(f"Radio óptimo: {res.x[0]:.4f} m")
print(f"Altura óptima: {res.x[1]:.4f} m")
print(f"Costo mínimo: ${res.fun:.2f}")
print(f"Volumen resultante: {np.pi * res.x[0]**2 * res.x[1]:.2f} m³")
```

---

## 4. Evaluación y Tarea

### Actividad: Optimización de una Viga

Se entrega una función de "Costo de Viga" que depende de altura ($h$) y ancho ($b$) de la sección transversal, con ruido añadido (incertidumbre en precio del material). El estudiante debe:

1. Encontrar las dimensiones óptimas
2. Comparar Descenso de Gradiente vs. método de SciPy sobre superficie rugosa
3. Probar con $\alpha = 10$ para ver cómo el algoritmo **diverge**

### Debugging: Ascenso en vez de Descenso

Se entrega código donde la regla de actualización es:

```python
current_pos = current_pos + learning_rate * grad  # ← ERROR: suma en vez de resta
```

El costo **aumenta** infinitamente. El estudiante debe identificar que el signo está invertido (Ascenso de Gradiente en vez de Descenso).

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
