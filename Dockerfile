# On reste sur une base moderne mais on va la nettoyer
FROM continuumio/miniconda3 AS builder

# 1. Installation de pythonocc et fastmcp en une seule étape + Nettoyage
# On force le canal conda-forge et on supprime les caches immédiatement
RUN conda install -y -c conda-forge \
    pythonocc-core \
    && pip install --no-cache-dir fastmcp \
    && conda clean -afy

# 2. Préparation de l'application
WORKDIR /app
COPY *.py ./

CMD ["python", "MCP_STEP.py"]