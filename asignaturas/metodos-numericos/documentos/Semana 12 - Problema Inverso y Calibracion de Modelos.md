# Semana 12 — El Problema Inverso y Calibración de Modelos

---

## 1. La Narrativa del Ingeniero

### El Escenario

Se trabaja en I+D para una empresa aeroespacial. Se acaba de imprimir en 3D una pieza de titanio con geometría de entramado (*lattice structure*) para reducir peso. Se tiene un **Modelo de Elementos Finitos (FEM)** que predice cómo se deforma la pieza bajo carga, pero el modelo necesita dos propiedades del material impreso: el **Módulo de Young** ($E$) y el **coeficiente de endurecimiento** ($n$).

El problema es que, debido al proceso de impresión, estas propiedades **no son las mismas** que las del titanio estándar.

### El Conflicto

Se fue al laboratorio, se estiró una probeta impresa y se obtuvieron **datos ruidosos** de fuerza vs. desplazamiento:

- **Teoría:** $\sigma = f(\epsilon, E, n)$
- **Realidad:** Se tiene $\sigma$ (datos) y $\epsilon$ (datos), pero no $E$ ni $n$
- **Limitación:** No se pueden despejar $E$ y $n$ algebraicamente porque la ecuación constitutiva es compleja y no lineal

### La Solución

Se utiliza el **Problema Inverso**: en lugar de ir de Parámetros → Resultados, se va de Resultados → Parámetros, formulando esto como un problema de **optimización**: se busca la combinación de $E$ y $n$ que minimice la diferencia entre la simulación y la realidad.

---

## 2. Fundamento Teórico

El problema inverso se resuelve reformulando la calibración como una **minimización de una función de costo**.

### 2.1 El Modelo Directo ($M$)

Función física que, dados parámetros $\mathbf{p}$ y entrada $\mathbf{x}$, predice una salida $\hat{y}$:

$$\hat{y} = M(\mathbf{x}; \mathbf{p})$$

### 2.2 La Función de Costo ($J$)

Cuantifica qué tan lejos está la predicción del modelo ($\hat{y}$) de los datos experimentales ($y_{\text{exp}}$). Se usa la **Suma de Errores Cuadráticos** (SSE):

$$J(\mathbf{p}) = \sum_{i=1}^{N} \left( y_{\text{exp}}^{(i)} - M(x^{(i)}; \mathbf{p}) \right)^2$$

### 2.3 La Optimización

Se busca el vector de parámetros $\mathbf{p}^*$ que minimice $J$:

$$\mathbf{p}^* = \underset{\mathbf{p}}{\text{argmin}} \ J(\mathbf{p})$$

Se utilizan algoritmos iterativos (BFGS, Nelder-Mead de `scipy.optimize`) que navegan por el "paisaje del error" buscando el valle más profundo.

### 2.4 Comparación: Problema Directo vs. Inverso

| | **Problema Directo** | **Problema Inverso** |
|:---|:---|:---|
| Dirección | Parámetros → Resultados | Resultados → Parámetros |
| Lo conocido | $E$, $n$, $\epsilon$ | $\sigma_{\text{exp}}$, $\epsilon_{\text{exp}}$ |
| Lo buscado | $\sigma$ (predicción) | $E$, $n$ (parámetros) |
| Herramienta | Evaluación del modelo | **Optimización** |
| Dificultad | Generalmente bien planteado | Puede ser **mal condicionado** (múltiples soluciones) |

---

## 3. Implementación en Python

### 3.1 Generación de Datos "Experimentales"

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.optimize import minimize
import seaborn as sns
sns.set_theme(style="whitegrid")

# Parámetros REALES (desconocidos para el ingeniero)
E_real = 200.0   # GPa (Módulo de Young)
K_real = 500.0   # MPa (parámetro de resistencia)
n_real = 10.0    # exponente de forma

def true_material_response(strain, E, K, n):
    """Modelo tipo Ramberg-Osgood simplificado"""
    return (E * strain) / ((1 + (E * strain / K)**n)**(1/n))

# Generar experimento virtual con ruido
np.random.seed(42)
strain_data = np.linspace(0, 0.05, 50)
noise = np.random.normal(0, 15, strain_data.shape)
stress_data = true_material_response(strain_data, E_real, K_real, n_real) + noise

df_lab = pd.DataFrame({'Strain': strain_data, 'Stress_MPa': stress_data})
print(df_lab.head())
```

### 3.2 Definición del Modelo y Función de Costo

```python
def model_prediction(params, strain):
    """Modelo teórico con parámetros a calibrar"""
    E, K, n = params
    if n <= 0 or K <= 0 or E <= 0:
        return 1e6 * np.ones_like(strain)
    return (E * strain) / ((1 + (E * strain / K)**n)**(1/n))

def objective_function(params, x_data, y_data):
    """Error Cuadrático Medio (MSE) — lo que el optimizador minimiza"""
    y_pred = model_prediction(params, x_data)
    return np.mean((y_data - y_pred)**2)
```

### 3.3 Proceso de Calibración

```python
# Adivinanza inicial (critical en ingeniería)
x0 = [150.0, 400.0, 1.0]

# Error inicial
print(f"Error con guess {x0}: {objective_function(x0, df_lab['Strain'], df_lab['Stress_MPa']):.2f}")

# Optimización con Nelder-Mead
result = minimize(
    objective_function,
    x0,
    args=(df_lab['Strain'], df_lab['Stress_MPa']),
    method='Nelder-Mead',
    tol=1e-4
)

print(f"Éxito: {result.success}")
print(f"Parámetros calibrados: E={result.x[0]:.2f} GPa, K={result.x[1]:.2f} MPa, n={result.x[2]:.2f}")
print(f"Parámetros reales:    E={E_real:.2f} GPa, K={K_real:.2f} MPa, n={n_real:.2f}")
```

### 3.4 Visualización de Resultados

```python
plt.figure(figsize=(10, 6))
plt.scatter(df_lab['Strain'], df_lab['Stress_MPa'],
            color='gray', alpha=0.6, label='Datos Exp. (Ruidosos)')

# Guess inicial
y_init = model_prediction(x0, df_lab['Strain'])
plt.plot(df_lab['Strain'], y_init, 'r--', label=f'Guess Inicial')

# Modelo calibrado
y_calib = model_prediction(result.x, df_lab['Strain'])
plt.plot(df_lab['Strain'], y_calib, 'b-', linewidth=2, label='Modelo Calibrado')

plt.title('Calibración de Modelo Constitutivo: Problema Inverso')
plt.xlabel('Deformación ($\\epsilon$) [-]')
plt.ylabel('Esfuerzo ($\\sigma$) [MPa]')
plt.legend()
plt.grid(True)
plt.show()
```

---

## 4. Evaluación y Tarea

### Actividad de Laboratorio: "El Termómetro Forense"

**Contexto:** Se entrega un set de datos de temperatura vs. tiempo de un motor enfriándose.

**Tareas:**
1. Limpiar los datos (eliminar outliers de fallas del sensor)
2. Proponer la Ley de Enfriamiento de Newton: $T(t) = T_{\text{amb}} + (T_0 - T_{\text{amb}})e^{-kt}$
3. Usar `scipy.optimize.minimize` para encontrar $k$ y $T_0$ (asumiendo $T_{\text{amb}}$ conocida)
4. **Pregunta crítica:** ¿Qué pasa si la adivinanza inicial $x_0$ es negativa para $k$? (Discusión sobre restricciones físicas vs. matemáticas)

### Debugging: Errores Típicos en Calibración

| Error | Síntoma | Corrección |
|:---|:---|:---|
| Función de costo sin elevar al cuadrado | El optimizador intenta llevar el error a $-\infty$ | Usar `(y_pred - y_data)**2` |
| Datos sin normalizar | Desbordamiento numérico (esfuerzo en Pa = 200,000,000) | Normalizar antes de optimizar |
| Adivinanza inicial en región plana | El optimizador no se mueve | Graficar la función de costo primero |

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
