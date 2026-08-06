from fastapi import FastAPI
from reports import router as reports_router

app = FastAPI(
    title="API Reportes Bingo",
    description="API de reportes para el sistema de Bingo Salvatore",
    version="1.0.0"
)

# Incluir router de reportes
app.include_router(reports_router)

# Endpoint raíz
@app.get("/")
def raiz():
    return {
        "mensaje": "API de Reportes Bingo - Funcionando",
        "documentacion": "/docs"
    }