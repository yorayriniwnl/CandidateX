"""Synthetic golden codebases for precision testing of static code intelligence."""

import os


def create_golden_fastapi_repo(root_dir: str):
    """Creates a complete Python microservice repository structure."""
    os.makedirs(os.path.join(root_dir, "src", "domain"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "src", "services"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "src", "api"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "docs", "adr"), exist_ok=True)

    # pyproject.toml
    with open(os.path.join(root_dir, "pyproject.toml"), "w") as f:
        f.write("""[project]
name = "golden-fastapi-service"
version = "0.1.0"
dependencies = [
    "fastapi>=0.110.0",
    "sqlalchemy>=2.0.0",
    "torch>=2.0.0",
]
""")

    # src/api/routes.py
    with open(os.path.join(root_dir, "src", "api", "routes.py"), "w") as f:
        f.write("""from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter()

class UserPayload(BaseModel):
    username: str
    email: str

def get_auth_user():
    return {"user": "admin"}

@router.get("/users")
async def list_users(user = Depends(get_auth_user)):
    try:
        return [{"id": 1, "username": "alice"}]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
""")

    # src/services/user_service.py
    with open(os.path.join(root_dir, "src", "services", "user_service.py"), "w") as f:
        f.write("""class UserService:
    def __init__(self):
        pass

    async def get_user_by_id(self, user_id: int):
        return {"id": user_id}
""")

    # docs/adr/0001_database_choice.md
    with open(os.path.join(root_dir, "docs", "adr", "0001_database_choice.md"), "w") as f:
        f.write("""# 1. Selection of PostgreSQL for Event Storage

## Context
We require ACID transactions and JSONB indexing for multi-tenant analysis.

## Decision
We will use PostgreSQL with SQLAlchemy 2.0.

## Consequences
High consistency and mature ecosystem support.
""")

    # README.md
    with open(os.path.join(root_dir, "README.md"), "w") as f:
        f.write("""# Golden FastAPI Service

## Getting Started
Run `pip install -e .` and start with `uvicorn src.api.routes:router`.

## Architecture
```mermaid
graph TD
    API[FastAPI] --> Svc[UserService]
    Svc --> DB[(PostgreSQL)]
```
""")


def create_golden_polyglot_files(root_dir: str):
    """Creates sample TypeScript, Go, Java, and C++ files."""
    os.makedirs(os.path.join(root_dir, "ts"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "go"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "java"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "cpp"), exist_ok=True)

    # TypeScript / Express
    with open(os.path.join(root_dir, "ts", "server.ts"), "w") as f:
        f.write("""import express from "express";
import { z } from "zod";

const app = express();
const UserSchema = z.object({ name: z.string() });

app.get("/health", async (req, res) => {
    try {
        res.json({ status: "ok" });
    } catch (err) {
        res.status(500).send();
    }
});
""")

    # Go
    with open(os.path.join(root_dir, "go", "main.go"), "w") as f:
        f.write("""package main
import "net/http"

func handleRoot(w http.ResponseWriter, r *http.Request) {
    ch := make(chan int)
    go func() {
        ch <- 42
    }()
    val := <-ch
    _ = val
}

func main() {
    http.HandleFunc("/api", handleRoot)
}
""")

    # Java
    with open(os.path.join(root_dir, "java", "UserController.java"), "w") as f:
        f.write("""package com.example.demo;
import org.springframework.web.bind.annotation.*;
import org.springframework.stereotype.Service;

@RestController
@RequestMapping("/api/v1")
public class UserController {
    @GetMapping("/items")
    public String getItems() {
        return "items";
    }
}

@Service
class ItemService {}
""")

    # C++
    with open(os.path.join(root_dir, "cpp", "core.cpp"), "w") as f:
        f.write("""#include <memory>
#include <vector>
#include <algorithm>

void process() {
    auto ptr = std::make_unique<int>(10);
    std::vector<int> numbers = {3, 1, 4, 1, 5};
    std::sort(numbers.begin(), numbers.end());
}
""")
