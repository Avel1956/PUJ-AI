# Semana 10 — Raíces de Ecuaciones No Lineales

---

## 1. La Narrativa del Ingeniero

### Contexto: Diseño de Sistemas de Tuberías Industriales

Se es ingeniero de fluidos diseñando el sistema de refrigeración de una planta o un oleoducto. Para calcular la pérdida de presión por fricción en flujos turbulentos se utiliza la ecuación de **Colebrook-White**:

$$\frac{1}{\sqrt{f}} = -2 \log_{10} \left( \frac{\epsilon/D}{3.7} + \frac{2.51}{Re \sqrt{f}} \right)$$

**El bloqueo:** Esta ecuación es **implícita**: el factor de fricción $f$ aparece a ambos lados de la igualdad, dentro de un logaritmo y una raíz cuadrada. No existe manipulación algebraica que permita despejar $f = \dots$.

**La solución:** No se "despeja" la variable; se reformula el problema para encontrar la raíz de una función residual, y se deja que el computador itere hasta encontrar el equilibrio.

---

## 2. Fundamento Teórico

Para resolver una ecuación implícita, se convierte a la forma $g(x) = 0$. Se define el **residuo** como:

$$g(f) = \frac{1}{\sqrt{f}} + 2 \log_{10} \left( \frac{\epsilon/D}{3.7} + \frac{2.51}{Re \sqrt{f}} \right) = 0$$

Se busca el valor de $f$ que haga que $g(f) \approx 0$.

### 2.1 Método de Bisección (Cerrado)

| Característica | Descripción |
|:---|:---|
| **Concepto** | Si $g(a)$ y $g(b)$ tienen signos opuestos, la raíz está en $[a,b]$. Se corta el intervalo a la mitad repetidamente |
| **Algoritmo** | $c = \frac{a+b}{2}$; si $g(a) \cdot g(c) < 0$, entonces $b = c$; si no, $a = c$ |
| **Ventaja** | Convergencia **garantizada** (siempre que haya cambio de signo) |
| **Desventaja** | Convergencia **lenta** (lineal); requiere conocer un intervalo inicial $[a,b]$ |

### 2.2 Método de Newton-Raphson (Abierto)

Utiliza la pendiente (derivada) de la función para proyectar una mejor estimación:

$$x_{n+1} = x_n - \frac{g(x_n)}{g'(x_n)}$$

| Característica | Descripción |
|:---|:---|
| **Ventaja** | Convergencia **cuadrática** (muy rápida cerca de la raíz) |
| **Desventaja** | Puede **divergir** si la estimación inicial es mala o si $g'(x) \approx 0$ |
| **Requisito** | Se necesita la derivada $g'(x)$ (analítica o numérica) |

### 2.3 Criterios de Parada

| Criterio | Fórmula | Cuándo usarlo |
|:---|:---|:---|
| Error absoluto | $\|x_{n+1} - x_n\| < \text{tol}$ | Cuando la magnitud de $x$ es $\approx 1$ |
| Error relativo | $\frac{\|x_{n+1} - x_n\|}{\|x_{n+1}\|} < \text{tol}$ | Cuando la magnitud de $x$ varía mucho |
| Residuo | $\|g(x_n)\| < \text{tol}$ | Complementario; útil si $g'(x) \approx 0$ |

> ⚠️ **Error común:** Usar `while x != x_new:` como condición de parada. Debido al error de punto flotante (IEEE 754, Semana 2), es casi imposible que dos floats sean *exactamente* iguales. Siempre usar `while abs(x - x_new) > tolerancia:`.

---

## 3. Implementación en Python

### 3.1 Visualización (Paso Crítico)

Antes de pedirle al computador que busque, se debe **graficar** para saber dónde está la raíz. Físicamente, el factor de fricción $f$ para flujo turbulento suele estar entre 0.008 y 0.1.

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy import optimize

# Parámetros físicos
Re = 100000      # Número de Reynolds
ed = 0.001       # Rugosidad relativa (epsilon/D)

# Función Colebrook-White como g(f) = 0
def colebrook_residual(f, Re, ed):
    if f <= 0:
        return 1e6
    left = 1 / np.sqrt(f)
    right = -2.0 * np.log10((ed / 3.7) + (2.51 / (Re * np.sqrt(f))))
    return left - right

# Visualización
f_vals = np.linspace(0.008, 0.1, 100)
residuals = [colebrook_residual(f, Re, ed) for f in f_vals]

plt.figure(figsize=(10, 6))
plt.plot(f_vals, residuals, 'b-', label='Residuo g(f)')
plt.axhline(0, color='red', linestyle='--', label='Cero (Raíz buscada)')
plt.xlabel('Factor de Fricción (f)')
plt.ylabel('Valor del Residuo')
plt.title('Búsqueda Gráfica de la Raíz')
plt.legend()
plt.grid(True)
plt.show()
```

> 📊 La gráfica corta el eje cero cerca de 0.02. Ese será el *initial guess* ($x_0$).

### 3.2 Newton-Raphson Manual

```python
def derivative_approx(func, x, args, h=1e-5):
    """Derivada numérica por diferencias finitas centrales"""
    return (func(x + h, *args) - func(x - h, *args)) / (2 * h)

def newton_raphson(func, x0, args, tol=1e-6, max_iter=50):
    x = x0
    for i in range(max_iter):
        g_val = func(x, *args)
        g_prime = derivative_approx(func, x, args)
        
        if abs(g_prime) < 1e-10:
            print("¡Derivada cercana a cero! El método falla.")
            break
        
        x_new = x - g_val / g_prime
        
        if abs(x_new - x) < tol:
            return x_new
        
        x = x_new
    
    return x

f_sol = newton_raphson(colebrook_residual, x0=0.01, args=(Re, ed))
print(f"Factor de fricción: {f_sol:.5f}")
```

### 3.3 Solución Profesional con SciPy

En la práctica se usan algoritmos híbridos como **Brentq** que combinan la seguridad de la bisección con la velocidad de Newton:

```python
sol = optimize.root_scalar(
    colebrook_residual, args=(Re, ed),
    bracket=[0.001, 0.1], method='brentq'
)
print(f"Solución: {sol.root:.5f}")
print(f"Iteraciones: {sol.iterations}")
print(f"¿Convergió?: {sol.converged}")
```

---

## 4. Evaluación y Tarea

### Actividad: Calibración de un Termistor

La relación entre resistencia $R$ y temperatura $T$ de un termistor está dada por:

$$R = R_0 \exp\left[ \beta \left( \frac{1}{T} - \frac{1}{T_0} \right) \right]$$

El estudiante debe:

1. Recibir un dataset con valores medidos de $R$ (con ruido)
2. Dado $R_{\text{medido}}$, calcular $T$ usando búsqueda de raíces
3. **Reto:** Resolver la forma no despejable $R = A \cdot T^2 + B \cdot \ln(T)$

### Debugging: Bucle Infinito

Se entrega un código de Newton-Raphson que entra en bucle infinito. El error: `while x != x_new:` — debido a IEEE 754, cambiar a `while abs(x - x_new) > tolerancia:` y agregar `max_iter`.

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
