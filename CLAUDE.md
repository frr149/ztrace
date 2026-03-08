# ztrace

Script CLI que resume la salida de `xctrace` (Instruments) en un formato compacto optimizado para consumo por LLMs (especialmente Claude Code).

## Problema

`xctrace export` genera XML de decenas de miles de líneas (call trees completos, cada sample individual, metadata repetitiva). Cuando Claude Code perfila apps Swift con xctrace, el output consume la ventana de contexto rápidamente y pierde información relevante entre el ruido.

## Objetivo

Un script que tome un `.trace` bundle (o lo genere) y produzca un resumen de ~200 líneas con los hotspots reales, filtrando frames del sistema que no son accionables.

## Plan de implementación (por fases)

### Fase 0: Investigación (HACER PRIMERO, antes de escribir código)

**CRÍTICO: No asumir nada sobre el formato de xctrace. Verificar todo empíricamente.**

1. Ejecutar `xctrace export --help` y documentar las opciones reales disponibles
2. Crear `test/fixtures/hotspot.swift` — programa trivial con hotspots predecibles:
   - Función `heavyWork()` que consuma ~70% CPU (ej: cálculos en loop)
   - Función `lightWork()` que consuma ~30% CPU
   - Ejecución de ~3 segundos
3. Perfilarlo: `xctrace record --template 'Time Profiler' --launch .build/debug/hotspot --output test/fixtures/sample.trace`
4. Exportar: `xctrace export --input test/fixtures/sample.trace` (probar con y sin flags)
5. Guardar el XML crudo en `test/fixtures/sample-export.xml`
6. Analizar el XML: documentar tags, estructura, cómo se representan frames, call trees, tiempos
7. Escribir hallazgos en `docs/xctrace-schema.md`

**Solo avanzar a Fase 1 cuando el schema esté documentado con datos reales.**

### Fase 1: Parser mínimo

- Leer el XML real (no un schema inventado)
- Extraer call tree con tiempos/conteos por frame
- Distinguir frames del usuario vs frames del sistema (heurística a definir tras ver datos reales)
- Output: lista ordenada de hotspots con % de tiempo

### Fase 2: CLI usable

```bash
# Resumir un .trace existente
ztrace summary ./MyApp.trace

# Grabar + resumir en un paso
ztrace record ./MyApp --template 'Time Profiler' --duration 5
```

- Instalar en `~/.local/bin/ztrace`
- Output compacto, pensado para pegar en contexto de LLM

### Fase 3: Refinamiento

- Filtros configurables (profundidad de call stack, umbral de %, exclusión de módulos)
- Soporte para otros templates (Allocations, Leaks) si tiene sentido
- Comparación entre dos traces (antes/después de optimización)

## Stack

- **Lenguaje:** Swift (coherente con el caso de uso, acceso nativo a frameworks Apple si hace falta)
- **Build:** Swift Package Manager
- **Dependencias:** mínimas, preferir stdlib. XMLParser de Foundation para el XML.
- **Tests:** XCTest con fixtures reales (el .trace generado en Fase 0)

## Estructura esperada

```
ztrace/
├── CLAUDE.md              # Este fichero
├── Package.swift
├── Sources/
│   └── ztrace/
│       ├── main.swift     # CLI entry point
│       ├── TraceExporter.swift  # Wrapper sobre xctrace export
│       ├── XMLParser.swift      # Parser del XML exportado
│       └── Summarizer.swift     # Lógica de agregación y filtrado
├── Tests/
│   └── ztraceTests/
│       └── SummarizerTests.swift
├── test/
│   └── fixtures/
│       ├── hotspot.swift          # Programa Swift con hotspots conocidos
│       ├── sample.trace/          # Trace real (generado, gitignored)
│       └── sample-export.xml      # XML exportado (generado, gitignored)
└── docs/
    └── xctrace-schema.md         # Documentación del schema real de xctrace export
```

## Reglas

- **NO inventar el schema XML de xctrace.** Toda la lógica de parsing debe basarse en datos reales de Fase 0.
- **NO añadir dependencias externas** salvo que sea estrictamente necesario.
- **Tests contra fixtures reales**, no contra XML inventado.
- **Output optimizado para LLMs**: compacto, sin decoración innecesaria, información accionable.

## Validación

El script está bien si:
1. Con el fixture `hotspot.swift`, el resumen muestra `heavyWork` con ~70% y `lightWork` con ~30%
2. El output cabe en <200 líneas para un trace típico
3. No incluye frames de sistema que no son accionables (UIKit internals, libdispatch, etc.)
