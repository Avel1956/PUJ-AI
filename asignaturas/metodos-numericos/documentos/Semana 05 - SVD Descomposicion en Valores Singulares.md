# Semana 5 — Descomposición en Valores Singulares (SVD)

---

## 1. Fundamento Teórico

La **Descomposición en Valores Singulares** (*Singular Value Decomposition*, SVD) es una de las factorizaciones matriciales más importantes en álgebra lineal computacional. Permite descomponer cualquier matriz $\mathbf{A} \in \mathbb{R}^{m \times n}$ como el producto de tres matrices:

$$\mathbf{A} = \mathbf{U} \, \mathbf{\Sigma} \, \mathbf{V}^T$$

Donde:

| Matriz | Dimensiones | Propiedad |
|--------|-------------|-----------|
| $\mathbf{U}$ | $m \times m$ | Matriz **ortogonal**: $\mathbf{U}^T\mathbf{U} = \mathbf{I}$. Sus columnas son los **vectores singulares izquierdos** |
| $\mathbf{\Sigma}$ | $m \times n$ | Matriz **diagonal** con los valores singulares $\sigma_1 \geq \sigma_2 \geq \cdots \geq \sigma_r > 0$ en la diagonal |
| $\mathbf{V}^T$ | $n \times n$ | Matriz **ortogonal** transpuesta. Sus filas (columnas de $\mathbf{V}$) son los **vectores singulares derechos** |

---

## 2. Interpretación Geométrica

La SVD revela la **acción geométrica** de una matriz sobre un vector:

1. $\mathbf{V}^T$ **rota** el vector de entrada al sistema de coordenadas de los vectores singulares derechos
2. $\mathbf{\Sigma}$ **escala** cada componente por su valor singular correspondiente ($\sigma_i$)
3. $\mathbf{U}$ **rota** el resultado al sistema de coordenadas de salida

$$\mathbf{A}\mathbf{x} = \mathbf{U} \left( \mathbf{\Sigma} \left( \mathbf{V}^T \mathbf{x} \right) \right)$$

> Cualquier transformación lineal puede entenderse como: **rotar → escalar → rotar**.

---

## 3. Propiedades Fundamentales

### 3.1 Valores Singulares

Los valores singulares $\sigma_i$ son:
- **Siempre no negativos:** $\sigma_i \geq 0$
- **Ordenados descendentemente:** $\sigma_1 \geq \sigma_2 \geq \cdots \geq \sigma_r > 0$
- El número de valores singulares no nulos es igual al **rango** de $\mathbf{A}$

### 3.2 Relación con Autovalores

Los valores singulares de $\mathbf{A}$ están relacionados con los autovalores de $\mathbf{A}^T\mathbf{A}$ y $\mathbf{A}\mathbf{A}^T$:

$$\sigma_i = \sqrt{\lambda_i(\mathbf{A}^T\mathbf{A})} = \sqrt{\lambda_i(\mathbf{A}\mathbf{A}^T)}$$

- $\mathbf{V}$ contiene los **autovectores** de $\mathbf{A}^T\mathbf{A}$
- $\mathbf{U}$ contiene los **autovectores** de $\mathbf{A}\mathbf{A}^T$

### 3.3 Norma y Condicionamiento

- **Norma espectral:** $\|\mathbf{A}\|_2 = \sigma_1$ (el mayor valor singular)
- **Número de condición:** $\kappa(\mathbf{A}) = \frac{\sigma_1}{\sigma_r}$ (para el rango $r$)

---

## 4. SVD Reducida (*Economy SVD*)

Cuando $m \gg n$ (más filas que columnas, caso típico en datos), la SVD completa contiene información redundante. La **SVD reducida** solo conserva las $n$ primeras columnas de $\mathbf{U}$ y la matriz $\mathbf{\Sigma}$ cuadrada $n \times n$:

$$\mathbf{A}_{m \times n} = \mathbf{U}_{m \times n} \, \mathbf{\Sigma}_{n \times n} \, \mathbf{V}^T_{n \times n}$$

---

## 5. Aplicaciones en Ingeniería

| Aplicación | Descripción |
|------------|-------------|
| **PCA** | La SVD es la base matemática del Análisis de Componentes Principales |
| **Compresión de datos** | Aproximación de bajo rango: descartando valores singulares pequeños se reduce dimensionalidad |
| **Problemas inversos** | Regularización mediante truncamiento de valores singulares (TSVD) |
| **Análisis modal** | En vibraciones, los valores singulares identifican modos dominantes |
| **Procesamiento de señales** | Filtrado de ruido eliminando componentes de baja energía |

---

## 6. Aproximación de Bajo Rango

La SVD permite construir la **mejor aproximación de rango $k$** a una matriz (teorema de Eckart-Young):

$$\mathbf{A}_k = \sum_{i=1}^{k} \sigma_i \, \mathbf{u}_i \, \mathbf{v}_i^T$$

Donde $\mathbf{u}_i$ y $\mathbf{v}_i$ son las columnas de $\mathbf{U}$ y $\mathbf{V}$ respectivamente.

- $\mathbf{A}_k$ minimiza $\|\mathbf{A} - \mathbf{A}_k\|_2$ entre todas las matrices de rango $k$
- La energía retenida es $\frac{\sum_{i=1}^k \sigma_i^2}{\sum_{i=1}^r \sigma_i^2}$

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
