# Semana 13 — Machine Learning para Ingenieros

---

## 1. Programación Clásica vs. Machine Learning

Tradicionalmente, la programación sigue un paradigma determinista:

| Paradigma | Entrada | Proceso | Salida |
|-----------|---------|---------|--------|
| **Clásico** | Datos + Reglas | Programa (lógica explícita) | → Respuestas |
| **Machine Learning** | Datos + Respuestas | Algoritmo de aprendizaje | → Reglas (modelo) |

En el paradigma clásico, el ingeniero **codifica explícitamente** las reglas. En Machine Learning, el sistema **aprende las reglas** a partir de ejemplos.

---

## 2. Definición Formal

> *"Se dice que un programa de computadora aprende de la experiencia $E$ con respecto a una tarea $T$ y una medida de desempeño $P$, si su desempeño en $T$, medido por $P$, mejora con la experiencia $E$."*
>
> — Tom Mitchell (1997)

| Componente | Significado | Ejemplo (clasificación de correos) |
|-----------|-------------|-------------------------------------|
| **Tarea ($T$)** | Qué se quiere lograr | Clasificar correos como spam o no spam |
| **Experiencia ($E$)** | Datos de entrenamiento | Miles de correos etiquetados |
| **Desempeño ($P$)** | Métrica de evaluación | Porcentaje de correos correctamente clasificados |

---

## 3. Etapas de un Proyecto de Machine Learning

```
1. Definición del problema
        ↓
2. Recolección y preparación de datos
        ↓
3. Análisis exploratorio (EDA)
        ↓
4. Selección y entrenamiento del modelo
        ↓
5. Evaluación y validación
        ↓
6. Despliegue y monitoreo
```

### 3.1 Preparación de Datos

- **Limpieza:** Valores faltantes, outliers, datos inconsistentes
- **Transformación:** Normalización, estandarización, encoding de variables categóricas
- **División:** Conjuntos de entrenamiento (70%), validación (15%) y prueba (15%)

### 3.2 Entrenamiento

El modelo ajusta sus parámetros internos minimizando una **función de pérdida** que mide el error entre predicciones y valores reales.

---

## 4. Tipos de Aprendizaje

### 4.1 Aprendizaje Supervisado

Se dispone de datos etiquetados: pares $(\mathbf{x}_i, y_i)$ donde $\mathbf{x}_i$ son las características (*features*) e $y_i$ es la etiqueta (*label*).

| Tipo | Objetivo | Ejemplos de algoritmos |
|------|----------|----------------------|
| **Regresión** | Predecir valor continuo | Regresión lineal, Random Forest, SVR |
| **Clasificación** | Predecir categoría | Regresión logística, SVM, Random Forest, Redes Neuronales |

**Ejemplos en ingeniería:**
- Predecir la resistencia a la compresión del concreto (regresión)
- Clasificar modos de falla en una estructura (clasificación)

### 4.2 Aprendizaje No Supervisado

No se dispone de etiquetas. El algoritmo busca **patrones** o **estructura** en los datos.

| Técnica | Objetivo |
|---------|----------|
| **Clustering** (K-means, DBSCAN) | Agrupar observaciones similares |
| **Reducción de dimensionalidad** (PCA, t-SNE) | Simplificar datos preservando estructura |
| **Detección de anomalías** | Identificar observaciones atípicas |

### 4.3 Aprendizaje por Refuerzo

Un agente aprende a tomar decisiones interactuando con un entorno, recibiendo **recompensas** o **castigos** por sus acciones.

---

## 5. Algoritmos Fundamentales

| Algoritmo | Tipo | Fortaleza |
|-----------|------|-----------|
| **Regresión Lineal** | Regresión | Interpretable, rápido, base teórica sólida |
| **Regresión Logística** | Clasificación | Probabilidades calibradas, interpretable |
| **Árboles de Decisión** | Ambos | No lineal, interpretable, no requiere escalado |
| **Random Forest** | Ambos | Robusto, maneja bien datos ruidosos |
| **SVM** | Clasificación | Efectivo en alta dimensionalidad |
| **K-Nearest Neighbors** | Ambos | Simple, no paramétrico |
| **Redes Neuronales** | Ambos | Modelado de relaciones complejas no lineales |

---

## 6. Evaluación de Modelos

### 6.1 Métricas para Regresión

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| **MAE** | $\frac{1}{n}\sum \|y_i - \hat{y}_i\|$ | Error absoluto promedio |
| **MSE** | $\frac{1}{n}\sum (y_i - \hat{y}_i)^2$ | Penaliza más errores grandes |
| **RMSE** | $\sqrt{\text{MSE}}$ | Mismas unidades que $y$ |
| **$R^2$** | $1 - \frac{\sum(y_i - \hat{y}_i)^2}{\sum(y_i - \bar{y})^2}$ | Proporción de varianza explicada (0 a 1) |

### 6.2 Métricas para Clasificación

| Métrica | Definición |
|---------|------------|
| **Accuracy** | $\frac{\text{VP} + \text{VN}}{\text{Total}}$ |
| **Precision** | $\frac{\text{VP}}{\text{VP} + \text{FP}}$ |
| **Recall** | $\frac{\text{VP}}{\text{VP} + \text{FN}}$ |
| **F1-Score** | Media armónica de Precision y Recall |

### 6.3 Overfitting y Underfitting

| Problema | Síntoma | Solución |
|----------|---------|----------|
| **Underfitting** | Error alto en entrenamiento y prueba | Modelo más complejo, más features |
| **Overfitting** | Error bajo en entrenamiento, alto en prueba | Regularización, más datos, modelo más simple |

---

## 7. Flujo de Trabajo en Python (scikit-learn)

```python
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

# 1. Dividir datos
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 2. Entrenar modelo
model = LinearRegression()
model.fit(X_train, y_train)

# 3. Predecir
y_pred = model.predict(X_test)

# 4. Evaluar
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
print(f"MSE: {mse:.4f}, R²: {r2:.4f}")
```

---

## 8. Consideraciones para Ingeniería

| Principio | Implicación |
|-----------|-------------|
| **Calidad de datos > Complejidad del modelo** | Un modelo simple con buenos datos supera a uno complejo con datos sucios |
| **Interpretabilidad** | En ingeniería civil/mecánica, entender *por qué* el modelo predice algo es tan importante como la precisión |
| **Cuantificar incertidumbre** | Todo modelo tiene error; debe reportarse, no ocultarse |
| **Validación con principios físicos** | Las predicciones deben ser consistentes con las leyes de la física |

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
