# sofer

**[English](README.md) | [Español](README_ES.md)**

> **Sofer** (en hebreo: סופר, «escriba») — una persona que transcribe
> meticulosamente textos sagrados. Esta herramienta aplica el mismo cuidado a la
> documentación de conjuntos de datos.

**sofer es tanto una herramienta de línea de comandos como un servidor Model
Context Protocol (MCP). Ambas interfaces convierten un conjunto de datos en
bruto en un paquete documentado, perfilado y evaluado en cuanto a calidad —
combinando inferencia automática con conocimiento humano, y publicable en
Hugging Face Hub o en cualquier directorio local.**

[![CI](https://github.com/emiliodavola/sofer/actions/workflows/ci.yml/badge.svg)](https://github.com/emiliodavola/sofer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python >=3.10](https://img.shields.io/badge/python-3.10%2B-3776AB)](pyproject.toml)

## Qué hace sofer

sofer cubre la distancia entre una carpeta de archivos en bruto y un conjunto de
datos reutilizable. Convierte datos tabulares, inspecciona el esquema, detecta
splits, perfila columnas, marca posible PII, genera un codebook y una Dataset
Card, y valida el resultado antes de entregarlo.

Está pensado para investigadores, responsables de datos y equipos que publican
conjuntos de datos, ya sea en Hugging Face Hub, en un object store o en un
directorio local.

**Principios:**

- **Automatizar observaciones; no inventar conocimiento semántico.** sofer marca
  una inferencia como conjetura, nunca como un hecho.
- **Confidencial por defecto.** Los repositorios son privados salvo que cambies
  explícitamente esa postura.
- **Validar antes de publicar.** Nunca entregar un conjunto de datos roto.
- **Flujo en dos pasos.** `prepare` construye sin red; `publish` entrega.
- **Perfilado de solo lectura.** `profile` nunca modifica el conjunto de datos
  de origen.
- **Agnóstico al dominio.** Sirve para censos, encuestas, planillas,
  colecciones de documentos y otras fuentes tabulares.

## Instalación

sofer no se publica en PyPI, así que instalarlo solo por nombre de paquete no
resuelve nada: se instala desde un tag de release en Git.

Tomá el tag de la última release — publicado en la
[página de releases](https://github.com/emiliodavola/sofer/releases/latest), o
impreso por un CLI `gh` autenticado:

```bash
gh release view --repo emiliodavola/sofer --json tagName --jq .tagName
# por ejemplo: v0.6.2
```

Después instalá ese tag, reemplazando `X.Y.Z`:

```bash
uv tool install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z" --force
```

Después verificá:

```bash
sofer --help
sofer --version
```

`sofer --version` coincide con el tag del release. Otras vías de instalación
soportadas:

```bash
pip install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"
pip install "sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"
uvx --from git+https://github.com/emiliodavola/sofer.git@vX.Y.Z --with "sofer[mcp]" sofer-mcp --help
```

**Actualizar.** El pin al tag es deliberado: `uv tool upgrade sofer` no mueve un
tag fijado a una release más nueva. Volvé a correr la instalación con el tag
nuevo — o el comando que resuelve la última release — con `--force`. Instalar
sin `@tag` sigue la punta de `main`, cuya versión es un build de desarrollo (por
ejemplo `0.6.2.dev7+g4de2c3d`), no una release.

Ver [alternativas de instalación](docs/getting-started.md#install) para la
comparación completa.

### Servidor MCP

La misma instalación incluye el servidor `sofer-mcp`. Registralo con un agente soportado —
`opencode`, `codex`, `gemini`, `pi`, `hermes` o `all`:

```bash
sofer mcp add --agent <agent>
```

El comando escribe la configuración MCP del host; `--scope` y `--cwd` controlan dónde. Ver
[configuración de agentes](docs/agent-setup.md) para el registro y [servidor MCP](docs/mcp.md)
para la superficie de tools.

## Inicio rápido

Ejecutá estos comandos desde el directorio del conjunto de datos.

```bash
# 1. Create the configuration and scaffold raw/
sofer init my-dataset --user myuser

# 2. Discover data files
sofer scan my-dataset.toml

# 3. Fill the human metadata step
sofer meta check my-dataset.toml
sofer meta set my-dataset.toml \
  --set description="<what the data contains>" \
  --set license="<license from the data owner>" \
  --set source="<source organisation>" \
  --set tags="<tag1>,<tag2>"

# 4. Build the package locally — no network calls
sofer prepare my-dataset.toml

# 5. Inspect the result in build/

# 6. Publish as a separate, explicit step
sofer publish my-dataset.toml --dry-run
sofer publish my-dataset.toml --target local --output ./out/   # no network
# or: sofer publish my-dataset.toml                            # Hugging Face Hub
```

> **`scan` mueve archivos.** La Fase 1 MUEVE los archivos sueltos soportados a
> `raw/`, preservando el árbol; la Fase 2 copia `raw/` a `cache/`. El movimiento
> mantiene las fuentes registradas en `raw/`, no solo en el `cache/` descartable.

> **La construcción local no es publicación.** `prepare` escribe el paquete en
> `build/` y nunca contacta Hugging Face. Inspeccioná y editá los artefactos
> antes de publicar.

> **Los repositorios son privados por defecto.** Un destino público es una
> decisión separada y requiere autorización explícita. Ver
> [Security](docs/security.md).

## Qué contiene el paquete

```text
build/                  prepare output; publish input
├── *.parquet           converted data (or originals with convert_to_parquet = false)
├── README.md           generated Dataset Card
├── LICENSE             generated from [meta] license
├── manifest.json       delivery record used by publish
├── codebook.md         root index, with --all-files
└── codebooks/          one page per file, with --all-files
```

El layout de origen es `raw/` → `cache/` → `build/`:

- `raw/` es la raíz de fuentes versionada.
- `cache/` es la caché de artefactos ignorada por git y usada por `scan`.
- `build/` es el directorio del paquete, configurable con `[dataset] build_dir`.

Formatos de entrada soportados: CSV (`.csv`), TSV (`.tsv`), Parquet
(`.parquet`), Excel (`.xlsx`) y JSON Lines (`.jsonl`). Ver
[Dataset configuration](docs/dataset-config.md#source-layout) y
[Data package](docs/data-package.md#supported-formats) para reglas de
conversión, limitaciones y splits.

## MCP para agentes de IA

sofer incluye un servidor Model Context Protocol por stdio con **19 tools**, **4
resources** y **3 prompts**. Expone el mismo pipeline determinista y no llama a
ningún LLM; el único acceso de red es la subida a Hugging Face dentro de
`sofer_publish_confirm`. `fastmcp` viene incluido por defecto, y `sofer[mcp]` es
un alias de la misma rueda.

Toda sesión MCP empieza con `sofer_init`, la única tool admitida mientras la
sesión no está inicializada. Adjuntá un conjunto de datos existente con
`config=...`, o creá uno con `name`/`user`/`cwd`; cualquier otra tool y toda
lectura de resources con datos se rechaza con `INITIALIZATION_REQUIRED` hasta
que esa llamada tenga éxito. El listado de tools y resources, los prompts
estáticos y `sofer://status` siguen disponibles sin init.

Usá `sofer mcp add --agent <opencode|codex|gemini|pi|hermes|all>` para
registrarlo. La cadena canónica es:

```python
# Session gate (adjunta un conjunto de datos existente; no escribe archivos)
sofer_init(config="my-dataset.toml")
# ...o creá un conjunto de datos desde cero:
# sofer_init(name="my-dataset", user="myuser", cwd="datasets/my-dataset")
# Phase 0 Bootstrap (solo greenfield)
sofer_scan_apply(config="my-dataset.toml")
sofer_meta_set(config="my-dataset.toml", values={"license": "<license>"})
# Phase 1 Build
sofer_validate(config="my-dataset.toml")
sofer_prepare(config="my-dataset.toml", output_dir=None, run_checks=True, force=False)
sofer_codebook_all(config="my-dataset.toml")
sofer_profile_all(config="my-dataset.toml")
sofer_render_all(config="my-dataset.toml")
# Phase 2 Publish
sofer_publish(config="my-dataset.toml", dry_run=True)
```

Ver [MCP server](docs/mcp.md) y [Agent setup](docs/agent-setup.md).

## Documentación

| Tarea | Leer |
| --- | --- |
| Alternativas de instalación, recorrido completo, paso de metadata | [Getting started](docs/getting-started.md) |
| Comandos, flags, `meta` y `mcp` | [CLI reference](docs/cli.md) |
| TOML del conjunto de datos, `[meta]`, `[[file]]`, `[[check]]`, `[[quality]]` | [Dataset configuration](docs/dataset-config.md) |
| Formatos, conversión, splits, calidad, codebooks, perfilado | [Data package](docs/data-package.md) |
| Defaults y precedencia de `[tool.sofer]` | [Tool-wide configuration](docs/configuration.md) |
| Tools, resources, prompts y contratos de respuesta MCP | [MCP server](docs/mcp.md) |
| Registro de agentes, entorno y timeouts | [Agent setup](docs/agent-setup.md) |
| Contención de rutas, approval phrase, credenciales | [Security](docs/security.md) |
| Windows, subidas al Hub y reportes de fallos | [Troubleshooting](docs/troubleshooting.md) |

## Contribución

La arquitectura, el setup de desarrollo, las convenciones y los quality gates
están en [CONTRIBUTING.md](CONTRIBUTING.md). Los pull requests son bienvenidos;
ver la [plantilla de PR](.github/PULL_REQUEST_TEMPLATE.md). Los reportes de
seguridad siguen [SECURITY.md](SECURITY.md).

## Relacionado

- [Leek group data sharing guide](https://github.com/jtleek/datasharing)
- [Hugging Face Hub documentation](https://huggingface.co/docs/hub/)
- [MIT License](LICENSE)
