# xctrace export XML Schema (Time Profiler)

Documentación empírica basada en datos reales de `xctrace export` con el template "Time Profiler".

## Flujo de exportación

```bash
# 1. Ver tabla de contenidos (qué tablas hay)
xctrace export --input file.trace --toc

# 2. Exportar tabla específica via XPath
xctrace export --input file.trace --xpath '/trace-toc/run[@number="1"]/data/table[@schema="time-profile"]'
```

## Tablas relevantes

De la TOC, las tablas útiles para profiling de CPU:

| Schema | Descripción |
|--------|-------------|
| `time-profile` | Samples con backtrace completo (la principal) |
| `time-sample` | Samples crudos con rate configurable |

La tabla `time-profile` es la que contiene los datos del call tree.

## Estructura XML de `time-profile`

```xml
<trace-query-result>
  <node xpath="...">
    <schema name="time-profile">
      <!-- 7 columnas -->
      <col><mnemonic>time</mnemonic></col>      <!-- Sample Time -->
      <col><mnemonic>thread</mnemonic></col>     <!-- Thread -->
      <col><mnemonic>process</mnemonic></col>    <!-- Process -->
      <col><mnemonic>core</mnemonic></col>       <!-- Core -->
      <col><mnemonic>thread-state</mnemonic></col> <!-- State -->
      <col><mnemonic>weight</mnemonic></col>     <!-- Weight (duración del sample) -->
      <col><mnemonic>stack</mnemonic></col>      <!-- Backtrace -->
    </schema>

    <row>...</row>  <!-- Un row por sample -->
    <row>...</row>
    ...
  </node>
</trace-query-result>
```

## Estructura de un `<row>` (sample)

```xml
<row>
  <sample-time id="1" fmt="00:00.794.882">794882958</sample-time>
  <thread id="2" fmt="Main Thread 0xdf999e (hotspot, pid: 97835)">
    <tid id="3" fmt="0xdf999e">14653854</tid>
    <process id="4" fmt="hotspot (97835)">
      <pid id="5" fmt="97835">97835</pid>
    </process>
  </thread>
  <process ref="4"/>
  <core id="7" fmt="CPU 6 (P Core)">6</core>
  <thread-state id="8" fmt="Running">Running</thread-state>
  <weight id="9" fmt="1.00 ms">1000000</weight>
  <backtrace id="10">
    <frame .../>  <!-- leaf frame (top of stack) -->
    <frame .../>
    ...
    <frame .../>  <!-- root frame (entry point) -->
  </backtrace>
</row>
```

### Campos clave

- **`<sample-time>`**: Timestamp en nanosegundos. `fmt` da formato legible.
- **`<weight>`**: Duración del sample en nanosegundos. Típicamente 1ms (1000000ns) para Time Profiler a 1kHz.
- **`<thread-state>`**: `Running`, `Blocked`, etc.
- **`<backtrace>`**: Call stack del sample, de hoja a raíz.

## Sistema id/ref (deduplicación)

xctrace usa un sistema de IDs globales para evitar repetir datos:

- **Primera aparición**: `<element id="42" ...>datos</element>`
- **Referencias posteriores**: `<element ref="42"/>`

Aplica a TODOS los elementos: `<frame>`, `<thread>`, `<process>`, `<core>`, `<weight>`, `<thread-state>`, `<sample-time>`, `<backtrace>`.

**Importante:** Un `ref` es semánticamente idéntico al elemento original con ese `id`. El parser debe mantener un diccionario `id → elemento` para resolver refs.

Ejemplo:
```xml
<!-- Primera vez que aparece este frame -->
<frame id="59" name="heavyWork()" addr="0x1027ec9a8">
  <binary id="60" name="hotspot" UUID="..." path="/Users/.../hotspot"/>
</frame>

<!-- Posteriores samples que pasan por el mismo frame -->
<frame ref="59"/>
```

**Nota:** La misma función puede tener múltiples IDs si se muestrea en diferentes direcciones (distintos puntos del código dentro de la misma función). En nuestro fixture, `heavyWork()` aparece con ids 59, 79, 241, 351, 700, 1999 — cada uno muestreado en una dirección distinta dentro del loop.

## Estructura de `<frame>`

```xml
<frame id="59" name="heavyWork()" addr="0x1027ec9a8">
  <binary id="60" name="hotspot"
          UUID="CB81B0E9-4BC2-44B5-8381-67F387C22F7E"
          arch="arm64"
          load-addr="0x1027ec000"
          path="/Users/fernando/code/ztrace/test/fixtures/hotspot"/>
</frame>
```

- **`name`**: Nombre del símbolo (función). Incluye parámetros genéricos para Swift stdlib.
- **`addr`**: Dirección de memoria del sample.
- **`<binary>`**: Imagen ejecutable que contiene el frame.
  - `name`: Nombre corto del binario.
  - `path`: Ruta completa.
  - `UUID`: Build UUID para simbolicación.

## Distinguir frames de usuario vs sistema

Heurística basada en `<binary path>`:

| Path prefix | Tipo |
|-------------|------|
| `/usr/lib/` | Sistema (dyld, libSystem, libdispatch, etc.) |
| `/usr/lib/swift/` | Swift runtime (stdlib) |
| `/System/` | Frameworks Apple |
| Todo lo demás | **Usuario** |

Binarios encontrados en nuestro fixture:

| Binario | Path | Tipo |
|---------|------|------|
| hotspot | `/Users/.../hotspot` | **Usuario** |
| dyld | `/usr/lib/dyld` | Sistema |
| libswiftCore.dylib | `/usr/lib/swift/libswiftCore.dylib` | Swift runtime |
| libsystem_m.dylib | `/usr/lib/system/libsystem_m.dylib` | Sistema (math) |
| libSystem.B.dylib | `/usr/lib/libSystem.B.dylib` | Sistema |
| libdyld.dylib | `/usr/lib/system/libdyld.dylib` | Sistema |
| libsystem_platform.dylib | `/usr/lib/system/libsystem_platform.dylib` | Sistema |
| libsystem_pthread.dylib | `/usr/lib/system/libsystem_pthread.dylib` | Sistema |
| libsystem_malloc.dylib | `/usr/lib/system/libsystem_malloc.dylib` | Sistema |
| libdispatch.dylib | `/usr/lib/system/libdispatch.dylib` | Sistema |

## Orden de frames en `<backtrace>`

Los frames van de **hoja a raíz** (leaf-to-root):

```
frame[0] = función actual (donde se tomó el sample)
frame[1] = quien llamó a frame[0]
...
frame[N] = entry point (start / main)
```

Ejemplo típico con nuestro fixture:
```
sin()                          ← leaf (libsystem_m)
IndexingIterator.next()        ← Swift stdlib
heavyWork()                    ← CÓDIGO USUARIO
main                           ← entry point
start                          ← dyld
```

## Estadísticas del fixture

- **Total samples**: 3045 (pero solo 727 backtraces únicas — muchas referencian backtraces previas)
- **Duración del trace**: 3.84 segundos
- **Sample rate**: 1ms (1kHz)
- **heavyWork samples**: ~60% (438/727 backtraces con definición o ref a frames de heavyWork)
- **lightWork samples**: ~39% (283/727)
- **Startup/other**: ~1% (6)

## Notas para el parser

1. **Resolver refs es obligatorio.** Muchos rows referencian frames/backtraces definidos antes. Sin resolución, se pierden datos.
2. **Contar por backtrace, no por row.** Hay 3045 rows pero solo 727 backtraces distintas. Muchos rows comparten backtrace via `ref`.
3. **Weight indica duración real.** Normalmente 1ms pero podría variar. Usar weight para calcular tiempo total, no contar samples.
4. **Una función = múltiples frame IDs.** Agrupar por `name`, no por `id`.
5. **El leaf frame no siempre es código usuario.** Muchas veces el sample pilla la CPU en `sin()` (libsystem_m), pero el frame interesante es `heavyWork()` más arriba en el stack.
6. **Para hotspots de usuario:** buscar el frame más profundo cuyo binary no sea de sistema. Ese es el "punto caliente" real.
