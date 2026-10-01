# Semana 3 — Series de Taylor y Diferenciación Numérica

---

## 1. Discretizando el Continuo

En el cálculo diferencial tradicional, la derivada se define como un límite matemático cuando el intervalo de tiempo tiende a cero:

$$v(t) = \lim_{\Delta t \to 0} \frac{x(t + \Delta t) - x(t)}{\Delta t}$$

En el ejercicio cotidiano, **esta aproximación analítica no es factible o está muy limitada por la naturaleza discreta de los datos**.

En la mayoría de los fenómenos analizados en ingeniería (como el movimiento de un elemento mecánico o la deformación de una estructura) **no se dispone de una función continua $x(t)$**, sino una serie de lecturas discretas tomadas por un sensor en un intervalo de tiempo finito $h$ (o $\Delta t$).

Para aplicar los principios del cálculo a fenómenos físicos reales se usan **métodos numéricos** que permiten aproximaciones a esa tasa de cambio instantánea, siendo uno de los más usados las **Diferencias Finitas**.

---

## 2. La Serie de Taylor

Es la técnica más usada para discretizar derivadas.

La Serie de Taylor permite aproximar el valor de una función en un punto futuro $x_{i+1}$ basándose en el valor actual $x_i$ y sus derivadas sucesivas.

Si se asume que $h = x_{i+1} - x_i$, la expresión de la serie de Taylor es:

$$f(x_{i+1}) = f(x_i) + f'(x_i)h + \frac{f''(x_i)h^2}{2!} + \frac{f'''(x_i)h^3}{3!} + \cdots + R_n$$

Donde $R_n$ representa el **término residual** o **error de truncamiento**.

**Interpretación física:** Esta expansión representa, por ejemplo en cinemática, que la posición futura de un objeto es su posición actual más el desplazamiento a velocidad constante, más una corrección por la aceleración, y así sucesivamente.

Al **truncar** (cortar) la serie, se obtienen fórmulas algebraicas para estimar las derivadas $f'(x)$, $f''(x)$.

---

## 3. Tipos de Diferencias Finitas

Haciendo manipulaciones de la Serie de Taylor, se puede despejar la derivada de primer orden $f'(x_i)$ y usar **tres formas de aproximación**, cada una con propiedades diferentes.

### 3.1 Diferencia hacia Adelante (*Forward Difference*)

Si se corta la serie tras la primera derivada:

$$f(x_{i+1}) = f(x_i) + f'(x_i)h$$

Al despejar $f'(x_i)$:

$$f'(x_i) \approx \frac{f(x_{i+1}) - f(x_i)}{h}$$

| Propiedad | Valor |
|-----------|-------|
| **Error** | $\mathcal{O}(h)$ — primer orden |
| **Uso** | Cálculo de derivadas al **inicio** de una serie ($t=0$) donde no existe un punto anterior |

### 3.2 Diferencia hacia Atrás (*Backward Difference*)

Si se expande la serie de Taylor hacia el pasado ($x_{i-1} = x_i - h$):

$$f(x_{i-1}) = f(x_i) - f'(x_i)h + \frac{f''(x_i)h^2}{2!} - \cdots$$

Despejando y truncando:

$$f'(x_i) \approx \frac{f(x_i) - f(x_{i-1})}{h}$$

| Propiedad | Valor |
|-----------|-------|
| **Error** | $\mathcal{O}(h)$ — primer orden |
| **Uso** | Cálculo de derivadas al **final** de un *dataset* del cual se desconoce el futuro |

### 3.3 Diferencia Central (*Central Difference*)

**Es el método más robusto.** Si se resta la expansión hacia atrás de la expansión hacia adelante, **los términos de orden par ($h^2$) se cancelan mutuamente**:

$$f'(x) \approx \frac{f(x_{i+1}) - f(x_{i-1})}{2h}$$

| Propiedad | Valor |
|-----------|-------|
| **Error** | $\mathcal{O}(h^2)$ — segundo orden |
| **Uso** | Muy eficiente para **puntos internos**. Reducir $h$ a la mitad reduce el error a la cuarta parte |

---

## 4. Segunda Derivada

En problemas dinámicos es fundamental conocer la aceleración ($a = d^2x/dt^2$). Puede obtenerse una fórmula de diferencia finita para la segunda derivada **sumando las expansiones de Taylor hacia adelante y hacia atrás**:

$$f''(x_i) \approx \frac{f(x_{i+1}) - 2f(x_i) + f(x_{i-1})}{h^2}$$

> **Error:** Al ser un caso particular de la diferencia central, el error es también $\mathcal{O}(h^2)$.

---

## 5. Implementación Computacional

Para minimizar los efectos de deriva numérica en la implementación de estas técnicas, debe seguirse el proceso adecuado:

1. **Adquisición y limpieza** de datos
2. **Suavizado de datos** usando filtros para reducir el error antes de la derivación
3. **Aplicar diferenciación vectorizada:** usar algoritmos optimizados para aplicar automáticamente diferencias centrales o direccionales según se requiera

### Consecuencias de un $h$ inadecuado

> Si el intervalo de muestreo $h$ es demasiado pequeño (alta frecuencia de muestreo) sin un filtrado adecuado, la derivada numérica **amplificará el ruido del sensor hasta enmascarar la señal física**. Una posición $x(t)$ aparentemente normal puede resultar en una aceleración $a(t)$ inutilizable.

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
