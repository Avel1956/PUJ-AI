# Semana 1 — El Ingeniero como Científico de Datos

## Módulo I: Adquisición y Limpieza de Datos

---

## 1. Ingeniería de Datos

Es la disciplina que se enfoca en diseñar, construir y mantener sistemas para recopilar, almacenar, procesar y analizar información de manera eficiente.

Los ingenieros de datos crean flujos de trabajo que garantizan la calidad, accesibilidad y escalabilidad de los datos para apoyar la toma de decisiones informadas.

Se distinguen tres roles complementarios:

| Rol | Enfoque |
|-----|---------|
| **Ingeniería de Datos** | Infraestructura y flujo de datos |
| **Ciencia de Datos** | Análisis y modelado predictivo con datos existentes |
| **Análisis de Datos** | Insights descriptivos y visualización |

## 2. El Paradigma Ingenieril Moderno

El ingeniero moderno debe estar preparado para usar datos "sucios", en muchos casos señales de series temporales ruidosas.

- **El dato crudo no es información, es la materia prima.**
- **Objetivo:** Transformar datos crudos (lecturas de sensores: voltajes, deformaciones, resistencia, etc.) en magnitudes físicas confiables (deformación, temperatura, etc.).

## 3. Estructura de Datos Tabulares

Generalmente los datos pueden ordenarse en estructuras matriciales:

$$D = \begin{bmatrix} 
t_0 & S_{1,0} & \cdots & S_{n,0} \\
t_1 & S_{1,1} & \cdots & S_{n,1} \\
\vdots & \vdots & \ddots & \vdots \\
t_m & S_{1,m} & \cdots & S_{n,m}
\end{bmatrix}$$

Donde:
- **$m$ (filas):** observaciones o instantes de muestreo
- **$n$ (columnas):** variables o *features*

## 4. Epistemología del Dato en Ingeniería

En pregrado es normal adquirir un enfoque determinista ($y = f(x)$) donde las entradas son conocidas y exactas. **En la ingeniería real se opera en un entorno estocástico e imperfecto.**

El dato crudo no es la realidad física, es una aproximación digital sujeta a una **cadena de degradación**:

```
Fenómeno físico (Realidad continua)
        ↓
Transducción (Conversión voltaje/corriente + ruido térmico)
        ↓
Digitalización (Cuantización y discretización temporal)
        ↓
Transmisión/Almacenamiento (Pérdida de paquetes, corrupción de bits)
```

---

## 5. Teoría del Dato Faltante

Cuando se encuentra un `NaN` (*Not a Number*) o un nulo, no es simplemente la ausencia de un dato: **es un evento estadístico**. Antes de aplicar cualquier tratamiento correctivo, debe comprenderse el **mecanismo de pérdida**.

### Clasificación del Dato Faltante

#### A. MCAR — *Missing Completely at Random*

La probabilidad de que falte un dato es **independiente** tanto de los valores observados como de los no observados.

- **Ejemplo:** Un sensor se queda sin batería aleatoriamente.
- **Tratamiento:** Se pueden eliminar las filas `NaN` sin introducir sesgos (*bias*) en el modelo.

#### B. MAR — *Missing at Random*

La falta de datos depende de **otras variables observadas**, pero no del valor faltante en sí.

- **Ejemplo:** Un anemómetro falla más a menudo cuando el termómetro marca temperaturas bajo cero (la falla depende de la temperatura, no de la velocidad del viento).
- **Tratamiento:** Métodos de imputación basados en regresión.

#### C. MNAR — *Missing Not at Random*

La ausencia **depende del valor que se está midiendo**.

- **Ejemplo:** Un sensor de deformación deja de enviar datos porque la deformación excedió su rango físico y falló.
- **Tratamiento:** Analizar con cuidado; no se puede descartar a la ligera porque la falla es crítica en ingeniería.

---

## 6. Métodos de Imputación

Sustituir un `NaN` por un valor calculado **es crear información sintética**.

### Imputación por Media/Mediana

$$\hat{X}_i = \mu$$

- Preserva el momento primero (media) pero **reduce artificialmente la varianza** ($\sigma^2$), lo que puede llevar a **subestimar el riesgo del sistema**.

### Imputación por Interpolación Lineal

Asume que la variable cambia linealmente entre $t_{i-1}$ y $t_{i+1}$:

$$X(t) = X_0 + (X_1 - X_0) \frac{t - t_0}{t_1 - t_0}$$

- **Válido para:** Fenómenos físicos con inercia (temperaturas, nivel de fluidos, deformaciones).
- **Inválido para:** Procesos estocásticos (vibraciones de alta frecuencia).

---
### Ejemplo de Imputación

Un sensor de una caldera toma la temperatura cada minuto. A los tres minutos hubo un fallo de transmisión (`NaN`):

| Tiempo (min) | Temperatura (°C) |
|:---:|:---:|
| 1 | 100 |
| 2 | 110 |
| 3 | **NaN** |
| 4 | 130 |
| 5 | 140 |

**Estrategia A — Imputación por media global (ingenuo):**

$$\mu = \frac{100 + 110 + 130 + 140}{4} = \frac{480}{4} = 120\text{ °C} \rightarrow \text{NaN}$$

**Estrategia B — Interpolación lineal:**

$$T(3) = 110 + (130 - 110)\frac{3-2}{4-2} = 110 + 20 \cdot \frac{1}{2} = 120\text{ °C}$$

---

## 7. Detección de Anomalías (*Outliers*)

Un *outlier* es una observación que diverge del patrón general de la muestra.

### A. Enfoque Paramétrico: Z-Score

Asume que el ruido del sensor sigue una distribución Gaussiana (Normal): $X \sim \mathcal{N}(\mu, \sigma^2)$.

Se define el puntaje estándar:

$$Z_i = \frac{X_i - \mu}{\sigma}$$

- Si $|Z_i| > 3$, la probabilidad de que el dato sea legítimo es $< 0.27\%$.

**Limitación:** La media $\mu$ y la desviación estándar $\sigma$ son muy sensibles a los propios *outliers*. Un error extremo puede inflar $\sigma$, enmascarando otros errores.

### B. Enfoque Robusto: Rango Intercuartílico (IQR)

No asume normalidad y usa la **mediana** (estadística robusta).

Se calculan los cuartiles $Q_1$ (25%) y $Q_3$ (75%):

$$IQR = Q_3 - Q_1$$

Límites de aceptación:

$$L_{\text{inf}} = Q_1 - 1.5 \cdot IQR$$
$$L_{\text{sup}} = Q_3 + 1.5 \cdot IQR$$

Todo lo que caiga fuera de este rango es una anomalía.

---

## 8. Conceptos Estadísticos Fundamentales

### Media y Mediana

| Medida | Definición |
|--------|-----------|
| **Promedio** | $\displaystyle \bar{x} = \frac{\sum X_i}{n}$ |
| **Mediana** ($n$ impar) | Valor central: posición $\frac{n+1}{2}$ |
| **Mediana** ($n$ par) | $\displaystyle \frac{X_{(n/2)} + X_{(n/2+1)}}{2}$ |

### Varianza

| Tipo | Fórmula | Uso |
|------|---------|-----|
| **Poblacional** $\sigma^2$ | $\displaystyle \frac{\sum (X_i - \mu)^2}{N}$ | Todos los datos del universo |
| **Muestral** $s^2$ | $\displaystyle \frac{\sum (X_i - \bar{x})^2}{n-1}$ | Estimación desde una muestra |

### Distribución Gaussiana o Normal

$$X \sim \mathcal{N}(\mu, \sigma^2)$$

- **$\mu$ (Mu):** Media o promedio, centro de la campana.
- **$\sigma^2$ (sigma cuadrado):** Varianza. Mide qué tan dispersa es la campana:
  - Grande → distribución baja y ancha
  - Pequeña → distribución alta y estrecha

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
