# Mapa interactivo de Risaralda

Mapa de los 14 municipios de Risaralda (Colombia). Al hacer clic en un municipio se levanta en 3D su lugar representativo y el resto de la página se desenfoca.

Para verlo, abre `risaralda.html` en un navegador. Es un solo archivo; solo usa internet para cargar la tipografía.

| Municipio | Lugar representativo |
|---|---|
| Pereira | Viaducto César Gaviria Trujillo |
| Dosquebradas | Mirador El Chaquiro |
| Santa Rosa de Cabal | Los Termales |
| Marsella | Casa de la Cultura y su ajedrez gigante |
| La Virginia | Estatua del Caballero Gaucho |
| Belén de Umbría | Parroquia Santa Rosa de Lima |
| Apía | Museo Alboín Gómez |
| Balboa | El Balcón Florido |
| Guática | Jardín Botánico |
| La Celia | Parque principal |
| Santuario | Parque Nacional Natural Tatamá y sus frailejones |
| Quinchía | Museo Tierras de Xixarca |
| Pueblo Rico | Plaza principal y Alcaldía |
| Mistrató | Avistamiento de aves (Bangsia aurinegra) |

Los modelos son ilustrativos y están muy ampliados respecto a la escala del mapa. Las ubicaciones son reales; varias formas son aproximadas porque no se encontraron descripciones del lugar (ver los comentarios de cada modelo en `fuentes/template.html`).

## Cómo modificarlo

No edites `risaralda.html` directamente: se genera a partir de `fuentes/`. Cambia `fuentes/template.html` y vuelve a generar la página con Python 3:

```
python -I fuentes/build.py fuentes/datos/zona.geojson risaralda.html fuentes/template.html fuentes/datos/osm.json
```

El relieve del mapa es la imagen `img/relieve.png`. Si cambia la zona del mapa, vuelve a generarla (si faltan datos de elevación, el script imprime las direcciones de las teselas que hay que descargar en `fuentes/datos/dem/`):

```
python -I fuentes/relieve.py fuentes/datos/zona.geojson fuentes/datos/dem img/relieve.png
```

Para agregar un municipio, añade su modelo a `MODELOS` y su texto a `NOTAS` en la plantilla, y una capa `<g class="modelo3d">` dentro del mapa.

## Datos

- Límites municipales: DANE, vía [geoBoundaries](https://www.geoboundaries.org/) (2020). `zona.geojson` es un recorte alrededor de Risaralda.
- Relieve: [Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) de AWS (zoom 11), derivadas de SRTM (NASA) y otras fuentes abiertas.
- Vías, ríos, cerros y cascadas: © colaboradores de [OpenStreetMap](https://www.openstreetmap.org/copyright), licencia ODbL.
