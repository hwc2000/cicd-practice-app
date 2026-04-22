from fastapi import FastAPI

app = FastAPI(title="CI/CD Practice App")


@app.get("/")
def read_root():
    return {"message": "hello cicd"}


@app.get("/health")
def health_check():
    return {"status": "unhealthy"}

