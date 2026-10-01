# Semana 17 — Cuantificación de Incertidumbre (Monte Carlo) y Método de Elementos Finitos 1D

---

## PARTE A — Simulación de Monte Carlo

---

### A.1 La Narrativa del Ingeniero

Se diseña una viga de acero para un puente peatonal. El manual dice que el acero estructural tiene un límite elástico $f_y = 250\text{ MPa}$. Pero en la realidad:

- El **proveedor** entrega aceros con $f_y$ entre 230 y 270 MPa
- La **carga viva** (personas) varía entre 2 y 5 kN/m²
- Las **dimensiones** de fabricación tienen tolerancias de $\pm 3\text{ mm}$

> **Pregunta clave:** ¿Cuál es la **probabilidad de falla** considerando todas estas fuentes de incertidumbre simultáneamente?

El enfoque determinista tradicional usa **factores de seguridad** ($FS = 1.5$). Pero esto no cuantifica el **riesgo real**. La Simulación de Monte Carlo responde: "De 100,000 escenarios simulados, la viga falla en 234 — probabilidad de falla $\approx 0.23\%$".

---

### A.2 Fundamento Teórico

La Simulación de Monte Carlo es un método numérico que usa **muestreo aleatorio repetido** para estimar cantidades deterministas (probabilidades, integrales, valores esperados).

#### Procedimiento General

```
1. IDENTIFICAR parámetros inciertos y sus distribuciones
        ↓
2. GENERAR N muestras aleatorias de cada parámetro
        ↓
3. EVALUAR el modelo para cada combinación
        ↓
4. AGREGAR resultados (histograma, media, intervalo de confianza)
```

#### Ley de los Grandes Números

A medida que $N \to \infty$, la media muestral converge a la media poblacional:

$$\bar{X}_N = \frac{1}{N}\sum_{i=1}^{N} X_i \longrightarrow \mu \quad \text{cuando } N \to \infty$$

#### Error de Monte Carlo

El error escala como $O(1/\sqrt{N})$:

$$\text{Error} \approx \frac{\sigma}{\sqrt{N}}$$

> 🔑 Para reducir el error a la mitad, se necesita **cuadruplicar** el número de simulaciones.

---

### A.3 Implementación en Python

```python
import numpy as np
import matplotlib.pyplot as plt

# --- 1. Definir distribuciones de parámetros inciertos ---
N = 100000  # Número de simulaciones

# Resistencia del acero: Normal(250, 15) MPa
fy = np.random.normal(250, 15, N)

# Carga: Uniforme entre 2 y 5 kN/m²
q = np.random.uniform(2, 5, N)

# Ancho de viga: Normal(200, 2) mm
b = np.random.normal(200, 2, N)

# Altura de viga: Normal(400, 3) mm
h = np.random.normal(400, 3, N)

# --- 2. Modelo determinista (viga simplemente apoyada) ---
L = 5000  # Luz en mm

# Momento máximo: M = q*L²/8  (kN·mm/mm → MPa después de convertir)
M = q * L**2 / 8 * 1000  # Convertir a N·mm/mm

# Módulo resistente: S = b*h²/6  (mm³)
S = b * h**2 / 6

# Esfuerzo máximo: sigma = M/S  (MPa)
sigma_max = M / S

# --- 3. Análisis de resultados ---
falla = sigma_max > fy
prob_falla = np.mean(falla) * 100

print(f"Probabilidad de falla: {prob_falla:.2f}%")
print(f"Intervalo de confianza 95% para sigma: "
      f"[{np.percentile(sigma_max, 2.5):.1f}, "
      f"{np.percentile(sigma_max, 97.5):.1f}] MPa")

# --- 4. Visualización ---
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

axes[0].hist(fy, bins=50, color='steelblue', edgecolor='white', alpha=0.8)
axes[0].axvline(250, color='red', linestyle='--', label='Nominal')
axes[0].set_title('Resistencia $f_y$ (MPa)')
axes[0].legend()

axes[1].hist(sigma_max, bins=50, color='darkorange', edgecolor='white', alpha=0.8)
axes[1].axvline(250, color='red', linestyle='--', label='$f_y$ nominal')
axes[1].set_title('Esfuerzo máximo $\sigma$ (MPa)')
axes[1].legend()

axes[2].hist(sigma_max[falla], bins=30, color='crimson', edgecolor='white', alpha=0.8)
axes[2].set_title(f'Casos de falla ({np.sum(falla)} de {N})')

plt.tight_layout()
plt.show()
```

---

## PARTE B — Método de Elementos Finitos 1D (Barra Axial)

---

### B.1 ¿Por qué el MEF?

Consideremos una viga de sección variable sometida a cargas distribuidas, apoyada sobre cimentación elástica no uniforme. Su comportamiento está gobernado por una EDO que **no admite solución analítica exacta** en la mayoría de casos prácticos.

> **Idea central del MEF:** Dividir el dominio en subdominios pequeños (**elementos**), aproximar la solución en cada uno con funciones simples (polinomios de bajo grado), y exigir consistencia entre elementos → **sistema de ecuaciones algebraicas** $K u = F$.

### B.2 El Problema Modelo: Barra Axial

```text
  ▓▓▓|————————————————————————→ P
  ▓▓▓|   f(x) ↓↓↓↓↓↓↓↓↓↓
  ▓▓▓|════════════════════|
  u=0  x=0              x=L
```

Ecuación diferencial gobernante:

$$-\frac{d}{dx}\!\left[EA\,\frac{du}{dx}\right] = f(x), \qquad 0 < x < L$$

Con condiciones de frontera: $u(0) = 0$, $EA\,\frac{du}{dx}\big|_{x=L} = P$.

### B.3 La Formulación Débil

Se multiplica por una función de prueba $v(x)$ (con $v(0)=0$), se integra y se aplica integración por partes:

$$\int_0^L EA\,\frac{du}{dx}\,\frac{dv}{dx}\,dx = \int_0^L f\,v\,dx + P \cdot v(L)$$

> 🔑 La integración por partes **reduce el orden** de derivadas (de 2º a 1º) e **incorpora automáticamente** las condiciones naturales de frontera.

### B.4 Discretización: Elementos y Funciones de Forma

Se divide $[0,L]$ en $n$ elementos mediante nodos $x_1, x_2, \dots, x_{n+1}$.

Dentro del elemento $e$ (nodos $x_a$, $x_b$, longitud $\ell_e = x_b - x_a$):

$$u(x) \approx u^e(x) = N_1(x)\,u_a + N_2(x)\,u_b$$

**Funciones de forma lineales:**

$$N_1(x) = \frac{x_b - x}{\ell_e}, \qquad N_2(x) = \frac{x - x_a}{\ell_e}$$

Propiedades: $N_i(x_j) = \delta_{ij}$ (vale 1 en su nodo, 0 en los demás).

### B.5 Matriz de Rigidez Elemental

$$K^e_{ij} = \int_{x_a}^{x_b} EA\,\frac{dN_i}{dx}\,\frac{dN_j}{dx}\,dx$$

Resultado (para $EA$ y $\ell_e$ constantes):

$$\boxed{\mathbf{K}^e = \frac{EA}{\ell_e}\begin{bmatrix} 1 & -1 \\ -1 & 1 \end{bmatrix}}$$

> ✎ **Esta es la rigidez de un resorte lineal.** El MEF transforma una EDO en una red de resortes.

**Vector de fuerzas elementales** (carga uniforme $f$):

$$\mathbf{f}^e = \frac{f\,\ell_e}{2}\begin{Bmatrix}1\\1\end{Bmatrix}$$

### B.6 Ensamblaje Global y Condiciones de Frontera

Cada $\mathbf{K}^e$ ($2 \times 2$) aporta a la matriz global $\mathbf{K}$ ($(n+1)\times(n+1)$). Las entradas se **acumulan** en las posiciones correspondientes.

Para 2 elementos uniformes (3 nodos):

$$\mathbf{K} = k\begin{bmatrix} 1 & -1 & 0 \\ -1 & 2 & -1 \\ 0 & -1 & 1 \end{bmatrix}, \quad k = \frac{EA}{\ell}$$

Aplicando $u_1 = 0$ (empotramiento) por modificación fila/columna y resolviendo $\mathbf{K}\mathbf{u} = \mathbf{F}$, se obtienen los desplazamientos nodales.

### B.7 Post-proceso: Esfuerzos

$$\sigma^e = E\,\frac{du^e}{dx} = \frac{E}{\ell_e}(u_b - u_a)$$

El esfuerzo es **constante dentro de cada elemento** y discontinuo en los nodos (normal para elementos lineales; se refina con más elementos).

---

## 4. Evaluación y Tarea

### Actividad Integradora (Proyecto Final)

Combinar ambas técnicas:

1. **Modelar** una barra axial con propiedades de material **inciertas** ($E \sim \text{Normal}$, carga $f \sim \text{Uniforme}$)
2. **Resolver** con MEF 1D para cada muestra de Monte Carlo ($N = 10,\!000$)
3. **Reportar:** distribución de desplazamiento máximo, probabilidad de exceder desplazamiento admisible
4. **Entregable:** Notebook de Jupyter + informe (máx. 4 páginas) con figuras y conclusiones

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
