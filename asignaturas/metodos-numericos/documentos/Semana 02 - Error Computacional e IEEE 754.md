# Semana 2 — Aritmética Computacional y la Naturaleza del Error

---

## 1. La Precisión Finita

### Escenario

> Se está diseñando el sistema de emergencia para un tren de alta velocidad. El sistema de control recibe la posición del tren $x(t)$ desde un sensor láser cada milisegundo. Para determinar la fuerza de frenado, el procesador debe calcular la aceleración instantánea, que es la segunda derivada de la posición:
>
> $$a(t) = \frac{d^2x}{dt^2}$$

Para obtener la derivada exacta, se sabe que $\Delta t \to 0$:

$$f'(x) = \lim_{\Delta t \to 0} \frac{f(x + \Delta t) - f(x)}{\Delta t}$$

**Posible solución:** Programar el procesador para que tome una lectura cada nanosegundo ($10^{-9}$) y aplicar la fórmula de diferencias finitas:

$$a(t) \approx \frac{x(t + \Delta t) - 2x(t) + x(t - \Delta t)}{\Delta t^2}$$

**El problema:** En las pruebas, el tren activa los frenos de emergencia aleatoriamente en tramos rectos. Al revisar los *logs* se observan aceleraciones de hasta **5000 m/s²** en momentos en que el tren está casi detenido.

---

## 2. La Catástrofe de Cancelación

**La causa:** Al restar dos posiciones $x(t + \Delta t)$ y $x(t)$ casi idénticas (dado el tamaño de $\Delta t$), los primeros dígitos significativos se cancelan, dejando solo "ruido" numérico en los últimos decimales. Al dividir ese ruido por un número muy pequeño ($\Delta t$), el error se **amplifica**.

Este fenómeno se conoce como:
- **Catástrofe de cancelación**
- **Límite de precisión de la máquina**

---

## 3. El Estándar IEEE 754

Las computadoras son **sistemas discretos finitos** en los que se intenta representar **fenómenos continuos infinitos**.

El estándar IEEE 754 (doble precisión, 64 bits) es la norma que rige la representación de números en ingeniería (`float` en Python, `double` en C++).

Un número en memoria **no es un valor exacto**, sino una ecuación almacenada en 64 bits:

$$X_{\text{mach}} = (-1)^s \cdot (1.m) \cdot 2^{e - 1023}$$

Donde:

| Componente | Bits | Descripción |
|-----------|------|-------------|
| **Signo ($s$)** | 1 bit | $0$ = positivo, $1$ = negativo |
| **Exponente ($e$)** | 11 bits | Rango de magnitud ($10^{-308}$ a $10^{308}$). *Bias* de 1023 permite exponentes negativos sin usar otro bit de signo |
| **Mantisa/Fracción ($m$)** | 52 bits | Determina la precisión. Hay un bit adicional ($1.$) que no se almacena por normalización |

---

## 4. El Epsilon de la Máquina ($\varepsilon_{\text{mach}}$)

Dado que solo se dispone de 52 bits para la fracción, existe una **distancia mínima indivisible** entre $1.0$ y el siguiente número representable:

$$\varepsilon_{\text{mach}} = 2^{-52} \approx 2.2204 \times 10^{-16}$$

> Cualquier fenómeno físico que suceda con tiempos o magnitudes inferiores a $\varepsilon_{\text{mach}}$ **no existe para el computador**.
>
> $$1 + 10^{-17} = 1$$

---

## 5. El Error en Ingeniería

El error total se compone de dos fenómenos opuestos:

$$E_{\text{total}} = |E_{\text{truncamiento}}| + |E_{\text{redondeo}}|$$

### A. Error de Truncamiento

Aparece cuando se aproxima un proceso infinito con pasos finitos.

Usando la serie de Taylor se puede cuantificar la pérdida al discretizar una derivada:

$$f(x + h) = f(x) + f'(x)h + \frac{f''(x)h^2}{2!} + \cdots$$

### B. Precisión vs. Ruido

La teoría señala que para minimizar el error de truncamiento, debe hacerse $h \to 0$. **Pero los datos experimentales contienen ruido de medición** (error aleatorio $E$).

Si se considera una señal ruidosa $\tilde{f}(x) = f(x) + E$, al aplicar una diferencia finita, el error total se compone del error de truncamiento más el error inducido por el ruido:

$$E_{\text{total}} = G h + \frac{2E}{h}$$

- $G h \to$ **disminuye** cuando $h \to 0$
- $\frac{2E}{h} \to$ **aumenta hiperbólicamente** con $h \to 0$ (amplificación del ruido)

---

## 6. El $h$ Óptimo

Se deriva e iguala a cero:

$$\frac{dE}{dh} = 0 \quad \Rightarrow \quad h_{\text{opt}} \approx \sqrt{\varepsilon_{\text{mach}}} \approx 10^{-8}$$

> La mejor precisión en derivadas numéricas **no se logra con $h = 10^{-16}$** sino con $h = 10^{-8}$. Un valor más pequeño **empeora** el resultado.

---

*Pontificia Universidad Javeriana Cali — Modelado Computacional e Ingeniería Basada en Datos*
