# Semana 6 — Análisis de Componentes Principales (PCA)

---

## 1. Fundamento Teórico

El **Análisis de Componentes Principales** (PCA, por sus siglas en inglés) es una técnica de reducción de dimensionalidad que transforma un conjunto de variables posiblemente correlacionadas en un nuevo conjunto de variables **no correlacionadas** llamadas **componentes principales**.

PCA identifica las direcciones de **máxima varianza** en los datos y proyecta los datos originales sobre esas direcciones.

---

## 2. Motivación

En problemas de ingeniería con múltiples sensores y variables, es común encontrar:

- **Multicolinealidad:** variables altamente correlacionadas que aportan información redundante
- **Alta dimensionalidad:** muchas variables ($n$ grande) que dificultan la visualización y el modelado
- **Ruido:** variables con poca variación que solo aportan ruido de medición

PCA resuelve estos problemas encontrando una **base óptima** de menor dimensión.

---

## 3. Procedimiento Matemático

Dada una matriz de datos $\mathbf{X} \in \mathbb{R}^{m \times n}$ con $m$ observaciones y $n$ variables:

### Paso 1: Centrado de los Datos

Se resta la media de cada columna para que los datos tengan media cero:

$$\bar{x}_j = \frac{1}{m} \sum_{i=1}^{m} x_{ij}$$

$$\mathbf{X}_{\text{centrado}} = \mathbf{X} - \mathbf{1} \bar{\mathbf{x}}^T$$

### Paso 2: Escalado (Opcional pero Recomendado)

Cuando las variables tienen unidades diferentes, se escala por la desviación estándar:

$$x_{ij}^{\text{std}} = \frac{x_{ij} - \bar{x}_j}{\sigma_j}$$

Esto asegura que todas las variables contribuyan equitativamente.

### Paso 3: Matriz de Covarianza

Se calcula la matriz de covarianza de los datos centrados:

$$\mathbf{C} = \frac{1}{m-1} \mathbf{X}_{\text{centrado}}^T \mathbf{X}_{\text{centrado}}$$

- $\mathbf{C}_{jj} = \sigma_j^2$ (varianza de la variable $j$)
- $\mathbf{C}_{jk} = \text{Cov}(X_j, X_k)$ (covarianza entre variables $j$ y $k$)

### Paso 4: Descomposición Espectral

Se calculan los autovalores y autovectores de $\mathbf{C}$:

$$\mathbf{C} \mathbf{v}_i = \lambda_i \mathbf{v}_i$$

O equivalentemente, usando la **SVD** de $\mathbf{X}_{\text{centrado}}$:

$$\mathbf{X}_{\text{centrado}} = \mathbf{U} \mathbf{\Sigma} \mathbf{V}^T$$

Donde:
- $\lambda_i = \frac{\sigma_i^2}{m-1}$ (autovalores = valores singulares al cuadrado sobre $m-1$)
- $\mathbf{V}$ contiene los **componentes principales** (direcciones)

### Paso 5: Selección de Componentes

Los componentes se ordenan por varianza explicada descendente:

$$\text{Varianza explicada por } PC_k = \frac{\lambda_k}{\sum_{i=1}^n \lambda_i} \times 100\%$$

Se seleccionan los $k$ primeros componentes que capturen un porcentaje suficiente de la varianza total (típicamente $\geq 90\%$).

### Paso 6: Proyección

Los datos se proyectan al nuevo espacio de dimensión reducida:

$$\mathbf{Z} = \mathbf{X}_{\text{centrado}} \mathbf{V}_k$$

Donde $\mathbf{V}_k$ contiene las primeras $k$ columnas de $\mathbf{V}$.

---

## 4. Interpretación de los Componentes

| Concepto | Significado |
|----------|-------------|
| **PC1** | Dirección de **máxima varianza** en los datos |
| **PC2** | Dirección de máxima varianza **ortogonal a PC1** |
| **Loadings** ($\mathbf{V}$) | Pesos que indican cuánto contribuye cada variable original a cada componente |
| **Scores** ($\mathbf{Z}$) | Coordenadas de cada observación en el nuevo espacio |

---

## 5. Relación PCA-SVD

PCA y SVD están íntimamente relacionados:

| PCA | SVD |
|-----|-----|
| Matriz de covarianza $\mathbf{C}$ | $\mathbf{X}_{\text{centrado}} = \mathbf{U} \mathbf{\Sigma} \mathbf{V}^T$ |
| Autovalores $\lambda_i$ | $\lambda_i = \sigma_i^2 / (m-1)$ |
| Componentes principales | Columnas de $\mathbf{V}$ |
| Scores | $\mathbf{Z} = \mathbf{U} \mathbf{\Sigma}$ |

> **Ventaja práctica:** La SVD es numéricamente más estable que calcular la matriz de covarianza explícitamente, especialmente para datos mal condicionados.

---

## 6. Aplicaciones en Ingeniería

| Aplicación | Descripción |
|------------|-------------|
| **Reducción de dimensionalidad** | Datos de $n$ sensores → $k$ componentes ($k \ll n$) |
| **Visualización** | Proyección a 2D o 3D para inspección visual |
| **Detección de anomalías** | Observaciones con alto error de reconstrucción en el espacio reducido |
| **Compresión de datos** | Almacenar solo scores y loadings de los $k$ primeros componentes |
| **Análisis modal operacional** | Identificación de modos de vibración en estructuras civiles |

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
