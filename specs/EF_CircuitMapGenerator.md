# Especificación Funcional — Circuit Map Generator
**Versión:** 1.0  
**Fecha:** Marzo 2026  
**Proyecto:** Generador estático de mapas interactivos de circuitos turísticos  
**Contexto:** Etapa adicional en pipeline de publicación WordPress  
**Estado:** Borrador aprobado

---

## 1. Contexto y propósito

Existe un pipeline automatizado que, dado un JSON de circuito turístico, genera y publica una página en WordPress siguiendo una plantilla predefinida. Actualmente ese pipeline inserta una imagen fija (JPG/PNG) como elemento visual del mapa del recorrido.

El objetivo de este proyecto es reemplazar esa imagen fija por un **mapa interactivo HTML** que el visitante puede explorar día a día, sin modificar el resto del pipeline ni requerir ningún servidor adicional, plugin de WordPress, ni dependencia en tiempo de ejecución del lado del visitante.

El generador es un script Python que se añade como una etapa más del pipeline existente. Su entrada es el mismo JSON que ya maneja el pipeline. Su salida es un bloque HTML autónomo listo para insertarse en la página WordPress.

---

## 2. Posición en el pipeline

```
[Fuente de datos]
      ↓
[JSON del circuito]          ← entrada existente
      ↓
[Etapas existentes del pipeline]
      ↓
[generate_map.py]            ← ETAPA NUEVA (este proyecto)
      ↓
[HTML del mapa — self-contained]
      ↓
[Inserción en WordPress via REST API]
      ↓
[Página WordPress publicada]
```

La etapa nueva no altera ni reemplaza ningún paso anterior. Consume el mismo JSON y produce un artefacto adicional que el pipeline inserta en un campo específico del post de WordPress.

---

## 3. Descripción funcional del mapa generado

### 3.1 Visualización del recorrido

El mapa muestra el territorio relevante al circuito (país, región o continente según la extensión del recorrido) con las siguientes capas de información superpuestas:

- Un marcador por cada ciudad visitada, con el número de noches indicado visualmente.
- Las rutas terrestres entre ciudades consecutivas, trazadas siguiendo carreteras reales, dibujadas como líneas animadas sobre el mapa.
- Los tramos aéreos (vuelos incluidos), representados como arcos curvos de línea discontinua con un indicador visual diferenciado.
- Una distinción visual clara entre el tramo activo (día seleccionado) y el resto del recorrido.

### 3.2 Navegación por días

El visitante puede explorar el itinerario día a día mediante:

- Botones de día numerados alineados horizontalmente bajo el mapa, con scroll horizontal en móvil.
- Botones de anterior y siguiente para avanzar secuencialmente.
- Clic directo en un marcador del mapa para saltar al día de esa ciudad.

Al cambiar de día, el mapa anima la transición: la ruta se ilumina hasta el día activo y la cámara vuela suavemente a la ciudad correspondiente.

### 3.3 Panel de información por día

Al seleccionar un día se muestra un panel con:

- Número de día y día de la semana.
- Ciudades visitadas ese día.
- Descripción de actividades extraída directamente del JSON.
- Indicadores visuales de servicios incluidos: almuerzo, cena, vuelo.

### 3.4 Autonomía del componente

El HTML generado es completamente autónomo:

- No realiza ninguna llamada a servidores externos en tiempo de ejecución del visitante.
- Los datos del circuito (coordenadas, rutas GeoJSON, descripción de días) están inlineados como variables JavaScript dentro del propio archivo.
- La librería de mapas (MapLibre GL JS) se carga desde CDN público al abrir la página. Si se requiere funcionamiento offline completo, puede incluirse en el bundle.
- Los tiles del mapa base provienen de un servicio de tiles vectoriales público (MapTiler o similar). La API key, si se requiere, se configura en el generador y se embebe en el HTML en tiempo de generación.

---

## 4. Flujo funcional del generador

### Paso 1 — Recepción del JSON

El generador recibe el JSON del circuito como argumento o como objeto Python si se llama como módulo desde el pipeline. Valida que contenga los campos mínimos necesarios: `id`, `titulo`, `itinerario` con al menos un día, y `ciudades` por día.

### Paso 2 — Extracción de ciudades

El generador analiza el campo `ciudades` de cada día del itinerario y extrae una lista de ciudades únicas a geocodificar. Ciudades compuestas como "Delhi → Agra" o "Udaipur ✈ Mumbai" se descomponen en sus componentes individuales. Los separadores reconocidos son `→`, `✈`, `-`, y `,`.

### Paso 3 — Geocodificación con caché

Para cada ciudad única, el generador consulta primero un caché local en disco (`coords_cache.json`). Si la ciudad no está en caché, llama al servicio de geocodificación (Nominatim por defecto, con fallback a MapTiler Geocoding si se configura). El resultado se guarda en caché antes de continuar. La caché es compartida entre todas las ejecuciones del pipeline, por lo que ciudades frecuentes como Madrid, París o Delhi se resuelven solo la primera vez.

### Paso 4 — Detección de tipo de tramo

Para cada par de ciudades consecutivas en el itinerario, el generador determina si el tramo es terrestre o aéreo. La detección es aéreo si el campo `ciudades` contiene el carácter `✈`, o si la descripción del día contiene las palabras "vuelo", "aeropuerto" o "flight", o si el campo `vuelos_incluidos` del JSON especifica ese tramo.

### Paso 5 — Cálculo de rutas

Para tramos terrestres, el generador llama a OSRM (configurable: instancia pública o local) con las coordenadas de origen y destino. La respuesta GeoJSON del trayecto por carretera se simplifica para reducir el tamaño del HTML final (tolerancia de Douglas-Peucker configurable). Para tramos aéreos, el generador calcula matemáticamente un arco de gran círculo entre los dos puntos, sin llamar a OSRM.

### Paso 6 — Renderizado del HTML

Con todos los datos procesados, el generador renderiza la plantilla Jinja2 del mapa, inyectando como variables JavaScript inlineadas: las coordenadas de todas las ciudades, los GeoJSON de todas las rutas, el itinerario completo con descripciones y servicios incluidos. El resultado es un string HTML completo y autónomo.

### Paso 7 — Inserción en WordPress

El HTML generado se entrega al pipeline de dos formas posibles según configuración:

- Como string de retorno si el generador se llama como función Python desde el pipeline.
- Como archivo `{circuit_id}_map.html` guardado en un directorio de salida si se llama como script de línea de comandos.

La inserción en WordPress la realiza el pipeline existente, no el generador. El campo de destino es un campo ACF de tipo `textarea` o `wysiwyg` en el post del circuito, que la plantilla WordPress renderiza directamente con `echo get_field('circuit_map_html')`.

---

## 5. Comportamiento en casos especiales

| Situación | Comportamiento |
|---|---|
| Ciudad no encontrada en geocodificación | Se omite el marcador de esa ciudad; el resto del mapa se genera normalmente. Se registra una advertencia en el log del pipeline. |
| OSRM no disponible | El tramo terrestre se dibuja como línea recta entre los dos puntos (fallback). Se registra una advertencia. |
| Circuito de un solo día | El mapa muestra el marcador de la ciudad sin rutas. El panel de navegación muestra solo el día único. |
| Tramo con misma ciudad origen y destino | Se omite la ruta para ese tramo. La ciudad muestra sus noches acumuladas. |
| JSON sin campo `incluye` | El panel de días omite los chips de servicios incluidos sin error. |
| Ciudad con nombre ambiguo | El generador acepta un `coords_override` opcional en el JSON para forzar coordenadas específicas por nombre de ciudad. |

---

## 6. Criterios de aceptación

| ID | Escenario | Criterio |
|---|---|---|
| CA-01 | JSON válido de 10 días | El HTML generado contiene todos los marcadores, rutas y panel de días en menos de 30 segundos |
| CA-02 | Navegación por días | Al hacer clic en un día el mapa anima la cámara y resalta la ruta hasta ese punto |
| CA-03 | Tramo aéreo | El vuelo aparece como arco curvo discontinuo visualmente distinto de las rutas terrestres |
| CA-04 | Marcador de ciudad | Muestra el número de noches correcto según los días agrupados en esa ciudad |
| CA-05 | Panel de servicios | Los chips de almuerzo y cena aparecen exactamente en los días indicados en el JSON |
| CA-06 | Visualización móvil | El mapa ocupa el ancho completo y el panel de días usa scroll horizontal en pantallas menores a 768px |
| CA-07 | Caché de coordenadas | La segunda ejecución con el mismo circuito no realiza ninguna llamada a Nominatim |
| CA-08 | HTML autónomo | El mapa funciona correctamente al abrir el HTML directamente desde disco (file://) |
| CA-09 | Integración pipeline | La función `generate_circuit_map(json_dict)` retorna un string HTML válido sin efectos secundarios |
| CA-10 | Ciudad no encontrada | El script termina sin error y el log contiene la advertencia de ciudad no resuelta |

---

## 7. Restricciones y exclusiones de v1.0

- No se incluye enriquecimiento de descripciones de lugares con IA (queda para v1.1).
- No se incluye visualización 3D de terreno.
- No se soporta modo offline completo (tiles del mapa requieren conexión).
- No se genera imagen estática de fallback para redes sociales (og:image).
- El generador no gestiona la autenticación con WordPress — esa responsabilidad permanece en el pipeline existente.
- No se soportan circuitos con más de un vuelo de regreso o rutas circulares en v1.0.

---

## 8. Glosario

| Término | Definición |
|---|---|
| Pipeline | El proceso automatizado existente que transforma JSON de circuitos en páginas WordPress publicadas |
| HTML self-contained | Archivo HTML que incluye todos sus datos y dependencias de forma que funciona sin llamadas adicionales al servidor |
| Tramo | Segmento de desplazamiento entre dos ciudades consecutivas del itinerario |
| Geocodificación | Proceso de convertir el nombre de una ciudad en coordenadas geográficas (latitud, longitud) |
| GeoJSON | Formato estándar para representar geometrías geográficas (puntos, líneas) en JSON |
| Caché de coordenadas | Archivo JSON local que almacena coordenadas ya resueltas para evitar llamadas repetidas a Nominatim |
| OSRM | Open Source Routing Machine — motor que calcula rutas reales por carretera dado un origen y destino |
| Arco de gran círculo | Curva que representa la ruta más corta entre dos puntos sobre la superficie de la Tierra, usado para visualizar vuelos |
| MapLibre GL JS | Librería JavaScript open-source para renderizar mapas vectoriales interactivos en el browser |
| Jinja2 | Motor de templates Python usado para generar el HTML final a partir de una plantilla y los datos del circuito |
