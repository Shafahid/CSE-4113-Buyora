from fastapi import FastAPI

app = FastAPI(title="Buyora API")


@app.get("/")
async def root():
    return {"message": "Welcome to Buyora API"}
