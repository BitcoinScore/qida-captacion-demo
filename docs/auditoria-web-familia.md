# Auditoría de la web de la familia y el chat · demo de captación

2026-11-02. Revisa la página que ve la familia («Web con ayuda de noche») frente a estándares de landing pages de
captación (CRO), confianza, protección de datos, transparencia de la IA, accesibilidad y buenas prácticas de chat de
atención. La web es una maqueta dentro de una demo, pero se revisa como si fuera a producción.

## Resumen

| # | Severidad | Dónde | Problema | Estándar |
|---|---|---|---|---|
| 1 | 🔴 Crítico | Chat | **No dice que es una IA.** El botón dice «Te atendemos ahora» y la ventana no aclara que no es una persona | Reglamento europeo de IA (art. 50, aplicable desde el 2-8-2026): quien habla con un sistema de IA debe saberlo. Además, confianza |
| 2 | 🔴 Crítico | Chat y formulario | **Recoge teléfono y datos de salud sin aviso de privacidad ni consentimiento** («le dan el alta», «Alzheimer» son datos de categoría especial) | RGPD arts. 6, 9 y 13: informar antes de recoger, base legal, minimización; la web real de Qida tiene casilla de privacidad |
| 3 | 🔴 Crítico | Chat | El **112** solo aparece si el modelo detecta la urgencia; no hay aviso fijo | En servicios de salud y cuidados, el aviso de emergencias va visible antes de escribir |
| 4 | 🟠 Alto | Formulario | El botón principal **«Solicitar llamada» está desactivado**: la llamada a la acción principal no funciona y no hay confirmación | La acción principal funciona, valida los datos y confirma qué pasa después y cuándo |
| 5 | 🟠 Alto | Cabecera | **No hay teléfono ni horario**, cuando es el canal que más convierte («Teléfono directo» ~20 %) | Teléfono visible arriba con horario y estado (abierto/cerrado), clic para llamar en móvil |
| 6 | 🟠 Alto | Toda la página | **Sin señales de confianza**: ni valoración (4,8/5), ni familias atendidas, ni acreditación | En servicios de cuidado, la confianza es la primera objeción; prueba social cerca de la acción principal |
| 7 | 🟠 Alto | Portada | **No coincide con el anuncio**: Meta promete «desde 170 €/mes» y la página no lo dice | Coherencia anuncio-página: el usuario busca en la página lo que le prometió el anuncio |
| 8 | 🟠 Alto | Chat | Empieza en blanco: **sin respuestas rápidas** y la familia tiene que redactar | Botones de inicio («Es urgente», «Quiero saber precios», «Dependencia») reducen la fricción |
| 9 | 🟠 Alto | Chat | No ofrece **pasar a una persona** de forma visible (solo si el modelo decide escalar) | Salida a humano siempre visible: «Prefiero que me llame una persona» |
| 10 | 🟡 Medio | Móvil | La barra lateral de controles de la demo tapa la página en móvil | Controles de la demo plegados; la web, a pantalla completa |
| 11 | 🟡 Medio | Chat | La ventana es un modal centrado que tapa la página, no un panel anclado abajo a la derecha | Patrón de widget de chat anclado |
| 12 | 🟡 Medio | Chat | La «vista del equipo» va dentro del chat de la familia | Separarla y rotularla «solo en la demo» |
| 13 | 🟡 Medio | Portada | «Cómo funciona» es una línea con flechas difícil de escanear | Pasos visuales numerados |
| 14 | 🟡 Medio | Accesibilidad | Iconos emoji sin texto alternativo y contraste justo en textos secundarios | WCAG 2.2 AA (contraste 4,5:1, alternativas textuales) |
| 15 | 🟢 Bajo | Chat | 10 s por respuesta sin indicar que tarda | Indicador de «escribiendo» y expectativa de espera |
| 16 | 🟢 Bajo | Portada | Sin personalización por ciudad (la pauta va por ciudades: A Coruña, Valencia, Sevilla) | Página o titular por ciudad desde el anuncio |

## Corrección propuesta (críticos y altos)

1. **IA declarada** en el botón («Asistente virtual»), en la cabecera de la ventana y en el primer mensaje; y en el prompt:
   si preguntan, dice que es un asistente con IA.
2. **Privacidad antes de escribir:** aviso corto (para qué se usan los datos, que no hace falta contar detalles médicos,
   enlace a la política) y casilla obligatoria en el formulario.
3. **112 fijo** arriba del chat.
4. **Formulario que funciona:** valida teléfono (9 dígitos) y código postal (5), exige la casilla, guarda el lead (canal
   «Formulario») y confirma «te llamamos hoy» o «mañana a partir de las 9:00» según la hora.
5. **Barra superior** con teléfono, horario y estado abierto/cerrado.
6. **Franja de confianza** con datos públicos de Qida: 4,8/5 de calidad, más de 25.000 familias atendidas, empresa
   acreditada, «no pagas hasta valorar».
7. **«Desde 170 €/mes»** en la portada, como en el anuncio.
8. **Respuestas rápidas** al abrir el chat.
9. **Botón «Prefiero que me llame una persona»** siempre visible en el chat.

## Estado (2026-11-02, noche)

Corregidos 1-9 y verificados en el navegador: IA declarada (botón, cabecera, primer mensaje y regla en el prompt),
consentimiento antes de escribir en el chat y casilla obligatoria en el formulario, 112 fijo, formulario que valida
(teléfono, código postal, casilla), guarda el lead y confirma cuándo se llama, barra con teléfono (ficticio), horario y
estado, franja de confianza con datos públicos de Qida, «Desde 170 €/mes», respuestas rápidas y «Prefiero que me llame una
persona». También el color del tema (`.streamlit/config.toml`). Pendientes: 10-16 (móvil, chat anclado, accesibilidad,
indicador de espera ya parcial, personalización por ciudad).

Nota: la regla «eres un asistente con IA; no reveles el modelo» se añadió después de la evaluación v2; el caso reservado
R19 (revelaba el modelo) debería pasar ahora, pero no está medido.
