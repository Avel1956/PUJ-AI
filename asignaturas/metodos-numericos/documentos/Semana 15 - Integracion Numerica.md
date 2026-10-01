# Semana 15 — Integración Numérica

---

## 1. La Narrativa del Ingeniero

### El Escenario: Prueba de Frenado

Se es el ingeniero de dinámica en una prueba de frenado de un nuevo vehículo eléctrico. El coche está instrumentado con un acelerómetro de alta frecuencia que registra la aceleración longitudinal ($a_x$) cada 0.01 segundos durante una maniobra de emergencia.

El sensor entrega un archivo CSV con dos columnas: **tiempo** y **aceleración**. La pregunta del jefe es simple: *"¿Exactamente cuántos metros recorrió el auto antes de detenerse?"*

### El Bloqueo Teórico

En cálculo clásico: $x(t) = \iint a(t)\,dt\,dt$. Pero en la vida real:

1. **No hay función $a(t)$:** No existe una fórmula $a(t) = 5t^2$. Solo hay una nube de **puntos discretos**
2. **Los datos tienen ruido:** El sensor vibra, añadiendo errores
3. **Integrar el ruido genera "Drift":** Pequeños errores en aceleración se **acumulan** al integrar dos veces para llegar a la posición

---

## 2. Fundamento Teórico

La integración numérica aproxima el área bajo la curva definida por un conjunto de puntos discretos o una función difícil de integrar analíticamente.

### 2.1 Métodos de Newton-Cotes (Datos Tabulados)

Ideales para datos de sensores (puntos equiespaciados).

#### Regla del Trapecio

Aproxima el área entre dos puntos como un **trapecio lineal**. Robusta y simple:

$$I \approx \frac{h}{2} \left[ f(x_0) + 2\sum_{i=1}^{n-1} f(x_i) + f(x_n) \right]$$

Donde $h = x_{i+1} - x_i$ es el paso constante.

| Característica | Valor |
|:---|:---|
| Error de truncamiento | $O(h^2)$ |
| Grado de precisión | 1 (exacta para polinomios lineales) |
| Robustez | Alta |

#### Regla de Simpson 1/3

Ajusta **parábolas** (polinomios de grado 2) entre cada trío de puntos. Más precisa:

$$I \approx \frac{h}{3} \left[ f(x_0) + 4\sum_{i \text{ impar}} f(x_i) + 2\sum_{i \text{ par}} f(x_i) + f(x_n) \right]$$

| Característica | Valor |
|:---|:---|
| Error de truncamiento | $O(h^4)$ |
| Grado de precisión | 3 (exacta para polinomios cúbicos) |
| Requisito | Número **par** de subintervalos (impar de puntos) |

### 2.2 Cuadratura de Gauss (Integración de Funciones)

Base de los **Elementos Finitos (FEM)**. En lugar de puntos equiespaciados, se eligen **puntos óptimos** (puntos de Gauss) y pesos específicos para minimizar el error:

$$\int_{-1}^{1} f(x)\,dx \approx \sum_{i=1}^{n} w_i f(x_i)$$

> 🔑 Con solo **2 puntos de Gauss** se integra exactamente un polinomio **cúbico**. Esto hace que FEM sea computacionalmente eficiente.

---

## 3. Implementación en Python

### 3.1 Simulación del Acelerómetro

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import integrate
import seaborn as sns
sns.set_theme(style="whitegrid")

# Datos sintéticos de una frenada
t = np.linspace(0, 10, 100)              # 10 segundos
a_real = -5.0 * np.ones_like(t)          # Frenado ideal: -5 m/s²
a_real[t > 4] = 0                        # Se detiene a los 4s

# Añadir ruido gaussiano (sensor real)
np.random.seed(42)
noise = np.random.normal(0, 0.5, size=len(t))
a_medida = a_real + noise

df = pd.DataFrame({'tiempo': t, 'aceleracion': a_medida})

# Visualización
plt.figure(figsize=(10, 4))
plt.plot(t, a_real, 'r--', alpha=0.5, label='Real (desconocida)')
plt.plot(t, a_medida, 'b-', label='Lectura del sensor')
plt.xlabel('Tiempo (s)')
plt.ylabel('Aceleración (m/s²)')
plt.title('Lectura del Acelerómetro (con Ruido)')
plt.legend()
plt.show()
```

### 3.2 Integración Acumulativa (Trapecio)

```python
v0 = 20  # Velocidad inicial: 20 m/s (72 km/h)

# Integrar aceleración → velocidad
v_trapz = integrate.cumulative_trapezoid(
    df['aceleracion'], df['tiempo'], initial=0
)
v_calculada = v_trapz + v0

# Integrar velocidad → posición
posicion = integrate.cumulative_trapezoid(
    v_calculada, df['tiempo'], initial=0
)
```

### 3.3 Comparación y Análisis del "Drift"

```python
# Solución teórica para comparar
v_teorica = v0 + a_real * t
v_teorica[t > 4] = 0

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

ax1.plot(t, v_teorica, 'k--', label='Teórica')
ax1.plot(t, v_calculada, 'g-', label='Integración Numérica')
ax1.set_title('Velocidad Recuperada del Sensor')
ax1.set_ylabel('Velocidad (m/s)')
ax1.legend()

ax2.plot(t, posicion, 'm-')
ax2.set_title('Posición Estimada (Distancia de Frenado)')
ax2.set_ylabel('Distancia (m)')
ax2.set_xlabel('Tiempo (s)')

plt.tight_layout()
plt.show()
```

### 3.4 Cuadratura de Gauss con SciPy

```python
def f(x):
    return np.sin(x) * np.exp(-0.1 * x)

result, error = integrate.quad(f, 0, 10)
print(f"Integral (Quad Gaussiana): {result:.5f}")
print(f"Error estimado: {error:.2e}")
```

---

## 4. Evaluación y Tarea

### Actividad de Laboratorio: "El Problema del Sismógrafo"

**Datos:** Archivo `.csv` de un sismograma (aceleración del suelo) de un terremoto.

**Tareas:**
1. Cargar y limpiar los datos (repaso Semanas 1–2)
2. Integrar aceleración → velocidad del suelo
3. Integrar velocidad → desplazamiento del suelo
4. **El Reto:** Al final del terremoto, el desplazamiento calculado NO vuelve a cero (el edificio parece haberse movido 50 metros)
5. **Corrección:** Aplicar "Corrección de Línea Base" (restar tendencia lineal) para eliminar el *drift* numérico

### Debugging: Error Dimensional

```python
# CÓDIGO CON ERROR — el estudiante olvida multiplicar por dt
velocidad = []
for i in range(len(aceleracion)):
    area = aceleracion[i]              # ← ERROR: dimensionalmente incorrecto
    velocidad.append(area)             #    m/s² ≠ m/s
```

**Corrección:** `area = aceleracion[i] * dt` o usar `integrate.cumulative_trapezoid`.

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
