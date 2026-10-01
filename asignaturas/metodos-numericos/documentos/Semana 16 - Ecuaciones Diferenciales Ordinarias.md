# Semana 16 — Ecuaciones Diferenciales Ordinarias (EDO)

---

## 1. La Narrativa del Ingeniero

### El Problema: Diseño de Suspensión de un Vehículo Off-Road

Se está diseñando el sistema de suspensión de un vehículo todoterreno. Se necesita garantizar que, cuando el vehículo atraviese un bache o un resalto a 40 km/h, la aceleración vertical transmitida al conductor **no supere** el umbral de confort y que la suspensión no golpee sus topes mecánicos.

### La Limitación Teórica

Por la Segunda Ley de Newton, el sistema se rige por:

$$m\ddot{x} + c\dot{x} + kx = F(t)$$

En los libros de texto, $F(t)$ suele ser cero (vibración libre) o una onda seno perfecta. Pero en la realidad:

- El perfil de la carretera es **irregular, discontinuo** o una señal compleja de un sensor
- Resolver esto analíticamente es **imposible** o ineficiente para perfiles de carga reales

Se necesita "integrar" el movimiento **paso a paso en el tiempo** usando el computador.

---

## 2. Fundamento Teórico

### 2.1 Reducción a Sistema de Primer Orden

No se resuelve la ecuación de segundo orden directamente. Se convierte en un **sistema de ecuaciones de primer orden** definiendo el **Vector de Estado**:

$$\mathbf{y}(t) = \begin{bmatrix} x(t) \\ v(t) \end{bmatrix}$$

Donde $x$ es posición y $v$ es velocidad. Derivando:

$$\frac{d\mathbf{y}}{dt} = \begin{bmatrix} v(t) \\ a(t) \end{bmatrix} = \begin{bmatrix} v(t) \\ \frac{1}{m}\big(F(t) - c \cdot v(t) - k \cdot x(t)\big) \end{bmatrix}$$

Esto tiene la forma general:

$$\frac{d\mathbf{y}}{dt} = \mathbf{f}(t, \mathbf{y})$$

### 2.2 Método de Euler (Explícito)

Proyecta el futuro usando la pendiente actual:

$$\mathbf{y}_{n+1} = \mathbf{y}_n + h \cdot \mathbf{f}(t_n, \mathbf{y}_n)$$

| Característica | Valor |
|:---|:---|
| Precisión | $O(h)$ — primer orden |
| Estabilidad | Condicional (requiere $h$ pequeño) |
| Uso | **Didáctico** — no profesional |

> ⚠️ Acumula error rápidamente y es inestable si $h$ no es suficientemente pequeño.

### 2.3 Runge-Kutta 45 (RK45) — El Estándar Industrial

Evalúa la pendiente en **varios puntos intermedios** para predecir el siguiente paso con alta precisión. Ajusta el tamaño del paso $h$ **dinámicamente** según la curvatura de la solución:

$$k_1 = \mathbf{f}(t_n, \mathbf{y}_n)$$
$$k_2 = \mathbf{f}\!\left(t_n + \frac{h}{2}, \mathbf{y}_n + \frac{h}{2}k_1\right)$$
$$k_3 = \mathbf{f}\!\left(t_n + \frac{h}{2}, \mathbf{y}_n + \frac{h}{2}k_2\right)$$
$$k_4 = \mathbf{f}(t_n + h, \mathbf{y}_n + h k_3)$$
$$\mathbf{y}_{n+1} = \mathbf{y}_n + \frac{h}{6}(k_1 + 2k_2 + 2k_3 + k_4)$$

| Característica | Valor |
|:---|:---|
| Precisión | $O(h^4)$ — cuarto orden |
| Paso adaptativo | ✓ (RK45 = pareja 4º/5º orden) |
| Uso | **Profesional** — `scipy.integrate.solve_ivp` |

### 2.4 Concepto de Rigidez (Stiffness)

Un sistema es **rígido** (*stiff*) cuando tiene dinámicas en escalas de tiempo muy diferentes. Métodos explícitos (Euler, RK45) requieren pasos **extremadamente pequeños** para mantener estabilidad. Para sistemas rígidos se usan **métodos implícitos** (Radau, BDF).

---

## 3. Implementación en Python

### 3.1 Modelo del Sistema de Suspensión

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# Parámetros físicos
m = 450.0      # Masa suspendida (kg) — un cuarto de vehículo
k = 35000.0    # Rigidez del resorte (N/m)
c = 4000.0     # Amortiguamiento (N·s/m)

# Perfil de la carretera
def perfil_carretera(t):
    """Bache trapezoidal: 10 cm entre t=1s y t=1.5s"""
    return 0.10 if 1.0 <= t <= 1.5 else 0.0

# Sistema de EDOs
def suspension_dynamics(t, y):
    """y = [posición, velocidad]"""
    x, v = y
    x_suelo = perfil_carretera(t)
    
    fuerza_resorte = k * (x_suelo - x)
    fuerza_amortiguador = c * (0 - v)
    aceleracion = (fuerza_resorte + fuerza_amortiguador) / m
    
    return [v, aceleracion]
```

### 3.2 Euler Manual (Propósito Didáctico)

```python
dt = 0.05                      # Paso grande para evidenciar error
t_euler = np.arange(0, 5, dt)
y_euler = np.zeros((len(t_euler), 2))
y_euler[0] = [0.0, 0.0]        # [posición inicial, velocidad inicial]

for i in range(len(t_euler) - 1):
    dydt = suspension_dynamics(t_euler[i], y_euler[i])
    y_euler[i+1, 0] = y_euler[i, 0] + dydt[0] * dt
    y_euler[i+1, 1] = y_euler[i, 1] + dydt[1] * dt
```

### 3.3 Solución Profesional: `solve_ivp` (RK45)

```python
sol = solve_ivp(
    suspension_dynamics,
    t_span=[0, 5],
    y0=[0.0, 0.0],
    method='RK45',
    t_eval=np.linspace(0, 5, 500)   # Puntos de salida
)
```

### 3.4 Comparación Euler vs. RK45

```python
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# Posición
ax1.plot(t_euler, y_euler[:, 0], 'r--', label='Euler (dt=0.05s)')
ax1.plot(sol.t, sol.y[0], 'b-', linewidth=2, label='SciPy RK45')
ax1.set_ylabel('Desplazamiento (m)')
ax1.set_title('Respuesta de la Suspensión: Euler vs. RK45')
ax1.legend()
ax1.grid(True)

# Velocidad
ax2.plot(t_euler, y_euler[:, 1], 'r--')
ax2.plot(sol.t, sol.y[1], 'b-', linewidth=2)
ax2.set_ylabel('Velocidad (m/s)')
ax2.set_xlabel('Tiempo (s)')
ax2.grid(True)

plt.tight_layout()
plt.show()
```

> 📊 Euler sobrestima la respuesta y muestra picos falsos. RK45 suaviza correctamente. **No usar Euler para sistemas que afectan la seguridad humana.**

---

## 4. Evaluación y Tarea

### Actividad de Laboratorio: "Diseño de Amortiguadores"

1. Modificar `perfil_carretera` para importar un `.csv` con datos reales de un acelerómetro
2. Iterar sobre el valor de $c$ (amortiguamiento) usando un bucle
3. **Objetivo:** Encontrar el $c$ que minimice el tiempo de estabilización (oscilación < 1 mm) después del impacto

### Debugging: Errores Típicos

| Error | Síntoma | Causa |
|:---|:---|:---|
| Signo del amortiguamiento | La energía **crece** sin input externo | `+c*v` en vez de `-c*v` (inyecta energía en vez de disiparla) |
| Indexado invertido | Resultados sin sentido físico | `v, x = y` en vez de `x, v = y` |
| Paso de tiempo muy grande | Euler diverge | Reducir `dt` o usar RK45 |

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
