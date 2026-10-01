# Semana 4 — Sistemas Lineales y Factorización LU

---

## 1. Acoplamiento Físico y Sistemas de Ecuaciones

En muchos de los procesos ingenieriles, los componentes de un sistema **raramente actúan de forma aislada**. El comportamiento de un elemento discreto afecta y depende del estado de sus vecinos, lo que se conoce como **acoplamiento**.

En sistemas interdependientes, como armaduras estructurales, este fenómeno se modela usando **ecuaciones algebraicas lineales simultáneas**, cuya formulación para un sistema en equilibrio estático es:

$$\mathbf{K}\{\mathbf{u}\} = \{\mathbf{F}\}$$

| Símbolo | Significado |
|---------|-------------|
| $\mathbf{K}$ | **Matriz de rigidez** — propiedades geométricas y materiales del sistema |
| $\{\mathbf{u}\}$ | **Vector de desplazamientos** (incógnitas) — respuesta del sistema |
| $\{\mathbf{F}\}$ | **Vector de fuerzas** — cargas externas |

Este problema se generaliza en álgebra lineal como:

$$\mathbf{A}\mathbf{x} = \mathbf{b}$$

Sin embargo, se requieren **aproximaciones numéricas** cuando el cálculo tradicional se hace excesivamente costoso computacionalmente o poco preciso.

---

## 2. Sistemas Lineales y Estructuras Dispersas

En problemas de ingeniería estructural con miles de nodos, la matriz $\mathbf{K}$ es típicamente **dispersa** (*sparse*): la mayoría de sus elementos son cero.

### 2.1 Formato COO (*Coordinate List*)

Se almacenan únicamente los elementos no nulos como tripletas $(i, j, \text{valor})$:

```python
# Ejemplo de almacenamiento COO en Python (scipy.sparse)
from scipy.sparse import coo_matrix

row  = [0, 0, 1, 1, 2]     # índices de fila
col  = [0, 1, 1, 2, 2]     # índices de columna
data = [4, 1, 3, 2, 5]     # valores no nulos

A_coo = coo_matrix((data, (row, col)), shape=(3, 3))
```

### 2.2 Formato CSR (*Compressed Sparse Row*)

Más eficiente para operaciones matriciales. Almacena tres arreglos:

- `data`: valores no nulos (por filas)
- `indices`: índice de columna de cada valor
- `indptr`: punteros al inicio de cada fila en `data`

**Ejemplo — Barra 1D con 3 nodos:**

Matriz de rigidez:

$$\mathbf{K} = \begin{bmatrix} 100 & -100 & 0 \\ -100 & 300 & -200 \\ 0 & -200 & 200 \end{bmatrix}$$

Almacenamiento CSR:
- `data = [100, -100, -100, 300, -200, -200, 200]`
- `indices = [0, 1, 0, 1, 2, 1, 2]`
- `indptr = [0, 2, 5, 7]`

---

## 3. Ineficacia de la Inversión de Matrices

En álgebra lineal tradicional, la solución explícita para $\mathbf{A}\mathbf{x} = \mathbf{b}$ es:

$$\mathbf{x} = \mathbf{A}^{-1}\mathbf{b}$$

Sin embargo, en **computación científica** el cálculo de la matriz inversa $\mathbf{A}^{-1}$ se considera deficiente por dos motivos principales:

| Problema | Descripción |
|----------|-------------|
| **Costo computacional** | Calcular la inversa explícita requiere más operaciones que resolver el sistema directamente |
| **Inestabilidad numérica** | La inversión de matrices mal condicionadas (determinante cercano a cero) amplifica los errores de redondeo |

> **Axioma fundamental:** Nunca se invierte una matriz a menos que sea estrictamente necesario para un análisis teórico. Para hallar $\mathbf{x}$ se utilizan **métodos de factorización**.

---

## 4. Factorización LU

La factorización (o descomposición) **LU** es el algoritmo estándar para resolver sistemas de ecuaciones lineales en ingeniería. Descompone la matriz $\mathbf{A}$ en el producto de dos matrices triangulares:

$$\mathbf{A} = \mathbf{L} \cdot \mathbf{U}$$

| Matriz | Descripción |
|--------|-------------|
| $\mathbf{L}$ (*Lower*) | Matriz triangular **inferior** con elementos nulos encima de la diagonal y unos en la diagonal ($L_{ii} = 1$) |
| $\mathbf{U}$ (*Upper*) | Matriz triangular **superior** con elementos nulos bajo la diagonal |

---

## 5. Procedimiento de Solución

Una vez factorizada $\mathbf{A}$, el sistema original $\mathbf{A}\mathbf{x} = \mathbf{b}$ se transforma en:

$$\mathbf{L}(\mathbf{U}\mathbf{x}) = \mathbf{b}$$

Este sistema se resuelve en **dos pasos** muy eficientes computacionalmente:

### Paso A: Sustitución hacia Adelante (*Forward Substitution*)

Se define un vector auxiliar $\mathbf{y}$ tal que $\mathbf{L}\mathbf{y} = \mathbf{b}$. Como $\mathbf{L}$ es triangular inferior, $y_1$ se calcula inmediatamente, $y_2$ depende de $y_1$, y así sucesivamente:

$$y_i = b_i - \sum_{j=1}^{i-1} L_{ij} \, y_j$$

### Paso B: Sustitución hacia Atrás (*Backward Substitution*)

Con $\mathbf{y}$ conocido, se resuelve $\mathbf{U}\mathbf{x} = \mathbf{y}$. Dado que $\mathbf{U}$ es triangular superior, se comienza calculando $x_n$, luego $x_{n-1}$, hasta $x_1$:

$$x_i = \frac{1}{U_{ii}} \left( y_i - \sum_{j=i+1}^{n} U_{ij} \, x_j \right)$$

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
