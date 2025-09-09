#!/bin/bash
# Este script automatiza el proceso de actualización de traducciones.

echo "--- 1. Extrayendo textos de las plantillas (.pot)... ---"
pybabel extract -F babel.cfg -o messages.pot .

echo "--- 2. Actualizando el catálogo de inglés (.po)... ---"
pybabel update -i messages.pot -d translations -l en

# Si en el futuro agregas más idiomas, simplemente descomenta
# y adapta la siguiente línea. Por ejemplo, para francés:
# echo "--- 3. Actualizando el catálogo de francés... ---"
# pybabel update -i messages.pot -d translations -l fr

echo "--- 4. Compilando todos los catálogos (.mo)... ---"
pybabel compile -d translations

echo ""
echo "--- ¡Proceso completado! ---"
echo "Recuerda traducir cualquier texto nuevo que haya aparecido en: translations/en/LC_MESSAGES/messages.po"
