#!/bin/bash

PROJECT_NAME="DetectionDatasetAnnotator"
PACKAGE_NAME="detection_dataset_annotator"
PACKAGE_PARENT_PATH="../src"
DOCS_PATH="./tmp-out"

mkdir -p $DOCS_PATH

# --- 1. Cria docs com sphinx-quickstart não interativo ---
sphinx-quickstart $DOCS_PATH \
    -q \
    -p $PROJECT_NAME \
    -a "Fernando Pujaico Rivera" \
    --sep \
    --makefile \
    --batchfile

# --- 2. Ajusta conf.py ---
CONF_FILE="$DOCS_PATH/source/conf.py"
if [ -f "$CONF_FILE" ]; then
    # Define tema ReadTheDocs
    sed -i "s/html_theme = 'alabaster'/html_theme = 'sphinx_rtd_theme'/" $CONF_FILE

    # Ativa autodoc e napoleon
    sed -i "s/extensions = \[/extensions = \['sphinx.ext.autodoc', 'sphinx.ext.napoleon', /" $CONF_FILE
else
    echo "Erro: conf.py não encontrado em $CONF_FILE"
    exit 1
fi

echo "Sphinx configurado para autodoc, napoleon e tema ReadTheDocs."


# --- 2.1 Adiciona modules.rst ao toctree do index.rst ---
INDEX_FILE="$DOCS_PATH/source/index.rst"
if [ -f "$INDEX_FILE" ]; then
    # Adiciona "modules" ao final do toctree se ainda não estiver presente
    grep -qxF "   modules" "$INDEX_FILE" || sed -i "/.. toctree::/a\\
   modules
" "$INDEX_FILE"
fi

# --- 3. Gera arquivos .rst para todos os módulos do pacote ---
sphinx-apidoc -o $DOCS_PATH/source $PACKAGE_PARENT_PATH/$PACKAGE_NAME

# --- 4. Build HTML ---
cd $DOCS_PATH
make clean
PYTHONPATH=../../src make html

echo "Documentation created in $DOCS_PATH/build/html/index.html"

