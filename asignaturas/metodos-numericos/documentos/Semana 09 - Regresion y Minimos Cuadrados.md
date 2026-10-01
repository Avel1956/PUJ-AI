# Semana 9 — Regresión y Mínimos Cuadrados

---

## 1. El Problema Inverso

### Planteamiento

> Se realizan mediciones de $R$ a distintas temperaturas.
>
> - **Problema directo:** dados $\alpha = 0.5$ y $\beta = 10$, predecir $R$ para $T = 80\text{ °C}$
> - **Problema inverso:** determinar $\alpha$ y $\beta$ a partir de las mediciones

### Formulación General

Sea $f(x; \theta)$ un modelo paramétrico donde:
- $x$ es la variable de entrada
- $\theta = (\theta_0, \theta_1, \ldots, \theta_p)$ es el vector de **parámetros desconocidos**

Se dispone de $n$ observaciones experimentales:

$$\mathcal{D} = \{(x_1, y_1), (x_2, y_2), \ldots, (x_n, y_n)\}$$

Donde $y_i$ es el valor observado para la entrada $x_i$. En general hay un error introducido por errores de precisión, ruido, etc.:

$$y_i = f(x_i; \theta) + \varepsilon_i$$

- $\varepsilon_i$ es el **error** o **residuo** de la $i$-ésima observación

**El problema inverso consiste en encontrar $\theta$ tal que $f(x; \theta)$ sea lo más cercano posible a $y_i$ para todos los datos.**

---

## 2. El Residuo

Para un conjunto de parámetros $\theta$, el residuo de la observación $i$ se define como:

$$r_i(\theta) = y_i - f(x_i; \theta)$$

El residuo mide la **discrepancia** entre el valor observado y el valor predicho por el modelo.

> **Nota:** La condición $r_i = 0 \; \forall i$ (residuos exactamente nulos) requiere que el modelo pase exactamente por todos los datos experimentales, lo cual es **imposible** cuando hay más datos que parámetros y además implica ajustarse también al ruido de la medición.

---

## 3. Criterio de Mínimos Cuadrados

Se necesita una **función escalar** que agregue todos los residuos en una medida global del error.

La elección más utilizada es la **Suma de Cuadrados de los Residuos** (SCR o RSS por sus siglas en inglés):

$$S(\theta) = \sum_{i=1}^{n} r_i^2(\theta) = \sum_{i=1}^{n} \left[ y_i - f(x_i; \theta) \right]^2$$

El problema de **calibración** (o estimación) es entonces:

$$\hat{\theta} = \arg\min_{\theta} \, S(\theta)$$

### ¿Por qué los cuadrados?

| Razón | Explicación |
|-------|-------------|
| **Penaliza errores negativos y positivos por igual** | El cuadrado elimina el signo |
| **Penaliza más errores grandes que pequeños** | El cuadrado magnifica desviaciones grandes |
| **Es computable y analíticamente exacto** | Tiene solución cerrada (ecuaciones normales) |

---

## 4. Modelo Lineal Simple

Se parte del modelo lineal simple:

$$f(x; \theta_0, \theta_1) = \theta_0 + \theta_1 x$$

La función de pérdida (suma de cuadrados) es:

$$S(\theta_0, \theta_1) = \sum_{i=1}^{n} \left( y_i - (\theta_0 + \theta_1 x_i) \right)^2$$

Esta función es **diferenciable** en dos variables y su mínimo se encuentra donde el gradiente se anula, es decir, donde ambas derivadas parciales son cero:

$$\frac{\partial S}{\partial \theta_0} = -2 \sum_{i=1}^{n} (y_i - \theta_0 - \theta_1 x_i) = 0$$

$$\frac{\partial S}{\partial \theta_1} = -2 \sum_{i=1}^{n} x_i (y_i - \theta_0 - \theta_1 x_i) = 0$$

---

## 5. Ecuaciones Normales

Eliminando el $-2$ y distribuyendo se obtienen las **ecuaciones normales**:

$$\sum_{i=1}^{n} y_i - n\theta_0 - \theta_1 \sum_{i=1}^{n} x_i = 0$$

$$\sum_{i=1}^{n} x_i y_i - \theta_0 \sum_{i=1}^{n} x_i - \theta_1 \sum_{i=1}^{n} x_i^2 = 0$$

### Solución en Forma Compacta

Definiendo las medias y sumas de cuadrados:

$$\bar{x} = \frac{1}{n}\sum_{i=1}^{n} x_i, \quad \bar{y} = \frac{1}{n}\sum_{i=1}^{n} y_i$$

$$S_{xx} = \sum_{i=1}^{n} (x_i - \bar{x})^2 = \sum_{i=1}^{n} x_i^2 - n\bar{x}^2$$

$$S_{xy} = \sum_{i=1}^{n} (x_i - \bar{x})(y_i - \bar{y}) = \sum_{i=1}^{n} x_i y_i - n\bar{x}\bar{y}$$

La solución es:

$$\hat{\theta}_1 = \frac{S_{xy}}{S_{xx}}$$

$$\hat{\theta}_0 = \bar{y} - \hat{\theta}_1 \bar{x}$$

> **Interpretación de $\hat{\theta}_1$:** Mide la **covariación** entre $x$ e $y$, normalizada por la variación de $x$.

> **Interpretación de $\hat{\theta}_0$:** Implica que la recta de regresión pasa por el punto $(\bar{x}, \bar{y})$, que es el **centroide** de los datos.

---

## 6. Formulación Matricial

Este tipo de modelos, incluso los no lineales, pueden generalizarse y optimizarse computacionalmente usando álgebra matricial.

### Vector de Respuestas

$$\mathbf{y} = \begin{bmatrix} y_1 \\ y_2 \\ y_3 \\ \vdots \\ y_n \end{bmatrix}$$

### Matriz de Diseño

$$\mathbf{X} = \begin{bmatrix} 1 & X_1 \\ 1 & X_2 \\ 1 & X_3 \\ \vdots & \vdots \\ 1 & X_n \end{bmatrix}$$

### Modelo Matricial

$$\mathbf{y} = \mathbf{X}\boldsymbol{\theta}$$

La suma de cuadrados en forma matricial:

$$S(\boldsymbol{\theta}) = \|\mathbf{y} - \mathbf{X}\boldsymbol{\theta}\|^2 = (\mathbf{y} - \mathbf{X}\boldsymbol{\theta})^T (\mathbf{y} - \mathbf{X}\boldsymbol{\theta})$$

Minimizando con respecto a $\boldsymbol{\theta}$, las **ecuaciones normales matriciales** son:

$$\mathbf{X}^T \mathbf{X} \hat{\boldsymbol{\theta}} = \mathbf{X}^T \mathbf{y}$$

Si $\mathbf{X}^T \mathbf{X}$ es **invertible**:

$$\hat{\boldsymbol{\theta}} = (\mathbf{X}^T \mathbf{X})^{-1} \mathbf{X}^T \mathbf{y}$$

Esta expresión es el **estimador de mínimos cuadrados ordinarios** (OLS).

> **Precaución:** $\mathbf{X}^T \mathbf{X}$ no es invertible cuando uno de los parámetros es combinación lineal de otro (**multicolinealidad**).

---

## 7. Ejemplo de Calibración Manual

> Un experimento genera la posición $y$ (m) de un objeto en diferentes momentos $t$ (s). Se propone un modelo de movimiento uniforme simplificado: $y = \theta_0 + \theta_1 t$.

| $t_i$ (s) | $y_i$ (m) |
|:---:|:---:|
| 0 | 2.7 |
| 1 | 4.9 |
| 2 | 7.2 |
| 3 | 9.8 |
| 4 | 12.3 |

**Paso 1 — Calcular cantidades** ($n = 5$):

$$\bar{t} = \frac{0+1+2+3+4}{5} = 2, \quad \bar{y} = \frac{2.7+4.9+7.2+9.8+12.3}{5} = 7.38$$

$$\sum t_i^2 = 0+1+4+9+16 = 30, \quad S_{tt} = 30 - 5(2)^2 = 10$$

$$\sum t_i y_i = 0 + 4.9 + 14.4 + 29.4 + 49.2 = 97.9, \quad S_{ty} = 97.9 - 5(2)(7.38) = 24.1$$

**Paso 2 — Calcular parámetros calibrados:**

$$\hat{\theta}_1 = \frac{S_{ty}}{S_{tt}} = \frac{24.1}{10} = 2.41 \text{ m/s}$$

$$\hat{\theta}_0 = \bar{y} - \hat{\theta}_1 \bar{t} = 7.38 - 2.41(2) = 2.56 \text{ m}$$

**Modelo calibrado:** $\hat{y}(t) = 2.56 + 2.41t$

**Paso 3 — Verificar residuos** (siguiente sesión).

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
