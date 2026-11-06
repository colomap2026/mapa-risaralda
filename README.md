# Mapa interactivo de Risaralda

Mapa de los 14 municipios de Risaralda (Colombia). Al hacer clic en un municipio se levanta en 3D su lugar representativo y el resto de la página se desenfoca.

Para verlo, abre `risaralda.html` en un navegador. Es un solo archivo; solo usa internet para cargar la tipografía.

| Municipio | Lugar representativo |
|---|---|
| Pereira | Viaducto César Gaviria Trujillo |
| Dosquebradas | Mirador El Chaquiro |
| Santa Rosa de Cabal | Los Termales |
| Marsella | Casa de la Cultura y su ajedrez gigante |

Los demás municipios todavía no tienen estructura. Los modelos son ilustrativos y están muy ampliados respecto a la escala del mapa; la forma del mirador es genérica.

## Cómo modificarlo

No edites `risaralda.html` directamente: se genera a partir de `fuentes/`. Cambia `fuentes/template.html` y vuelve a generar la página con Python 3:

```
python -I fuentes/build.py fuentes/datos/zona.geojson risaralda.html fuentes/template.html fuentes/datos/osm.json
```

Para agregar un municipio, añade su modelo a `MODELOS` y su texto a `NOTAS` en la plantilla, y una capa `<g class="modelo3d">` dentro del mapa.

## Datos

- Límites municipales: DANE, vía [geoBoundaries](https://www.geoboundaries.org/) (2020). `zona.geojson` es un recorte alrededor de Risaralda.
- Vías, ríos, cerros y cascadas: © colaboradores de [OpenStreetMap](https://www.openstreetmap.org/copyright), licencia ODbL.
